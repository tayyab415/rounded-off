# Deployed bank assistants: what they actually handle

Researched 2026-11-15. Undated bank pages are marked "accessed 2026-11-15". "Vendor claim" and "company claim" mean nobody independent checked the number. The source list flags sources I saw only as search summaries.

## 1. Summary table

| Assistant | Bank | Country | Channels | Languages | Can act on | Inform or route only | Handoff | Numbers, with date |
|---|---|---|---|---|---|---|---|---|
| EVA | HDFC Bank | India | Website | English, Hindi, voice search [1] | Book FD, pay card bill, reissue debit card, close loan on card [1] | Product info, loan and card statements, EMI summary [1] | Not stated [1] | None published |
| WhatsApp Chat Banking | HDFC Bank | India | WhatsApp | Hindi, English, Hinglish voice notes [2] | 225+ services in 19 product lines, FD booking [2] | Alerts, "Connect to RM" [2] | Bots plus human agents for complex queries [2] | 1 crore 30-day actives, 2 crore 90-day actives, Mar 2026 [2] |
| AHA! 2.0 | Axis Bank | India | Website, mobile app | English, Hindi, voice input [3] | PIN change, card deactivation, cheque book, stop cheque, e-statement signup, card spend to EMI [3] | Balance, mini statement, card transactions, customer ID, offers [3] | Page says type "connect to an agent"; FAQ says it cannot connect to an executive [3] | 20M queries, 97% "accuracy", undated vendor claim [4] |
| Ask iPal | ICICI Bank | India | Net banking, iMobile, website | Not stated | None listed on current page [5] | NRI queries, account opening [5] | "Instant connection" to customer care [5] | None found |
| Keya | Kotak Mahindra | India | Phone IVR voicebot, chat | English, Hindi [6] | Not verified | Routes calls inside IVR [6] | Human agent if unresolved [6] | Response time down up to 50%, 2018 vendor claim [6] |
| SIA; YONO Ji | SBI | India | Web, 2017; YONO Business, 2026 [7][8] | Not stated | None confirmed | Product, feature and service guidance [7] | Not stated | 864M queries/day was a capacity claim, not usage, 2017 [8] |
| Support bots | PhonePe | India | In-app self-serve, chatbot, voicebot, IVR [9] | Hindi, Tamil, others [9] | In-flow fixes for login and Autopay issues [9] | Product Q&A for funds, insurance, cards [9] | Human agent gets AI summary of history [9] | 92% resolved without humans, CSAT 70%, Jul 2026 [9]; 94% of support, 80% of fraud investigations automated, Sep 2026 [10] |
| Ask Google Pay; Help chatbot | Google Pay | India | App | 10 Indian languages [12] | None | Spending insights, finance education [12]; Help bot interviews fraud reporters [13] | Not stated | Scam detection up 21%, Dec 2025, company claim [13] |
| MyUPI | NPCI, in BHIM app | India | App | English, Hindi, Telugu, Tamil, Bengali [14] | Raise and track complaint, pause/cancel Autopay, de-link UPI number, block a linked bank account, replay a payment with fresh UPI PIN [14] | Payee name check, scam-message help [14] | Not stated | Launched Sep 2026, no usage data |
| Erica | Bank of America | US | Mobile app only [19] | English only [19] | Lock/unlock debit card, replace card, start dispute, Zelle send/request, schedule bill payments [19][20] | Transaction search, spending, routing numbers, proactive insights [19] | Specialist by phone or chat when it can't answer [19] | 20.6M users, ~700M interactions in 2025; 3.2B total, Mar 2026 [18] |
| Eno | Capital One | US | SMS, app, web, email [21] | Not stated | None stated on current page [21] | Balance, alerts on surprising charges [21] | "Not a channel for disputes or errors" [21] | None |
| Fargo | Wells Fargo | US | Mobile app, voice and text [23] | English, Spanish [22] | Zelle, bill pay, transfers [22][23] | Routing numbers, balances, spending [22] | Design keeps no human in the loop; handoff not described [23] | 1B+ interactions, Mar 2026; 3M Spanish users, 160M interactions [22] |
| Cora / Cora+ | NatWest | UK | App, web | English | Top queries include stopping a transaction, address change, ordering a card [24] | Statements, ISA setup, spending chat in beta [24][25] | Agent receives AI summary [24] | 12.9M conversations in 2025 [25] |
| Messaging + routing agent | CommBank | Australia | App messaging [27] | English | Not specified | Routes simple queries to AI, sensitive ones to humans [27] | Human with AI summary [27] | 84.6% of self-service messaging resolved end-to-end, May 2026 [27] |
| Joy; digibot | DBS | Singapore, HK, Taiwan | IDEAL platform; app [28][29] | Not stated | Joy: "selected banking requests" in Singapore; digibot plans card block/replace, fee waivers [29] | Payment tracking, transaction and fee questions [29] | Auto-connect to specialist with co-pilot [28] | 120k pilot chats, CSAT +23%, Nov 2025 [28] |
| Blue | BBVA | Spain | App [30] | Not stated | "Common account and card transactions" [30] | 150 queries and transactions in total [30] | Cancel or ask for a human at any point [30] | None |
| Finn | bunq | Netherlands, EU | App [31] | 38 app languages, speech translation [31] | Runs checks on failed payments and disputes [31] | Receipts, documents [31] | Not stated | 80%+ of tickets automated, vendor case study [31] |
| AI Support; AIR | Revolut | UK, EU | App, voice in some countries [32] | Not stated | Disputed: see notes [32][33] | Spending, investments, travel [32][33] | Type "live agent" any time; auto-redirect [32] | None |
| Assistant; Pix via AI | Nubank | Brazil | App, WhatsApp [35] | Portuguese | Pix by text, audio or image [35] | Not stated | Up to 5 automated turns, then escalate [34] | 2M WhatsApp testers, Dec 2024 [35] |
| AI assistant | Klarna | Global | App [36] | 35+ languages [36] | Refunds, returns, cancellations, disputes [36] | Balances, payment schedule [36] | Live agent on request [36] | 2.3M chats, two-thirds of volume, Feb 2024 [36] |
| Ops Agent | Monzo | UK | App chat [38] | English | Find a missing refund, order a replacement card [38] | Answers from vetted knowledge base [38] | Any tripped guardrail goes to a human [38] | 150+ intents [38] |
| Starling Assistant | Starling | UK | App, voice via keyboard [39] | English | Set up savings goals with automatic transfers, organise bill payments [39] | PIN, new card, scam guidance [39] | Specialist support for vulnerable customers [39] | None |

