# Fraud controls at the moment of a payment or account change

Researched 2026-11-15. Undated pages are marked "accessed 2026-11-15". "Company claim" and "vendor claim" mean nobody independent checked the number. Sources marked "(summary only)" were seen as search-result text, not read in full.

## 1. Control table

| Control | Where used | When it fires | What the customer sees | Evidence or cost |
|---|---|---|---|---|
| Payee name check | UK CoP since 2020 [5]; Australia from Jul 2025 [5][18]; EU VoP from 9 Oct 2025 [21]; India RTGS/NEFT from 1 Apr 2025 [25] | Customer enters a new payee | "Match", "close match", "no match" or "other" [21]; India shows the core-banking name [25] | UK: misdirected payments down 59%, some fraud losses down 20-40% (Pay.UK author) [5]. CBA NameCheck stopped est. A$40m of scam payments in FY24 (company claim) [16]. A plausible name can still mislead. A Zelle scammer's account was named "Coned Billing" [23] |
| Warnings and purpose questions | UK banks [10][9]; Australian draft bank code makes "targeted warnings" mandatory [20] | Starling: "a large payment to someone new" [10] | Warning screen; questions about the payment | UK victims who ignore relevant warnings can lose reimbursement [1]. One provider found extra approval screens may cut payment completion [1] |
| Payment delay up to 4 business days | UK, from Oct 2024 [3] | Bank has "reasonable grounds to suspect", more than speculation, by end of next business day [3] | Told of the delay, the reason and what the bank needs, by end of next business day [3] | Must pay as soon as resolved; bank owes any interest and charges the delay causes [3]. Delays are among the controls UK PSPs added since 2023 [1] |
| In-call and screen-share check | Android pilot in most big UK banks, US, India, Brazil [6]; ANZ Plus active call status and screen-share protect [18] | Bank app opened while screen sharing on a call with an unsaved number [6] | Warning, one-tap "end call", 30-second wait [6] | "Thousands" of calls ended (company claim) [6]. ANZ: customers keeping defaults were 19x less likely to be scammed (bank claim, self-selected) [18] |
| Caller verification | Monzo call status [7]; CBA CallerCheck [16]; India 1600 numbers for bank calls [43] | Someone calls claiming to be the bank | App shows whether the bank is really on the line [7] | CallerCheck used 3.8m times in FY24 [16] |
| ML scam interruption | Revolut, Feb 2024 [8]; Starling assistant, Jun 2026 [9] | Model scores a payment as a likely scam | Payment declined, then guided questions; Starling suggests a call with staff [8][9] | Revolut: card investment-scam losses down 30% (company claim) [8] |
| Telco risk signals | UK Scam Signal, rolled out Nov 2024 [15]; India FRI, May 2025 [31] | At payment, on the payer's or payee's number | Delay, warning or decline [15][31] | Vodafone pilot: detection up 30% (claim) [15]. PhonePe declines "Very High" FRI numbers [31] |
| New-payee and new-device limits | Indian banks [37][38][39]; Bank of Ireland UK (summary only) [49] | First hours after adding a payee or registering UPI | Wait 30 min to 4 h; capped amounts | No public effect data found |
| Staff-to-police escalation | UK Banking Protocol, branch and phone [12][13] | Staff suspect pressure or coaching | Discreet questions; police attend, sometimes at home [12] | £59m stopped in 2025 (UK Finance) [13] |
| Self-lock "kill switch" | ANZ Digital Padlock, Aug 2025 [18]; proposed by RBI [26] | Customer triggers it | Digital access and cards locked until verified [18] | None published |
| Refund rules that drive all of the above | UK PSR, Oct 2024, cap £85,000 [1]; EU impersonation refund (deal Nov 2025) [22]; Australia SPF, duties from 31 Mar 2027 [20]; India, from 1 Jan 2027 [28] | After a loss | Refund, subject to caution tests | UK APP losses over Faster Payments down ~21% (£73m a year); refund rate 54% to 65% [1][2] |

