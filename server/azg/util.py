import json
import sys
sys.path.append("..")
from game import Game
import airegistry

def playAndScore(scenarioPo, statePo, blue_ai, red_ai):
    game = Game(scenarioPo)
    state = statePo
    params_json = json.dumps(scenarioPo)
    params_message = '{"type":"parameters", "parameters":'+params_json+'}'
    constructor, kwargs = airegistry.ai_registry[blue_ai]
    blue = constructor("blue", kwargs)
    blue.process(params_message)
    constructor, kwargs = airegistry.ai_registry[red_ai]
    red = constructor("red", kwargs)
    red.process(params_message)
    while not game.is_terminal(state):
        blue_obs = game.observation(state,"blue")
        blue_message = '{"type":"observation", "observation":'+json.dumps(blue_obs)+'}'
        blue_action = blue.process(blue_message)
        red_obs = game.observation(state,"red")
        red_message = '{"type":"observation", "observation":'+json.dumps(red_obs)+'}'
        red_action = red.process(red_message)
        if blue_action and red_action:
            raise "Both blue and red AIs are attempting to take an action"
        if blue_action:
            state = game.transition(state,json.loads(blue_action)["action"])
        if red_action:
            state = game.transition(state,json.loads(red_action)["action"])
    return game.score(state)


if __name__=="__main__":
    scenarioName = "2v1-5x5.scn"
    scenarioPo = json.load( open("../scenarios/"+scenarioName) )
    game = Game(scenarioPo)
    statePo = game.initial_state()
    value = playAndScore(scenarioPo, statePo, "pass-agg", "pass-agg")
    print("final score ",value)