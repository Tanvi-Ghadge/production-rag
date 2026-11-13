# Frozen corpus

Status: **frozen release `corpus-2026-11-09` — Week 7 corpus bulletin complete**  
Scope: public Indian payments, payment-system, KYC/AML, cyber-security,
data-protection, and related regulatory material.  
Count: **31 PDF documents** (18 in tenant `A`, 13 in tenant `B`).

This is the corpus contract for ingestion and evaluation. The application must
not silently add, replace, or delete a source. A corpus change requires a new
release identifier, an updated manifest, and a fresh evaluation run.

## Selection policy

Documents were selected because they are primary or explanatory publications
from an Indian public authority and support questions about payment
aggregators, UPI, e-mandates, PPIs, KYC/AML, payment-system security, or
data-protection. The release intentionally includes:

- 31 public PDFs, within the required 25-40 range;
- two isolated tenants for access-control tests;
- tables and schedules in the RBI directions and master directions;
- multiple version chains, including at least these superseding pairs:
  - `pa_guidelines_2020.pdf` -> `pa_md_2025.pdf`;
  - `kyc_md_2016.pdf` -> `kyc_md_2025.pdf`;
  - `cyber_md_2024.pdf` -> `cyber_md_2026.pdf`;
  - `ppi_md_2017.pdf` -> `ppi_md_2021.pdf`;
  - `emandate_2022.pdf` -> `emandate_2023.pdf` -> `emandate_2024.pdf` ->
    `emandate_framework_2026.pdf`.

The older documents remain in the corpus so that version-sensitive questions
can be evaluated. They are not deleted when superseded. Retrieval metadata must
mark the newer document as preferred and demote, rather than remove, older
versions.

No TeamLease data, private customer data, credentials, or non-public
documents are included.

## Source and usage terms

The source authorities are:

