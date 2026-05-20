# Documents Classifier

LLM-powered documents classifier — scores PDF and `.docx` documents against a configurable keyword list using the **GitHub Models API** (no paid subscription needed, just a GitHub token).

## Setup

```bash
cd ~/bin/documents-classifier
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Export your GitHub token (must have GitHub Models access enabled):

```bash
export GITHUB_TOKEN=ghp_...
```

## Configuration (`config.yaml`)

| Key | Description |
|---|---|
| `must_keywords` | Skills that count for 70 % of the score |
| `nice_keywords` | Skills that count for the remaining 30 % |
| `pass_threshold` | Minimum score (0–1) to be labelled **PASS** |
| `llm.model` | Any GitHub-hosted model (e.g. `gpt-4o`, `gpt-4o-mini`) |
| `output.copy_files` | `true` = copy originals; `false` = move them |

## Usage

```bash
python classifier.py /path/to/cvs/
# or with a custom config:
python classifier.py /path/to/cvs/ --config /path/to/config.yaml
```

## Output

| File | Description |
|---|---|
| `<documents_folder>/results.csv` | One row per document with score, matched/missing keywords, summary |
| `<documents_folder>/classified/pass/` | document that met the threshold |
| `<documents_folder>/classified/fail/` | document that did not meet the threshold |

### CSV columns

| Column | Description |
|---|---|
| `filename` | Original file name |
| `result` | `PASS`, `FAIL`, or `ERROR` |
| `score` | 0.000–1.000 composite score |
| `matched_must` | Must-have keywords detected (semicolon-separated) |
| `missing_must` | Must-have keywords **not** detected |
| `matched_nice` | Nice-to-have keywords detected |
| `summary` | 1-2 sentence LLM profile summary |

## Scoring formula

$$\text{score} = 0.7 \times \frac{|\text{matched\_must}|}{|\text{must\_keywords}|} + 0.3 \times \frac{|\text{matched\_nice}|}{|\text{nice\_keywords}|}$$

If only one category is configured, it carries 100 % of the score.
