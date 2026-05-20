"""Config file loading and validation."""

import yaml


def load_config(path: str) -> dict:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def validate_config(cfg: dict) -> list[str]:
    """Return a list of human-readable error strings (empty list = valid)."""
    errors: list[str] = []

    if not isinstance(cfg, dict):
        return ["config file must be a YAML mapping (key: value pairs), not a list or scalar"]

    must_keywords = cfg.get("must_keywords", [])
    nice_keywords = cfg.get("nice_keywords", [])
    if not isinstance(must_keywords, list):
        errors.append("must_keywords must be a YAML list (e.g. [Python, SQL])")
    if not isinstance(nice_keywords, list):
        errors.append("nice_keywords must be a YAML list (e.g. [Docker, Kubernetes])")

    if isinstance(must_keywords, list):
        non_str = [repr(k) for k in must_keywords if not isinstance(k, str)]
        if non_str:
            errors.append(f"must_keywords contains non-string item(s): {', '.join(non_str)}")
        blank = [repr(k) for k in must_keywords if isinstance(k, str) and not k.strip()]
        if blank:
            errors.append(f"must_keywords contains blank item(s): {', '.join(blank)}")
        no_alts = [
            repr(k) for k in must_keywords
            if isinstance(k, str) and k.strip() and not any(a.strip() for a in k.split(","))
        ]
        if no_alts:
            errors.append(
                f"must_keywords has entries with no valid alternatives after OR-splitting "
                f"(check for stray commas): {', '.join(no_alts)}"
            )
    if isinstance(nice_keywords, list):
        non_str = [repr(k) for k in nice_keywords if not isinstance(k, str)]
        if non_str:
            errors.append(f"nice_keywords contains non-string item(s): {', '.join(non_str)}")
        blank = [repr(k) for k in nice_keywords if isinstance(k, str) and not k.strip()]
        if blank:
            errors.append(f"nice_keywords contains blank item(s): {', '.join(blank)}")
        no_alts = [
            repr(k) for k in nice_keywords
            if isinstance(k, str) and k.strip() and not any(a.strip() for a in k.split(","))
        ]
        if no_alts:
            errors.append(
                f"nice_keywords has entries with no valid alternatives after OR-splitting "
                f"(check for stray commas): {', '.join(no_alts)}"
            )

    if isinstance(must_keywords, list) and isinstance(nice_keywords, list):
        if not must_keywords and not nice_keywords:
            errors.append(
                "must_keywords and nice_keywords are both empty — at least one keyword is required"
            )

    try:
        must_weight = float(cfg.get("must_weight", 0.7))
        nice_weight = float(cfg.get("nice_weight", 0.3))
        pass_threshold = float(cfg.get("pass_threshold", 0.6))
    except (TypeError, ValueError) as exc:
        errors.append(f"Numeric config value error: {exc}")
        return errors

    if not 0 <= must_weight <= 1:
        errors.append(f"must_weight ({must_weight}) must be between 0.0 and 1.0")
    if not 0 <= nice_weight <= 1:
        errors.append(f"nice_weight ({nice_weight}) must be between 0.0 and 1.0")
    if abs(must_weight + nice_weight - 1.0) > 1e-6:
        errors.append(
            f"must_weight ({must_weight}) + nice_weight ({nice_weight}) must sum to 1.0"
        )
    if not 0 <= pass_threshold <= 1:
        errors.append(
            f"pass_threshold ({pass_threshold}) must be between 0.0 and 1.0"
        )

    llm_cfg = cfg.get("llm")
    if llm_cfg is not None and not isinstance(llm_cfg, dict):
        errors.append("llm must be a YAML mapping (e.g. llm:\\n  model: gpt-4o-mini)")

    out_cfg = cfg.get("output", {})
    if out_cfg is not None and not isinstance(out_cfg, dict):
        errors.append("output must be a YAML mapping (e.g. output:\\n  csv_file: results.csv)")
    elif isinstance(out_cfg, dict):
        for key in ("top_n", "bottom_n"):
            val = out_cfg.get(key)
            if val is not None:
                try:
                    int_val = int(val)
                except (TypeError, ValueError):
                    errors.append(f"output.{key} must be an integer, got: {repr(val)}")
                else:
                    if int_val < 0:
                        errors.append(f"output.{key} ({int_val}) must be >= 0")
        workers_val = out_cfg.get("workers")
        if workers_val is not None:
            try:
                w = int(workers_val)
            except (TypeError, ValueError):
                errors.append(f"output.workers must be a positive integer, got: {repr(workers_val)}")
            else:
                if w < 1:
                    errors.append(f"output.workers ({w}) must be >= 1")

    return errors
