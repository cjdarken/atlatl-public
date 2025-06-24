from .base import AI
import asyncio
import websockets
import json
import argparse
import random
import operator
import math
import hashlib

# This AI has a representation of the map and units, and updates the unit representation as it changes
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import map
import unit
import status
from game import Game

import colorsys
import numpy as np
import scipy
from scipy.sparse import dok_matrix
import mobility
import combat

class PassAggFpAI(AI):
    def getPosture(self):
        str_red = 0
        str_blue = 0
        for unt in self.unitData.units():
            if unt.ineffective:
                continue
            if unt.faction=="red":
                str_red += unt.currentStrength
            elif unt.faction=="blue":
                str_blue += unt.currentStrength
        if self.role=="red" and str_red>=str_blue:
            posture = "attack"
        elif self.role=="blue" and str_blue>=str_red:
            posture = "attack"
        else:
            posture = "defense"
        return posture       
    def euclideanDistanceToOpfor(self, hex):
        xA = hex.x_grid
        yA = hex.y_grid
        closest = None
        closest_dist = float('inf')
        if not self.unitData.units():
            return float('inf')
        for target in self.unitData.units():
            if target.faction == self.role or target.ineffective or not target.hex:                 
                continue
            xB = target.hex.x_grid
            yB = target.hex.y_grid
            dist = map.gridDistance(xA,yA,xB,yB)
            if dist < closest_dist:
                closest_dist = dist
                closest = target
        return closest_dist
    def euclideanDistanceToCities(self, state, hex):
        xA = hex.x_grid
        yA = hex.y_grid
        closest_dist = float('inf')
        statusData = state["status"]
        if statusData['cityOwner']:
            for city_id in statusData['cityOwner']:
                xB = self.mapData.hexIndex[city_id].x_grid
                yB = self.mapData.hexIndex[city_id].y_grid
                dist = map.gridDistance(xA,yA,xB,yB)
                if dist < closest_dist:
                    closest_dist = dist  
        return closest_dist
    def _scoreHex(self, state, hex, posture):
        score = 1/(1+self.euclideanDistanceToCities(state, hex))
        if posture=="attack":
            score += 1/(1+self.euclideanDistanceToOpfor(hex))
        return score
    def _positionScore(self, game, state, posture):
        score = 0
        for unt in state["units"]:
            if unt["faction"]!=self.role or unt["ineffective"]:
                continue
            hex = self.mapData.hexIndex[unt["hex"]]
            score += self._scoreHex(state, hex, posture)
        return score
    def _legalActionSequences(self, game, state, partialSequence=[], verbose=False):     
        # state_str = json.dumps(state).encode()
        # state_hashobj = hashlib.sha1(state_str)
        # state_hex = state_hashobj.hexdigest()
        # print(f'in state {state_hex[:5]}')
        legal_actions = game.legal_actions(state)
        if not legal_actions or state["status"]["onMove"]!=self.role:
            yield state, partialSequence
            return
        for action in legal_actions:
            postaction_state = game.transition(state, action)
            yield from self._legalActionSequences(game,postaction_state,partialSequence+[action],verbose)
    def findBestActions(self, game, state, verbose=False):   
        best_actions = []
        if self.role == "blue":
            best_score = float("-inf")
            comparison_op = operator.gt
            position_score_sign = 1
        else:
            best_score = float("inf")
            comparison_op = operator.lt
            position_score_sign = -1
        for resulting_state,actions in self._legalActionSequences(game,state):
            atlatl_score = resulting_state["status"]["score"]
            position_score = position_score_sign * self._positionScore(game,resulting_state,self.getPosture())
            score = atlatl_score + position_score
            if comparison_op(score,best_score):
                best_actions, best_score = actions, score
        best_actions.reverse()
        return best_actions