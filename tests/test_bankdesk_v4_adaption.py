"""Tests for the Adaption test-wording step (scripts/bankdesk_v4_adaption.py). No network."""
import copy, json, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import bankdesk_v4 as g
import bankdesk_v4_env as e
import bankdesk_v4_words as W
import bankdesk_v4_adaption as A


def test_task_is_the_nebius_writer_task_and_hides_the_story():
    for i in range(100):
        w = g.sample_world(f"test-{i}"); lang = W.assign_lang(w["id"]); t = A.task_text(w, lang)
        sys_part, task = t.split(A.TASK_HEADER)
        assert sys_part == W.WRITER_SYSTEM and task == W.writer_task(w, e.case_facts(w), lang)
        w2 = copy.deepcopy(w); w2["story"] = {"truth": "genuine" if w["story"]["truth"] == "scam" else "scam", "kind": "x", "coaching": 0}
        assert A.task_text(w2, lang) == t
        assert not any(x in task.lower() for x in ("scam", "genuine", "coach"))


def test_rows_link_back_to_their_world():
    rows = A.task_rows(["test-3", "test-4"]) + A.task_rows(["test-3"], attempt=1)
    idx = {r["task"]: (r["world_id"], r["attempt"], r["lang"]) for r in rows}
    assert A.link({"world_id": "test-3", "original_prompt": rows[0]["task"]}, idx)[:2] == ("test-3", 0)
    assert A.link({"original_prompt": rows[2]["task"]}, idx)[:2] == ("test-3", 1)
    # whitespace or a lightly edited system part still links by the STYLE line and the account number
    edited = rows[1]["task"].replace("You write test data", "You write data") + "\n"
    assert A.link({"enhanced_prompt": edited}, idx)[:2] == ("test-4", 0)
    assert A.link({"original_prompt": "something else"}, idx)[0] is None


def test_shift_regime_tasks_and_rows_carry_the_shift_hash():
    base = g.params_hash(); old = g.REGIME
    try:
        g.set_regime("shift"); sh = g.params_hash(); assert sh != base
        t = A.task_rows(["shift-0"])[0]
        assert t["world_hash"] == sh and t["regime"] == "shift"
        w = g.sample_world("shift-0"); assert A.to_row(w, t["lang"], 0, {"opening": "x", "answers": {}}, "f")["world_hash"] == sh
        assert t["task"] == A.task_text(w, t["lang"])
        # a task file of the other regime is refused, so rows cannot be checked against the wrong worlds
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            g.set_regime("base"); json.dump(A.task_rows(["shift-1"])[0], open(os.path.join(d, "tasks_x.jsonl"), "w"))
            g.set_regime("shift")
            try: A.task_index(d); assert False, "should refuse"
            except SystemExit: pass
    finally:
        g.set_regime(old)
    assert g.params_hash() == base


def test_row_format_and_harness():
    w = next(w for w in (g.sample_world(f"test-{i}") for i in range(300)) if w["records"]["call"] != "none")
    f = e.case_facts(w); code = W.ref_code(w["id"]); gave = W.text_labels(w)["reference"] == "gave_reference"
    op = f"Hello, pay Rs {f['amount']:,} to {f['payee']}, a/c {f['account']}." + (f" It is {f['company']}." if f["company"] and f["company"] not in f["payee"] else "") \
         + (f" Contact {f['phone']}." if f["phone"] else "")
    obj = {"opening": op, "answers": {k: "No." for k in W.FIELD_ORDER} | {"reference": f"Code {code}." if gave else "I have no bill.", "purpose": "For my order."}}
    row = A.to_row(w, "en", 0, obj, "out_x.jsonl")
    assert row["writer"] == "adaption" and row["reviewer"] == W.DEEPSEEK and row["world_hash"] == g.params_hash()
    assert set(row) >= {"id", "lang", "opening", "answers", "writer", "reviewer", "world_hash"} and set(row["answers"]) == set(W.FIELD_ORDER)
    assert W.code_checks(row, w) == []
    ep = e.Episode(w, words=row)
    assert row["opening"] in ep.observation0()