## 2. Notes per assistant

**Erica.** Erica does not use generative AI. It matches the request to one of 700+ pre-written responses [17][19]. Bank of America says 98% of users find the information they need [17]. Disputes start in Erica but follow fixed rules: only posted transactions, usually within 60 days of the statement, and the bank suggests calling the merchant first [20]. Erica can also book an appointment as a handoff to human staff [17].

**Fargo.** Wells Fargo transcribes speech on the device, strips personal data with a small model, and only then sends text to an LLM. That LLM extracts the intent and the entities and nothing else; bank systems execute the action [23]. The sources disagree on Spanish. VentureBeat says Spanish is over 80% of usage [23]. The bank's own figures, 160M Spanish interactions out of 1B+, imply about 16% [22]. I trust the bank's numbers.

**Eno.** Capital One's page tells customers Eno is not a channel for disputes or errors, and lists a phone number instead [21]. Older press says Eno issues virtual card numbers. The current page does not mention them, so I left that out.

**Klarna.** The 2024 launch claimed the work of 700 agents and resolution in under 2 minutes against 11 before [36]. In May 2025 the CEO said cost had been "a too predominant evaluation factor" and the result was "lower quality". Klarna went back to hiring human agents [37].

**Revolut.** Its June 2026 notice says customers "will not be able to place, modify, or cancel any order ... nor take any other action that would result in you entering into a transaction" through the AI assistants [32]. TNW's launch story lists "card management" and eSIM purchases for AIR [33]. I could not reconcile the two. The notice is the binding document.

