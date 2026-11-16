# 02. Why customers contact Indian banks, and the rules for fixing each problem

Compiled 2026-11-15 for BankDesk v4. Bracketed numbers point to the source list.

Two rule sets change around the simulator's "today". A new RBI ombudsman scheme started on 1 July 2026 [34], and new fraud liability and compensation rules start on 1 January 2027 [16][17]. BankDesk v4 should fix one rule date and encode that set only.

## 1. Contact drivers

I found no public Indian figure for share of contact-centre volume by reason. The RBI and banks publish complaint counts, which over-weight failures and hide routine lookups. The table uses complaint shares as a proxy.

| Reason | Share (source, date, country) | Typical channel |
|---|---|---|
| Balance, statements, certificates | No share found. SBI: about 1.5 crore calls a month, about 40% self-served in IVR [6, Oct 2022, India]. About 80% of call drivers are basic service requests [5, Sep 2020, global] | IVR, WhatsApp, app; documents to registered email [32] |
| Login and account access | 28.3% of call drivers [5, Sep 2020, global] | App or IVR reset |
| Internet, mobile, UPI, IMPS | 19.3% of complaints against banks at RBI Ombudsman offices [1, FY25, India]; 36.8% at Canara Bank [3, FY26]; 20.9% at IndusInd [4, FY26] | Status check, auto-reversal, UDIR complaint in the UPI app |
| ATM and debit card, lost cards | 7.5% at ombudsman [1, FY25]; 16.5% at Canara [3, FY26] | 24x7 block by IVR, app, WhatsApp [22][32] |
| Credit cards | 17.2% at ombudsman [1, FY25]; 15.5% at IndusInd [4, FY26] | Issuer, then network chargeback |
| Loans, EMIs, recovery agents | 21.7% at ombudsman [1, FY25]; 15.7% loans plus 4.2% recovery agents at IndusInd [4]; 4.9% at Canara [3] | Branch, phone |
| Deposit accounts, account operation, KYC, contact updates | 20.6% at ombudsman [1, FY25]; 17.5% at IndusInd [4]; 2.3% at Canara [3] | Branch, or app with Aadhaar e-KYC [25] |
| Charges and fees | 3.2% at Canara [3, FY26] | Phone, branch |
| Filing a dispute | 5.2% of call drivers [5, Sep 2020, global] | Ticket |
| Fraud reports | No bank share found. 23.02 lakh complaints reached the national fraud system since 2021 [19, Dec 2025, India]. The top US checking-account complaint was deposits and withdrawals, many scam-induced [7, Mar 2026] | 1930, cybercrime.gov.in, bank 24x7 line |

Canara labels 70.8% of its 413,931 complaints as "digital" [3].

## 2. The real rules, by problem type

### 2.1 Money debited, transaction failed

A failed transaction is one not completed for a reason the customer did not cause, such as a link failure, an empty ATM or a time-out [8]. Reversal deadlines [8]:

| Case | Deadline | Compensation |
|---|---|---|
| UPI or IMPS transfer, beneficiary not credited | Beneficiary bank reverses by T+1 | Rs 100/day after T+1 |
| UPI merchant payment, no confirmation at merchant | T+5 | Rs 100/day after T+5 |
| ATM cash not dispensed | T+5 | Rs 100/day after T+5 |
| Card-to-card transfer | T+1 | Rs 100/day after T+1 |
| Card at PoS, no charge slip | T+5 | Rs 100/day after T+5 |
| NACH debit after mandate revoked | Resolve by T+1 | Customer's bank liable |

T is the calendar date. The bank credits compensation "without waiting for a complaint or claim" [8]. The e-commerce card row did not render on the RBI page, so its timeline is unverified.

### 2.2 UPI disputes through UDIR

UDIR is NPCI's in-app dispute system. NPCI polls banks for final status for up to 5 days. An unanswered merchant complaint becomes a chargeback after 3 days, a person-to-person one after T+1 [9]. Complaint codes [10]:
- Person to person: U010 beneficiary not credited on a pending or timed-out payment; U005 failed payment not reversed.
- Merchant: U008 goods not provided; U021 refund for returned goods not processed; U022 merchant got no confirmation; U023 "Paid by alternate means/Duplicate payment"; U009 failed payment not reversed.
- A successful person-to-person payment has no complaint code, so a wrong-recipient transfer is not a UDIR case.

