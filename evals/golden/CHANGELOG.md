# Golden Set Changelog

## 2026-11-13 — Heading-leakage fix (Phase 0a)

Applied rewrites to 40 factoid questions whose original text quoted section headings verbatim,
causing BM25/dense retrieval to match via exact string overlap rather than semantic relevance.
All rewrites derived from gold passage text only; section heading hidden from the rewriter.
Chunk IDs, reference answers, and source passages are unchanged.

### g001
- **Original:** According to A:ppi_md_2017, what requirement is stated in '15.3 PPI issuers shall ensure that the following framework is put in place to address the'?
- **Rewrite:**  What security controls must a PPI issuer implement when the same login credential is shared across the PPI and other services offered by the same issuer?

### g002
- **Original:** According to B:kyc_md_2016, what requirement is stated in 'the passage concerning suspicion involve proceeds offence'?
- **Rewrite:**  Under the KYC Master Direction, under what circumstances must a reporting entity treat a transaction as suspicious, even if the amount involved is small?

### g003
- **Original:** According to A:auth_directions_2025, what requirement is stated in '6. Principles for authentication of digital payment transactions'?
- **Rewrite:**  How many distinct authentication factors must a Payment System Provider apply to digital payment transactions, and what are the requirements for each factor?

### g004
- **Original:** According to B:pss_act_faq.pdf, what requirement is stated in 'the passage concerning application authorization made form'?
- **Rewrite:**  In which prescribed form must an entity apply for authorisation to operate a payment system under the Payment and Settlement Systems Regulations, 2008, and to whom is it submitted?

### g005
- **Original:** According to B:kyc_md_2025, what requirement is stated in '49. Simplified KYC norms for Foreign Portfolio Investors (FPIs):'?
- **Rewrite:**  What KYC documents must a bank collect when opening accounts for SEBI-registered Foreign Portfolio Investors investing under the Portfolio Investment Scheme, and what undertaking is required?

### g006
- **Original:** According to B:pmla_2002, what requirement is stated in '56. Agreements with foreign countries.—(1) The Central Government may enter i nto an agreement'?
- **Rewrite:**  For what purposes may the Central Government of India enter into agreements with foreign governments under the Prevention of Money Laundering Act, 2002?

### g007
- **Original:** According to B:kyc_md_2025, what requirement is stated in 'the passage concerning senior management whole time'?
- **Rewrite:**  What identity and address proof obligations apply to Senior Management (whole-time directors, partners, trustees) of an entity under the KYC Master Direction, and which documents may be substituted by a letter-head declaration?

### g008
- **Original:** According to A:ppi_faq, what requirement is stated in '3. Who are the issuers of PPIs?'?
- **Rewrite:**  Which categories of entities are permitted to issue Prepaid Payment Instruments in India, and what approval or authorisation does each category require?

### g009
- **Original:** According to A:ppi_md_2021, what requirement is stated in 'the passage concerning debit directed regulator courts'?
- **Rewrite:**  What restriction governs the transfer of service charges, commission, and forfeited amounts debited from a PPI, and to which account must such transfers be credited?

### g010
- **Original:** According to A:pa_guidelines_2020, what requirement is stated in '1.6. Information Security: Board approved information security policy shall be reviewed atleast'?
- **Rewrite:**  How frequently must a Payment Aggregator review its Board-approved information security policy, and what aspects must the policy address?

### g011
- **Original:** According to B:kyc_md_2025, what requirement is stated in 'the passage concerning mobile number registered bank'?
- **Rewrite:**  During a Video-based Customer Identification Process, what must an authorised officer do after the customer's OTP is successfully validated, and what additional capture is required from the officer?

### g012
- **Original:** According to A:pa_md_2025, what requirement is stated in 'the passage concerning operational requirements pre-funding allowed'?
- **Rewrite:**  Under the PA Master Directions 2025, is pre-funding of escrow accounts allowed for domestic Payment Aggregators, and how many additional escrow accounts may a PA maintain?

### g013
- **Original:** According to A:ppi_md_2017, what requirement is stated in '16.4.7 On being notified by the customer, the non- bank PPI issuer shall cr edit (notional'?
- **Rewrite:**  Within how many days must a non-bank PPI issuer credit the amount of an unauthorised electronic payment transaction back to the customer's PPI after notification, and can this credit exceed the PPI's maximum permissible limit?

