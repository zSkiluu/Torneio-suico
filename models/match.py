class Match:
    def __init__(self, p1, p2, round_number):
        self.p1 = p1
        self.p2 = p2
        self.winner = None
        self.round_number = round_number
        self.result_applied = False
    
    def is_bye(self):
        return self.p2 is None