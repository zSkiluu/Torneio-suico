from collections import defaultdict
from functools import cached_property
from services.tiebreakers import OMW, OOMW, SSRL


def can_play(p1, p2):
    return not p1.has_played(p2)


# Points (P) / Oponent's Match Win-rate(OMW) / Oponent's Oponent's Match Win-rate(OOMW) / Sum of the Square of the Round Lost(SSRL)
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

def global_try_pairing(players):
    if not players:
        return []

    p1 = players[0]
    rest_base = players[1:]

    for i, p2 in enumerate(rest_base):
        if not can_play(p1, p2):
            continue

        # Cria a nova sub-lista excluindo p1 (já fora) e p2 (índice i)
        rest = rest_base[:i] + rest_base[i + 1:]
        
        # Tenta resolver o restante da chave
        result = global_try_pairing(rest)

        # Se retornou uma lista válida, caminho perfeito
        if result is not None:
            return [(p1, p2)] + result

    # Falhou em encontrar adversário válido para p1 nesta ramificação
    return None

def group_by_score(players):
    groups = defaultdict(list)
    for p in players:
        groups[p.points].append(p)
    return groups

def assign_bye(players, cache):
    eligible = [p for p in players if not getattr(p, "had_bye", False)] or players
    # menor pontuação leva o bye → ordem crescente, pega [0]
    return sorted(eligible, key=lambda p: cache[p])[0]

def pair_group(group):
    pairing = try_pairing(group)
    if pairing:
        return pairing

    # fallback
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
            
    leftover = [p for p in group if p not in used]
    if leftover:
        # ordena por pontuação para ao menos criar confrontos razoáveis
        while len(leftover) >= 2:
            p1 = leftover.pop(0)
            p2 = leftover.pop(0)
            pairs.append((p1, p2))

        if leftover:
            # número ímpar após tudo: float down ou bye tratado pelo caller
            pairs.append((leftover[0], None))

    return pairs


def swiss_pairing(tournament):
    players = list(tournament.players)

    cache = build_tiebreaker(players, tournament)
    ranked = rank_players(players, cache)

    matches = []
    bye_player = None
    pairing_pool = ranked

    if len(ranked) % 2 == 1:
        bye_player = assign_bye(ranked, cache)
        pairing_pool = [p for p in ranked if p != bye_player]

    pairing_result = global_try_pairing(pairing_pool)

    if pairing_result is not None:
        matches.extend(pairing_result)
    else:
        fallback_pairs = pair_group(pairing_pool)
        matches.extend(fallback_pairs)

    if bye_player:
        matches.append((bye_player, None))

    return matches