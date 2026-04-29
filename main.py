from models.player import Player
from models.tournament import Tournament
from models.match import Match

from services.pairing import swiss_pairing
from services.scoring import apply_match_result
from services.tiebreakers import OMW, OOMW, SSRL

import random

def print_round(matches, round_number):
    print(f"\n=== Rodada {round_number} ===")

    for i, (p1, p2) in enumerate(matches, start=1):
        if p2 is None:
            print(f"{i}. {p1.name} recebeu BYE")
        else:
            print(f"{i}. {p1.name} vs {p2.name}")


def get_result_input(p1, p2):
    while True:
        result = input(f"Resultado ({p1.name} vs {p2.name}) [1/2/0]: ").strip()
        if result in {"1", "2", "0"}:
            return result
        print("Entrada inválida. Use 1, 2 ou 0.")


def play_round(tournament):
    round_obj = tournament.start_new_round()

    pairings = swiss_pairing(tournament)

    matches = []

    for p1, p2 in pairings:
        match = Match(p1, p2, round_obj.number)
        matches.append(match)

    round_obj.matches = matches

    print_round(pairings, round_obj.number)

    for match in matches:

        if match.is_bye():
            apply_match_result(match)
            continue

        result = get_result_input(match.p1, match.p2)

        if result == "1":
            match.winner = match.p1
        elif result == "2":
            match.winner = match.p2
        else:
            match.winner = None  # double loss

        apply_match_result(match)


def print_standings(tournament):
    print("\n=== Classificação ===")

    ranked = sorted(
        tournament.players,
        key=lambda p: (
            p.points,
            OMW(p),
            OOMW(p),
            SSRL(p, tournament)
        ),
        reverse=True
    )

    for i, p in enumerate(ranked, start=1):
        print(
            f"{i}. {p.name} - {p.points} pts | "
            f"OMW: {OMW(p):.2f} | "
            f"OOMW: {OOMW(p):.2f} | "
            f"SSRL: {SSRL(p, tournament)}"
        )

def main():
    try:
        with open('players.txt', 'r', encoding='utf-8') as f:
            nomes = [linha.strip() for linha in f if linha.strip()]
    except FileNotFoundError:
        print("Erro: O arquivo 'players.txt' não foi encontrado.")
        return

    num_players = len(nomes)
    
    if num_players == 0:
        print("O arquivo está vazio. Adicione nomes.")
        return

    print(f"Número de jogadores carregados: {num_players}")
    num_rounds = int(input("Número de rodadas: "))

    random.shuffle(nomes)
    
    players = [Player(i, nome) for i, nome in enumerate(nomes)]
    tournament = Tournament(players)

    for _ in range(num_rounds):
        play_round(tournament)
        print_standings(tournament)

    print("\n=== Torneio finalizado ===")

if __name__ == "__main__":
    main()