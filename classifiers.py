"""CV classification: LLM-based and fast keyword-matching implementations."""

import json
import re

from openai import OpenAI

SYSTEM_PROMPT = (
    "You are a precise CV/resume analyser. "
    "You identify which skills or concepts are semantically present in a candidate's CV, "
    "including synonyms, adjacent terms, and demonstrated experience — not only exact matches. "
    "Always respond with valid JSON only, no additional text."
)

USER_TEMPLATE = """\
Analyse the CV below and determine which keywords from the two lists are present.

Must-have keywords: {must_keywords}
Nice-to-have keywords: {nice_keywords}

Return a JSON object with exactly this structure:
{{
  "matched_must": ["<keyword>", ...],
  "matched_nice": ["<keyword>", ...],
  "keyword_details": {{
    "<keyword>": {{
      "found": true,
      "confidence": 0.95,
      "evidence": "short quote or note from the CV"
    }}
  }},
  "summary": "1-2 sentence profile summary"
}}

Only include a keyword in matched_must / matched_nice when you are reasonably confident it is present.
Use keyword_details to explain every keyword from both lists (found or not).

CV TEXT (truncated to 8000 chars):
---
{cv_text}
---
"""


def classify_cv(
    client: OpenAI,
    model: str,
    cv_text: str,
    must_keywords: list[str],
    nice_keywords: list[str],
) -> dict:
    """Call the LLM to identify matched keywords in a CV."""
    prompt = USER_TEMPLATE.format(
        must_keywords=json.dumps(must_keywords),
        nice_keywords=json.dumps(nice_keywords),
        cv_text=cv_text[:8000],
    )
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        response_format={"type": "json_object"},
        temperature=0.1,
    )
    content = response.choices[0].message.content
    if not content:
        raise ValueError("LLM returned an empty response; cannot parse JSON")
    return json.loads(content)


def classify_cv_keyword(
    cv_text: str,
    must_keywords: list[str],
    nice_keywords: list[str],
) -> dict:
    """Fast regex-based keyword matching — no LLM or network required."""
    matched_must: list[str] = []
    matched_nice: list[str] = []
    keyword_details: dict[str, dict] = {}

    def _scan(keywords: list[str], matched: list[str]) -> None:
        for kw in keywords:
            found = bool(re.search(r"(?<!\w)" + re.escape(kw) + r"(?!\w)", cv_text, re.IGNORECASE))
            if found:
                matched.append(kw)
            keyword_details[kw] = {
                "found": found,
                "confidence": 1.0 if found else 0.0,
                "evidence": "keyword scan",
            }

    _scan(must_keywords, matched_must)
    _scan(nice_keywords, matched_nice)

    return {
        "matched_must": matched_must,
        "matched_nice": matched_nice,
        "keyword_details": keyword_details,
        "summary": "Keyword scan only — no LLM summary.",
    }
