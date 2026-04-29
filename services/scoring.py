WIN_POINTS = 3

def apply_match_result(match):

    p1 = match.p1
    p2 = match.p2

    if getattr(match, "result_applied", False):
        raise ValueError("Resultado já foi aplicado para este match")

    if match.is_bye():
        p1.points += WIN_POINTS
        p1.matches_played += 1
        p1.had_bye = True

        match.result_applied = True
        return

    if match.winner not in (p1, p2, None):
        raise ValueError("Winner inválido")

    p1.matches_played += 1
    p2.matches_played += 1
    p1.add_opponent(p2)
    p2.add_opponent(p1)

    if match.winner == p1:
        p1.points += WIN_POINTS

    elif match.winner == p2:
        p2.points += WIN_POINTS

    match.result_applied = True