**Monzo.** The closest public match to BankDesk. The LLM agent triages each case to respond, hand off or close. It started read-only, with a human approving every message, later cut to QA sampling. It now resolves missing refunds end to end and is adding card replacement for fraud victims [38]. Showing transaction history only when the intent needed it raised resolution on transaction queries by 10 points. Testing uses LLM-simulated customers grounded in real chats and a stateful tool simulation, where blocking a card changes what later calls return [38].

**NatWest.** The bank named Cora's top queries in 2024: stopping a transaction, updating a home address, requesting a statement, ordering a new card, setting up an ISA [24]. In February 2026 it said agentic Cora will let customers "report and resolve fraud related cases in real time" [26]. I found no launch confirmation.

**DBS.** DBS says its assistants "will execute only customer-initiated instructions" [29]. The retail bot's planned action list is short: card usage, reward points, fee waivers, blocking or replacing cards [29].

**Nubank.** Pix over WhatsApp was capped at R$200 per transfer and R$2,000 a day during testing, below the app's limits [35]. The announcement does not describe a confirmation step [35].

**SBI.** I found no verified consumer GenAI assistant. YONO Ji, launched July 2026, serves YONO Business users, and the coverage describes guidance only [7].

**PhonePe.** The approach is "DIY first". The app detects the problem inside the payment flow, and bots handle what remains [9]. The 80% figure for fraud investigations is back-office automation, not a chatbot [10]. Paytm's 2026 AI push, Pi, is a B2B product for banks and insurers [11]; I could not verify any figure for Paytm's own support bot.

**Google Pay and NPCI.** Ask Google Pay is opt-in and gives information only [12]. Google's Help chatbot interviews users who report fraud and turns the answers into scam intelligence [13]. NPCI's MyUPI, launched September 2026, does more than any bank bot I found. It raises complaints with a reference number, pauses or cancels mandates, checks payee names, and blocks a linked bank account through a "Safety Switch" [14]. Its October 2025 predecessor, UPI Help, covered payments, mandates and disputes [15].

**Not verified.** Erica in Spanish; current Eno virtual card numbers; Axis AHA! 2.0 accuracy and escalation figures from an award listing; Kotak's Gupshup volumes; bunq's "97% of support" figure; Paytm's monthly query count; SBI WhatsApp and Bhashini features.

## 3. Common task list

Ordered by how many of the assistants above list each task, highest first within each group.

**Look up.** Account balance [3][19][21][22]. Transaction search or mini statement [3][19][29]. Card statement and dues [1][3][36]. Account details such as routing number or customer ID [3][19][22]. Status of a complaint, refund or card delivery [3][14][19][20]. Spending by category or payee [12][19][25][39].

**Fix.** Failed payment or missing refund [9][14][31][38]. Dispute a transaction [19][20][31][36]. Stop a cheque or a transaction [3][24]. Fee waiver [29]. PIN change [3].

**Move money.** Pay a bill [1][19][22][39]. Send to a person by Zelle, Pix or UPI [19][22][35][14]. Move money to own savings pots [39]. Book a fixed deposit [1][2]. Convert a card purchase to EMI [3].

**Change account.** Address or email update [24]. Order cheque book or new card [3][24]. Register for e-statements [3]. Pause or cancel an Autopay mandate [14]. De-link a UPI number [14].

**Protect.** Lock or unlock a card [3][19][29]. Replace a lost or stolen card [19][38]. Block a bank account [14]. Report fraud [13][26][38]. Scam advice [14][39]. Check payee name before paying [14].

**Route.** Connect to a human, a relationship manager, or book an appointment [2][17][19][30][32].

## 4. Design implications for BankDesk v4