Scale, for context. UK APP losses rose 19% to £576.4m in 2025 while impersonation ("safe account") losses fell 12% [4]. Australians reported A$2.18bn lost in 2025, up 7.8% on 2024 but 29.7% below the 2022 peak [19]. Westpac credits name checks, crypto payment blocks, branded in-app calls and a behavioural remote-access tool [17].

US note. The CFPB dropped its Zelle case in March 2025; New York's suit over missing safeguards survived a motion to dismiss on 20 Jul 2026 [23][24]. No US federal APP refund rule exists that I could find.

## 2. India: rules and dates

In force:
- RTGS/NEFT name lookup. Circular of 30 Dec 2024, live by 1 Apr 2025, on net banking, mobile banking and at branches [25]. UPI apps must show the bank-registered payee name from 30 Jun 2025 (summary only) [42].
- UPI P2P "collect" requests ended by 1 Oct 2025 (NPCI circular of 29 Jul 2025) [41].
- New UPI registration: Rs 5,000 cap for the first 24 hours on Android [39]. Axis says iOS gets Rs 25,000 over the first 120 hours [38].
- New payee. HDFC has a 30-minute cooling period plus 30 more minutes with SMS and email alerts [37] and a Rs 50,000 cap for 24 hours (summary only) [37]. Axis caps Rs 30,000 (net banking) or Rs 50,000 (app) for 24 hours, and Rs 5,000 for payees added within 24 hours of app onboarding [38]. No single RBI number exists; each bank sets its own.
- SIM change: telcos block SMS for 24 hours, which stops OTPs and UPI re-binding [40].
- Authentication Directions, 25 Sep 2025, compliance by 1 Apr 2026. Banks may add checks beyond two factors based on "location, user behaviour patterns, device attributes, historical transaction profile" [30].
- DoT Financial Fraud Risk Indicator, 21 May 2025. Mobile numbers are rated Medium, High or Very High from cybercrime reports, Chakshu and bank data. One UPI app added delays with confirmations [31].
- I4C. To 30 Jun 2026, CFCFRMS (the 1930 system) saved Rs 11,158 crore across 32.8 lakh complaints. The Suspect Registry (since 10 Sep 2024) holds 32.08 lakh layer-1 mule accounts and declined Rs 25,698 crore of payments [32].
- MuleHunter.AI was in 23 banks in Dec 2025 (summary only) [36] and 26 by Mar 2026 [29]. IDPIC was set up on 16 Oct 2025 to run the Digital Payments Intelligence Platform [29], which returns hashed "risk context" to member banks [35].
- NPCI piloted a federated model with four banks, mixing bank customer scores (age, occupation) with NPCI transaction and device scores, and an alert before paying flagged accounts [34].

Coming:
- Liability. Directions dated 24 Jun 2026 apply from 1 Jan 2027. A payment the customer approved "under coercion or duress" now counts as fraudulent. A victim losing up to Rs 50,000 gets 85% of net loss, capped at Rs 25,000, once in a lifetime, if they report to 1930/NCRP and the bank within five days. For smaller losses RBI funds 65 of the 85 points and each bank 10 [28]. I read the co-operative bank version; that other banks got matching text is reported but I did not check it.
- Discussion paper, 9 Apr 2026 [26][27]. Proposals: a one-hour lag on account-to-account transfers above Rs 10,000, including UPI, with a provisional debit and the right to cancel; no lag for merchant payments; "trusted person" approval above Rs 50,000 for customers aged 70+ and people with disabilities, with opt-out; annual limits pending checks; a kill switch. Comments closed 8 May. I found no final rule as of 15 Nov 2026.
- Supreme Court, 29 Oct 2026, on digital arrest. The court said banks should suspend transactions that "uncharacteristically deviate" from account history, alert police and verify physically, and repay victims in full where due diligence failed. The Attorney-General said RBI KYC amendment directions would be notified by 30 Nov and run by 31 Dec. He put digital-arrest losses at about Rs 800 crore this year against about Rs 3,000 crore last year [33]. BioCatch calls digital arrest India's most common scam type (vendor claim) [45].

