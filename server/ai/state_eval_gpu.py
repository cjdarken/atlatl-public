from .base import AI

#import asyncio
#import websockets
import json
#import argparse
#import random
#import operator
#import math
import collections
#import hashlib

# This AI has a representation of the map and units, and updates the unit representation as it changes
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import map
import unit
import status
from game import Game

import torch
sys.path.append("portabletorch")
import portabletorch

#import colorsys
#import numpy as np
#import scipy
#from scipy.sparse import dok_matrix
#import mobility
#import combat
import observation
from torch.utils.data import DataLoader

class StateEvalGPUAI(AI):
    def __init__(self, role, kwargs={}):
        AI.__init__(self, role, kwargs={})
        self.SAPair = collections.namedtuple('SAPair', ['state', 'actions'])
        self.device = ("cuda" if torch.cuda.is_available() else "cpu")
        print(f'Using device {self.device}')
        self.batch_size = 512
        if kwargs["neuralNet"]=="shared":
            self.nnValueFn = kwargs["neuralNetObj"]
        else:
            portable = portabletorch.PortableTorch.load(kwargs["neuralNet"])
            self.nnValueFn = portable.model.to(self.device)
        self.partialPly = False
        if kwargs["partialPly"]:
            self.partialPly = True
        self.depth_limit = 1
        if "depthLimit" in kwargs:
            self.depth_limit = int(kwargs["depthLimit"])
    def getNeuralNet(self):
        return self.nnValueFn
    def singleActions(self, game, start_state):
        result = []
        legal_actions = game.legal_actions(start_state)
        if not legal_actions or start_state["status"]["onMove"]!=self.role:
            return result
        for action in legal_actions:
            postaction_state = game.transition(start_state, action)
            result.append( self.SAPair(postaction_state,[action]))
        return result
    def allActionSequences(self, game, start_state, remainingDepth=1, dupCheck=None):
        # Return states and actions 
        result = []
        legal_actions = game.legal_actions(start_state)
        if not legal_actions or start_state["status"]["onMove"]!=self.role or remainingDepth==0:
            result.append(self.SAPair(start_state,[]))
            return result
        for action in legal_actions:
            postaction_state = game.transition(start_state, action)
            if isinstance(dupCheck, dict):
                key = json.dumps(postaction_state)
                if key in dupCheck:
                    continue
                dupCheck[key] = True
            pairs = self.allActionSequences(game, postaction_state, remainingDepth-1, dupCheck)
            for pr in pairs:
                result.append( self.SAPair(pr.state,[action]+pr.actions) )
        return result
    def findBestActions(self, game, state):  
        if self.partialPly:
            sapairs = self.allActionSequences(game, state, remainingDepth=self.depth_limit, dupCheck={}) 
        else:
            sapairs = self.allActionSequences(game, state, remainingDepth=float('inf'), dupCheck={}) 
        observation_list = [observation.observation(game, st) for st,_ in sapairs]
        observation_tensor = torch.stack(observation_list).to(self.device)
        loader = DataLoader(observation_tensor, batch_size=self.batch_size)
        with torch.no_grad():
            pred = torch.tensor([]).to(self.device)
            for batch, X in enumerate(loader):
                pred = torch.cat((pred, self.nnValueFn(X)), dim=0)
            if self.role=="blue":
                best_index = torch.argmax(pred).item()
            else:
                best_index = torch.argmin(pred).item()
            best_score = pred[best_index]
            best_actions = sapairs[best_index].actions[::-1]
        if self.partialPly:
            best_actions = [best_actions[len(best_actions)-1]]
        return best_actions
    
