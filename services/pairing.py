from collections import defaultdict
from functools import cached_property
from services.tiebreakers import OMW, OOMW, SSRL


def can_play(p1, p2):
    return not p1.has_played(p2)

def build_tiebreaker(players, tournament):
    #Calcula OMW/OOMW/SSRL uma única vez por player
    return {
        p: (p.points, 
            OMW(p), 
            OOMW(p), 
            SSRL(p, tournament))
        for p in players
    }


def rank_players(players, cache):
    return sorted(players, key=lambda p: cache[p], reverse=True)

def try_pairing(group):
    """
    Backtracking com poda: se nenhum adversário válido existe para p1,
    falha imediatamente sem explorar permutações inúteis.
    """
    if not group:
        return []

    p1 = group[0]
    rest_base = group[1:]  # evita recriar a fatia dentro do loop

    for i, p2 in enumerate(rest_base):
        if not can_play(p1, p2):
            continue

        # constrói rest sem p2
        rest = rest_base[:i] + rest_base[i + 1:]
        result = try_pairing(rest)

        if result is not None:
            return [(p1, p2)] + result

    return None

def group_by_score(players):
    groups = defaultdict(list)
    for p in players:
        groups[p.points].append(p)
    return groups

def assign_bye(players, cache):
    eligible = [p for p in players if not p.had_bye] or players
    # menor pontuação leva o bye → ordem crescente, pega [0]
    return sorted(eligible, key=lambda p: cache[p])[0]

def pair_group(group):
    pairing = try_pairing(group)
    if pairing:
        return pairing

    # fallback guloso
    pairs = []
    used = set()

    for i, p1 in enumerate(group):
        if p1 in used:
            continue
        for p2 in group[i + 1:]:
            if p2 not in used and can_play(p1, p2):
                pairs.append((p1, p2))
                used.add(p1)
                used.add(p2)
                break

    return pairs


def swiss_pairing(tournament):
    players = tournament.players

    # calcula tiebreakers apenas uma vez
    cache = build_tiebreaker(players, tournament)

    ranked = rank_players(players, cache)
    groups = group_by_score(ranked)

    matches = []
    float_down = None
    unpaired = []

    for score in sorted(groups.keys(), reverse=True):
        group = list(groups[score])

        if float_down:
            group.append(float_down)
            float_down = None

        group = rank_players(group, cache)  # usa cache, não recalcula

        if len(group) % 2 == 1:
            float_down = group.pop()

        matches.extend(pair_group(group))

    if float_down:
        unpaired.append(float_down)

    if unpaired:
        bye = assign_bye(unpaired, cache)
        matches.append((bye, None))

    return matches