Not verified: any RBI rule requiring call-back on high-value transfers. I found none.

## 3. Signals and checks a bank agent could call as tools

1. Name check. Returns match, close match, no match or unavailable [21]. Noisy in the scam direction. Most mule activity runs through real accounts held by deceived people, so the name matches [48], and names can be chosen to mislead [23]. Genuine close matches come from nicknames and joint accounts.
2. Payee risk. Account age, recent inbound count, registry flags (Suspect Registry, MuleHunter, DPIP) [29][32][35]. Coverage is partial (26 banks), and genuine small businesses also look new and busy.
3. Number risk (FRI style). Medium, High or Very High for the payee's mobile or UPI handle [31]. Fast but short-lived; scam numbers last a few days [31].
4. Session. Active call, whether the caller is a saved contact, screen sharing or a remote-access app, new device [6][44][47]. A remote-access session shows a genuine device fingerprint, so legacy checks miss it [44]. Genuine customers also share screens and take calls.
5. Behaviour. Hesitation, slow typing, guided input order, typing a payee number while on a call [44][46]. Feedzai says each signal is too weak alone and only shows risk in combination (vendor claim) [46].
6. SIM change. SIM swapped in the last 24-72 hours [15][40].
7. Account history. Recent limit raise, new payee, broken FD, mobile or email change, and deviation from the account's own baseline [30][33][46]. The FCA says unusual is "not necessarily grounds for suspicion", only for inquiry [3]. I found no published bank rule on "FD broken then transfer".
8. Caller check. Whether the bank is really calling [7][16][43]. Clean signal when it exists.
9. Customer answers. The weakest signal against coached victims, who arrive with a cover story for the first question; staff are taught to ask for specifics [48]. A request to lie to the bank is itself a scam marker [11].

## 4. Escalation and friction ladder

1. Score silently. Payments are risk-scored in the background; the customer sees nothing [34][46].
2. Inform. Show the name-check result. The EU deal says a mismatch means the bank refuses the order and tells the payer [22]; final legal text not checked.
3. Warn. Specific to the scam type, for large payments to new payees [10]. Android adds a 30-second pause [6].
4. Ask. Purpose questions, then follow-ups that need specifics [9][48].
5. Limit or cool. Caps and waiting periods after a new payee or device [37][38][39].
6. Delay. One hour (India, proposed) [26] up to four business days (UK), with a stated reason [3].
7. Call back. Contact through a channel the bank already holds, never a number the customer was given [48]. The UK delay exists so the bank can contact the payer or police [3].
8. Hold and hand to a specialist. Starling hands from its assistant to staff [9]; the Banking Protocol covers phone and online teams [12]. The EU deal guarantees access to a human, not only a chatbot [22].
9. Refuse or freeze. If suspicion stays after contact [3].
10. Report. Police in the Banking Protocol [12]; 1930/NCRP in India, which also decides compensation [28][32].

Over-blocking has a price. FOS hears complaints that a block "wasn't necessary" and a call would have settled it, and can award money for distress [14]. FCA guidance says pay as soon as the doubt is cleared, and record the reason, length and outcome of each delay plus any vulnerability [3]. The PSR evaluation found friction concentrated on crypto, international and mule-linked payments and vulnerable customers, with no clear drop in Faster Payments use [1].

## 5. Design implications for BankDesk v4