Since 15 February 2025, UDIR chargebacks are accepted or rejected automatically from the beneficiary bank's credit confirmation or return [11]. A vendor guide estimates 3 to 5 working days at the app, 3 to 5 at the bank, and 7 to 10 at NPCI [13].

### 2.3 Sent to the wrong UPI ID

This is not a failed transaction. There is no auto-reversal and no TAT compensation. "Banks cannot unilaterally debit the recipient's account." The sender's bank asks the beneficiary bank, which asks the recipient, and money returns only with consent. After 30 days the customer can go to the ombudsman, which cannot force recovery either. NPCI's helpline is 1800-120-1740 [12].

### 2.4 Card disputes, duplicates, goods not delivered

Visa, Mastercard and RuPay allow disputes up to 120 days from the transaction, but banks often set shorter deadlines. Disputes take 45 to 120 days, banks may give temporary credit, and the merchant's bank gets 30 to 45 days to reply [23]. The issuer must explain a disputed bill with evidence within 30 days [22]. UPI duplicates go under U023 [10].

### 2.5 Unauthorised and scam transactions

Until 31 December 2026 [14]:
- Zero liability if the bank was at fault, or if a third-party breach is reported within 3 working days of the bank's alert.
- Reported in 4 to 7 working days, liability is the lower of the amount or a cap. The cap is Rs 5,000 for basic savings accounts. It is Rs 10,000 for other savings accounts, individual current or overdraft accounts up to Rs 25 lakh, and cards up to Rs 5 lakh. It is Rs 25,000 for the rest.
- A customer who shared credentials bears losses until reporting; the bank bears losses after.
- After 7 working days, the bank's board policy applies.
- Shadow credit within 10 working days, resolution within 90 days, burden of proof on the bank.

From 1 January 2027, under directions issued 24 June 2026:
- Zero liability for a third-party breach reported within 5 calendar days [17].
- A victim who shared credentials and lost up to Rs 50,000 gets 85% of net loss or Rs 25,000, whichever is lower, once in a lifetime. They must report to the bank and to 1930 or the cybercrime portal within 5 calendar days, and the bank pays within 5 days of the application [16][17][18].
- The RBI funds 65%, the victim's bank 10% and the first receiving bank 10% [16].
- Credit-card fraud gets provisional credit within 5 calendar days. Domestic complaints close in 45 days, cross-border in 60. SMS alerts are mandatory above Rs 500 [16][17]. The March draft had proposed 30 days [15].

Recovery:
- The national fraud reporting system has saved Rs 7,130 crore across 23.02 lakh complaints since 2021, and I4C has shared 24.67 lakh first-layer mule accounts with banks [19].
- Investigators call the first 60 to 180 minutes the "golden hour". A prompt complaint puts a lien on every account the money reached, and courts order its return [20].
- An MHA procedure from January 2026 allows refunds under Rs 50,000 without a court order, and requires banks to lift a freeze after 90 days with no court order [21].
- DoT rates mobile numbers Medium, High or Very High fraud risk; PhonePe declines payments to Very High numbers [24].

### 2.6 Account changes

HDFC lets customers change their mobile number through its website, NetBanking, ATM or a branch. Online, it needs Aadhaar e-KYC by OTP, an OTP on the new number, and debit card or NetBanking authentication. It skips the old-number OTP if the customer says that phone is lost. The change can take 48 hours [25]. SBI's WhatsApp menu offers email update, Re-KYC and nominee update, but not mobile change [26]. The RBI ties all e-transactions to the registered mobile [14]. My reading is that this makes the number a credential, so banks keep its change off chat. No source says so directly.

Cooling periods:
- I found no published cooling period after a mobile-number change.
- HDFC allows Rs 50,000 in total to a new beneficiary in the first 24 hours, 4 new beneficiaries per 24 hours, and 30 minutes to activate one [27].
- SBI caps UPI at Rs 5,000 for 24 hours after a PIN set or reset on Android, and Rs 5,000 a day for 5 days on iOS. After that, the cap is Rs 1 lakh a day and 20 person-to-person payments per 24 hours [28].
- An April 2026 RBI discussion paper floated a one-hour cancellable hold on transfers above Rs 10,000, and a "trusted person" sign-off for senior citizens above Rs 50,000. I found no final rule [29].