### g014
- **Original:** According to A:pa_guidelines_2020, what requirement is stated in '8.9.1.1. Credits'?
- **Rewrite:**  What types of credit entries are permitted into a Payment Aggregator's nodal or escrow account under the PA Guidelines 2020?

### g015
- **Original:** According to A:emandate_2024, what requirement is stated in '5. This circular is issued under Section 18 read with Section 10 (2) of the Payment and'?
- **Rewrite:**  Under which statutory authority was the RBI e-mandate circular of 2024 issued, and when did it come into effect?

### g016
- **Original:** According to A:ppi_md_2021, what requirement is stated in '2021 (provisional balance sheet). This shall be reported to RBI, along with CA certifica te in'?
- **Rewrite:**  By what date were existing non-bank PPI issuers required to submit their provisional balance sheet and CA certificate under the 2021 PPI Master Direction, and what net-worth must they maintain thereafter?

### g017
- **Original:** According to A:pa_circular_2021, what requirement is stated in '1.2. In the case of bank PAs, there is no requirement of authorisation; they shall ensure'?
- **Rewrite:**  By what deadline were non-bank Payment Aggregators required to submit their application for authorisation under the PA Circular 2021?

### g018
- **Original:** According to B:cyber_md_2026, what requirement is stated in 'the passage concerning secure mail messaging systems'?
- **Rewrite:**  What does the Cyber Security Master Direction 2026 require regulated entities to assess regarding their secure mail and messaging systems?

### g019
- **Original:** According to A:pa_guidelines_2020, what requirement is stated in 'V Any other explanation / information in regard'?
- **Rewrite:**  What additional information or explanation must a director provide in a fit-and-proper declaration under the PA Guidelines 2020?

### g020
- **Original:** According to B:pmla_2002, what requirement is stated in '24 External dealings in narcotic drugs and psychotropic substances in contravention of section 12'?
- **Rewrite:**  Which offences under the Narcotic Drugs and Psychotropic Substances Act, 1985 are listed as scheduled offences in the Schedule to the Prevention of Money Laundering Act, 2002?

### g021
- **Original:** According to B:dpdp_rules_2025, what requirement is stated in '12. The Consent Manager shall have in place effective audit mechanisms to review, monitor, evaluate and'?
- **Rewrite:**  What must a Consent Manager's audit mechanism under the DPDP Rules 2025 review, monitor and evaluate, and to whom are the outcomes reported?

### g022
- **Original:** According to B:pmla_2002, what requirement is stated in '19. Power to arrest .—(1) If the Director, Deputy Director, Assistant Director or any other officer'?
- **Rewrite:**  Under the Prevention of Money Laundering Act, 2002, what conditions must be met before an authorised officer may arrest a person, and what must the officer do immediately after arresting them?

### g023
- **Original:** According to B:kyc_md_2016, what requirement is stated in 'the passage concerning undertake v-cip carry case'?
- **Rewrite:**  For which categories of customers may Regulated Entities use Video-based Customer Identification Process to perform Customer Due Diligence during on-boarding?

### g024
- **Original:** According to B:kyc_md_2025, what requirement is stated in 'the passage concerning order issued relation weapons'?
- **Rewrite:**  Under the KYC Master Direction 2025, what three conditions must be satisfied before a payment may be made in relation to weapons of mass destruction under a government order?

### g025
- **Original:** According to A:ppi_md_2021, what requirement is stated in 'the passage concerning annex- net-worth certificate submitted'?
- **Rewrite:**  Within what period must a non-bank PPI issuer submit the net-worth certificate (Annex-2) to the Regional Office of DPSS, RBI after completion of a financial year?

### g026
- **Original:** According to B:kyc_md_2025, what requirement is stated in '83. For the purpose of giving effect to the provisions of these Directions or in order to'?
- **Rewrite:**  What power does the RBI retain under the KYC Master Directions 2025 to address difficulties in the application or interpretation of its provisions?

### g027
- **Original:** According to B:dpdp_rules_2025, what requirement is stated in '23. िेटा द़िड्युसरी या मध्यवती से सूचिा मांर्िा—(1) क ेंद्र सरकार , अडिडियम के ऐसे प्रयोििों के डलए, िो सातवीं'?
- **Rewrite:**  Under the DPDP Rules 2025, within what timeframe must a Data Fiduciary or Intermediary provide information requested by the Central Government, and in what circumstance may disclosure be withheld?

### g028
- **Original:** According to A:pa_md_2025, what requirement is stated in 'the passage concerning purposes computation worth entity'?
- **Rewrite:**  How must a Payment Aggregator compute its net worth for the purposes of the PA Master Directions 2025?