- Split `verify_payee` into a name check (four outcomes) and a payee-risk check (age, inbound count, registry flag). A name match should not clear a scam, which matches v3's 15% mismatch rate for scams.
- Add a number-risk tool returning an FRI-style level, and a SIM-change flag for the customer's own number.
- Have `check_session` report whether the caller is a saved contact and how long the call has run, not just "on a call". That is the actual trigger Android uses [6].
- Replace the single terminal hold with graded actions: warn, ask, cool or delay, call back on the registered number, hold, refuse. Score friction per step on genuine cases, so a one-hour delay costs less than a block.
- Apply real limits in the simulator: 30-minute cooling, a Rs 50,000 first-day cap for new payees, Rs 5,000 for a new UPI device. Credit a genuine episode that ends with a scheduled transfer after cooling.
- Give coached victims a ready cover story for the first question and weaker answers to follow-ups. Reward follow-ups that ask for specifics.
- Add a caller check ("is the bank calling this customer?"). Any claim that the bank asked them to move money should end in a hold [7][11][48].
- Build a digital-arrest family: aged customer, long call, FD break, large transfer. Give the account a baseline so "deviation from history" is checkable [33].
- Grade hold messages (R3) on what the FCA requires in a delay notice: the reason, what the bank needs from the customer, and what happens next, in English or Hindi [3].
- Keep genuine-urgent cases where delay causes harm and count wrongful blocks as a cost, as FOS does [14].
- For confirmed scams, the final reply should tell the customer to report to 1930 or cybercrime.gov.in within five days, since compensation depends on it from 2027 [28].
- Add account-change tools (`change_registered_mobile`, `bind_new_device`) with a 24-hour cooling period, for takeover cases [40]. Alerts to the old number are common practice but I did not verify a rule.
- Offer a "trusted person" path for customers 70+, labelled as RBI's April 2026 proposal, not law [26].
- No public source gives base rates for these signals in genuine traffic. v3's noise levels stay design guesses; say so in the article.

Not verified: Lloyds, TSB and Monzo payment questionnaires (no detailed public source found); Featurespace and Indian vendors (Bureau, Signzy) capabilities; the RBI discussion paper text itself (read via Reuters).

## 6. Sources

