import asyncio
import websockets
import json
import argparse
import numpy as np

# This AI has a representation of the map and units, and updates the unit representation as it changes
import map
import unit
import sys
sys.path.append("..")
import airegistry
import observation
import game
from stable_baselines3 import DQN, PPO

action_count = 0

class NoNegativesRewArt:
    def __init__(self, own_faction=None):
        self.negative_rewards = 0
    def engineeredReward(self, reward, unitData=None, is_terminal = False):
        # Make this function just "return(reward)" to use raw rewards
        if reward < 0:
            self.negative_rewards += 1
            # Negative rewards turn into zero
            return 0
        # Positive rewards get discounted based on the number of negative rewards
        base = 10
        reward_discount = base / (base + self.negative_rewards)
        return reward * reward_discount

class BoronRewArt:
    # Boron did not use a terminal bonus (equiv. to terminal_bonus=0)
    def __init__(self, own_faction, terminal_bonus=25):
        self.own_faction = own_faction
        self.original_strength = None
        self.terminal_bonus = terminal_bonus
    def _totalFriendlyStrength(self, ownFaction, unitData):
        sum = 0
        for unt in unitData.units():
            if not unt.ineffective and unt.faction==ownFaction:
                sum += unt.currentStrength
        return sum
    def engineeredReward(self, raw_reward, unitData, is_terminal = False):
        if self.original_strength is None:
            self.original_strength = self._totalFriendlyStrength(self.own_faction, unitData)
        current_strength = self._totalFriendlyStrength(self.own_faction, unitData)
        if raw_reward < 0:
            raw_reward = 0
        if is_terminal:
            # Experimental
            raw_reward += self.terminal_bonus
        return raw_reward * current_strength / self.original_strength

