# Copilot instructions for vancebs/skills

Purpose: help future Copilot CLI sessions quickly understand repository structure, conventions, and how to run code.

---

## Quick commands (what actually exists in this repo)

- Syntax check a single Python script: python3 -m py_compile <path/to/script.py>
- Run environment checker (one-time per workspace): python3 <SKILL_DIR>/scripts/check_env.py
- Run the cron job entrypoint (single run): python3 <SKILL_DIR>/scripts/review_job.py --workspace <SKILL_WORKSPACE>
- Post a review (single): python3 <SKILL_DIR>/scripts/post_result.py --change-id 12345 --result PASS --report-file /tmp/report.txt

Note: There is no central test suite (pytest/tox) in this repository. Use py_compile and check_env.py for basic verification.

---

## High-level architecture

- This repo is a collection of "skills". Each skill lives in a top-level directory (e.g. gerrit-api, agent-code-review, skill-guide, atlassian-jira-confluence, T2MCodingRule).
- Each skill typically contains:
  - SKILL.md (usage, setup, workflows)
  - README.md (short quick-start)
  - scripts/ (Python scripts and config examples)
  - config templates (config.json.example or *_config.json.example)
- Runtime model: an agent sets two important directories per session: `SKILL_WORKSPACE` (project/workspace where configs & outputs live) and `SKILL_DIR` (the skill installation dir containing scripts). Skills rely on these two values.
- agent-code-review specific flow (simplified):
  1. check_env.py verifies environment and connectivity
  2. review_job.py (cron) ensures stream listener, reads events.jsonl (cursor), fetches commit metadata and diffs via Gerrit REST, prints structured JSON to stdout
  3. LLM performs review and calls post_result.py to submit comments and Verified label (or prints when test_mode=true)

---

## Key conventions and patterns (important for Copilot)

- SKILL_WORKSPACE vs SKILL_DIR
  - SKILL_WORKSPACE: project-specific config and outputs. Set once at session start and do not change.
  - SKILL_DIR: skill installation path — use to run skill scripts (python3 "$SKILL_DIR/scripts/...")
  - When multiple skills are used, prefer per-skill env vars (e.g. GERRIT_API_SKILL_DIR) to avoid collisions.

- Config file search order (implemented across skills — highest to lowest):
  1. {workspace}/config/{skill-name}/{file}
  2. {workspace}/config/{file}
  3. {workspace}/{file}
  4. {skill-dir}/{file}
  5. $HOME/.config/{skill-name}/{file}
  6. $HOME/.config/{file}
  7. $HOME/{file}

- CLI > config file > env var precedence is used by scripts. Many scripts accept `--workspace` or `--config` to avoid relying on env inheritance.

- File I/O safety:
  - Event queue uses JSONL lines; readers only process complete lines (ending with '\n').
  - Cursor file tracks read offset to avoid duplicate processing.
  - Writers aim to use atomic append + fsync where platform supports it.

- Security:
  - Scripts must not log secrets (passwords, hook tokens). check_env.py and others mask or avoid printing secrets.
  - Config files should be added to .gitignore (see SKILL.md notes).

- Cross-platform patterns:
  - Use pathlib.Path for path operations.
  - Prefer explicit `python3` on POSIX, `python` on Windows when noted in SKILL.md.
  - Avoid `python -c '...'` one-liners; prefer .py files.

- Git commit trailer: commits created by automated edits include the Co-authored-by trailer: `Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>` — keep this when automating commits.

---

## Per-skill noteworthy dependencies

- atlassian-jira-confluence: requires `atlassian-python-api` (pip install atlassian-python-api)
- Most other skills: pure Python stdlib + `ssh` binary for stream-events; no pip dependencies.

---

## Guidance for Copilot sessions (how to act)

- Always set SKILL_WORKSPACE at session start (absolute path) and, when needed, detect SKILL_DIR using the repo helper patterns in SKILL.md or skill-guide.
- Prefer calling scripts with full path and explicit --workspace to avoid env drift.
- For any code-modifying commit, follow the repository's git commit trailer convention.
- Use check_env.py when you need to verify the runtime environment before executing network operations.
- If you need to parse or produce events.jsonl, respect the "only complete lines" rule and update the cursor file after processing.

---

## Where to look next in this repo

- `skill-guide/SKILL.md` — canonical guidance on SKILL_DIR vs SKILL_WORKSPACE, path rules, and diagnostics.
- `agent-code-review/` — simplified, single-cron architecture and scripts (check_env.py, review_job.py, post_result.py).
- `gerrit-api/` — full Gerrit REST and stream-events helpers (gerrit_api.py, gerrit_stream_events.py).

---

If you want, I can also:
- add a small GitHub Actions workflow to run py_compile on all scripts on PRs, or
- generate quick copilot prompts for invoking review_job.py in OpenClaw and generic cron environments.

Would you like one of those added?