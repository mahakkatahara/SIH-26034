# Legal Metrology Compliance Rules — Citations Verification Register

> **Status:** Pending Human Legal Verification  
> **Source Acts & Rules:** Legal Metrology Act, 2009; Legal Metrology (Packaged Commodities) Rules, 2011; GSR 202(E); Amendments of 2021 (GSR 779(E)), 2022 (GSR 226(E)), and 2024.  
> **Policy Directive (AGENTS.md):** Every rule in `rule-engine/rules/rules.json` has `citation_verified: false` by default. Under no circumstances should an automated agent change this to `true`. Human legal verification against official Gazette of India notifications is required.

---

## 1. Statutory Citations Verification Matrix

| Rule ID | Field Name | Package Type Scope | Claimed Legal Reference | Legal Obligation / Requirement | Verified Against Gazette? |
|---|---|---|---|---|:---:|
| `NAME-001` | `commodity_name` | `any` | Rule 6(1)(a) — Legal Metrology (Packaged Commodities) Rules, 2011 | The generic or common name of the commodity contained in the package must be prominently declared on the principal display panel. | [ ] |
| `MRP-001` | `mrp` | `retail` | Rule 6(1)(f) — Legal Metrology (Packaged Commodities) Rules, 2011 | Maximum Retail Price (MRP) inclusive of all taxes must be declared on every pre-packaged retail commodity. | [ ] |
| `MRP-002` | `mrp` | `retail` | Rule 6(1)(f) — Legal Metrology (Packaged Commodities) Rules, 2011 | MRP declaration format: statutory indicator (`MRP`, `M.R.P.`, `Maximum Retail Price`, `Rs.`, `₹`) followed by amount with legal currency representation. | [ ] |
| `MRP-003` | `mrp` | `retail` | Rule 6(1)(f) — Legal Metrology (Packaged Commodities) Rules, 2011 | No person shall alter, obliterate, overwrite, or smudge the declaration of retail sale price on package. | [ ] |
| `TAX-001` | `mrp` | `retail` | Rule 6(1)(f) — Legal Metrology (Packaged Commodities) Rules, 2011 | The retail sale price must state "inclusive of all taxes" or "incl. of all taxes". | [ ] |
| `USP-001` | `unit_sale_price` | `retail` | Rule 6(1)(g) — Legal Metrology (Packaged Commodities) Rules, 2011 (GSR 779(E)) | Unit Sale Price (USP) per g/kg/ml/l/metre/number must be declared when package contains more than specified quantity thresholds. | [ ] |
| `NQ-001` | `net_quantity` | `any` | Rule 6(1)(b) — Legal Metrology (Packaged Commodities) Rules, 2011 | Net quantity in terms of standard unit of weight, measure, or number must be declared. | [ ] |
| `NQ-002` | `net_quantity` | `any` | Rule 7 & Rule 12 — Legal Metrology (Packaged Commodities) Rules, 2011 | Net quantity must use prescribed legal SI units (g, kg, ml, l, cm, m, nos) without non-standard abbreviations. | [ ] |
| `MFR-001` | `manufacturer_name` | `any` | Rule 6(1)(c) — Legal Metrology (Packaged Commodities) Rules, 2011 | Name of the manufacturer, packer, or importer must be clearly declared on package. | [ ] |
| `MFR-002` | `manufacturer_address` | `any` | Rule 6(1)(c) — Legal Metrology (Packaged Commodities) Rules, 2011 | Complete postal address including PIN code of manufacturer/packer/importer must be declared. | [ ] |
| `DATE-001` | `manufacturing_date` | `retail` | Rule 6(1)(e) — Legal Metrology (Packaged Commodities) Rules, 2011 | Month and year in which commodity is manufactured, packed, or imported must be declared. | [ ] |
| `DATE-002` | `best_before_date` | `retail` | Rule 6(1)(e) — Legal Metrology (Packaged Commodities) Rules, 2011 | Best before or use-by date must be declared on perishable/food commodities as prescribed. | [ ] |
| `BATCH-001` | `batch_number` | `retail` | Rule 6(1)(d) — Legal Metrology (Packaged Commodities) Rules, 2011 | Batch number, lot number, or code identification must be declared for trace-back compliance. | [ ] |
| `CC-001` | `consumer_care_info` | `retail` | Rule 6(1)(l) — Legal Metrology (Packaged Commodities) Rules, 2011 | Name, address, telephone number, and email of consumer care cell or person to be contacted in case of complaints. | [ ] |
| `COO-001` | `country_of_origin` | `retail` | Rule 6(1)(k) — Legal Metrology (PC) Rules 2011 & Consumer Protection Rules | Country of origin or manufacture must be declared on packages containing imported goods. | [ ] |
| `PLACE-001` | `placement` | `retail` | Rule 6(2) & Rule 9 — Legal Metrology (Packaged Commodities) Rules, 2011 | All mandatory declarations must appear grouped together on the Principal Display Panel (PDP) of the package. | [ ] |
| `FONT-001` | `font_size` | `retail` | Rule 6(4) — Legal Metrology (Packaged Commodities) Rules, 2011 | Height of letters and numerals must conform to minimum millimeter height thresholds prescribed in Rule 6(4). | [ ] |

