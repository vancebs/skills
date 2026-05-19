# Skill Quality Report — Portfolio Batch Review

**Evaluated:** 2026-05-19  
**Portfolio:** vancebs/skills  
**Skills Reviewed:** 6  
**Mode:** batch-portfolio  

---

## Portfolio Summary

| Skill | Desc (25%) | Org (30%) | Style (20%) | Struct (25%) | **Overall** | Grade |
|---|---|---|---|---|---|---|
| T2MCodingRule | 75 | 35 | 70 | 72 | **61** | **D** |
| atlassian-jira-confluence | 48 | 78 | 42 | 82 | **64** | **D** |
| claw-knowledge-base | 65 | 62 | 68 | 78 | **68** | **D+** |
| code-review | 72 | 58 | 82 | 68 | **69** | **D+** |
| gerrit-api | 68 | 42 | 45 | 75 | **57** | **F** |
| skill-guide | 78 | 28 | 78 | 72 | **61** | **D** |

**Portfolio Average: 63.3 / 100 (D)**  
**Certified (≥80):** 0 / 6  
**Passing (≥70):** 0 / 6  

---

## Clustered Issues — Root Causes

### 🔴 Cluster 1 (CRITICAL — affects ALL 6 skills): No Progressive Disclosure

**Impact:** Drags Content Organization score by 30–55 points per skill.

Every skill dumps all content into a single `SKILL.md`. None use a `references/` directory.  
The two largest offenders: `skill-guide` (4,084 words), `T2MCodingRule` (3,128 words).

**Affected:** T2MCodingRule, atlassian-jira-confluence, claw-knowledge-base, code-review, gerrit-api, skill-guide  
**Fix:** Extract detailed content (workflow tables, Mermaid diagrams, reference tables, rules lists) into `references/` subdirectory.

---

### 🔴 Cluster 2 (HIGH — affects 5 of 6 skills): Wrong Description Format

**Impact:** Loses 15–25 points in Description Quality.

No skill uses the required `"This skill should be used when..."` third-person format.

| Skill | Current Format | Issue |
|---|---|---|
| T2MCodingRule | `"T2Mobile公司编码规范... 调用此skill"` | Not third-person "This skill should be used when..." |
| atlassian-jira-confluence | `"Use this skill whenever..."` | Second-person imperative |
| claw-knowledge-base | `"OpenClaw-only shared knowledge base skill..."` | Descriptive, not trigger-phrase format |
| code-review | `"Focused on-demand code review skill..."` | Descriptive |
| gerrit-api | `"Interact with Gerrit Code Review via..."` | Descriptive verb, not trigger-phrase format |
| skill-guide | `"Two-in-one reference for working with..."` | Descriptive |

---

### 🟠 Cluster 3 (HIGH — affects 3 skills): Second-Person in Body

| Skill | Instances | Examples |
|---|---|---|
| atlassian-jira-confluence | ~8 actual (14 in env var examples) | `"run it from your project root"` |
| gerrit-api | ~7 actual | `"Use this when you need"`, `"your shell profile"`, `"Decide your mode first"` |
| T2MCodingRule | 1 | Minor |

**Note:** Many instances in env var templates (`you@example.com`, `your-pat-token`) are unavoidable boilerplate — not writing style violations.

---

### 🟡 Cluster 4 (MEDIUM — affects 2 skills): SKILL.md Too Long

| Skill | Word Count | Target | Excess |
|---|---|---|---|
| skill-guide | 4,084 | ≤2,000 | +2,084 |
| T2MCodingRule | 3,128 | ≤2,000 | +1,128 |
| gerrit-api | 2,431 | ≤2,000 | +431 |

---

### 🟡 Cluster 5 (MEDIUM — affects 2 skills): Template Script References

- `skill-guide` references `scripts/check_env.py`, `scripts/review_job.py`, `scripts/poll_events.py`, `scripts/stream.py` in prompt templates — these files don't exist in the skill's own directory. They are intended as *examples* but may confuse models looking for concrete scripts.
- `code-review` references `scripts/gerrit_api.py` (belongs to `gerrit-api` skill, not `code-review`).

---

## Per-Skill Dimension Breakdown

### 1. T2MCodingRule — 61/100 (D)

| Dimension | Score | Notes |
|---|---|---|
| Description Quality | 75/100 | Chinese trigger phrases, good coverage. Not standard third-person format. |
| Content Organization | 35/100 | 3,128 words, no `references/`, no `scripts/`, no `examples/` |
| Writing Style | 70/100 | 1 second-person instance. Content is reference knowledge (not instructions), so imperative form less applicable. |
| Structural Integrity | 72/100 | Valid YAML, minimal directory (only SKILL.md + README.md) |

**Primary weakness:** Entire content (16 regulatory chapters) in one file — no progressive disclosure.

---

### 2. atlassian-jira-confluence — 64/100 (D)