KYC, nominees, cards:
- Customers with no KYC change, or only an address change, can update by self-declaration, including through a business correspondent. Banks send 3 notices before the due date, one by letter, and 3 reminders after. Low-risk customers keep full account use until one year after the due date or 30 June 2026, whichever is later [30].
- Since 1 November 2025, up to 4 nominees are allowed. Deposits allow simultaneous or successive nomination; lockers allow successive only [31].
- Issuers must block a lost card at once and confirm it. Replacement needs explicit consent. Credit-card closure is due in 7 working days, then Rs 500 a day [22].

### 2.7 Statements and lookups

SBI's IVR gives balance, the last 5 transactions, account statements, nomination status, and TDS, deposit, home-loan and education-loan interest certificates. Statements and certificates go to the registered email; cards and cheque books go to the registered address. The IVR can also block an ATM card, internet banking or UPI [32]. SBI WhatsApp adds loan statements, Form 15G/H and pension slips [26]. PNB WhatsApp sends statements for up to 90 days as password-protected PDFs [33].

### 2.8 Escalation

Under the 2026 scheme, a customer can go to the RBI Ombudsman if the bank has not replied in 30 days, or a longer time set by RBI, NPCI or the card network. They must file within 90 days. Awards reach Rs 30 lakh for loss plus Rs 3 lakh for harassment. Complaints go through cms.rbi.org.in or 14448 [34]. In FY25, ombudsman offices settled 51.91% of maintainable complaints and rejected 43.36% [2].

## 3. Simulator rules we could encode

1. A failed UPI transfer must reverse by T+1. Before then, the agent checks status and asks the customer to wait. After T+1, it raises U010 or U005 and does not send a fresh transfer [8][10].
2. Failed merchant UPI payments and ATM non-dispense reverse by T+5 [8].
3. Compensation is Rs 100 per calendar day late, paid without a claim. The agent must not tell the customer to apply for it [8].
4. A wrong-recipient transfer gets no reversal, no debit from the recipient and no compensation. The right action is a recovery request that states the consent rule [12].
5. Goods not delivered is U008 on UPI, or a card chargeback within 120 days. The agent promises an investigation, not a refund [10][23].
6. Two equal debits to one payee close together are a duplicate, fixed with U023 or a card dispute [10].
7. On an unauthorised-transaction report, block the card or channel first, then log a timestamped complaint [14][22].
8. Liability is a function of account type, reporting delay in working days, and credential sharing [14]. From 2027 the window is 5 calendar days [17].
9. Shadow credit is due by working day 10 [14]; from 2027, card fraud credit by calendar day 5 [16].
10. If money has left the account, the agent sends the customer to 1930 and requests a beneficiary hold. Reward decays after 60 minutes [20].
11. From 2027, compensation = min(0.85 × net loss, 25,000) when loss ≤ 50,000, it is the first claim, and both reports came within 5 days [16][17].
12. Block lost cards on request. Reissue only with consent. Close credit cards within 7 working days [22].
13. Never change the mobile number in chat. The change needs e-KYC, an OTP on the new number and card or NetBanking authentication, and takes up to 48 hours [25].
14. New payees: Rs 50,000 in the first 24 hours, 4 per day [27]. UPI: Rs 5,000 for 24 hours after a PIN reset [28].
15. Send statements and certificates only to the registered email or address. Cap ranges at 90 days [32][33].
16. On day 30 of an open complaint, the agent gives the customer cms.rbi.org.in and 14448 [34].

## 4. Design implications for BankDesk v4

