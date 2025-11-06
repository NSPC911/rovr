def scorer(query: str, target: str) -> float:
    """Score a query based on the target

    Args:
        query(str): The search string to match against
        target(str): The string to evaluate for matching

    Returns:
        float: between 0 and 1, 0 is non-existent, 1 is exact
    """
    # string validation
    if not query:
        return 1.0

    if not target:
        return 0.0

    query_lower = query.lower()
    target_lower = target.lower()

    # exact
    if query_lower == target_lower:
        return 1.0

    match_positions = []
    target_idx = 0

    for query_char in query_lower:
        found = False
        while target_idx < len(target_lower):
            if target_lower[target_idx] == query_char:
                match_positions.append(target_idx)
                target_idx += 1
                found = True
                break
            target_idx += 1

        if not found:
            # char not in seq then die
            return 0.0

    # match first char
    first_pos_score = 1.0 - (match_positions[0] / len(target_lower))

    # match char spread
    if len(match_positions) == 1:
        spread_score = 1.0
    else:
        span = match_positions[-1] - match_positions[0] + 1
        ideal_span = len(query_lower)
        max_span = len(target_lower) - match_positions[0]

        if span == ideal_span:
            spread_score = 1.0
        else:
            spread_score = 1.0 - ((span - ideal_span) / max_span)

    # consecutive matches
    consecutive_count = 0
    for i in range(1, len(match_positions)):
        if match_positions[i] - match_positions[i - 1] == 1:
            consecutive_count += 1

    consecutive_score = (
        consecutive_count / (len(match_positions) - 1)
        if len(match_positions) > 1
        else 0.0
    )

    # density
    density_score = len(query_lower) / len(target_lower)

    final_score = (
        first_pos_score * 0.25
        + spread_score * 0.35
        + consecutive_score * 0.25
        + density_score * 0.15
    )

    return min(1.0, max(0.0, final_score))