### g029
- **Original:** According to A:upi_credit_lines_2023, what requirement is stated in '(UPI)'?
- **Rewrite:**  What types of accounts were already linked to UPI before the RBI announcement expanding scope to include pre-sanctioned credit lines?

### g030
- **Original:** According to B:pmla_2002, what requirement is stated in '40. Members, etc., to be public se rvants.—The 1[Chairman], Members and other officers and'?
- **Rewrite:**  Under the Prevention of Money Laundering Act, 2002, which officials of the Appellate Tribunal and Adjudicating Authority are deemed public servants?

### g031
- **Original:** According to B:kyc_md_2025, what requirement is stated in 'the passage concerning purpose proof address however'?
- **Rewrite:**  Under what conditions may a customer submit an OVD without their current address when opening an account, and within what period must they provide an OVD with the current address?

### g032
- **Original:** According to B:cyber_md_2024, what requirement is stated in '2 For the purpose of these Directions, Clearing Corporation of India Limited (CCIL), National Payments'?
- **Rewrite:**  Which categories of non-bank Payment System Operators are classified as 'large non-bank PSOs' for the purpose of the Cyber Security Master Directions 2024?

### g033
- **Original:** According to A:pa_guidelines_2020, what requirement is stated in '1.7.3. Enterprise Information Model: The entities shall establish and maintain an enterprise'?
- **Rewrite:**  What must a Payment Aggregator's enterprise information model enable, and what properties must it maintain regarding information creation, sharing and resilience?

### g034
- **Original:** According to A:ppi_faq, what requirement is stated in '22. What are the cash withdrawal limits in case of PPIs issued by banks?'?
- **Rewrite:**  What is the per-transaction and monthly cash withdrawal limit applicable at PoS devices for bank-issued Prepaid Payment Instruments?

### g035
- **Original:** According to B:kyc_md_2025, what requirement is stated in 'the passage concerning intimation concerned bank stock'?
- **Rewrite:**  When a frozen asset order cannot be passed within 5 working days, what must the Central Nodal Officer for UAPA do, and which institutions must receive intimation of the unfreezing order?

### g036
- **Original:** According to B:dpdp_rules_2025, what requirement is stated in '4. Registration and obligations of Consent Manager . — (1) A person who fulfils the conditions for'?
- **Rewrite:**  What process must a person follow to apply for registration as a Consent Manager under the DPDP Rules 2025, and what inquiry may the Board conduct on receipt of the application?

### g037
- **Original:** According to B:pmla_2002, what requirement is stated in '53. Empowerment of certain officers.—The Central Government may, by a special or general order,'?
- **Rewrite:**  Under the Prevention of Money Laundering Act, 2002, what is the minimum rank of an officer that the Central Government may empower to act as an authority, and under what exception may a lower-ranked officer be empowered?

### g038
- **Original:** According to B:kyc_md_2025, what requirement is stated in 'the passage concerning bank comply applicable reporting'?
- **Rewrite:**  What responsibilities does the KYC Master Direction 2025 place on an ordering bank when effecting cross-border or qualifying domestic wire transfers?

### g039
- **Original:** According to B:kyc_md_2016, what requirement is stated in 'J. The authorized officer shall provide a declaration about the capturing of the live'?
- **Rewrite:**  During a Video-based Customer Identification Process under the KYC Master Directions 2016, how is the authorised officer's declaration about capturing the customer's live photograph authenticated?

### g040
- **Original:** According to B:kyc_md_2025, what requirement is stated in '13. Procedure for communication of compliance of action taken under Section'?
- **Rewrite:**  What information must the Central Nodal Officer for UAPA and the Foreigners Division Nodal Officer furnish to the Ministry of External Affairs regarding action taken under Section 51A of PMLA?


## 2026-11-13 — Hand-check removals

Removed 5 auto-generated questions that failed hand-check:

- **g122** (factoid): Wrong doc tag: question says kyc_md_2016 but passage is UAPA §51A content from kyc_md_2025
- **g127** (factoid): Question/passage mismatch: question about V-CIP standards, passage about Aadhaar OTP conversion
- **g135** (table_lookup): Passage is letter salutation, not a threshold/limit
- **g136** (table_lookup): Passage is circular header text, not a data table
- **g138** (table_lookup): Passage is RBI website footer — no regulatory content

Passed: g128, g129, g155, g161 remain.