| Dimension | Score | Notes |
|---|---|---|
| Description Quality | 48/100 | Good trigger phrases. Uses "Use this skill whenever..." (2nd-person). 766 chars — 2.5× too long. |
| Content Organization | 78/100 | Best in portfolio. 1,612 words, has `references/` with 2 files. |
| Writing Style | 42/100 | 8 actual second-person violations; some env-var examples contribute noise. |
| Structural Integrity | 82/100 | Richest structure: YAML with `dependencies`, `references/`, `scripts/`. |

**Primary weakness:** Description format + writing style second-person.

---

### 3. claw-knowledge-base — 68/100 (D+)

| Dimension | Score | Notes |
|---|---|---|
| Description Quality | 65/100 | Has `triggers` field (good). Descriptive rather than trigger-phrase format. 448 chars slightly long. |
| Content Organization | 62/100 | 1,279 words (good), but no `references/`. |
| Writing Style | 68/100 | 2 second-person. Mix of Chinese + English instructions. |
| Structural Integrity | 78/100 | Rich YAML with `platform`, `keywords`, `triggers`. Has `scripts/`. |

**Primary weakness:** No `references/` despite potential for architectural docs.

---

### 4. code-review — 69/100 (D+)

| Dimension | Score | Notes |
|---|---|---|
| Description Quality | 72/100 | Good technical specifics. Describes capability, not trigger phrases. |
| Content Organization | 58/100 | 1,726 words acceptable, but no `references/` for workflows/report templates. |
| Writing Style | 82/100 | **Best style in portfolio.** 0 second-person. Good imperative usage. |
| Structural Integrity | 68/100 | References `scripts/gerrit_api.py` (external to skill), `scripts/fetch_patch.py` not in scripts/ |

**Primary weakness:** Missing `references/` + structural cross-skill script reference confusion.

---

### 5. gerrit-api — 57/100 (F)

| Dimension | Score | Notes |
|---|---|---|
| Description Quality | 68/100 | Good length (219 chars). No trigger phrases in quotes. No third-person format. |
| Content Organization | 42/100 | 2,431 words, no `references/` despite extensive API docs and workflow tables. |
| Writing Style | 45/100 | 7 actual second-person violations ("Use this when you need", "Decide your mode", "your shell profile"). |
| Structural Integrity | 75/100 | YAML has `metadata`, `compatibility`. All scripts exist. |

**Primary weakness:** Writing style (second-person) + no progressive disclosure.

---

### 6. skill-guide — 61/100 (D)

| Dimension | Score | Notes |
|---|---|---|
| Description Quality | 78/100 | Good: has `triggers` field, clear dual-purpose description. Not "This skill should be used when..." format. |
| Content Organization | 28/100 | **Worst in portfolio.** 4,084 words — 2× over limit. No `references/`. |
| Writing Style | 78/100 | 2 second-person. Good imperative instruction style. |
| Structural Integrity | 72/100 | Has `keywords`+`triggers` in YAML. Prompt templates reference non-existent scripts. |

**Primary weakness:** Document length — should split into SKILL.md + multiple `references/` files.

---

## Prioritized Fix Shortlist

### Priority 1 — Quick Wins (fix in 1–2 hours, highest ROI)

1. **All skills: Rewrite description to "This skill should be used when..."**  
   Impact: +10–25 pts on Description Quality per skill

2. **atlassian-jira-confluence + gerrit-api: Remove second-person from body text**  
   Impact: +20–25 pts on Writing Style for these two

3. **atlassian-jira-confluence: Shorten description to ≤300 chars**  
   Impact: +15 pts Description Quality

### Priority 2 — Medium Effort (2–4 hours, major structure improvement)

4. **skill-guide: Extract ~2,000 words into `references/`**  
   Suggested splits: `references/skill-usage-rules.md`, `references/skill-authoring-rules.md`, `references/prompt-templates.md`  
   Impact: +40 pts Content Organization

5. **T2MCodingRule: Extract chapters 4–16 into `references/`**  
   SKILL.md should keep only: overview + quick nav + chapters 1–3  
   Impact: +35 pts Content Organization

6. **gerrit-api: Extract API reference tables and workflows into `references/`**  
   Suggested: `references/rest-api-reference.md`, `references/stream-events-guide.md`  
   Impact: +30 pts Content Organization

### Priority 3 — Lower Priority (4+ hours, structural polish)

7. **code-review: Move review report template to `references/report-template.md`**

8. **claw-knowledge-base: Add `references/directory-structure.md`** with full path guide

9. **skill-guide: Clarify that prompt template script paths are illustrative** (not real file refs)

---

## Expected Score After Fixes

| Skill | Current | After P1 | After P1+P2 | Target Grade |
|---|---|---|---|---|
| T2MCodingRule | 61 (D) | 68 | 82 (B-) | B |
| atlassian-jira-confluence | 64 (D) | 78 | 87 (B+) | B+ |
| claw-knowledge-base | 68 (D+) | 73 | 81 (B-) | B |
| code-review | 69 (D+) | 74 | 82 (B-) | B |
| gerrit-api | 57 (F) | 68 | 81 (B-) | B |
| skill-guide | 61 (D) | 67 | 83 (B) | B |

See `improvement-plan-portfolio.md` for concrete file locations and suggested content.
