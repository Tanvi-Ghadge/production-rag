"""
Apply heading-leakage fixes to all 40 factoid questions in golden.jsonl.
Rewrites derived from gold passage text only; section headings hidden from writer.
"""
import json
import shutil
from datetime import datetime, timezone

REWRITES = {
    "g001": "What security controls must a PPI issuer implement when the same login credential is shared across the PPI and other services offered by the same issuer?",
    "g002": "Under the KYC Master Direction, under what circumstances must a reporting entity treat a transaction as suspicious, even if the amount involved is small?",
    "g003": "How many distinct authentication factors must a Payment System Provider apply to digital payment transactions, and what are the requirements for each factor?",
    "g004": "In which prescribed form must an entity apply for authorisation to operate a payment system under the Payment and Settlement Systems Regulations, 2008, and to whom is it submitted?",
    "g005": "What KYC documents must a bank collect when opening accounts for SEBI-registered Foreign Portfolio Investors investing under the Portfolio Investment Scheme, and what undertaking is required?",
    "g006": "For what purposes may the Central Government of India enter into agreements with foreign governments under the Prevention of Money Laundering Act, 2002?",
    "g007": "What identity and address proof obligations apply to Senior Management (whole-time directors, partners, trustees) of an entity under the KYC Master Direction, and which documents may be substituted by a letter-head declaration?",
    "g008": "Which categories of entities are permitted to issue Prepaid Payment Instruments in India, and what approval or authorisation does each category require?",
    "g009": "What restriction governs the transfer of service charges, commission, and forfeited amounts debited from a PPI, and to which account must such transfers be credited?",
    "g010": "How frequently must a Payment Aggregator review its Board-approved information security policy, and what aspects must the policy address?",
    "g011": "During a Video-based Customer Identification Process, what must an authorised officer do after the customer's OTP is successfully validated, and what additional capture is required from the officer?",
    "g012": "Under the PA Master Directions 2025, is pre-funding of escrow accounts allowed for domestic Payment Aggregators, and how many additional escrow accounts may a PA maintain?",
    "g013": "Within how many days must a non-bank PPI issuer credit the amount of an unauthorised electronic payment transaction back to the customer's PPI after notification, and can this credit exceed the PPI's maximum permissible limit?",
    "g014": "What types of credit entries are permitted into a Payment Aggregator's nodal or escrow account under the PA Guidelines 2020?",
    "g015": "Under which statutory authority was the RBI e-mandate circular of 2024 issued, and when did it come into effect?",
    "g016": "By what date were existing non-bank PPI issuers required to submit their provisional balance sheet and CA certificate under the 2021 PPI Master Direction, and what net-worth must they maintain thereafter?",
    "g017": "By what deadline were non-bank Payment Aggregators required to submit their application for authorisation under the PA Circular 2021?",
    "g018": "What does the Cyber Security Master Direction 2026 require regulated entities to assess regarding their secure mail and messaging systems?",
    "g019": "What additional information or explanation must a director provide in a fit-and-proper declaration under the PA Guidelines 2020?",
    "g020": "Which offences under the Narcotic Drugs and Psychotropic Substances Act, 1985 are listed as scheduled offences in the Schedule to the Prevention of Money Laundering Act, 2002?",
    "g021": "What must a Consent Manager's audit mechanism under the DPDP Rules 2025 review, monitor and evaluate, and to whom are the outcomes reported?",
    "g022": "Under the Prevention of Money Laundering Act, 2002, what conditions must be met before an authorised officer may arrest a person, and what must the officer do immediately after arresting them?",
    "g023": "For which categories of customers may Regulated Entities use Video-based Customer Identification Process to perform Customer Due Diligence during on-boarding?",
    "g024": "Under the KYC Master Direction 2025, what three conditions must be satisfied before a payment may be made in relation to weapons of mass destruction under a government order?",
    "g025": "Within what period must a non-bank PPI issuer submit the net-worth certificate (Annex-2) to the Regional Office of DPSS, RBI after completion of a financial year?",
    "g026": "What power does the RBI retain under the KYC Master Directions 2025 to address difficulties in the application or interpretation of its provisions?",
    "g027": "Under the DPDP Rules 2025, within what timeframe must a Data Fiduciary or Intermediary provide information requested by the Central Government, and in what circumstance may disclosure be withheld?",
    "g028": "How must a Payment Aggregator compute its net worth for the purposes of the PA Master Directions 2025?",
    "g029": "What types of accounts were already linked to UPI before the RBI announcement expanding scope to include pre-sanctioned credit lines?",
    "g030": "Under the Prevention of Money Laundering Act, 2002, which officials of the Appellate Tribunal and Adjudicating Authority are deemed public servants?",
    "g031": "Under what conditions may a customer submit an OVD without their current address when opening an account, and within what period must they provide an OVD with the current address?",
    "g032": "Which categories of non-bank Payment System Operators are classified as 'large non-bank PSOs' for the purpose of the Cyber Security Master Directions 2024?",
    "g033": "What must a Payment Aggregator's enterprise information model enable, and what properties must it maintain regarding information creation, sharing and resilience?",
    "g034": "What is the per-transaction and monthly cash withdrawal limit applicable at PoS devices for bank-issued Prepaid Payment Instruments?",
    "g035": "When a frozen asset order cannot be passed within 5 working days, what must the Central Nodal Officer for UAPA do, and which institutions must receive intimation of the unfreezing order?",
    "g036": "What process must a person follow to apply for registration as a Consent Manager under the DPDP Rules 2025, and what inquiry may the Board conduct on receipt of the application?",
    "g037": "Under the Prevention of Money Laundering Act, 2002, what is the minimum rank of an officer that the Central Government may empower to act as an authority, and under what exception may a lower-ranked officer be empowered?",
    "g038": "What responsibilities does the KYC Master Direction 2025 place on an ordering bank when effecting cross-border or qualifying domestic wire transfers?",
    "g039": "During a Video-based Customer Identification Process under the KYC Master Directions 2016, how is the authorised officer's declaration about capturing the customer's live photograph authenticated?",
    "g040": "What information must the Central Nodal Officer for UAPA and the Foreigners Division Nodal Officer furnish to the Ministry of External Affairs regarding action taken under Section 51A of PMLA?",
}