class AI:
    def __init__(self, role, kwargs={}):
        self.role = role
        self.rewart_class = BoronRewArt
        self.reset()
        self.subAIs = []
        self.mode = kwargs["mode"]
        if self.mode=="production":
            neural_net_file = kwargs["neuralNet"]
            if kwargs["dqn"]:
                self.model = DQN.load(neural_net_file)
            else:
                self.model = PPO.load(neural_net_file)
        self.setSubAIs(json.loads(kwargs["subAIs"]))
    def setSubAIs(self, subAIspecs):
        for constructor_name in subAIspecs:
            constructor, kwargs = airegistry.ai_registry[constructor_name]
            self.subAIs.append( constructor(self.role, kwargs) )
    def nextMover(self):
        for un in self.unitData.units():
            if un.faction==self.role and not self.attempted_moveD[un.uniqueId] and not un.ineffective:
                return un
        return None
    def moveMessage(self):
        action, _states = self.model.predict(self.observation())
        msg = self.actionMessageDiscrete(action)
        if msg is None:
            raise EnvironmentError("actionMessageDiscrete returned None")
        return msg
    def reset(self):
        self.accumulated_reward = 0
        self.last_terminal = None
        self.attempted_moveD = {}
        self.response_fn = None
        self.last_score = 0
        self.mapData = None
        self.unitData = None
        self.phaseCount = 0
        self.rewArt = self.rewart_class(self.role)
    def getNFeatures(self):
        return 3
    def nextMover(self):
        for un in self.unitData.units():
            if un.faction==self.role and not self.attempted_moveD[un.uniqueId] and not un.ineffective:
                return un
        return None
    def sendToServer(self, messageO):
        if self.response_fn:
            self.response_fn(messageO)
    def updateLocalState(self, obs):
        for unitObs in obs['units']:
            uniqueId = unitObs['faction'] + " " + unitObs['longName']
            un = self.unitData.unitIndex[ uniqueId ]
            un.partialObsUpdate( unitObs, self.unitData, self.mapData )
        reward = obs['status']['score'] - self.last_score
        # Reward must have its sign flipped if red is to be trained
        is_terminal = obs['status']['isTerminal']
        self.accumulated_reward += self.rewArt.engineeredReward(reward, self.unitData, is_terminal)
        self.last_score = obs['status']['score']
        self.city_owners = obs['status']['cityOwner']
    def process(self, message, response_fn):
        self.response_fn = response_fn # Store for later use
        msgD = json.loads(message)
        if msgD['type'] == "parameters":
            paramD = msgD['parameters']
            self.game = game.Game(paramD)
            # reset state variables
            self.reset()
            self.mapData = map.MapData()
            self.unitData = unit.UnitData()
            self.rewArt = self.rewart_class(self.role)
            self.phase = None
            for unt in self.unitData.units():
                if unt.faction == self.role:
                    self.attempted_moveD[unt.uniqueId] = False           
            map.fromPortable(paramD['map'], self.mapData)
            unit.fromPortable(paramD['units'], self.unitData, self.mapData)
            self.maxPhases = paramD['score']['maxPhases']
            self.state = self.game.initial_state()
            for ai in self.subAIs:
                ai.process(message, None)
            responseD = { "type":"role-request", "role":self.role}
        elif msgD['type'] == 'observation':
            obs = msgD['observation']
            self.last_obs_msg = message
            self.last_terminal = obs['status']['isTerminal']
            self.score = obs['status']['score']
            if self.last_terminal:
                if self.mode=="production":
                    responseD = None
                else: # self.mode=="training"
                    # Needed to provide final observation to gym agents
                    self.updateLocalState(obs)
                    responseD = {"type":"gym-pause"}
            elif obs['status']['onMove'] == self.role:
                if obs['status']['setupMode']:
                    self.phase = "setup"
                    responseD = { "type":"action", "action":{"type":"pass"} }
                else:
                    if self.phase != "move":
                        self.phase = "move"
                        self.phaseCount = obs['status']['phaseCount']
                        for unt in self.unitData.units():
                            if unt.faction == self.role:
                                self.attempted_moveD[unt.uniqueId] = False
                    self.updateLocalState(obs)
                    if self.mode=="production":
                        responseD = self.moveMessage() # Might be a pass
                    else:
                        if self.nextMover():
                            responseD = {"type":"gym-pause"}
                        else: # Possibly no friendlies left alive
                            responseD = { "type":"action", "action":{"type":"pass"} }
            else:
                self.phase = "wait"
                responseD = None       
        elif msgD['type'] == 'reset':
            self.reset()
            responseD = None
        else:
            raise Exception(f'Unknown message type {msgD["type"]}')
        if responseD:
            return json.dumps(responseD)
    def feature(self, fn, type):
        count = 0
        self.arrayIndex = {}
        self.inverseIndex = []
        for hexId in self.mapData.hexIndex:
            self.arrayIndex[hexId] = count
            self.inverseIndex.append(hexId)
            count += 1
        dim = self.mapData.getDimensions()
        mat = np.zeros((dim['height'],dim['width']))
        if type=="hex":
            for hexId in self.mapData.hexIndex:
                hex = self.mapData.hexIndex[hexId]
                mat[hex.y_offset, hex.x_offset] = fn(hex)
        elif type=="unit":
            for unitId in self.unitData.unitIndex:
                unt = self.unitData.unitIndex[unitId]
                hex = unt.hex
                if hex:
                    mat[hex.y_offset, hex.x_offset] = fn(unt)
        else: # type=="owner"
            for hexId in self.city_owners:
                hex = self.mapData.hexIndex[hexId]
                mat[hex.y_offset, hex.x_offset] = fn(hexId, self.city_owners)
        return mat
    def action_result(self):
        done = self.last_terminal 
        reward = self.accumulated_reward
        self.accumulated_reward = 0
        info = {'score':self.last_score}
        return (self.observation(), reward, done, info)
    def observation(self):
        return observation.observation(self.game,self.state)
    def noneOrEndMove(self):
        if self.nextMover():
            return None
        else:
            return { "type":"action", "action":{"type":"pass"} }
    def actionMessageDiscrete(self, action):
        # action is in [0..(num_subAIs-1)]
        actionS = self.subAIs[action].process(self.last_obs_msg)
        actionD = json.loads(actionS)
        return actionD
