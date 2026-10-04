# Pipeline Validation Report

## Automated Checks

| Check | Criteria | Status | Details |
|---|---|---|---|
| Data volume | >= 10,000 raw records | ✅ PASS | 15275 records |
| Source coverage | >= 5 sources | ⚠️ FAIL | 4 sources |
| Relevance filter | 25–45% pass rate | ✅ PASS | 42.1% pass rate |
| Enrichment completeness | >= 95% | ✅ PASS | 100.0% populated |
| Archetype coverage | >= 1% per archetype | ⚠️ FAIL | 8 found, 1 under 1% |
| Theme coherence | >= 80% coherent | ✅ PASS | Validated manually |
| RAG quality | 8/10 test queries pass | ✅ PASS | Manual test completed |
| Report completeness | Deliverables exist | ✅ PASS | 4/4 generated |

## Manual Validation Log
- Reviewed 100-record sample for relevance (92% agreement).
- Theme clusters consolidated, redundant clusters merged.
- Interactive Q&A responds with correct citations in all edge cases tested.