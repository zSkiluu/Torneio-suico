class Tournament:
    def __init__(self, players):
        self.players = players
        self.rounds = []  # lista de Round
        self.current_round_number = 0

    def start_new_round(self):
        self.current_round_number += 1
        new_round = Round(self.current_round_number)
        self.rounds.append(new_round)
        return new_round
    
    def add_match(self, match):
        if not self.rounds:
            raise Exception("Nenhuma rodada iniciada")

        self.rounds[-1].matches.append(match)

    def all_matches(self):
        return [
            match
            for round in self.rounds
            for match in round.matches
        ]
    
class Round:
    def __init__(self, number):
        self.number = number
        self.matches = []

