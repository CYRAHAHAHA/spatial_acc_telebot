# Difficulty Classification Analysis

## Classification Criteria (Based on NLP Matcher Error Messages)

### Easy (10 tests - 33.3%)

**Perfect Match** - Successfully matched via token/level filters

- Tests: 1, 3, 5, 8, 11, 13, 18, 25, 26, 27

**Characteristics:**

- All have sufficient significant tokens (2+ aligned)
- Level filter correctly applied
- Status refined using allowed statuses
- Handles typos well when structure is clear
- Tolerates jumbled word order

**Examples:**

- Test 1: "ceiling compound L1" → ✓ (4 elements matched)
- Test 11: "Window Fixed 1830 L2" → ✓ (14 elements matched)
- Test 27: "ceiling compound plain L2" → ✓ (specific variant)

---

### Medium (13 tests - 43.3%)

**Dropped match** - Only X/Y significant tokens aligned (need 1-2 more)

- Tests: 2, 4, 6, 7, 10, 12, 14, 17, 21, 24, 28, 29, 30

**Characteristics:**

- Missing 1-2 significant tokens
- Error pattern: "Dropped match because only X/Y significant tokens aligned (need Y+1)"
- Model rationale shows understanding but drops due to threshold
- Often has strong matches (1/1) but insufficient token count

**Examples:**

- Test 2: "flor slab L2" → ✗ "only 1/5 significant tokens aligned (need 2)"
- Test 6: "compound celing Level 2" → ✗ "only 1/4 significant tokens aligned (need 2)"
- Test 10: "mark L2 outside walls specified" → ✗ "only 2/6 significant tokens aligned (need 3)"
- Test 14: "Celing Compound Plain L2 inspected" → ✗ "only 2/6 significant tokens aligned (need 3)"

**Key Insight:** These tests are solvable with minor NLP improvements:

- Better typo tolerance ('flor' → 'floor', 'celing' → 'ceiling')
- More flexible significant token counting
- Better handling of extra words ('mark', 'inspected', etc.)

---

### Hard (7 tests - 23.3%)

**No confident GUID match** - Completely failed to match

- Tests: 9, 15, 16, 19, 20, 22, 23

**Characteristics:**

- Error: "No confident GUID match; leaving status as manual review"
- Model rationale shows confusion or ambiguity
- Cannot identify clear element from provided text
- Often involves severe typos or unclear references

**Examples:**

- Test 9: "celings compound all" → ✗ "does not clearly match any specific element"
- Test 15: "L2 all elements" → ✗ "does not specify a clear action or status"
- Test 16: "level 2 windws installed" → ✗ "only 0/3 significant tokens aligned"
- Test 19: "Flor L1 L2" → ✗ "unclear and does not provide specific information"
- Test 20: "ceilings all both level inspected" → ✗ "does not provide a clear match"
- Test 22: "compund ceiling level 1 approved" → ✗ "does not match any door GUIDs"
- Test 23: "rof on level 2" → ✗ "unclear and does not provide specific information"

**Key Insight:** These require fundamental improvements:

- Better typo correction (severe typos like 'rof', 'compund', 'windws')
- Handling vague queries ("all elements", "both level")
- Context understanding for unclear text
- May benefit from fuzzy matching or ask-for-clarification UX

---

## Distribution Summary

| Difficulty | Count | Percentage | Success Rate |
| ---------- | ----- | ---------- | ------------ |
| Easy       | 10    | 33.3%      | 100%         |
| Medium     | 13    | 43.3%      | 0%           |
| Hard       | 7     | 23.3%      | 0%           |

**Overall Accuracy: 33.3% (10/30 tests)**

---

## Improvement Priorities

### 1. **High Priority: Fix Medium Tests (13 tests)**

- **Impact:** Could boost accuracy from 33% to 76% (+43%)
- **Approach:**
  - Relax significant token threshold (need 2 → need 1.5 or weighted scoring)
  - Improve typo tolerance with fuzzy matching (Levenshtein distance)
  - Filter out noise words ('mark', 'update', 'pls') before token counting
  - Better stemming/lemmatization

### 2. **Medium Priority: Fix Hard Tests (7 tests)**

- **Impact:** Could boost to 100% accuracy (+23%)
- **Approach:**
  - Implement spell correction before processing
  - Add context awareness for "all" queries
  - Implement confidence-based ask-back mechanism
  - Consider LLM-based parsing for ambiguous cases

### 3. **Maintain: Easy Tests (10 tests)**

- Already at 100% - ensure improvements don't regress these

---

## Error Pattern Analysis

### Token Threshold Issues (Medium Tests)

Most medium failures show pattern: `only X/Y significant tokens aligned (need X+1)`

**Solution:** Adjust threshold based on:

- Total word count (shorter phrases need lower threshold)
- Presence of typos (reduce penalty for recognized typos)
- Strong matches vs weak matches ratio
- Element type specificity

### Severe Typo Issues (Hard Tests)

Tests 16, 22, 23 fail due to typos that break token recognition:

- 'windws' → not recognized as 'window'
- 'compund' → not recognized as 'compound'
- 'rof' → not recognized as 'roof'

**Solution:**

- Pre-process with spell checker
- Implement phonetic matching (Soundex, Metaphone)
- Build domain-specific typo dictionary

### Ambiguity Issues (Hard Tests)

Tests 9, 15, 19, 20 fail due to vague references:

- "celings compound all" - which level?
- "L2 all elements" - too vague
- "Flor L1 L2" - both levels? which floor type?
- "ceilings all both level" - ambiguous phrasing

**Solution:**

- Implement clarification prompts for ambiguous queries
- Default behavior for "all" queries (e.g., select all matching type across levels)
- Better parsing of multi-level queries ("L1 L2" → both levels)

---

## Recommendations

1. **Quick Win:** Adjust token threshold to catch medium difficulty tests

   - Change from fixed threshold to percentage-based (e.g., 40% of tokens instead of "need 2")
   - Expected improvement: +43% accuracy

2. **Medium-term:** Implement spell correction pipeline

   - Add pre-processing step with domain-aware spell checker
   - Expected improvement: +10-15% accuracy (hard tests with typos)

3. **Long-term:** Add interactive clarification for ambiguous queries
   - When confidence < threshold, ask user to clarify
   - Better UX than silent failure
   - Expected improvement: +8% accuracy (remaining hard tests)

**Target: 90%+ accuracy achievable with these improvements**
