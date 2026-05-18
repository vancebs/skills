# t2-config

Centralized configuration management for agent skills. Use `cfg://<namespace>/<key>` to read or write configuration values stored in `${CFG_DIR}/<namespace>.json`.

## Quick Start

```bash
# Install
npx skills add https://github.com/vancebs/skills --skill t2-config

# Set CFG_DIR (Linux/macOS)
export CFG_DIR="$(pwd)/config"

# Check environment
python3 scripts/check_env.py

# Write a value
python3 scripts/t2_config.py set gerrit-api/url "https://gerrit.example.com"

# Read a value
python3 scripts/t2_config.py get gerrit-api/url
```

> **Trigger:** `cfg://` — whenever you see `cfg://<namespace>/<key>`, this skill handles reading or writing that configuration value.
