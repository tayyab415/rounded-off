# Agentic payments and the rails under them

Research note for BankDesk v4, compiled 2026-11-15. Sources are dated in the list at the end. Vendor statements are marked "vendor claim". If I saw only a search snippet and not the page itself, the source entry says so.

## 1. Schemes and protocols at a glance

| Scheme / protocol | Owner | Date | How permission is granted | Limits and scope | Auth still required | Dispute / liability |
|---|---|---|---|---|---|---|
| UPI Reserve Pay, formerly single-block-multiple-debit | NPCI | Jul 2024; OC-228, FY2025-26 [3][12] | Customer creates one block per merchant; NPCI treats it as a mandate [3] | ≤₹10,000, ≤90 days, one block per merchant, verified low-ticket merchants. A debit must follow a customer purchase action [3] | No PIN per debit; issuer validates each one [3][30] | Online dispute resolution; alerts on create, debit, revoke, expiry [3] |
| UPI Circle, extended to software and "AI profiles" by OC-201B | NPCI | Aug 2024; 2025-10-08 [6] | Primary links a secondary user or device with 2FA, devices close together [6] | ₹15,000/month, ₹5,000/txn, ₹5,000 in first 24 hours, max 5 devices, P2M only. AI profiles in a closed user group [6][12] | Debits "only initiated by explicit user action" [12] | Online dispute resolution [6] |
| AutoPay and all e-mandates | RBI | 2026-04-21 [2] | One-time registration with additional factor of authentication (AFA) | No AFA up to ₹15,000 per debit; ₹1 lakh for insurance, mutual funds, card bills [2] | AFA at registration, first debit, changes, revocation, opt-out [2] | 24-hour pre-debit notice; customer liability rules apply [2] |
| Unified Agent Protocol | NPCI | Reported Sep 2026, on hold [7][33] | Rule-based instructions on Circle and Reserve Pay; agent registry [33][35] | Reserve Pay caps "may be revisited" [33] | Not public | Liability framework planned, not disclosed [33][35] |
| Razorpay Agentic Payments, ChatGPT and Claude | Razorpay, NPCI, OpenAI, Anthropic | 2025-10-09; 2026-02-20 [27][30] | One-time spending limit per merchant on Reserve Pay [30] | Closed pilot; Axis Bank, Airtel Payments Bank [27][30] | No repeated PIN, vendor claim [30] | Not stated |
| Pine Labs P3P | Pine Labs | 2026-06-11 [31] | One upfront UPI mandate; Grantex handles identity and spend controls [31] | Pre-approved limits, revocable [31] | None per payment, vendor claim [31] | Not stated [32] |
| Visa Intelligent Commerce, Trusted Agent Protocol | Visa | 2025-04-30; 2025-10-14 [39][40] | Consumer sets limits; tokens bound to one agent and use [39][41] | Spend limits, merchant categories, approval thresholds [41] | Passkeys; agent signs each request, merchant checks Visa's registry [40] | Shared signals "help manage disputes" [39]; agent-error disputes not explained [40] |
| Mastercard Agent Pay | Mastercard | 2025-04-29; India Feb 2026 [29][42] | Registered agents use agentic tokens [42] | Budgets, categories, time windows [43] | Passkeys, device biometrics [42][43] | "Verifiable Intent" record feeds "Agentic Disputes" [43] |
| AP2 | Google, donated to FIDO Alliance | 2025-09-16 [44][45] | Signed Intent Mandate, then Cart Mandate [44] | Price limits, timing, conditions in the intent [44] | User signs cart if present; otherwise agent builds it from the intent [44] | Audit trail only [44] |
| ACP and ChatGPT Wallet | OpenAI, Stripe | API version 2026-01-30 [46] | Delegated token with an allowance [46] | `one_time`, `max_amount`, `merchant_id`, `expires_at` [46] | User approves each purchase in ChatGPT [47] | Merchant owns fraud and support [47] |
| PayPal agent ready | PayPal | 2025-10-28 [49] | PayPal wallet | Not stated | Normal PayPal checks | Buyer protection applies, vendor claim [49] |
| Stripe Issuing for agents | Stripe | Private preview [50] | Card issued per agent | Single-use cards, period limits, category allowlist [50] | Issuer's real-time approval [50] | Not stated |
| Amex ACE kit | American Express | 2026-04-14 [51] | Agent registration plus cardmember enrolment and intent [51] | Registered agents only | Tokenised credential [51] | Amex refunds the cardmember when a registered agent errs [51] |

