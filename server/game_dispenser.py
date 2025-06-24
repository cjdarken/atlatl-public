import game

class ScenarioGeneratorGameDispenser():
    def __init__(self,scenario_generator):
        self.scenario_generator = scenario_generator
    def get_next_game(self):
        scenarioPo = self.scenario_generator()
        return game.Game(scenarioPo)

# Used by gameserver unit test
class ConstantGameDispenser():
    def __init__(self,game):
        self.game = game
    def get_next_game(self):
        return self.game