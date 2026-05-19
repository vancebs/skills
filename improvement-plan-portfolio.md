# Skill Improvement Plan — Portfolio

**Generated:** 2026-05-19  
**Scope:** All 6 skills in vancebs/skills  
**Priority Summary:** High: 3 items · Medium: 4 items · Low: 3 items  

---

## High Priority Improvements

### H1 — Rewrite all descriptions to "This skill should be used when..." format

**Affects:** All 6 skills  
**Dimension:** Description Quality  
**Impact:** +10 to +25 pts per skill  
**Effort:** 30 min total

For each skill, replace the frontmatter `description` with a phrase in the form:

> `This skill should be used when the user asks to "X", "Y", "Z" or mentions ...`

#### Suggested rewrites

**T2MCodingRule/SKILL.md** — current: Chinese descriptive
```yaml
# Suggested
description: >
  This skill should be used when the user asks about T2Mobile coding standards,
  "git commit message format", "code review rules", "PR flow", "Java naming conventions",
  "C++ coding style", "security coding requirements", "compatibility coding", or any
  T2Mobile development process question. Covers C/C++/Java style, Gerrit workflow,
  ADR, release process, and test management.
```

**atlassian-jira-confluence/SKILL.md** — current: second-person, 766 chars (too long)
```yaml
# Suggested (trim to ~280 chars)
description: >
  This skill should be used when the user asks to "create a Jira issue",
  "update Confluence page", "search issues with JQL", "add comment to ticket",
  "get sprint info", "list Confluence spaces", or any Jira/Confluence CRUD
  operation. Covers all Jira and Confluence REST operations via atlassian-python-api.
```

**claw-knowledge-base/SKILL.md** — current: descriptive
```yaml
# Suggested
description: >
  This skill should be used when the user references "kb://", reads or writes
  to the shared knowledge base, asks to "save to knowledge base", "search knowledge base",
  "store review result", or manages the OpenClaw shared Markdown directory under
  KNOWLEDGE_BASE_DIR. OpenClaw platform only.
```

**code-review/SKILL.md** — current: descriptive capability statement
```yaml
# Suggested
description: >
  This skill should be used when the agent receives a Gerrit change URL,
  change-id (I[0-9a-f]{40}), commit SHA, change number, or stream event JSON
  and needs to perform code review. Fetches patch via gerrit-api, reviews per
  T2MCodingRule, and posts result back to Gerrit. Triggered on demand only.
```

**gerrit-api/SKILL.md** — current: capability description
```yaml
# Suggested
description: >
  This skill should be used when the user asks to "query a Gerrit change",
  "fetch a diff", "post a code review", "submit or abandon a change",
  "listen to Gerrit stream events", or needs REST/SSH access to Gerrit.
  Provides Python scripts for all Gerrit REST operations and SSH stream-events.
```

**skill-guide/SKILL.md** — current: good but not standard format
```yaml
# Suggested (keep triggers field, update description)
description: >
  This skill should be used when the user encounters a path error, config
  loading failure, SKILL_DIR issue, or any problem using an installed skill
  (PART 1); or when the user asks to "create a skill", "write a SKILL.md",
  "improve a skill description", or needs skill authoring standards (PART 2).
  Supplements skill-creator with detailed rules and templates.
```

---

### H2 — Remove second-person from gerrit-api body text

**File:** `gerrit-api/SKILL.md`  
**Dimension:** Writing Style  
**Impact:** +25 pts Writing Style  
**Effort:** 20 min

Specific lines to fix:

| Line | Current | Suggested |
|---|---|---|
| ~38 | `# Required (set once per session or in your shell profile)` | `# Required (set once per session or in shell profile)` |
| ~73 | `If you see an error, see **Troubleshooting** below.` | `On error, see **Troubleshooting** below.` |
| ~112 | `Use this when you need to perform a code review` | `Use for performing a code review on a Gerrit change.` |
| ~169 | `Use this when you need to react to Gerrit events` | `Use for reacting to Gerrit events in real time.` |
| ~171 | `Decide your mode first:` | `Select the appropriate mode:` |
| ~407 | `Only use direct HTTP if you need operations not covered by the script.` | `Use direct HTTP only for operations not covered by the script.` |

---

### H3 — Shorten atlassian-jira-confluence description to ≤300 chars

**File:** `atlassian-jira-confluence/SKILL.md`  
**Dimension:** Description Quality  
**Impact:** +15 pts  
**Effort:** 10 min  
**Action:** Apply the suggested rewrite from H1 (280 chars).

---

## Medium Priority Improvements

### M1 — Extract skill-guide references/ (biggest length offender)

**File:** `skill-guide/SKILL.md` (4,084 words → target ≤2,000)  
**Dimension:** Content Organization  
**Impact:** +40 pts  
**Effort:** 1.5 hours

