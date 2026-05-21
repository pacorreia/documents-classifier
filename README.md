# Documents Classifier

LLM-powered documents classifier — scores PDF and `.docx` documents against a configurable keyword list using the **GitHub Models API** (no paid subscription needed, just a GitHub token).

A fast offline mode (`--no-llm`) is also available for keyword-only matching with no API calls.

## Installation

Download the latest self-contained binary from the [Releases](../../releases) page — no Python required.

| Platform | File |
|---|---|
| Linux (amd64) | `documents-classifier-vX.Y.Z-linux-amd64.tar.gz` |
| Windows (amd64) | `documents-classifier-vX.Y.Z-windows-amd64.zip` |

Extract and place the binary alongside a `config.yaml` file.

## Usage

**Linux / macOS**

```bash
# LLM mode (default)
GITHUB_TOKEN=ghp_... ./documents-classifier /path/to/docs/

# Offline keyword-only mode — no token required
./documents-classifier /path/to/documents/ --no-llm

# Custom config file
./documents-classifier /path/to/documents/ --config /path/to/config.yaml

# Limit parallel workers
./documents-classifier /path/to/documents/ --workers 2
```

**Windows**

```powershell
$env:GITHUB_TOKEN = "ghp_..."
.\documents-classifier.exe C:\path\to\documents\
```

## Configuration (`config.yaml`)

```yaml
# Keywords that MUST be present — scored at 70% weight
must_keywords:
  - "network, networking"   # comma-separated = OR (any one satisfies this)
  - kubernetes
  - terraform

# Nice-to-have keywords — scored at 30% weight
nice_keywords:
  - Docker
  - Azure
  - "ArgoCD, Flux"

must_weight: 0.7
nice_weight: 0.3

# A document is "PASS" when combined score >= this threshold
pass_threshold: 0.6

llm:
  endpoint: "https://models.inference.ai.azure.com"
  model: "gpt-4o-mini"   # any GitHub-hosted model (e.g. gpt-4o, gpt-4o-mini)

output:
  csv_file: "results.csv"
  pass_folder: "classified/pass"
  fail_folder: "classified/fail"
  copy_files: true     # true = copy originals; false = move them
  top_n: 3
  bottom_n: 3

workers: 5             # GitHub Models caps concurrent requests at 5
```

| Key | Description |
|---|---|
| `must_keywords` | Skills that count for `must_weight` of the score |
| `nice_keywords` | Skills that count for `nice_weight` of the score |
| `pass_threshold` | Minimum score (0–1) to be labelled **PASS** |
| `llm.model` | Any GitHub-hosted model |
| `output.copy_files` | `true` = copy originals; `false` = move them |

## Output

| Path | Description |
|---|---|
| `<folder>/results.csv` | One row per document — score, matched/missing keywords, summary |
| `<folder>/classified/pass/` | Documents that met the threshold |
| `<folder>/classified/fail/` | Documents that did not meet the threshold |

### CSV columns

| Column | Description |
|---|---|
| `filename` | Original file name |
| `result` | `PASS`, `FAIL`, or `ERROR` |
| `score` | 0.000–1.000 composite score |
| `matched_must` | Must-have keywords detected (semicolon-separated) |
| `missing_must` | Must-have keywords **not** detected |
| `matched_nice` | Nice-to-have keywords detected |
| `summary` | 1–2 sentence LLM profile summary |

## Scoring formula

Each keyword group contributes equally within its category. A group is satisfied when **any** of its alternatives is matched.

$$\text{score} = w_{\text{must}} \times \frac{\text{must groups matched}}{\text{total must groups}} + w_{\text{nice}} \times \frac{\text{nice groups matched}}{\text{total nice groups}}$$

If only one category is configured, it carries 100% of the score.

## Building from source

**Linux / macOS**

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
bash build.sh
# output: dist/documents-classifier
```

**Windows**

```powershell
.\build-windows.ps1
# output: dist\documents-classifier.exe
```

## CI/CD

| Workflow | Trigger | Action |
|---|---|---|
| PR Validation | Pull request → `main` | Runs `ruff` linter |
| Release Please | Push → `main` | Opens a release PR; merging it tags the release |
| Build Binaries | Push `v*` tag / manual | Builds Linux + Windows binaries and attaches them to the release |

Releases follow [Conventional Commits](https://www.conventionalcommits.org/):

| Commit prefix | Version bump |
|---|---|
| `fix: ...` | patch — `0.1.1` |
| `feat: ...` | minor — `0.2.0` |
| `feat!:` / `BREAKING CHANGE:` | major — `1.0.0` |

## Requirements

- A GitHub account with [GitHub Models](https://github.com/marketplace/models) access (for LLM mode)
- `GITHUB_TOKEN` with GitHub Models access enabled (for LLM mode)