- Fix one rule date. Late 2026 means the 2017 liability rules plus RB-IOS 2026. January 2027 adds compensation and 5-day windows.
- Most fixes are a status check, a wait or a ticket. A small helpful model will want to resend money or refund the customer itself. Make both cost money in R1.
- Add a transaction-status tool returning success, failed, pending, deemed or reversed, and expect it first in every payment complaint.
- Simulate the calendar. Rules use calendar days, working days and hours, so episodes need transaction timestamps, a "now" and holidays.
- The hard step is telling problems apart. "My money is gone" can be a failed payment, a wrong recipient, a scam or a merchant dispute. Pair cases with the same opening, as v3 does for scam versus genuine.
- In fraud cases, score the order (block, hold, 1930, complaint) and the elapsed minutes.
- Account changes are where takeovers happen. Test that the agent will not change the mobile or email in chat, and will not send statements to an address the caller supplies.
- Correct refusals exist. Ombudsman offices reject 43% of maintainable complaints [2], and wrong-recipient refunds are out of the bank's hands [12]. Score a correct "no" plus the right referral as success.
- Penalise promising compensation beyond the rules, and penalise asking customers to claim what is automatic.
- US banks deny many scam claims because the customer "actively participated in the transaction" [7]. India's 2027 rules pay those victims a capped sum [16]. Keep "customer moved the money" separate from "someone else moved it" in the state.
- Weight cases by the complaint data. Digital and UPI is 19% to 37% of bank complaints, loans 5% to 22%, account operation and KYC 2% to 21% [1][3][4]. Debit plus credit cards are about 25% at the ombudsman [1]. Give lookups their own share, since complaint data hides them.
- A one-hour cancellable hold on large transfers to new payees would fit BankDesk [29]. Label it as a proposal if used.

## 5. Sources

