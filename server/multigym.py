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
#import ai.gym_ai_surrogate
import json

class Args:
    def __init__(self, scenario="2v1-5x5.scn", v=False, blueAI="passive", redAI="passive", blueNeuralNet=None, redNeuralNet=None, blueReplay=None, redReplay=None, blueSubAIs=[], redSubAIs=[], openSocket=False, scenarioSeed=None, scenarioCycle=0, nReps=0):
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
        
class GymEnvironment(gym.Env):
    def __init__(self, role="blue", subAIs=["pass","agg"],versusAI="passive", versusNeuralNet=None, scenario="2v1-5x5.scn", saveReplay=False, actions19=True, openSocket=False, verbose=False, scenarioSeed=None, scenarioCycle=0):
        # ai should be one of: "gym", "gymx2", "gym12", "gym13", "gym14"
        self.role = role
        if role=="red":
            redAI = "multigym"
            redNeuralNet = None
            blueAI = versusAI
            blueNeuralNet = versusNeuralNet
        else:
            redAI = versusAI
            redNeuralNet = versusNeuralNet
            blueAI = "multigym"
            blueNeuralNet = None
        self.args = Args(blueAI=blueAI, redAI=redAI, blueNeuralNet=blueNeuralNet, redNeuralNet=redNeuralNet, blueSubAIs=subAIs, redSubAIs=subAIs, scenario=scenario, v=verbose, openSocket=openSocket, scenarioSeed=scenarioSeed, scenarioCycle=scenarioCycle)
        server.init(self.args)
        map_dim = server.mapDimensionBackdoor()
        dim = (map_dim['height'], map_dim['width']) # Must be set to agree with scenario.
        self.action_space = gym.spaces.Discrete(len(subAIs)) 
        nFeatures = 17 # Must match num layers in returned values from observation.py:observation()
        self.observation_space = gym.spaces.Box(low=0.0, high=1.0, shape=(nFeatures, dim[0], dim[1]), dtype=np.float32)
        self.metadata = {'render.modes': ['human']}
        self.reward_range = (-np.inf, np.inf)
        server.getGymAI().setSubAIs(subAIs)
    def reset(self):
        return server.reset()
    def close(self):
        pass
    def render(self):
        pass
    def step(self, action):
        # Illegal action (off-map move attempt) should be converted to a no-op
        msgD = server.getGymAI().actionMessageDiscrete(action)
        if msgD is not None:
            server.addMessageRunLoop(msgD)
        return server.getGymAI().action_result()
    
if __name__=="__main__":
    env = GymEnvironment()
    obs = server.reset()
    terminal = False
    while not terminal:
        #print(f'reset returns {obs}')
        action = env.action_space.sample()
        print(f'sample of action space: {action}')
        obs, reward, terminal, info = env.step(action)
    print(f'game over {info}')


