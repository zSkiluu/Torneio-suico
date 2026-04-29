class Player:
    def __init__(self, id, name):
        self.id = id
        self.name = name
        self.points = 0
        self.opponents = []
        self.results = []
        self.had_bye = False
        self.loss_rounds = []  
        self.matches_played = 0

    def add_opponent(self, player):
        self.opponents.append(player)

    def has_played(self, opponent):
        return opponent in self.opponents