1. RBI, Annual Report of Ombudsman Scheme 2024-25, Appendix 1.6. https://www.rbi.org.in/Scripts/PublicationsView.aspx?id=23441 (1 Dec 2025)
2. CAalley, reprint of Business Standard, RBI ombudsman FY25. https://caalley.com/news-updates/indian-news/rbi-ombudsman-complaints-rise-13-6-in-fy25-led-by-loan-and-card-issues (1 Dec 2025)
3. Canara Bank, Disclosure of complaints FY 2025-26. https://www.canarabank.bank.in/documents/d/guest/disclosure-of-complaints-march-2026 (2026)
4. IndusInd Bank, Complaint analysis FY 2025-26. https://www.indusind.bank.in/content/dam/regulatoryDisclosure/grievanceRedressal/complaint-analysis-FY-25-26.pdf (2026)
5. PaymentsJournal, on Finn AI's call-driver report. https://www.paymentsjournal.com/whats-my-password-account-access-is-most-common-contact-center-request-for-banks/ (22 Sep 2020; older than wanted, the only quantified mix found)
6. Business Standard, SBI call-centre revamp. https://www.business-standard.com/article/finance/sbi-revamps-call-centre-to-offer-30-banking-solutions-in-12-languages-122101001104_1.html (10 Oct 2022; figures from search results, page blocked)
7. CFPB, Consumer Response Annual Report 2025, section 4.4. https://files.consumerfinance.gov/f/documents/cfpb_2025-cr-annual-report_2026-03.pdf (Mar 2026)
8. RBI, TAT and compensation for failed transactions, RBI/2019-20/67. https://www.rbi.org.in/Scripts/NotificationUser.aspx?Id=11693&Mode=0 (20 Sep 2019)
9. Razorpay, NPCI-led UDIR explainer. https://razorpay.com/blog/all-you-need-to-know-about-npci-led-udir/ (22 Feb 2024)
10. Juspay, UPI complaints guide. https://juspay.io/in/docs/upi-consumer-stack/docs/resources/complaints-guide (undated, read 15 Nov 2026)
11. Upstox, UPI auto-chargeback rule. https://upstox.com/news/business-news/latest-updates/new-auto-chargeback-rule-for-upi-transactions-to-kick-in-from-feb-15-check-all-details/article-145762 (13 Feb 2025)
12. CAalley, reprint of Business Standard, wrong UPI payments. https://caalley.com/news-updates/indian-news/wrong-upi-payment-heres-what-you-can-recover-and-what-you-cant (29 Jan 2026)
13. Paytm blog, how NPCI handles UPI complaints. https://paytm.com/blog/payments/upi/how-npci-handles-upi-complaints/ (11 Jul 2025, updated 17 Apr 2026)
14. RBI, Limiting liability in unauthorised electronic banking transactions, RBI/2017-18/15. https://www.rbi.org.in/Scripts/NotificationUser.aspx?Id=11040 (6 Jul 2017)
15. TaxGuru, RBI draft fraud liability overhaul. https://taxguru.in/rbi/rbi-proposes-overhaul-digital-fraud-liability-framework-key.html (9 Mar 2026)
16. CAalley, reprint of Economic Times, RBI final fraud rules. https://caalley.com/news-updates/indian-news/rbi-finalises-digital-banking-fraud-protection-rules-introduces-shadow-reversal-extends-relief-to-sole-proprietors (25 Jun 2026)
17. CorpLawUpdates, summary of RBI/2026-27/167 to 173. https://www.corplawupdates.in/updates/rbi-fraudulent-ebt-customer-protection-compensation-directions (directions dated 24 Jun 2026; RBI text not read)
18. Business Today, compensation rules from January 2027. https://www.businesstoday.in/personal-finance/news/story/rbis-new-digital-fraud-compensation-rules-from-january-2027-how-victims-can-recover-up-to-rs25000-539435-2026-06-26 (26 Jun 2026)
19. DeshGujarat, government reply on CFCFRMS. https://deshgujarat.com/2025/12/03/over-rs-7130-crore-saved-in-23-02-lakh-cyber-fraud-complaints-govt-to-rs-mp-nathwani (3 Dec 2025)
20. The Chenab Times, golden hour. https://thechenabtimes.com/2025/12/07/act-within-golden-hour-to-recover-money-lost-in-cyber-fraud-experts/ (7 Dec 2025)
21. Drishti IAS, MHA SOP on cyber financial frauds. https://www.drishtiias.com/daily-updates/daily-news-analysis/mhas-new-sop-on-cyber-financial-frauds (17 Jan 2026; SOP text not read)
22. RBI, Master Direction on credit and debit cards. https://www.rbi.org.in/Scripts/BS_ViewMasDirections.aspx?id=12300 (21 Apr 2022, updated 7 Mar 2024)
23. Business Standard, disputing a card charge. https://www.business-standard.com/finance/personal-finance/disputing-a-wrong-credit-card-charge-experts-say-timing-decides-refunds-126011500758_1.html (15 Jan 2026)
24. The Week (PTI), DoT Financial Fraud Risk Indicator. https://www.theweek.in/wire-updates/business/2025/05/21/dcm92-biz-dot-cyber-cyberfraud.html (21 May 2025)
25. HDFC Bank, update registered mobile number. https://www.hdfc.bank.in/savings-account/services/update-mobile-number (undated, read 15 Nov 2026)
26. SBI, WhatsApp Banking. https://sbi.bank.in/web/personal-banking/digital/whatsapp-banking (updated 12 May 2026)
27. HDFC Bank, NEFT limits. https://www.hdfc.bank.in/neft/limits (undated, read 15 Nov 2026)
28. SBI YONO blog, UPI limits and cooling period. https://sbi.bank.in/web/yono/blog/understand-upi-transaction-limits-cooling-period-and-payment-tips (27 Jun 2025)
29. Business Today, RBI one-hour delay proposal. https://www.businesstoday.in/industry/banks/story/1-hr-delay-for-digital-payments-over-rs-10000-rbi-proposes-plan-to-curb-frauds-524994-2026-04-10 (10 Apr 2026)
30. RBI, KYC (Amendment) Directions, 2025. https://www.rbi.org.in/scripts/NotificationUser.aspx?Id=12866 (12 Jun 2025)
31. Tribune India (PTI), four nominees from 1 November. https://www.tribuneindia.com/news/business/now-bank-customers-can-opt-for-four-nominees-in-accounts-from-nov-1 (24 Oct 2025)
32. SBI, Contact Centre. https://sbi.bank.in/web/customer-care/contact-centre (updated 16 Sep 2026)
33. PSU Connect, PNB WhatsApp statements. https://psuconnect.in/news/pnb-users-can-download-statement-and-interest-certificate-through-whatsapp/43974 (28 Aug 2024)
34. RBI, FAQ on the Integrated Ombudsman Scheme, 2026. https://www.rbi.org.in/ScriptS/FAQDisplay.aspx?Id=153 (1 Jul 2026)