- **Most tools should read; few should write.** Erica answers from fixed responses [19], Revolut's AI may not start any transaction [32], and Eno refuses disputes [21]. Give BankDesk a wide read side and a short write list. The skill being scored is choosing between them.
- **Split write tools into "protect" and "move money".** Banks let bots lock or replace a card, block an account, or pause a mandate [14][19][29]. Money movement is gated and capped [35]. Protect tools should be cheap and reversible. Money tools should run only on a customer instruction, as DBS requires [29], and after a step-up check.
- **Model step-up authentication as a tool.** Real bots ask for registered mobile plus last four card digits [1], login [3][19], or a fresh UPI PIN [14]. A `verify_customer` or `request_otp` result should gate write tools. Some simulated customers should fail or refuse it.
- **Add per-channel limits.** Nubank capped WhatsApp Pix below app limits [35]. A rupee cap on chat makes "split it into smaller payments" a visible red flag.
- **Treat handoff as a scored action.** Nearly every assistant above offers one. The CFPB names "doom loops" with no way to a human as a core harm [40], Klarna reversed course [37], and RBI's FREE-AI committee says customers must be able to reach a human [41]. Reward handoff when warranted. Penalise refusing a second explicit request for a human. Require a short case summary on handoff, as PhonePe, NatWest and DBS do [9][24][28].
- **Make complaints and failed UPI payments first-class.** RBI requires a failed-but-debited UPI transfer to reverse by T+1, with ₹100 per day compensation after that [16]. Add `raise_complaint` that returns a reference number, `check_complaint_status`, and transaction states such as pending, failed-debited and reversed. Copy Erica's dispute rules: posted transactions only, within a time window [20].
- **Fraud: open a case, block, escalate, promise nothing.** Live bots take reports and give guidance [13][39]. Investigation stays with humans or back-office systems [10][38]. An agent that promises a refund on a scam report should lose points.
- **Hindi means Hinglish, in WhatsApp-sized turns.** HDFC added Hinglish voice notes on WhatsApp, its biggest chat channel [2]. Google Pay covers 10 languages and MyUPI 5 [12][14]. Simulated customers should code-mix, send short messages, and write amounts in lakh and crore.
- **Scope the data each tool returns.** Monzo gained 10 points by showing history only when the intent needed it [38]. Prefer `get_transactions(payee, days)` over dumping the account.
- **Size the intent list like a real bank.** Monzo sees 150+ intents [38], BBVA covers 150 [30], and NatWest's top five are mundane [24]. A v4 list of 20 to 30 intents, weighted toward look-ups, covers the head of a real distribution.
- **Do not reward containment.** Vendor "accuracy" and containment are not resolution [4][27]. PhonePe pairs 92% automation with 70% CSAT [9], and Klarna's cost focus lowered quality [37]. Score correct outcomes and unsafe actions, not deflection.
- **Cite Monzo as precedent.** Monzo tests its live agent with LLM-simulated customers and a stateful tool simulation [38], the same design as BankDesk.

## 5. Sources