OpenAI moved from in-chat Instant Checkout to merchant-run checkout by April 2026 [48].

## 2. India: the rules in force

Authentication. Every domestic digital payment needs two factors, one of them dynamic, from 2026-04-01. If a loss comes from a payment that broke these rules, the issuer repays it in full. Issuers may add risk-based checks. Recurring e-mandate debits after the first are exempt [1]. UPI accepts on-device biometrics instead of the PIN up to ₹5,000. A PIN reset disables biometrics [4].

Limits. P2P UPI is ₹1 lakh a day. Since 2025-09-15, listed P2M categories allow ₹5 lakh per payment and ₹10 lakh a day [8]. UPI Lite is ₹1,000 per payment with a ₹5,000 balance [9]. UPI 123PAY is ₹10,000 per payment [10]. Since 2025-08-01 a UPI app allows 50 balance checks a day, and AutoPay debits run outside peak hours [11].

E-mandates. The 2026 framework keeps the ₹15,000 and ₹1 lakh no-AFA ceilings. It requires a 24-hour pre-debit notice naming merchant, amount, date and mandate reference. One clause matters for scams: "Payments under e-mandates shall not be subject to any other limits / controls set by the customer" [2].

Agentic work. The ChatGPT pilot ran on Reserve Pay [27]. NPCI's own AI tools help customers and do not move money. UPI HELP, live 2025-10-08, checks status, logs complaints, and pauses or revokes mandates by deep-linking to the UPI app's confirmation screen. NPCI says "all the decision making shall be done either by the customer and/or the Issuer bank" [5]. MyUPI, shown in September 2026, adds payee context before approval and automated chargebacks [36]. Reuters reported a Unified Agent Protocol and an agent registry that month [33][35]. MIT SMR India, citing Business Standard, says the launch is on hold pending regulatory clearance [7]. The NPCI circular index showed no circular on it on 2026-11-15 [37].

Fraud and liability. RBI says account takeover is now rare and most fraud is "authorised push payment", where victims "themselves initiate and authenticate transactions". India recorded 28 lakh frauds worth ₹22,931 crore in 2025. Transfers above ₹10,000 were 45% of cases and 98.5% of value [13]. RBI's April 2026 discussion paper proposed [13]:
- a one-hour hold, cancellable by the payer, on account-to-account transfers of ₹10,000 or more, with merchant payments, mandates and whitelisted payees exempt;
- a "trusted person" co-approver above ₹50,000 for customers aged 70+ and persons with disabilities;
- a ₹25 lakh yearly credit cap on accounts without enhanced checks;
- per-mode on/off switches and a kill switch, which mandates may bypass.

Comments closed 2026-05-08. Banks asked for a ₹25,000 threshold [16]. I found no final rule.

The revised liability rules, issued 2026-06-24, apply from 2027-01-01 [17][18]. A payment the customer approved "under coercion or duress from the third-party" now counts as fraud. The bank must prove customer liability. SMS alerts are compulsory above ₹500. A victim who loses up to ₹50,000 gets 85% of the net loss, capped at ₹25,000, once in a lifetime, if they report to the bank and to 1930 or the cybercrime portal within five days [18][19].

Toolkits. Razorpay's official MCP server serves merchants. It creates orders and payment links but only reads payouts, and it leaves refunds off the remote server [38]. Cashfree's agent MCP takes over a chat at payment time using Reserve Pay [28]. I found no first-party PhonePe or Paytm agent toolkit, and no current NPCI source for "Hello UPI".

## 3. Money-movement tools a bank agent could expose