1. Frontier Economics for PSR, "Independent evaluation of APP scam policies: summary report", https://www.frontier-economics.com/media/2ctd3jq2/app-fraud-evaluation-final-summary-report-26-06-26.pdf , 26 Jun 2026.
2. Regulation Tomorrow, "Payment fraud falls by £73m following PSR reimbursement scheme", https://www.regulationtomorrow.com/2026/07/payment-fraud-falls-by-73m-following-psr-reimbursement-scheme/ , Jul 2026.
3. FCA, FG24/6 "Guidance for firms that enables a risk-based approach to payments", http://www.fca.org.uk/publication/finalised-guidance/fg24-6.pdf , 22 Nov 2024.
4. UK Finance, "Fraud remains a national security threat as criminals steal almost £1.3 billion", https://www.ukfinance.org.uk/news-and-insight/press-release/fraud-report-2026-press-release , 15 Jun 2026.
5. Finextra (Pay.UK author), "Confirmation of Payee five years on", https://www.finextra.com/the-long-read/1396/confirmation-of-payee-five-years-on , 7 Jul 2025.
6. Google, "Android expands pilot for in-call scam protection for financial apps", https://blog.google/security/android-expands-pilot-in-call-scam-protection-financial-apps/ , 3 Dec 2025.
7. Monzo help, "If someone calls you claiming to be from Monzo, check it's us in the app", https://monzo.com/help/monzo-fraud-category/monzo-call-status-web , accessed 2026-11-15.
8. Revolut, "Revolut launches AI feature to protect customers from card scams", https://www.revolut.com/en-US/news/revolut_launches_ai_feature_to_protect_customers_from_card_scams_and_break_the_scammers_spell/ , 15 Feb 2024.
9. FStech, "Starling expands AI assistant to detect 10 types of fraud", https://www.fstech.co.uk/fst/Starling_Expands_AI_Assistant_To_Detect_10_Types_Of_Fraud.php , 24 Jun 2026.
10. Starling help, "Why am I being warned about making a payment?", https://help.starlingbank.com/hc/en-us/articles/360010461159 , accessed 2026-11-15.
11. Take Five, "Courier fraud", https://www.takefive-stopfraud.org.uk/protect-yourself/courier-fraud/ , accessed 2026-11-15.
12. Surrey Police, "Fraud newsletter March 2026", https://www.surrey.police.uk/police-forces/surrey-police/areas/campaigns/2026/fraud-newsletter-march-2026/ , Mar 2026.
13. House of Commons Library, "Banking fraud" CBP-8545, https://researchbriefings.files.parliament.uk/documents/CBP-8545/CBP-8545.pdf , 29 Jul 2026.
14. Financial Ombudsman Service, "Frozen accounts and blocked payments", https://www.financial-ombudsman.org.uk/consumers/complaints-can-help/banking-and-payments/frozen-accounts-blocked-payments , accessed 2026-11-15.
15. CGAP, "Solutions to protect consumers from fraud in digital finance", https://www.cgap.org/research/publication/solutions-to-protect-consumers-fraud-in-digital-finance , May 2026.
16. CommBank, "Anti-scam measures cut scam losses for CommBank customers in half", https://www.commbank.com.au/articles/newsroom/2024/08/cba-cuts-scam-losses-for-customers.html , Aug 2024.
17. Westpac, media release on scam prevention, https://www.westpac.com.au/about-westpac/media/media-releases/2025/15-january/ , 15 Jan 2025.
18. The Digital Banker (ANZ release), "Digital Padlock now live", https://thedigitalbanker.com/digital-padlock-now-live-anz-aims-for-national-standard-in-scam-protection/ , Aug 2025.
19. ACCC, "Continued action critical to combat fraud as annual scam losses exceed $2 billion", https://www.accc.gov.au/media-release/continued-action-critical-to-combat-fraud-as-annual-scam-losses-exceed-2-billion , 30 Mar 2026.
20. HSF Kramer, "Stage 1 of the Scams Prevention Framework", https://www.hsfkramer.com/insights/2026-06/stage-1-of-the-scams-prevention-framework , 10 Jun 2026.
21. ECB, "Instant Payments Regulation", https://www.ecb.europa.eu/paym/retail/instant_payments/html/instant_payments_regulation.en.html , accessed 2026-11-15.
22. European Parliament, "Payment services deal: more protection from online fraud and hidden fees", https://www.europarl.europa.eu/news/en/press-room/20251121IPR31540/ , 27 Nov 2025.
23. New York Attorney General, "Attorney General James sues company behind Zelle", https://ag.ny.gov/press-release/2025/attorney-general-james-sues-company-behind-zelle-enabling-widespread-fraud , 13 Aug 2025.
24. Consumer Finance Monitor, "New York court refuses to dismiss Attorney General's fraud case against Zelle operator", https://www.consumerfinancemonitor.com/2026/07/31/new-york-court-refuses-to-dismiss-attorney-generals-sweeping-fraud-case-against-zelle-operator-early-warning-services/ , 31 Jul 2026.
25. RBI, "Introduction of beneficiary bank account name look-up facility for RTGS and NEFT", https://www.rbi.org.in/Scripts/NotificationUser.aspx?Id=12759&Mode=0 , 30 Dec 2024.
26. Reuters, "India's central bank mulls delay in some digital payments to curb fraud", https://www.reuters.com/sustainability/boards-policy-regulation/indias-central-bank-mulls-delay-some-digital-payments-curb-fraud-2026-04-09/ , 9 Apr 2026.
27. RBI, "Exploring safeguards in digital payments to curb frauds", https://m.rbi.org.in/Scripts/PublicationsView.aspx?id=23810 , Apr 2026 (summary only).
28. RBI, "(Rural Co-operative Banks - Responsible Business Conduct) Third Amendment Directions, 2026", https://www.rbi.org.in/Scripts/BS_CircularIndexDisplay.aspx?Id=13549 , 24 Jun 2026.
29. PIB (Finance), "RBI strengthens framework on unauthorised electronic banking transactions", https://www.pib.gov.in/PressReleasePage.aspx?PRID=2244478 , 24 Mar 2026.
30. RBI, "Authentication mechanisms for digital payment transactions Directions, 2025", https://www.rbi.org.in/Scripts/NotificationUser.aspx?Id=12898 , 25 Sep 2025.
31. PIB (DoT), "DoT introduces Financial Fraud Risk Indicator (FRI)", https://www.pib.gov.in/PressReleasePage.aspx?PRID=2130249 , 21 May 2025.
32. PIB (Home Affairs), "National cybercrime response mechanism", https://www.pib.gov.in/PressReleasePage.aspx?PRID=2287674 , 22 Jul 2026.
33. The Hindu, "Supreme Court calls for financial institutions to compensate digital arrest victims", https://www.thehindu.com/news/national/sc-calls-for-mandatory-compensation-to-digital-fraud-victims-in-case-of-banks-due-diligence/article71640230.ece , 29 Oct 2026.
34. ET BFSI, "How NPCI is looking to combat rising UPI frauds with AI tools", https://bfsi.economictimes.indiatimes.com/news/how-npci-is-looking-combat-rising-upi-frauds-with-ai-tools/119961408 , 4 Apr 2025.
35. IDPIC, "The Digital Payments Intelligence Platform", https://idpic.org.in/how-dpip-works , accessed 2026-11-15.
36. Medianama, "23 banks use MuleHunter.AI", https://www.medianama.com/2025/12/223-rti-23-banks-mulehunter-mule-accounts/ , Dec 2025 (summary only).
37. HDFC Bank, "Cooling period", https://www.hdfc.bank.in/security-measures/cooling-period , accessed 2026-11-15; NEFT limits page https://www.hdfc.bank.in/neft/limits (summary only).
38. Axis Bank, "Mobile and Internet Banking FAQs", https://www.axis.bank.in/docs/default-source/ld/digital-banking_faqs.pdf , accessed 2026-11-15.
39. Google Pay Help, "Standard UPI transaction limits", https://support.google.com/pay/india/answer/7359498 , accessed 2026-11-15 (summary only).
40. Moneycontrol, "Why you lose banking services, UPI access and OTPs for 24 hours after SIM change", https://www.moneycontrol.com/technology/how-sim-swap-or-esim-transfer-can-affect-your-banking-otps-and-upi-access-and-why-this-is-actually-important-article-13928656.html , 23 May 2026.
41. Times of India, "NPCI to end P2P collect requests from October 1", https://timesofindia.indiatimes.com/business/india-business/upi-fraud-clampdown-npci-to-end-p2p-collect-requests-from-october-1-banks-apps-told-to-block-pull-transactions-permanently/articleshow/123309612.cms , Aug 2025 (summary only).
42. Economic Times, "New UPI rules from June 30", https://m.economictimes.com/wealth/spend/less-upi-frauds-now-thanks-to-this-new-feature-you-will-know-exactly-whom-you-are-making-upi-payment-to/articleshow/120698374.cms , 2025 (summary only).
43. TRAI, Direction on 1600 series for service and transactional calls, https://www.trai.gov.in/sites/default/files/2025-11/Direction_19112025.pdf , 19 Nov 2025 (summary only).
44. BioCatch, "Impersonation scams", https://www.biocatch.com/social-engineering-scam-detection/impersonation-scams , accessed 2026-11-15.
45. BioCatch, "2025 Digital Banking Fraud Trends in India", https://www.biocatch.com/report-digital-banking-fraud-trends-india-2025 , 2025.
46. Feedzai, "How to stop scams with signal convergence", https://www.feedzai.com/blog/stop-scams-signal-convergencehow-to-stop-scams-with-signal-convergence/ , accessed 2026-11-15.
47. Sardine, "Device and behavior intelligence", https://www.sardine.ai/device-and-behavior , accessed 2026-11-15.
48. BankersHub, "How front-line bank staff can spot fraud red flags", https://www.bankershub.com/blogs/blog/how-front-line-staff-spot-fraud-red-flags , 3 Nov 2026.
49. Bank of Ireland UK, "About online payment limits", https://www.bankofirelanduk.com/online-banking/changes-to-online-banking/ , accessed 2026-11-15 (summary only).
