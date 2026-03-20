# Donor Template Gap Prioritization (Top-5)

Related: #42, #48, #50

Scoring model:
- **Impact** (1-5): effect on pilot donor success
- **Effort** (1-5): implementation complexity (higher = harder)
- **Priority Score** = Impact × 2 + (6 - Effort)

| Rank | Gap | Impact | Effort | Priority Score | Why now |
|------|-----|--------|--------|----------------|---------|
| 1 | EU: Risk & safeguarding annex | 5 | 2 | 14 | Frequent compliance blocker for EU-style submissions |
| 2 | World Bank: Results framework layout | 5 | 3 | 13 | Core artifact for approval readiness |
| 3 | UN: Budget framework adapter | 4 | 3 | 11 | High friction in export/finance review |
| 4 | State Department: M&E plan generator | 4 | 4 | 10 | Needed for stronger technical scoring |
| 5 | GIZ: Monitoring matrix mapper | 3 | 3 | 9 | Improves consistency; medium pilot impact |

## Proposed Implementation Order
1. EU safeguarding annex
2. World Bank results framework
3. UN budget framework
4. State Department M&E plan
5. GIZ monitoring matrix

## Definition of Done for "template supported"
- Required sections generated with donor-specific headings
- Export artifacts pass `.docx/.xlsx` smoke checks
- Critic reports no critical compliance findings
- At least 3 successful pilot runs for the donor artifact
