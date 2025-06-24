# Implementation strategy for Gym interface (reset and step)
# To "reset" the environment, the game will be restored to its initial state.
# To "step" the environement, the specified action will be taken (by piping it to the AI function) 
#   and the state changed appropriately.  If the next moves belongs to the other player, these moves 
#   will also be immediately taken. The resulting
#   state and the accumulated reward will then be returned as the result of the originally specified
#   action. The simulation pauses, waiting for the next specified action.

import server
import asyncio
import gym
import map
import numpy as np
import ai.gym_ai_surrogate
import json


class Args:
    def __init__(self, scenario="plain2v1.scn", v=False, blueAI="passive", redAI="passive", blueNeuralNet=None, redNeuralNet=None, blueReplay=None, redReplay=None, blueSubAIs=[], redSubAIs=[], openSocket=False, scenarioSeed=None, scenarioCycle=0, nReps=0):
        self.scenario = scenario
        self.v = v
        self.blueAI = blueAI
        self.redAI = redAI
        self.blueNeuralNet = blueNeuralNet
        self.redNeuralNet = redNeuralNet
        self.blueReplay = blueReplay
        self.redReplay = redReplay
        self.openSocket = openSocket
        self.exitWhenTerminal = False
        self.scenarioSeed = scenarioSeed
        self.scenarioCycle = scenarioCycle
        self.nReps = -1 # next-game only happens on explicit reset()
        self.blueDepthLimit = None
        self.redDepthLimit = None
        self.blueSubAIs = json.dumps(blueSubAIs)
        self.redSubAIs = json.dumps(redSubAIs)
        self.blueSearch = False
        self.redSearch = False
        
class GymEnvironment(gym.Env):
    def __init__(self, role="blue", versusAI="passive", versusNeuralNet=None, scenario="plain2v1.scn", saveReplay=False, actions19=True, ai="gym", openSocket=False, verbose=False, scenarioSeed=None, scenarioCycle=0):
        # ai should be one of: "gym", "gymx2", "gym12", "gym13", "gym14"
        self.role = role
        if role=="red":
            redAI = ai
            redNeuralNet = None
            blueAI = versusAI
            blueNeuralNet = versusNeuralNet
        else:
            redAI = versusAI
            redNeuralNet = versusNeuralNet
            blueAI = ai
            blueNeuralNet = None
        self.args = Args(blueAI=blueAI, redAI=redAI, blueNeuralNet=blueNeuralNet, redNeuralNet=redNeuralNet, scenario=scenario, v=verbose, openSocket=openSocket, scenarioSeed=scenarioSeed, scenarioCycle=scenarioCycle)
        server.init(self.args)
        map_dim = server.mapDimensionBackdoor()
        if ai=="gymx2":
            # Doubled coordinates
            dim = (map_dim['height']*2+1, map_dim['width']) # Must be set to agree with scenario.
        else:
            dim = (map_dim['height'], map_dim['width']) # Must be set to agree with scenario.
        if actions19:
            self.action_space = gym.spaces.Discrete(19) # Moves/fires to/at up to two hexes away
        else:
            self.action_space = gym.spaces.Discrete(7) # Moves/fires to/at neighbor hexes only
        nFeatures = server.getGymAI().getNFeatures()
        self.observation_space = gym.spaces.Box(low=0.0, high=1.0, shape=(nFeatures, dim[0], dim[1]), dtype=np.float32)
        self.metadata = {'render.modes': ['human']}
        self.reward_range = (-np.inf, np.inf)
    def reset(self):
        return server.reset()
    def close(self):
        pass
    def render(self):
        pass
    def step(self, action):
        # Illegal action (off-map move attempt) should be converted to a no-op
        msg = server.getGymAI().actionMessageDiscrete(action)
        if msg is not None:
            server.addMessageRunLoop(msg)
        return server.getGymAI().action_result()

