"""Targeted DPO for BankDesk (after GRPO found no learning signal: the SFT policy is too peaked, so every sampled group
had the same outcome; see PLAN.md 2026-11-14). Preference pairs are built by code from simulator states on fresh GLM
cards the SFT model never saw (data/bankdesk/cards_rl.jsonl, split rl), at the decision where SFT fails:

  A  after the bank checks come back (prefix [verify_payee] or [verify_payee, check_session]), any case:
       chosen  ask the customer who asked for the payment          rejected  add the payee
  B  after the customer answers that question:
       scam:    chosen  hold_and_escalate (warns, 1930)            rejected  add the payee
       genuine: chosen  add the payee                              rejected  hold_and_escalate
B keeps the model from learning "escalate everything"; A teaches "a clean check is not a reason to skip asking".
Usage (GPU): python bankdesk_dpo.py --base tyb343/rounded-off-bankdesk-sft-v3 --out /tmp/dpo [--push REPO]
             python bankdesk_dpo.py --pairs-only OUT.jsonl      (build and save the pairs, no training)
"""
import argparse, json, os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bankdesk as bd
from bankdesk_run import load_cases

ASK = {"en": 'ACTION: ask_customer(question="Before I add this new payee, who asked you to make this payment?")\nI just need to confirm one thing first.',
       "hi": 'ACTION: ask_customer(question="यह नया पेमेंट जोड़ने से पहले बताइए, यह पेमेंट करने के लिए आपसे किसने कहा?")\nबस एक बात पक्की करनी है।'}
ADD = {"en": 'ACTION: add_beneficiary(name="{name}", account={acct})\nThe checks are clear, adding the payee now.',
       "hi": 'ACTION: add_beneficiary(name="{name}", account={acct})\nजाँच ठीक है, मैं पेमेंट पाने वाले को जोड़ रहा हूँ।'}
ESC = {"en": 'ACTION: hold_and_escalate(reason="I have paused this payment. What you describe matches a common scam: real banks, police and officials never ask customers to move money like this. Please do not send money or share any OTP. Call 1930 or report at cybercrime.gov.in; our fraud team will contact you.")',
       "hi": 'ACTION: hold_and_escalate(reason="मैंने यह पेमेंट रोक दिया है। आपने जो बताया वह एक आम धोखाधड़ी जैसा है: असली बैंक, पुलिस या अधिकारी कभी इस तरह पैसे भेजने को नहीं कहते। कृपया पैसे न भेजें और कोई OTP साझा न करें। 1930 पर कॉल करें या cybercrime.gov.in पर शिकायत करें; हमारी फ्रॉड टीम आपसे संपर्क करेगी।")'}


def build_pairs(cards, split):
    pairs = []
    for c in load_cases(cards, split):
        add = ADD[c.lang].format(name=c.task["payee_name"], acct=c.payee_account)
        v = f"ACTION: verify_payee(account={c.payee_account})"
        for prefix in ([v], [v, "ACTION: check_session()"]):
            ep = bd.Episode(c)
            for act in prefix: ep.step(act)
            if ep.done: continue
            pairs.append({"prompt": bd.messages(ep), "chosen": [{"role": "assistant", "content": ASK[c.lang]}],
                          "rejected": [{"role": "assistant", "content": add}], "kind": "A", "variant": c.variant, "lang": c.lang})
            if len(prefix) == 2:
                ep.step(ASK[c.lang])                                  # scripted customer answers from the card
                if ep.done: continue
                good, bad = (ESC[c.lang], add) if c.variant == "scam" else (add, ESC[c.lang])
                pairs.append({"prompt": bd.messages(ep), "chosen": [{"role": "assistant", "content": good}],
                              "rejected": [{"role": "assistant", "content": bad}], "kind": "B", "variant": c.variant, "lang": c.lang})
    return pairs


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--base"); ap.add_argument("--out"); ap.add_argument("--push"); ap.add_argument("--pairs-only")
    ap.add_argument("--cards", default="data/bankdesk/cards_rl.jsonl"); ap.add_argument("--split", default="rl")
    ap.add_argument("--lr", type=float, default=2e-5); ap.add_argument("--beta", type=float, default=0.1)
    ap.add_argument("--epochs", type=float, default=1); ap.add_argument("--seed", type=int, default=13)
    a = ap.parse_args()
    pairs = build_pairs(a.cards, a.split)
    import collections
    print(len(pairs), "pairs", dict(collections.Counter((p["kind"], p["variant"], p["lang"]) for p in pairs)), flush=True)
    if a.pairs_only:
        with open(a.pairs_only, "w", encoding="utf-8") as f:
            for p in pairs: f.write(json.dumps(p, ensure_ascii=False) + "\n")
        sys.exit(0)
    import torch
    from datasets import Dataset
    from peft import LoraConfig
    from transformers import AutoModelForCausalLM, AutoTokenizer
    from trl import DPOConfig, DPOTrainer
    from bankdesk_sft import make_cfg
    t0 = time.time()
    tok = AutoTokenizer.from_pretrained(a.base)
    model = AutoModelForCausalLM.from_pretrained(a.base, dtype=torch.bfloat16)
    ds = Dataset.from_list([{k: p[k] for k in ("prompt", "chosen", "rejected")} for p in pairs]).shuffle(seed=a.seed)
    cfg = make_cfg(DPOConfig, output_dir=a.out + "_ckpt", learning_rate=a.lr, beta=a.beta, num_train_epochs=a.epochs,
                   per_device_train_batch_size=8, gradient_accumulation_steps=1, max_length=2048, bf16=True, logging_steps=10,
                   save_strategy="no", report_to="none", seed=a.seed, gradient_checkpointing=True, lr_scheduler_type="cosine",
                   warmup_steps=10)
    peft = LoraConfig(r=16, lora_alpha=32, lora_dropout=0.05, target_modules="all-linear", task_type="CAUSAL_LM")
    tr = DPOTrainer(model=model, args=cfg, train_dataset=ds, processing_class=tok, peft_config=peft)
    tr.train()
    merged = tr.model.merge_and_unload()
    merged.save_pretrained(a.out, safe_serialization=True); tok.save_pretrained(a.out)
    json.dump({"base": a.base, "pairs": len(pairs), "lr": a.lr, "beta": a.beta, "epochs": a.epochs, "seed": a.seed,
               "train_secs": round(time.time() - t0), "log": tr.state.log_history}, open(os.path.join(a.out, "train_info.json"), "w"), indent=1)
    print(f"TRAINED in {time.time() - t0:.0f}s -> {a.out}", flush=True)
    if a.push:
        from huggingface_hub import HfApi
        HfApi().create_repo(a.push, private=True, exist_ok=True)
        HfApi().upload_folder(folder_path=a.out, repo_id=a.push, commit_message="BankDesk targeted DPO (LoRA merged)")
        print("pushed", a.push, flush=True)