Create the following files:

**`skill-guide/references/skill-authoring-rules.md`** (~1,500 words)  
Move: 规范 1–8, 规范 11 (Harness Engineering) — the detailed rule bodies  
SKILL.md keeps: rule titles + one-liner summaries linking to this file

**`skill-guide/references/prompt-templates.md`** (~800 words)  
Move: 规范 10 (all three prompt template examples A/B/C)  
SKILL.md keeps: 规范 10 header + table of when to use

**`skill-guide/references/quick-reference.md`** (~300 words)  
Move: §1.7 快速参考卡  
SKILL.md keeps: link to it

After extraction, update SKILL.md index links to point to reference files.

---

### M2 — Extract T2MCodingRule chapters into references/

**File:** `T2MCodingRule/SKILL.md` (3,128 words → target ≤1,500)  
**Dimension:** Content Organization  
**Impact:** +35 pts  
**Effort:** 1 hour

Create `T2MCodingRule/references/` with:

| File | Chapters | Approx words |
|---|---|---|
| `coding-standards.md` | 四 Java 规范, 五 C 规范, 六 C++ 规范 | ~1,500 |
| `process-workflow.md` | 三 Code Review, 十一 PR流程, 十二 SDK升级, 十三 测试, 十四 发布, 十五 需求 | ~800 |
| `security-compatibility.md` | 七 安全, 八 兼容性, 九 检测流程 | ~400 |

SKILL.md keeps: 一 Commit Message, 二 提交前检查, 十六 综合自查清单, 快速导航, 常见场景速查

---

### M3 — Extract gerrit-api API reference into references/

**File:** `gerrit-api/SKILL.md` (2,431 words → target ≤1,800)  
**Dimension:** Content Organization  
**Impact:** +25 pts  
**Effort:** 45 min

Create `gerrit-api/references/`:

| File | Content to move |
|---|---|
| `rest-api-reference.md` | Full `gerrit_api.py` function table, URL/method matrix |
| `stream-events-guide.md` | SSH stream-events setup, event schema tables, reconnect logic |

SKILL.md keeps: setup checklist, quick-start examples, env var table, troubleshooting.

---

### M4 — Fix code-review cross-skill script reference confusion

**File:** `code-review/SKILL.md`  
**Dimension:** Structural Integrity  
**Impact:** +10 pts  
**Effort:** 15 min

Line ~X references `scripts/gerrit_api.py` — this file lives in the `gerrit-api` skill, not in `code-review/scripts/`. Update references to clarify:

```markdown
<!-- Before -->
Use scripts/gerrit_api.py to fetch the change.

<!-- After -->
Use **gerrit-api** skill's `scripts/gerrit_api.py` to fetch the change.
(See gerrit-api skill for script location and usage.)
```

---

## Low Priority Improvements

### L1 — Add examples/ to atlassian-jira-confluence

**Effort:** 1 hour  
Create `atlassian-jira-confluence/examples/` with:
- `create-jira-issue.py` — minimal working example
- `create-confluence-page.py` — minimal working example

Impact: +5 pts Structural Integrity

---

### L2 — Clarify skill-guide prompt template script paths are illustrative

**File:** `skill-guide/SKILL.md` (or after moving to references/)  
**Effort:** 15 min  
Add a note before prompt template scripts section:

```markdown
> **Note:** Script paths in the following prompt templates (e.g. `scripts/review_job.py`) are
> placeholders — replace with actual paths from the relevant installed skill.
```

---

### L3 — Add `examples/` directory to code-review

**Effort:** 30 min  
Create `code-review/examples/example-review-input.md` with sample Gerrit change inputs and expected review output. Impact: +5 pts Structural Integrity.

---

## Implementation Order

Execute in this sequence for maximum grade improvement per hour:

```
1. H1 — Rewrite all descriptions (30 min)           → All 6 skills: +10–25 pts each
2. H2 — Remove gerrit-api second-person (20 min)    → gerrit-api: +25 pts Style
3. H3 — Shorten atlassian description (10 min)      → atlassian: +15 pts
4. M1 — skill-guide references/ split (1.5 hrs)     → skill-guide: +40 pts Org
5. M2 — T2MCodingRule references/ split (1 hr)      → T2MCodingRule: +35 pts Org
6. M3 — gerrit-api references/ split (45 min)       → gerrit-api: +25 pts Org
7. M4 — code-review script ref fix (15 min)         → code-review: +10 pts Struct
8. L1–L3 — Examples and polish (1.5 hrs)            → Various: +5 pts each
```

**Total estimated effort: ~6 hours**  
**Expected portfolio average after all: 82/100 (B-)**
