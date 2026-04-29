from collections import defaultdict
from services.tiebreakers import OMW, OOMW, SSRL


def can_play(p1, p2):
    return not p1.has_played(p2)


def rank_players(players, tournament):
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


def try_pairing(group):
    if not group:
        return []

    p1 = group[0]

    for i in range(1, len(group)):
        p2 = group[i]

        if not can_play(p1, p2):
            continue

        rest = group[1:i] + group[i+1:]
        result = try_pairing(rest)

        if result is not None:
            return [(p1, p2)] + result

    return None


def group_by_score(players):
    groups = defaultdict(list)

    for p in players:
        groups[p.points].append(p)

    return groups


def assign_bye(players, tournament):
    eligible = [p for p in players if not p.had_bye]

    if not eligible:
        eligible = players

    return sorted(
        eligible,
        key=lambda p: (
            p.points,
            OMW(p),
            OOMW(p),
            SSRL(p, tournament)
        )
    )[0]


def pair_group(group):
    pairing = try_pairing(group)

    if pairing:
        return pairing

    pairs = []
    used = set()

    for i in range(len(group)):
        if group[i] in used:
            continue

        for j in range(i + 1, len(group)):
            if group[j] in used:
                continue

            if can_play(group[i], group[j]):
                pairs.append((group[i], group[j]))
                used.add(group[i])
                used.add(group[j])
                break

    return pairs


def swiss_pairing(tournament):
    players = tournament.players

    ranked = rank_players(players, tournament)
    groups = group_by_score(ranked)  # ✅ CORREÇÃO

    matches = []
    float_down = None
    unpaired = []

    for score in sorted(groups.keys(), reverse=True):
        group = list(groups[score])  # evita mutação

        # aplicar float
        if float_down:
            group.append(float_down)
            float_down = None

        group = rank_players(group, tournament)  # ✅ CORREÇÃO

        # ímpar → separa float
        if len(group) % 2 == 1:
            float_down = group.pop()

        pairings = pair_group(group)
        matches.extend(pairings)

    # sobrou jogador → BYE
    if float_down:
        unpaired.append(float_down)

    if unpaired:
        bye = assign_bye(unpaired, tournament)
        matches.append((bye, None))

    return matches