- `get_balance`, `get_transactions(from, to)`, `get_statement(month)`. Read-only.
- `add_payee(name, account|VPA, IFSC, rail)` returns `pending`. Banks set activation delays and first-window caps. SBI activates after 1 hour, or 4 hours for IMPS payees, then caps the first 4 days at ₹5 lakh in total. It will not activate a payee "over phone call/e-mail" [22]. HDFC activates after 30 minutes and caps the first 24 hours at ₹50,000 [23]. Kotak caps them at ₹25,000 [24].
- `transfer(from, payee_id, amount, rail, purpose)` needs AFA [1] and returns `pending_cancellable` if the proposed one-hour hold applies [13].
- `create_standing_instruction(payee, max_amount, frequency, end)` follows the e-mandate rules: AFA at setup and first debit, 24-hour notice, per-debit opt-out [2].
- `create_reserve(merchant, amount ≤ 10000, expiry ≤ 90d)` and `revoke_reserve` [3].
- `delegate(secondary, monthly ≤ 15000, per_txn ≤ 5000)` and `revoke_delegation` [6].
- `set_limit(mode, daily)` and `toggle_mode(mode)`. SBI lets customers change the transfer limit online at any time, up to ₹25 lakh a day [22]. I found no Indian rule that delays a raised limit.
- `freeze_digital_payments()` turns on instantly. Turning it off needs strict checks or a branch visit [13].
- `close_fd(fd_id, full|partial)`. Banks must allow early withdrawal on individual deposits of ₹1 crore or less. Interest is paid for the period actually run, and nothing under the 7-day minimum. An undisclosed penalty cannot be charged [20]. SBI's posted penalty is 0.5% up to ₹5 lakh and 1% above, on a page last updated in 2019 [21]. Sweep-in breaks FD units, usually the newest first [25].
- `convert_to_emi(card_txn, tenure)` must show principal, interest and discount before conversion [26]. I did not research pay-later rules.
- `report_fraud(txn_ids)` blocks further debits, points to 1930, and starts the five-day clock [18].
- `manage_mandate(id, action)` deep-links to the customer's UPI app, as UPI HELP does [5].

## 4. Risks

- Coached victims. RBI says victims now approve the fraud payments themselves [13]. Moneylife notes a one-hour hold does little against "digital arrest" scams that run for days [15]. RBI expects fraudsters to talk victims into whitelisting payees [13].
- Prompt injection. Unit 42 describes a hidden instruction on a deals site that adds a gift card for the attacker to the cart. A user shown only the total approves it [52].
- Agent spoofing. Visa built TAP because merchants cannot tell agents from bots [40]. Mastercard warns that "someone is building an agent designed to look exactly like the good ones" [43].
- Mandate abuse. E-mandate debits ignore customer limits [2], and the kill switch may exempt them [13].
- Misread intent. An agent can stay inside its limits and still get the request wrong, and "agents will look statistically abnormal by design" to fraud models [7]. Fed Governor Waller said fraud systems "calibrated to human behavior" may not carry over [55].
- Weaker protection. NatWest, Bank of America, ING and three other banks warned that agents may type card details into websites or steer users to weaker payment methods [53].
- Unclear liability. Waller asked "who is on the hook if an agent makes the wrong purchase?" [55]. In the US, handing an agent your card can count as consent [54]. Amex covers registered agents [51]. India's registry will list agents, but a source told Reuters liability needs regulation [35]. RBI Deputy Governor Jain said risk duty stays with the firm when a vendor supplies the model [34].

## 5. Design implications for BankDesk v4

- Give every money tool a mandate-shaped argument: payee, max amount, expiry, scope, purpose, consent reference. AP2, ACP and Reserve Pay all use this shape [3][44][46], and the scorer can check action against consent.
- Split request from settlement. Transfers of ₹10,000 or more to non-whitelisted payees return `pending_cancellable` for one hour [13]. Make the threshold configurable so ₹25,000 can be tested too [16].
- Payees start `pending`, with a 30-minute to 4-hour delay and a first-window cap from ₹25,000 to ₹5 lakh [22][23][24]. The agent cannot activate a payee from chat, as at SBI [22]. This slows the add-payee-then-transfer pattern the v3 cards cluster on.
- The agent never holds the second factor. Tools return `otp_sent` and the customer confirms in their own app [1]. A customer reading out an OTP, or asking the agent to skip it, is a scam signal.
- Confirmation shows payee name, account, amount and items, not a single total [52]. Score whether the agent reads them back correctly.
- Treat limit raises and whitelisting mid-chat as high risk, since RBI expects scammers to push for both [13]. A delay on raised limits would be a BankDesk choice, not a rule.
- Add `freeze_digital_payments` as a cheap safe action [13] and `report_fraud` with the five-day clock [18].
- Add mandate tools with real caps: Reserve Pay at ₹10,000 and 90 days, AutoPay at ₹15,000 without AFA, Circle at ₹5,000 and ₹15,000 [2][3][6]. New scam cards: a "verification mandate" to a fake merchant, or delegation to a "helper".
- `close_fd` quotes the penalty and lost interest before it runs [20][21]. "Break your FD" is a scam step, and the quote gives the agent a reason to pause.
- Add a vulnerable-customer card flag: age 70+ or disability, with a trusted-person approval above ₹50,000 [13].
- Log one audit record per action: agent ID, customer instruction, consent reference, checks run. This mirrors Verifiable Intent, TAP and NPCI's registry [35][40][43], and R2 can read it.
- Price losses with the 2027 rules. The bank carries the burden of proof, and a coached victim's loss up to ₹50,000 earns at most 85% or ₹25,000 back [18]. That gives a cost-weighted R1 split between customer and bank.
- Treat P2P as final and P2M as disputable. RBI exempts merchant payments from the hold because they already have dispute channels [14].
- Keep irreversible tools gated. Razorpay's MCP leaves payout creation out [38], and UPI HELP hands mandate changes back to the customer's app [5].

