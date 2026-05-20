"""CV score calculation from classification results."""


def calculate_score(
    result: dict,
    must_groups: list[list[str]],
    nice_groups: list[list[str]],
    must_weight: float = 0.7,
    nice_weight: float = 0.3,
) -> float:
    """
    Score = must_weight × (satisfied must groups / total must groups)
          + nice_weight × (satisfied nice groups / total nice groups).
    A group is satisfied when at least one of its alternative keywords is matched.
    If a category is empty its weight is redistributed entirely to the other.
    """
    matched_must = set(result.get("matched_must", []))
    matched_nice = set(result.get("matched_nice", []))

    must_ratio = (
        min(1.0, sum(1 for g in must_groups if any(a in matched_must for a in g)) / len(must_groups))
        if must_groups
        else None
    )
    nice_ratio = (
        min(1.0, sum(1 for g in nice_groups if any(a in matched_nice for a in g)) / len(nice_groups))
        if nice_groups
        else None
    )

    if must_ratio is None and nice_ratio is None:
        return 0.0
    if must_ratio is None:
        return round(nice_ratio, 3)
    if nice_ratio is None:
        return round(must_ratio, 3)
    return round(must_ratio * must_weight + nice_ratio * nice_weight, 3)