1. HDFC Bank, "EVA ChatBot", https://www.hdfc.bank.in/ways-to-bank/digital-banking/eva-chatbot , undated, accessed 2026-11-15.
2. Goa Plus News, HDFC Bank WhatsApp Chat Banking milestone, https://goaplusnews.com/?p=12919 , 13 May 2026.
3. Axis Bank, "Axis AHA!", https://www.axis.bank.in/bank-smart/axis-aha , undated, accessed 2026-11-15.
4. Gupshup case study via casestudies.com, "Axis Bank's AI-powered bot Aha! handled 20M queries with 97% accuracy", https://www.casestudies.com/company/gupshup/case-study/axis-banks-ai-powered-bot-aha-handled-20m-queries-with-97-accuracy , undated. Vendor claim; seen as search snippet only.
5. ICICI Bank, "Ask iPal", https://www.icici.bank.in/nri-banking/ask-ipal-demo , undated, accessed 2026-11-15.
6. Nuance, Kotak Keya launch, https://news.nuance.com/2018-05-17-Kotak-Mahindra-Banks-Taps-Nuance-to-Launch-its-AI-Powered-Virtual-Voice-Assistant-Keya , 17 May 2018. Vendor claim; search summary only.
7. Morung Express / IANS, "SBI launches YONO upgrades, new AI capabilities on 71st Bank Day", https://morungexpress.com/sbi-launches-yono-upgrades-new-ai-capabilities-on-71st-bank-day , 1 Jul 2026.
8. Business Wire / Payjo, "Payjo Powered SBI SIA", https://www.businesswire.com/news/home/20170925005726/en/Payjo-Powered-SBI-SIA-Revolutionizes-AI-Banking-Industry , 25 Sep 2017. Vendor claim; search summary only.
9. PhonePe Tech Blog, "How AI-Driven Automation is Scaling PhonePe's Customer Support Framework", https://tech.phonepe.com/how-ai-driven-automation-is-scaling-phonepes-customer-support-framework/ , 13 Jul 2026.
10. Complete AI Training, "PhonePe automates 94% of customer support and 80% of fraud investigations", https://completeaitraining.com/news/phonepe-automates-94-of-customer-support-and-80-of-fraud/ , 10 Sep 2026.
11. PaymentExpert, "AI agents to unlock new value and revenue for Paytm?", https://paymentexpert.com/2026/09/09/paytm-ai-agent-upgrade-business-clien/ , 9 Sep 2026.
12. Google India Blog, "Introducing Ask Google Pay, and expanding everyday credit", https://blog.google/intl/en-in/products/explore-communicate/introducing-ask-google-pay-and-expanding-everyday-credit/ , 29 Jul 2026.
13. Google India Blog, "Google Pay: Advancing Payments, Credit, and Commerce in India", https://blog.google/intl/en-in/products/explore-communicate/google-pay-advancing-payments-credit-and-commerce-in-india/ , 17 Dec 2025.
14. Business Today, "BHIM app gets MyUPI AI assistant", https://www.businesstoday.in/latest/economy/story/bhim-app-gets-myupi-ai-assistant-with-247-multilingual-upi-support-key-features-explained-557091-2026-09-22 , 22 Sep 2026.
15. Business Today, "RBI rolls out AI-based UPI HELP ... at GFF 2025", https://www.businesstoday.in/personal-finance/news/story/rbi-rolls-out-ai-based-upi-help-iot-payments-new-credit-features-at-gff-2025-497393-2025-10-08 , 8 Oct 2025. Search summary only.
16. Reserve Bank of India, circular RBI/2019-20/67 on TAT and compensation for failed transactions, https://www.rbi.org.in/Scripts/NotificationUser.aspx?Id=11693 , 20 Sep 2019.
17. Bank of America newsroom, "Erica Surpasses 3 Billion Client Interactions", https://newsroom.bankofamerica.com/content/newsroom/press-releases/2025/08/a-decade-of-ai-innovation--bofa-s-virtual-assistant-erica-surpas.html , 20 Aug 2025.
18. Bank of America via PR Newswire / Barchart, "BofA AI and Digital Innovations Fuel 30 Billion Client Interactions", https://www.barchart.com/story/news/665679/bofa-ai-and-digital-innovations-fuel-30-billion-client-interactions , 10 Mar 2026.
19. Bank of America, "Erica, your virtual financial assistant", https://info.bankofamerica.com/en/digital-banking/erica , undated, accessed 2026-11-15.
20. Bank of America, "How to Dispute a Charge", https://www.bankofamerica.com/help/how-to-dispute-a-charge/ , undated, accessed 2026-11-15.
21. Capital One, "Eno", https://www.capitalone.com/digital/tools/eno/ , undated, accessed 2026-11-15.
22. Wells Fargo newsroom, "Wells Fargo Reaches Major Digital Milestones", https://newsroom.wf.com/news-releases/news-details/2026/Wells-Fargo-Reaches-Major-Digital-Milestones/default.aspx , 26 Mar 2026.
23. VentureBeat, "Wells Fargo's AI assistant just crossed 245 million interactions", https://www.venturebeat.com/ai/wells-fargos-ai-assistant-just-crossed-245-million-interactions-with-zero-humans-in-the-loop-and-zero-pii-to-the-llm , 8 Apr 2025.
24. NatWest Group, "NatWest launches Cora+", https://www.natwestgroup.com/news-and-insights/news-room/press-releases/data-and-technology/2024/jun/natwest-launches-cora-plus-the-latest-generative-ai-upgrade-to-t.html , 10 Jun 2024.
25. NatWest Group, "Tech, data and AI", https://www.natwestgroup.com/who-we-are/about-natwest-group/tech-data-and-AI.html , 2026 page with 2025 figures.
26. FStech, "Thousands of NatWest customers to soon have access to agentic financial assistant", https://www.fstech.co.uk/fst/Thousands_Of_NatWest_Customers_To_Soon_Have_Access_To_Agentic_Financial_Assistant.php , 17 Feb 2026.
27. iTnews, "CBA to take AI orchestration agent beyond its retail bank", https://www.itnews.com.au/news/cba-to-take-ai-orchestration-agent-beyond-its-retail-bank-627249 , 10 Jul 2026.
28. DBS newsroom, "DBS rolls out Gen AI-powered chatbot to all corporate clients", https://www.dbs.com/newsroom/DBS_rolls_out_Gen_AI_powered_chatbot_to_all_corporate_clients , 10 Nov 2025.
29. iTnews Asia, "DBS enables AI assistants with agentic capabilities", https://www.itnews.asia/news/dbs-enables-ai-assistants-with-agentic-capabilities-to-support-banking-tasks-627732 , 28 Jul 2026.
30. BBVA, "BBVA will offer AI-powered account and card management with its virtual assistant", https://www.bbva.com/en/innovation/for-the-first-time-in-spain-bbva-will-offer-ai-powered-account-and-card-management-with-its-virtual-assistant/ , 14 Feb 2025.
31. Anthropic customer story, "bunq", https://claude.com/customers/bunq , undated, 2026 footer. Vendor case study.
32. Revolut, "Understanding how Revolut's AI Assistants use your personal data", https://cdn.revolut.com/terms_and_conditions/pdf/revolut_s_ai_assistant_c305e066_1.0.2_1781775214_en.pdf , 18 Jun 2026 per file metadata.
33. The Next Web, "Revolut launches its new AI assistant AIR to UK customers", https://thenextweb.com/news/revolut-launches-its-new-ai-assistant-air-to-uk-customers , 10 Apr 2026.
34. The Paypers, "Nubank partners with OpenAI", https://thepaypers.com/fintech/news/nubank-partners-with-openai-in-order-to-elevate-customer-experience , 10 Mar 2025.
35. Nubank newsroom, "Nubank leverages AI to scale Pix operations", https://nu.com/en/newsroom/consumers/nubank-leverages-ai-to-scale-pix-operations , 10 Dec 2024.
36. Klarna, "Klarna AI assistant handles two-thirds of customer service chats in its first month", https://www.klarna.com/international/press/klarna-ai-assistant-handles-two-thirds-of-customer-service-chats-in-its-first-month/ , 27 Feb 2024.
37. Finextra, "Klarna takes foot off AI gas as CEO acknowledges importance of human customer service", https://www.finextra.com/newsarticle/45956/klarna-rethinks-ai-customer-service-push-as-as-ceo-acknowledges-value-of-human-touch , 9 May 2025.
38. Monzo blog, "Engineering the Future of Customer Operations: The Monzo Ops Agent", https://monzo.com/blog/engineering-the-future-of-customer-operations-the-monzo-ops-agent , 4 Jun 2026.
39. Starling Bank, "Starling launches UK's first Agentic AI financial assistant", https://www.starlingbank.com/news/starling-launches-agentic-ai-assistant/ , March 2026; the page shows no date, and TNW dates the launch to 20 Mar 2026.
40. CFPB, "Chatbots in consumer finance", https://www.consumerfinance.gov/data-research/research-reports/chatbots-in-consumer-finance/chatbots-in-consumer-finance/ , 6 Jun 2023.
41. S.S. Rana & Co., "The FREE AI framework", https://ssrana.in/articles/the-free-ai-framework-regulating-ai-in-financial-sector/ , 27 Aug 2025, summarising the RBI FREE-AI report of 13 Aug 2025. Primary RBI text not checked.