## Sources

1. RBI, Authentication mechanisms for digital payment transactions Directions, 2025-09-25. https://www.rbi.org.in/Scripts/NotificationUser.aspx?Id=12898
2. RBI, Digital Payments – E-mandate Framework, 2026, 2026-04-21. https://rbi.org.in/scripts/FS_Notification.aspx?Id=13374&fn=9&Mode=0
3. NPCI, UPI OC-228/2025-26, Enhancements in UPI Reserve Pay, FY2025-26, no date printed. https://www.npci.org.in/uploads/UPI_OC_No_228_FY_2025_26_Enhancement_in_UPI_Single_Block_Multiple_Debits_UPI_Reserve_Pay_a9095c181d.pdf
4. NPCI, UPI OC-226/2025-26, Additional authentication methods in UPI, FY2025-26, no date printed. https://www.npci.org.in/uploads/UPI_OC_No_226_FY_2025_26_Introduction_of_Additional_Authentication_methods_in_UPI_42c3693399.pdf
5. NPCI, UPI OC-227/2025-26, UPI HELP pilot, 2025-10-08. https://www.npci.org.in/uploads/UPI_OC_No_227_FY_2025_26_Introduction_of_UPI_HELP_Assistant_pilot_an_AI_powered_support_for_UPI_payments_cd501de8f3.pdf
6. Khaitan & Co, ERGO: Enabling agentic payments on UPI rails, on NPCI OC-201B, 2025-11-20. https://www.khaitanco.com/sites/default/files/2025-11/ERGO%20-%20Enabling%20Agentic%20Payments%20%20on%20UPI%20Rails%20-%2020%20November%202025.pdf
7. MIT Sloan Management Review India, India's agentic payment push leaves liability unclear, 2026-09-22. https://mitsloanindia.com/article/indias-agentic-payment-push-leaves-liability-unclear/
8. DD News, UPI P2M limit up to ₹10 lakh a day, 2025-09-15. https://ddnews.gov.in/en/npci-raises-daily-upi-payment-limit-on-p2m-transactions-to-%E2%82%B910-lakh/
9. RBI, Amendment to framework for small value digital payments in offline mode, UPI Lite, 2024-12-04. https://rbi.org.in/Scripts/BS_CircularIndexDisplay.aspx?Id=12752
10. Inc42, RBI increases transaction limits for UPI123Pay, UPI Lite, 2024-10-09. https://inc42.com/buzz/rbi-increases-transaction-limits-for-upi123pay-upi-lite
11. The Week, UPI changes from August 1, 2025-08-01. https://www.theweek.in/news/biz-tech/2025/08/01/major-upi-changes-from-august-1-here-is-the-full-list-of-balance-enquiry-limits-pending-payment-status-upi-security-and-more-from-npci.html
12. tomcn.uk, personal blog quoting OC-201B and OC-228, 2026-09-02. https://tomcn.uk/news/2026-09-02-npci-uap-upi-circle-agentic-payments
13. RBI, Discussion paper: Exploring safeguards in digital payments to curb frauds, 2026-04-09. https://rbidocs.rbi.org.in/rdocs/Publications/PDFs/DP090420261ED5D6E68D724A6EA870B7E68E45F80F.PDF
14. Reuters via Yahoo Finance, India mulls payment lags, checks for senior citizens, 2026-04-09. https://finance.yahoo.com/economy/policy/articles/indias-central-bank-mulls-delay-135740570.html
15. Moneylife, RBI's proposed digital payment safeguards, 2026-04-15. https://www.moneylife.in/article/rbis-proposed-digital-payment-safeguards-what-do-they-mean-for-you/80218.html
16. Angel One, Banks support RBI 1-hour delay, seek ₹25,000 threshold, 2026-05-15. https://www.angelone.in/news/economy/banks-support-rbi-proposal-for-1-hour-digital-payment-delay-seeks-25-000-threshold-limit
17. RBI press release, Amendment directions on limiting customer liability, 2026-06-24. https://www.rbi.org.in/scripts/BS_PressReleaseDisplay.aspx?prid=63011
18. RBI, Commercial Banks – Responsible Business Conduct Third Amendment Directions, 2026, 2026-06-24, effective 2027-01-01. https://www.rbi.org.in/Scripts/NotificationUser.aspx?Id=13543&Mode=0
19. Inc42, RBI's digital fraud compensation rules, 2026-06-25. https://inc42.com/buzz/rbis-digital-fraud-compensation-rules-victims-to-get-up-to-₹25000/
20. RBI, Commercial Banks – Interest Rate on Deposits Directions, 2025, 2025-11-28, updated 2026-10-01. https://rbi.org.in/scripts/BS_ViewMasDirections.aspx?id=13157
21. SBI, Term deposits, SME page, last updated 2019-11-29. https://sbi.bank.in/web/business/sme/sme-fixed-deposits/term-deposits
22. SBI, FAQs on new beneficiary addition, undated, read 2026-11-15. https://www.onlinesbi.sbi/sbijava/new_ben_add_faq_0.html
23. HDFC Bank, Funds transfer to other bank, undated, read 2026-11-15; the ₹50,000 cap is from the search snippet of this page. https://www.hdfc.bank.in/money-transfer/add-a-beneficiary/funds-transfer-to-other-bank
24. Kotak Mahindra Bank, Transaction limits for beneficiaries, undated, read 2026-11-15. https://kotak.com/en/help-center/bill-payment-and-recharge/manage-beneficiaries/what-are-transaction-limits-while-sending-money-to-the-beneficiary.html
25. IndusInd Bank blog, How sweep-in works, undated. https://www.indusind.bank.in/iblogs/fixed-deposit/how-sweep-in-works-which-deposit-breaks-first-and-why-it-matters-for-your-returns/
26. Legal500, summary of RBI Credit and Debit Card Directions 2022, 2022-06-17; I did not read the RBI text. https://www.legal500.com/intelligence/india/finance-and-banking/master-directions-%E2%80%93-credit-cards-and-debit-cards-%E2%80%93-issuance-and-conduct-directions-2022
27. Reuters, India rolls out pilot for e-commerce payments via ChatGPT, 2025-10-09. https://www.reuters.com/world/india/indias-payments-authority-razorpay-launch-ai-led-payments-chatgpt-2025-10-09/
28. Cashfree Payments, Agentic Payments press release, 2025-10-09, vendor. https://www.cashfree.com/news-room/cashfree-payments-becomes-one-of-the-first-fintechs-in-india-to-unveil-agentic-payments-bringing-end-to-end-ai-commerce-inside-chat/
29. Mastercard India, First authenticated agentic commerce transaction in India, Feb 2026, vendor. https://www.mastercard.com/news/ap/en-in/newsroom/press-releases/en-in/2026/february/mastercard-demonstrates-readiness-for-a-new-era-of-ai-powered-payments-in-india-with-its-first-authenticated-agentic-commerce-transaction/
30. Razorpay blog, Agentic Payments for UPI on Claude, 2026-02-20, vendor. https://razorpay.com/blog/agentic-payments-and-npci/
31. Pine Labs, P3P launch press release, 2026-06-11, vendor. https://www.pinelabs.com/media-analyst/the-ai-agent-can-now-pay-pine-labs-launches-p3p-indias-first-agentic-payment-protocol-built-on-upi
32. Medianama, How NPCI should approach agentic payments, opinion, 2026-07-10. https://www.medianama.com/2026/07/223-npci-agentic-payments-upi/
33. Reuters, India preparing rollout of agentic payments on UPI, 2026-09-01. https://www.reuters.com/world/india/india-preparing-rollout-agentic-payments-upi-sources-say-2026-09-01/
34. Business Today, RBI DG Rohit Jain on safeguards at GFF 2026, 2026-09-09. https://www.businesstoday.in/industry/banks/story/heres-what-rbi-dg-rohit-jain-said-on-need-for-more-safeguards-at-gff-2026-554404-2026-09-09
35. Reuters, India plans AI registry as it looks to roll out agentic payments, 2026-09-10. https://www.reuters.com/world/india/india-plans-ai-registry-it-looks-roll-out-agentic-payments-sources-say-2026-09-10/
36. Indiantelevision, NPCI unveils UPI Tap & Pay and MyUPI at GFF 2026, 2026-09-12. https://indiantelevision.com/mam/npci-unveils-upi-tap-pay-and-ai-powered-myupi-at-gff-2026/
37. NPCI, UPI circulars index, read 2026-11-15. https://www.npci.org.in/circulars/upi
38. Razorpay, official MCP server README, GitHub, read 2026-11-15. https://github.com/razorpay/razorpay-mcp-server
39. Visa, Find and buy with AI: Visa unveils new era of commerce, 2025-04-30. https://usa.visa.com/about-visa/newsroom/press-releases.releaseId.21361.html
40. VentureBeat, Visa launches Trusted Agent Protocol, 2025-10-14. https://venturebeat.com/ai/visa-just-launched-a-protocol-to-secure-the-ai-shopping-boom-heres-what-it
41. Visa Perspectives, Visa and OpenAI partnership, 2026-06-10. https://corporate.visa.com/en/sites/visa-perspectives/innovation/visa-openai-partnership.html
42. Mastercard, Mastercard unveils Agent Pay, 2025-04-29. https://newsroom.mastercard.com/news/press/2025/april/mastercard-unveils-agent-pay-pioneering-agentic-payments-technology-to-power-commerce-in-the-age-of-ai
43. Mastercard, Trust for agentic commerce, white paper, Sep 2026. https://www.mastercard.com/content/dam/mccom/shared/news-and-trends/stories/2026/trust-for-agentic-commerce-white-paper/Trust%20for%20agentic%20commerce%20white%20paper.pdf
44. Google Cloud blog, Announcing Agent Payments Protocol, 2025-09-16. https://cloud.google.com/blog/products/ai-machine-learning/announcing-agents-to-payments-ap2-protocol
45. AP2 project site, notes v0.2 and FIDO Alliance donation, read 2026-11-15. https://ap2-protocol.org/
46. Agentic Commerce Protocol, Delegate payment API reference, API version 2026-01-30. https://agenticcommerce.dev/docs/reference/payments
47. OpenAI developer docs, Commerce: accept payments with ChatGPT Wallet, read 2026-11-15. https://developers.openai.com/commerce/specs/payment
48. Checkout.com, OpenAI's agentic commerce shift, 2026-04-20, vendor. https://checkout.com/blog/openai-agentic-commerce-shift
49. PayPal newsroom, PayPal launches agentic commerce services, 2025-10-28, vendor. https://newsroom.paypal-corp.com/2025-10-28-PayPal-Launches-Agentic-Commerce-Services-to-Power-AI-Driven-Shopping
50. Stripe docs, Issuing for agents, private preview, read 2026-11-15. https://docs.stripe.com/issuing/agents
51. Digital Commerce 360, American Express launches developer kit and purchase protection for agentic commerce, 2026-04-14. https://www.digitalcommerce360.com/2026/04/14/american-express-agentic-commerce-developer-kit-purchase-protection/
52. Palo Alto Networks Unit 42, Retail fraud and agentic AI, 2026-03-20, vendor research. https://unit42.paloaltonetworks.com/retail-fraud-agentic-ai/
53. Reuters via The Star, Banks warn AI shopping bots raise scam, fraud and data-privacy risks, 2026-09-22. https://www.thestar.com.my/tech/tech-news/2026/09/22/banks-warn-ai-shopping-bots-raise-scam-fraud-and-data-privacy-risks
54. NerdWallet, Can you get your money back if an AI agent makes a financial mistake?, 2026-09-29. https://www.nerdwallet.com/credit-cards/news/ai-agent-makes-mistake
55. Federal Reserve, Governor Waller, Payments in the age of AI agents, 2026-09-28. https://www.federalreserve.gov/newsevents/speech/waller20260928a.htm