---

## 2. Gazette Verification Guidance & Amendments Cross-Reference

### A. Wholesale Package Exemptions (Rule 24)
- **Legal Context:** Under Rule 24 of the Legal Metrology (Packaged Commodities) Rules, 2011, wholesale packages are subject to a relaxed declaration regime.
- **Required Declarations:**
  1. Name and address of manufacturer or packer or importer (`MFR-001`, `MFR-002`).
  2. Net quantity of the commodity contained in the wholesale package (`NQ-001`, `NQ-002`).
  3. Generic or common name of the commodity (`NAME-001`).
- **Exemptions:** Wholesale packages are legally exempt from consumer-facing retail declarations including MRP (`MRP-001` to `MRP-003`, `TAX-001`), Unit Sale Price (`USP-001`), Date of packing (`DATE-001`), Consumer care details (`CC-001`), and Batch numbers (`BATCH-001`).
- **Gazette Verification Note:** Verify whether any recent amendments modify Rule 24 requirements for specific bulk goods or e-commerce wholesale shipping cartons.

### B. Unit Sale Price (USP) Amendments (GSR 779(E) & GSR 202(E))
- **Legal Context:** Introduced by Ministry of Consumer Affairs via GSR 779(E) dated 2nd November 2021, and notified under GSR 202(E) / subsequent enforcement extension notifications.
- **Rules Applicable:** For pre-packaged commodities containing more than $1\text{ kg}$ / $1\text{ L}$ or $1\text{ unit}$, unit sale price in terms of per g, per kg, per ml, per l, or per item must be explicitly declared alongside total MRP.
- **Gazette Verification Note:** Cross-reference effective enforcement dates and verify if commodities sold in quantities $< 1\text{ kg}$ / $< 1\text{ L}$ must display per $100\text{g}$ / per $100\text{ml}$ or per gram/ml.

### C. Legal Metrology (Packaged Commodities) Amendment Rules, 2022 & 2024
- **Electronic Products / QR Code Provisions:** Verify GSR 521(E) allowing declarations (except MRP, net quantity, consumer care, and date) through QR codes for electronic products.
- **Month/Year Format:** Verify whether `MM/YYYY` or `Month YYYY` format flexibilities are recognized under recent guidance circulars.

---

---

## 3. Legal Auditor Sign-Off Protocol
To mark a citation as verified in `rule-engine/rules/rules.json`:
1. Check the corresponding box `[x]` in the matrix above.
2. Record the exact Ministry of Consumer Affairs, Food and Public Distribution Notification number and date in this document.
3. Only upon explicit human sign-off from Legal Metrology authorized officers may `"citation_verified": true` be committed.

---

## 4. Pending Human Legal Review: Rule Semantics Proposals

### `PLACE-001` — Multi-Panel Declaration Placement Semantics
- **Rule ID:** `PLACE-001`
- **Claimed Legal Reference:** Rule 6(2), Rule 7, and Rule 9 — Legal Metrology (Packaged Commodities) Rules, 2011.
- **Current System Behavior:**
  Evaluates `len(distinct_panels) > 1 -> FAILED`. Any inspection containing declarations extracted across multiple panels (e.g. `FRONT` and `BACK`) triggers a statutory violation: *"Mandatory declarations are distributed across multiple panels/images instead of grouped on a single panel"*.
- **Proposed System Behavior:**
  1. **Principal Display Panel (PDP) Mandate (Rules 7 & 9):**
     - Common/generic commodity name (`NAME-001`) and Net Quantity (`NQ-001`) must appear on the **Principal Display Panel** (`FRONT`).
  2. **Information Panel Legality (Rule 6(2)):**
     - Other mandatory declarations (Manufacturer Name/Address, Dates of Mfg/Expiry, Batch Number, MRP, USP, Consumer Care) are legally permitted on an **Information Panel** (`BACK` or `SIDE`).
  3. **Violation Trigger:**
     - Only flag `PLACE-001` as FAILED if mandatory PDP declarations (`commodity_name`, `net_quantity`) are absent from the PDP panel, OR if information panel declarations are illegibly fragmented across non-contiguous surfaces without required statutory prominence.
- **Statutory Text Relied Upon:**
  - *Rule 6(2):* "Every package shall bear thereon the information as is specified in sub-rule (1) and sub-rule (3)... on the principal display panel or on a panel adjacent thereto."
  - *Rule 7(1):* "The principal display panel in relation to a package shall be that part of the package which is suitable for display during normal sales."
  - *Rule 9(1):* "Every declaration which is required to be made on a package under these rules shall be— (a) legible and conspicuous..."
- **Status:** Pending formal human legal review and Gazette verification. No automated rule semantics change has been committed.

