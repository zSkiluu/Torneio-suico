def winrate(player):
    if player.matches_played == 0:
        return 0
    rate = player.points / (3 * player.matches_played)
    return max(0.33, rate)


def OMW(player):
    if not player.opponents:
        return 0

    return sum(winrate(op) for op in player.opponents) / len(player.opponents)


def OOMW(player):

    if not player.opponents:
        return 0

    return sum(OMW(op) for op in player.opponents) / len(player.opponents)

def SSRL(player, tournament):
    total = 0

    for round_obj in tournament.rounds:
        for match in round_obj.matches:

            if match.p2 is None:
                continue  

            if player not in (match.p1, match.p2):
                continue

            if match.winner is None:
                total += match.round_number ** 2
                continue

            if match.winner != player:
                total += match.round_number ** 2

    return total

def final_rank(players, tournament):
    return sorted(
        players,
        key=lambda p: (
            p.points,
            OMW(p),
            OOMW(p),
            SSRL(p, tournament)
        ),
        reverse=True
    )