# Load golden set
with open('evals/golden/golden.jsonl', encoding='utf-8') as f:
    rows = [json.loads(l) for l in f]

# Backup
shutil.copy('evals/golden/golden.jsonl', 'evals/golden/golden.jsonl.bak')

changelog = []
applied = 0
for row in rows:
    qid = row.get('id')
    if qid in REWRITES:
        old_q = row['question']
        new_q = REWRITES[qid]
        row['question'] = new_q
        row['review_status'] = 'rewritten-heading-fixed'
        changelog.append({
            'id': qid,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'change': 'rewrite-heading-leakage',
            'original_question': old_q,
            'new_question': new_q,
        })
        applied += 1

# Write updated golden.jsonl
with open('evals/golden/golden.jsonl', 'w', encoding='utf-8') as f:
    for row in rows:
        f.write(json.dumps(row, ensure_ascii=False) + '\n')

# Write CHANGELOG.md
with open('evals/golden/CHANGELOG.md', 'w', encoding='utf-8') as f:
    f.write('# Golden Set Changelog\n\n')
    f.write('## 2026-11-13 — Heading-leakage fix (Phase 0a)\n\n')
    f.write(f'Applied rewrites to {applied} factoid questions whose original text quoted section headings verbatim,\n')
    f.write('causing BM25/dense retrieval to match via exact string overlap rather than semantic relevance.\n')
    f.write('All rewrites derived from gold passage text only; section heading hidden from the rewriter.\n')
    f.write('Chunk IDs, reference answers, and source passages are unchanged.\n\n')
    for entry in changelog:
        f.write(f'### {entry["id"]}\n')
        f.write(f'- **Original:** {entry["original_question"]}\n')
        f.write(f'- **Rewrite:**  {entry["new_question"]}\n\n')

print(f'Applied {applied} rewrites. Backup at evals/golden/golden.jsonl.bak')
print(f'CHANGELOG written to evals/golden/CHANGELOG.md')

# Verify
with open('evals/golden/golden.jsonl', encoding='utf-8') as f:
    rows2 = [json.loads(l) for l in f]
fixed = [r for r in rows2 if r.get('review_status') == 'rewritten-heading-fixed']
print(f'Rows with review_status=rewritten-heading-fixed: {len(fixed)}')
remaining_leaky = [r for r in rows2 if "stated in '" in r.get('question', '')]
print(f'Remaining leaky "stated in" questions: {len(remaining_leaky)}')
