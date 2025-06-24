import asyncio
import websockets
import json
import argparse
import numpy as np

# Allows file to be invoked from any directory and still import from parent directory and azg
import os, sys
parentpath = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
azgpath = os.path.join(parentpath, "azg")
sys.path.append(parentpath)
sys.path.append(azgpath)

from stable_baselines3 import PPO, DQN

from alphazero_observation import make_observation

# This AI has a representation of the map and units, and updates the unit representation as it changes
import map
import unit

import alphazero_game
import alphazero_nnet
import azg

default_neural_net_dir = "temp"
action_count = 0

def debugPrint(str):
    condition = False
    if condition:
        print(str)

class AI:
    evenXOffsets18 = ((0,-1), (1,-1), (1,0), (0,1), (-1,0), (-1,-1),
                        (0,-2), (1,-2), (2,-1), (2,0), (2,1), (1,1), 
                        (0,2), (-1,1), (-2,1), (-2,0), (-2,-1), (-1,-2))
    oddXOffsets18 = ((0,-1), (1,0), (1,1), (0,1), (-1,1), (-1,0),
                        (0,-2), (1,-1), (2,-1), (2,0), (2,1), (1,2), 
                        (0,2), (-1,2), (-2,1), (-2,0), (-2,-1), (-1,-1))
    class dotdict(dict):
        def __getattr__(self, name):
            return self[name]
    args = dotdict({
        'numIters': 1, # Was 1000 cjd
        'numEps': 100,              # Number of complete self-play games to simulate during a new iteration.
        'tempThreshold': 15,        #
        'updateThreshold': 0.6,     # During arena playoff, new neural net will be accepted if threshold or more of games are won.
        'maxlenOfQueue': 200000,    # Number of game examples to train the neural networks.
        'numMCTSSims': 25,          # Number of games moves for MCTS to simulate.
        'arenaCompare': 4,         # Number of games to play during arena play to determine if new net will be accepted. # Was 40 cjd
        'cpuct': 1,

        'checkpoint': './temp/',
        'load_model': False,
        'load_folder_file': ('/dev/models/8x100x50','best.pth.tar'),
        'numItersForTrainExamplesHistory': 20,
    })
    def __init__(self, role, kwargs):
        self.role = role
        # Load neural net
        if "neuralNet" in kwargs:
            neural_net_dir = kwargs["neuralNet"]
        else:
            neural_net_dir = default_neural_net_dir

        self.astar_game = alphazero_game.AtlatlGame()
        nnet = alphazero_nnet.NNetWrapper(self.astar_game)
        nnet.load_checkpoint(folder=neural_net_dir, filename='best.pth.tar')
        self.nmcts = azg.MCTS.MCTS(self.astar_game, nnet, AI.args)
        # arena = Arena(lambda x: np.argmax(nmcts.getActionProb(x, temp=0)),

        self.mapData = None
        self.unitData = None
        self.reset()
    def reset(self):
        self.attempted_moveD = {}
        self.phaseCount = 0
    def nextMover(self):
        for un in self.unitData.units():
            if un.faction==self.role and not self.attempted_moveD[un.uniqueId] and not un.ineffective:
                return un
        return None
    def moveMessage(self):
        while self.nextMover():
            debugPrint(f"processing next mover {self.nextMover().uniqueId}")

            #actionOffset = np.argmax(self.nmcts.getActionProb(self.observation(), temp=0))
            board = {"param":self.paramD, "state":self.obsD}
            #actionOffset = np.argmax(self.nmcts.getActionProb(board, temp=0))
            probs = self.nmcts.getActionProb(board, temp=1)
            #print(f'azero, moveMessage, action probs {probs}')
            actionOffset = np.argmax(probs)
            action = self.astar_game.vectorIndexActionToAtlatl(actionOffset, board)
            print(f"moveMessage action {action}")
            if action != None:
                #return action
                return {"type":"action", "action":action}
        # No next mover
        return { "type":"action", "action":{"type":"pass"} }
    def process(self, message, response_fn=None):
        msgD = json.loads(message)
        if msgD['type'] == "parameters":
            paramD = msgD['parameters']
            self.paramD = paramD
            # reset state variables
            self.mapData = map.MapData()
            self.unitData = unit.UnitData()
            self.phase = None
            for unt in self.unitData.units():
                if unt.faction == self.role:
                    self.attempted_moveD[unt.uniqueId] = False           
            map.fromPortable(paramD['map'], self.mapData)
            unit.fromPortable(paramD['units'], self.unitData, self.mapData)
            responseD = { "type":"role-request", "role":self.role}
        elif msgD['type'] == 'observation':
            obs = msgD['observation']
            self.obsD = obs
            if not obs['status']['isTerminal'] and obs['status']['onMove'] == self.role:
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
                    for unitObs in obs['units']:
                        uniqueId = unitObs['faction'] + " " + unitObs['longName']
                        un = self.unitData.unitIndex[ uniqueId ]
                        un.partialObsUpdate( unitObs, self.unitData, self.mapData )
                    responseD = self.moveMessage() # Might be a pass
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
        if self.doubledCoordinates:
            mat = np.zeros((2*dim['height']+1,dim['width']))
        else:
            mat = np.zeros((dim['height'],dim['width']))
        if type=="hex":
            for hexId in self.mapData.hexIndex:
                hex = self.mapData.hexIndex[hexId]
                x_mat, y_mat = hex.x_offset, hex.y_offset
                if self.doubledCoordinates:
                    y_mat = 2*y_mat + x_mat%2
                mat[y_mat, x_mat] = fn(hex)
        else: # type=="unit"
            for unitId in self.unitData.unitIndex:
                unt = self.unitData.unitIndex[unitId]
                hex = unt.hex
                if hex:
                    x_mat, y_mat = hex.x_offset, hex.y_offset
                    if self.doubledCoordinates:
                        y_mat = 2*y_mat + x_mat%2
                    mat[y_mat, x_mat] = fn(unt)
        return mat
    def observation(self):
        pass # virtual
    def action_result(self):
        done = self.last_terminal
        reward = self.accumulated_reward
        self.last_terminal = None # Make False???
        self.accumulated_reward = 0
        debugPrint(f'action_result returning done {done}')
        return (self.observation(), reward, done, {})
    def noneOrEndMove(self):
        if self.nextMover():
            return None
        else:
            return { "type":"action", "action":{"type":"pass"} }
    def actionMessageDiscrete(self, action):
        # Action represents the six or 18 most adjacent hexes plus wait,
        # either in range 0..6 or 0..18
        global action_count
        action_count += 1
        mover = self.nextMover()
        self.attempted_moveD[mover.uniqueId] = True
        
        debugPrint(f'gym_ai_surrogate:actionMessageDiscrete mover {mover.uniqueId} hex {mover.hex.id} action {action}')
            
        if action==0:
            debugPrint("Action was wait")
            return self.noneOrEndMove() # wait
        hex = mover.hex
        moveTargets = mover.findMoveTargets(self.mapData, self.unitData)
        fireTargets = mover.findFireTargets(self.unitData)
        if not moveTargets and not fireTargets:
            # No legal moves
            debugPrint("No legal moves")
            return self.noneOrEndMove()
        if hex.x_offset%2:
            delta = AI.oddXOffsets18[action-1]
        else:
            delta = AI.evenXOffsets18[action-1]
        to_hex_id = f'hex-{hex.x_offset+delta[0]}-{hex.y_offset+delta[1]}'
        if not to_hex_id in self.mapData.hexIndex:
            # Off-map move.
            debugPrint("Off-map move")
            return self.noneOrEndMove()
        to_hex = self.mapData.hexIndex[to_hex_id]
        if to_hex in moveTargets:
            return {"type":"action", "action":{"type":"move", "mover":mover.uniqueId, "destination":to_hex_id}}
        for fireTarget in fireTargets:
            if to_hex == fireTarget.hex:
                return {"type":"action", "action":{"type":"fire", "source":mover.uniqueId, "target":fireTarget.uniqueId}}
        # Illegal move request
        debugPrint("Illegal move")
        return self.noneOrEndMove()

class AIaz(AI):
    def __init__(self, role, kwargs):
        AI.__init__(self, role, kwargs)
    def observation(self):
        return make_observation(self.paramD, self.obsD, self.mapData, self.unitData)