- [Reserve Bank of India](https://www.rbi.org.in/), including its master
  directions, circulars, press releases, FAQs, and payment-system
  publications;
- [Ministry of Electronics and Information Technology](https://www.meity.gov.in/)
  and the [India Code](https://www.indiacode.nic.in/) repository;
- the [Gazette of India](https://egazette.nic.in/) for public statutory
  publications.

The canonical source collections used for verification are:

- RBI [master directions](https://www.rbi.org.in/Scripts/BS_ViewMasDirections.aspx),
  [circular index](https://www.rbi.org.in/Scripts/BS_CircularIndexDisplay.aspx),
  [press releases](https://www.rbi.org.in/Scripts/BS_PressReleaseDisplay.aspx),
  and [FAQs](https://www.rbi.org.in/Scripts/FAQView.aspx);
- MeitY [Digital Personal Data Protection Rules, 2025](https://www.meity.gov.in/documents/act-and-policies/digital-personal-data-protection-rules-2025-gDOxUjMtQWa);
- [India Code](https://www.indiacode.nic.in/) for Acts and consolidated
  statutory text;
- [Gazette of India](https://egazette.nic.in/) for Gazette notifications.

The exact landing page is a citation attribute to be populated from these
collections during ingestion. The frozen identity of a source is the local
path plus its complete SHA-256 digest; a moved or redesigned authority page
must not cause the source bytes to change.

The PDFs were obtained from public authority pages or their public document
repositories and are stored unchanged under `corpus/raw/<tenant>/`. The local
file is the ingestion input; the authority page is the legal/source reference.
Where a publication has both an HTML landing page and a PDF, the landing page
is the preferred human-readable citation.

No source was treated as carrying an unrestricted open-source or public-domain
licence. The permissible use of these public documents is limited to
non-commercial research, internal compliance evaluation, and building the
prototype RAG service described in this repository. Redistribution of the
source PDFs requires permission from the issuing authority. This service does
not host or redistribute the PDFs; ingestion reads them from the local
`corpus/raw/<tenant>/` directory.

The project does not claim that a government publication is copyright-free.
Legal review is required before distributing the PDFs or using the corpus
outside this research/service deployment.

## Document manifest

Every row is a frozen source. `tenant` is an access-control partition, not a
claim about the document's legal audience. The `sha256` values are the complete
digests recorded in `corpus/audit.csv`; ingestion must verify and preserve
them. Canonical URLs point to the RBI / MeitY / India Code / Gazette of India
collections where the document was located.

| # | Tenant | File | SHA-256 | Pages | Tables | Authority | Canonical URL | Publication date | Superseded by |
|---|--------|------|---------|-------|--------|-----------|---------------|------------------|---------------|
| 1 | A | auth_directions_2025.pdf | ca18278f26aa13f59e01cb73b616344c85ec60b93330aff0b3d497410544c05d | 8 | 2 | RBI | https://www.rbi.org.in/Scripts/BS_ViewMasDirections.aspx | September 25, 2025 | — |
| 2 | A | auth_press_2025.pdf | 753ec1ca1304b63aef2f0c0ec9cb2e7a10b86c8f1cc1fa6e149aa5f8e3e9484a | 1 | 1 | RBI | https://www.rbi.org.in/Scripts/BS_PressReleaseDisplay.aspx | September 25, 2025 | — |
| 3 | A | emandate_2022.pdf | efa88fb0d3e9052a7630134b5b5b7a9ef72916d6dd4be8c59b9c6e44abee87bf | 2 | 0 | RBI | https://www.rbi.org.in/Scripts/BS_ViewMasDirections.aspx | June 16, 2022 | emandate_2023.pdf |
| 4 | A | emandate_2023.pdf | 888570502dbcc3e4609625bf100d92b213f5482fa6b5b6d1de79fe8393aa3727 | 1 | 0 | RBI | https://www.rbi.org.in/Scripts/BS_ViewMasDirections.aspx | December 12, 2023 | emandate_2024.pdf |
| 5 | A | emandate_2024.pdf | f8de8395e2ff87220d0416f4aacfda8fee1a7f19fcc663d21fb2b8be8bf7df45 | 2 | 0 | RBI | https://www.rbi.org.in/Scripts/BS_ViewMasDirections.aspx | August 22, 2024 | emandate_framework_2026.pdf |
| 6 | A | emandate_framework_2026.pdf | 1b8c8e39a4498d83025a7d0183d4cc5e045ce237d0745b8978e677646bcfdf9c | 4 | 1 | RBI | https://www.rbi.org.in/Scripts/BS_ViewMasDirections.aspx | April 21, 2026 | — |
| 7 | A | emandate_press_2026.pdf | f1d31305ac5807cdf6eca046d77aefd42a3a23632540b5bc99e718a0dc48cb12 | 1 | 1 | RBI | https://www.rbi.org.in/Scripts/BS_PressReleaseDisplay.aspx | April 21, 2026 | — |
| 8 | A | pa_circular_2021.pdf | 9e83eedebdfec1a5e66bf04b49423b25fab0f7835b3ff2af916a402b7a3174b3 | 5 | 0 | RBI | https://www.rbi.org.in/Scripts/BS_CircularIndexDisplay.aspx | March 31, 2021 | pa_md_2025.pdf |
| 9 | A | pa_guidelines_2020.pdf | 3e3e4292f3512e83b32d1e581b95c83e26829beb49be6292e6ff3b111b4f4233 | 21 | 10 | RBI | https://www.rbi.org.in/Scripts/BS_ViewMasDirections.aspx | March 17, 2020 | pa_md_2025.pdf |
| 10 | A | pa_md_2025.pdf | 4463e369582b44f20b9bc3c45e39ed4695174f3c8119168184480e39ef816fd7 | 26 | 4 | RBI | https://www.rbi.org.in/Scripts/BS_ViewMasDirections.aspx | September 15, 2025 | — |
| 11 | A | pa_press_2025.pdf | b28c961ecc3241ac7ae31f49eb188c06d21634d8a570cd4c905f9261420570e6 | 1 | 2 | RBI | https://www.rbi.org.in/Scripts/BS_PressReleaseDisplay.aspx | September 15, 2025 | — |
| 12 | A | ppi_faq.pdf | 8ed2761fe23721af5d143e33cdfd193d5084f056e9aa851ebd56c3197651d43a | 5 | 0 | RBI | https://www.rbi.org.in/Scripts/FAQView.aspx | November 22, 2022 | — |
| 13 | A | ppi_md_2017.pdf | 252c91386f2e23ed1b9844a6d6c6b6d9b822511229b45d2ad58442487a90ec90 | 37 | 13 | RBI | https://www.rbi.org.in/Scripts/BS_ViewMasDirections.aspx | October 11, 2017 | ppi_md_2021.pdf |
| 14 | A | ppi_md_2021.pdf | 39ee8614df7676631433fb964d6122a35b689ac4a0ecb742de5c74df13b3f540 | 40 | 18 | RBI | https://www.rbi.org.in/Scripts/BS_ViewMasDirections.aspx | August 27, 2021 | — |
| 15 | A | tat_failed_txn_2019.pdf | 666fe280ed11486cea4e36f905318e75322ed9343a6b188008d0936f800f88f6 | 5 | 2 | RBI | https://www.rbi.org.in/Scripts/BS_ViewMasDirections.aspx | September 20, 2019 | — |
| 16 | A | upi_credit_lines_2023.pdf | 08fa229999db25e8900f655cbd9e3f97b67826aa78915383ee4cdf543332abc8 | 1 | 2 | RBI | https://www.rbi.org.in/Scripts/BS_PressReleaseDisplay.aspx | April 06, 2023 | — |
| 17 | A | upi_oc185b_2025.pdf | d44d26aeaa594a9693035f2f7054b6a4bb962c3ced94e9523e3c5ac55f8bd127 | 2 | 0 | RBI / NPCI | https://www.npci.org.in/ | FY 2025-26 | — |
| 18 | A | upi_ppi_tpap_2024.pdf | 17e2b392b57e4a2864bef4d375cfa0223e812d67724809b182caa9d1411725f3 | 2 | 1 | RBI | https://www.rbi.org.in/Scripts/BS_ViewMasDirections.aspx | December 27, 2024 | — |
| 19 | B | cust_liability_2017.pdf | a669bd4f2271963ff7703eed6ac8725ac58e4b5f95ce8f09bfa6a826c09a33e1 | 9 | 4 | RBI | https://www.rbi.org.in/Scripts/BS_ViewMasDirections.aspx | July 6, 2017 | — |
| 20 | B | cyber_md_2024.pdf | cea770c08e6b987d28ff3c6949de88b62ed2926ca1004d3bebb365d079599b9b | 16 | 15 | RBI | https://www.rbi.org.in/Scripts/BS_ViewMasDirections.aspx | July 30, 2024 | cyber_md_2026.pdf |
| 21 | B | cyber_md_2026.pdf | 32b22ad6b9b349cb40dfeae3ee3c90bc6c1020b014ab08d1a196c2dfc684c3e3 | 32 | 6 | RBI | https://www.rbi.org.in/Scripts/BS_ViewMasDirections.aspx | November 05, 2026 | — |
| 22 | B | data_storage_2018.pdf | 00d7e3d9d7a9b93a5acaa5dc710b2c4d3ee0c881811eaf6e30cc6f3615321409 | 1 | 0 | RBI | https://www.rbi.org.in/Scripts/BS_ViewMasDirections.aspx | April 6, 2018 | — |
| 23 | B | data_storage_faq.pdf | 090efc1ad3fd4a2554b328c106a43f41c3fcae81ed2a9010dddf59ae9bbb22e0 | 2 | 0 | RBI | https://www.rbi.org.in/Scripts/FAQView.aspx | April 6, 2018 | — |
| 24 | B | dpdp_act_2023.pdf | 4deb23981d3010c8225a2ff6149e7243dc2268455b299e283afebdd7b72a7d15 | 21 | 1 | MeitY / India Code | https://www.indiacode.nic.in/ | August 11, 2023 | — |
| 25 | B | dpdp_rules_2025.pdf | eabc7d05e013144615d78ddc0e8b9c9aac1920e814f4fad38ce6560951f5aa08 | 41 | 13 | MeitY / Gazette of India | https://egazette.nic.in/ | November 13, 2025 | — |
| 26 | B | kyc_md_2016.pdf | 7ee5c336f273be6970e41f11c57aa9b5eb8ed31c433aeeca0831110e775fdab9 | 107 | 21 | RBI | https://www.rbi.org.in/Scripts/BS_ViewMasDirections.aspx | February 25, 2016 | kyc_md_2025.pdf |
| 27 | B | kyc_md_2025.pdf | a2f5e724f1a21282fddd03e2bae1306eeef34663c953b9e111f8d12bf6bfdbdb | 101 | 3 | RBI | https://www.rbi.org.in/Scripts/BS_ViewMasDirections.aspx | November 28, 2025 | — |
| 28 | B | kyc_psp_circular_2025.pdf | cbc48f52d75d7b522ec07e25d871efb5e4c9610f41de87ac615f6a3fb42d14e2 | 5 | 5 | RBI | https://www.rbi.org.in/Scripts/BS_CircularIndexDisplay.aspx | November 28, 2025 | — |
| 29 | B | pmla_2002.pdf | d3699f0228f7b9cdf8311f9e8998032fb15e6570070b99a578eca3cb8fcd6413 | 47 | 0 | India Code / Government of India | https://www.indiacode.nic.in/ | 2002 | — |
| 30 | B | pss_act_2007.pdf | a625816550bb36ad04ebd9f6405dee0b46eefa407debe597c79536338a2ad5e1 | 21 | 0 | RBI / India Code | https://www.rbi.org.in/Scripts/BS_ViewMasDirections.aspx | 2007 | — |
| 31 | B | pss_act_faq.pdf.pdf | cd360e533b4f3a15303a998f01eb4a39c8cd96408c1777c6cd6f1feb37fb6ac9 | 8 | 0 | RBI | https://www.rbi.org.in/Scripts/FAQView.aspx | October 20, 2025 | — |

The detailed ingestion audit is in
[`corpus/audit.csv`](../corpus/audit.csv). It records page count, empty pages,
detected tables, date clues, and the complete SHA-256 digest for each row.

## Table / OCR inventory

The following documents contain extractable tables or schedules that support
table-lookup questions (limits, TAT days, report names, compensation amounts):

| Document | Table locations | Table type |
|----------|----------------|------------|
| `pa_guidelines_2020.pdf` | Multiple pages | PA reporting schedules |
| `pa_md_2025.pdf` | Multiple pages | PA master direction tables |
| `ppi_md_2017.pdf` | Multiple pages | PPI limits and KYC tiers |
| `ppi_md_2021.pdf` | Multiple pages | PPI master direction tables |
| `tat_failed_txn_2019.pdf` | Page 5 | TAT and compensation schedule |
| `upi_credit_lines_2023.pdf` | Page 1 | UPI credit line scope table |
| `upi_ppi_tpap_2024.pdf` | Page 1-2 | TPAP onboarding table |
| `cust_liability_2017.pdf` | Multiple pages | Customer liability tables |
| `cyber_md_2024.pdf` | Multiple pages | Cyber resilience control tables |
| `cyber_md_2026.pdf` | Multiple pages | Cyber resilience control tables |
| `dpdp_rules_2025.pdf` | Multiple pages | DPDP Rules schedules |
| `kyc_md_2016.pdf` | Multiple pages | KYC tier and CDD tables |
| `kyc_md_2025.pdf` | Multiple pages | KYC master direction tables |

The following PDF has no extractable text and must not be used as answer evidence:

| Document | Issue | Disposition |
|----------|-------|-------------|
| `upi_oc185b_2025.pdf` | Image-only scan, 2/2 pages no text | Ingestion reports `needs_ocr`; excluded from answerable chunks |

## Known source-quality exception

`corpus/raw/A/upi_oc185b_2025.pdf` is image-only: both pages have no extractable
text. The official NPCI download was re-checked on 9 Nov 2026 and remains
image-only; its SHA-256 is unchanged. It remains in the frozen release because
it is a relevant official publication and is useful for testing scan/OCR
failure handling. It must not be used as answer evidence until OCR is
performed and manually checked. The ingestion job must report it as
`needs_ocr`, not as a successful text parse. This is a known source limitation,
not a corpus-integrity failure.

## Version and freshness rules

Each document record must include:

- stable `document_id` derived from tenant and local filename;
- complete SHA-256 content hash;
- issuing authority and canonical source URL;
- publication date, effective date when stated, and retrieval date;
- version/supersedes/superseded-by relationships;
- tenant and source path;
- parser status, page count, and table/OCR flags.

For a changed source, create a new manifest row and release rather than
mutating this one. Re-ingestion may update derived indexes, but it must never
change the frozen source bytes. A new release is required when the authority
publishes a correction, amendment, consolidated direction, or replacement.

## Acceptance checks for this release

- [x] 25-40 public documents: 31.
- [x] Two tenant partitions: A and B.
- [x] At least two explicit superseding pairs: five version chains recorded.
- [x] Documents include tables: verified in `corpus/audit.csv`.
- [x] No TeamLease or private data.
- [x] Every PDF has an audit row and a tenant path.
- [x] Duplicate audit hashes: none.
- [x] Scanned-source limitation is explicitly recorded and verified against
  the official NPCI download.
- [x] Complete SHA-256 values are recorded in the audit manifest.
- [x] Canonical authority collections and usage terms are recorded.

Per-document landing-page URLs are derived source metadata for ingestion and
citation. They do not change the frozen corpus or require replacing any PDF.
# Scope decision

The roadmap target is 100-150 questions. This repository deliberately freezes
120 active, human-reviewed questions for the Week 7-9 deliverable. The golden
set in `evals/golden/golden.jsonl` contains 120 records covering factoid,
multi-hop, table lookup, version-sensitive, unanswerable, and adversarial
categories.
