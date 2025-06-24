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

from  . import scoring

class AI(scoring.AI):
    def __init__(self, role, kwargs={}):
        super().__init__(role,kwargs)
        self.score_is_Q = False
    def scenario_available(self):
        self.runDijkstra()
    def runDijkstra(self):
        self.paths = {}
        for type in mobility.cost:
            self.paths[type] = self.runDijkstraType(type)
    def runDijkstraType(self,type):
        # Compute distances assuming mover is armor
        count = 0
        self.arrayIndex = {}
        self.inverseIndex = []
        for hexId in self.mapData.hexIndex:
            self.arrayIndex[hexId] = count
            self.inverseIndex.append(hexId)
            count += 1
        mat = dok_matrix((count,count), dtype=np.float32)
        for hexId in self.mapData.hexIndex:
            hex = self.mapData.hexIndex[hexId]
            neighs = map.getNeighborHexes(hex, self.mapData)
            for neigh in neighs:
                cost = mobility.cost[type][neigh.terrain]
                i = self.arrayIndex[hexId]
                j = self.arrayIndex[neigh.id]
                mat[i,j] = cost
        return scipy.sparse.csgraph.dijkstra(mat)
    def score_fn(self ,game, state, action):
        return self.getScore( state )
    def getScore(self, state, verbose=False):
        EPS = 1e-12
        unitData = unit.UnitData()
        unit.fromPortable(state["units"], unitData, self.mapData)
        redUnits = []
        blueUnits = []
        for unt in unitData.units():
            if unt.faction=="red":
                redUnits.append(unt)
            else:
                blueUnits.append(unt)
        action_score = 0
        weight = {}
        weight_sum = {}
        if verbose:
            print('weight computation')
        for blue in blueUnits:
            if blue.ineffective:
                continue
            iblue = self.arrayIndex[blue.hex.id]
            blue_sd = combat.range[blue.type] * 100
            for red in redUnits:
                if red.ineffective:
                    continue
                ired = self.arrayIndex[red.hex.id]
                red_sd = combat.range[red.type] * 100
                red_dist = self.paths[red.type][ired,iblue]
                blue_dist = self.paths[blue.type][iblue,ired]
                weight[blue.uniqueId,red.uniqueId] = math.exp(-blue_dist**2/blue_sd**2/2)
                weight_sum[blue.uniqueId] = weight_sum.get(blue.uniqueId,EPS) + weight[blue.uniqueId,red.uniqueId]
                weight[red.uniqueId,blue.uniqueId] = math.exp(-red_dist**2/red_sd**2/2)
                weight_sum[red.uniqueId] = weight_sum.get(red.uniqueId,EPS) + weight[red.uniqueId,blue.uniqueId]
                if verbose:
                    print(f'blue {blue.uniqueId} red {red.uniqueId} weight b-r {weight[blue.uniqueId,red.uniqueId]} weight r-b {weight[red.uniqueId,blue.uniqueId]}' )
        if verbose:
            print('score computation')
        for blue in blueUnits:
            if blue.ineffective:
                continue
            for red in redUnits:
                if red.ineffective:
                    continue
                blue_base_kill_rate = blue.currentStrength * combat.firepower[blue.type][red.type]
                red_base_kill_rate = red.currentStrength * combat.firepower[red.type][blue.type]
                red_score = red_base_kill_rate * weight[red.uniqueId,blue.uniqueId]**2/weight_sum[red.uniqueId]
                blue_score = blue_base_kill_rate * weight[blue.uniqueId,red.uniqueId]**2/weight_sum[blue.uniqueId]
                red_score /= self.heuristic_score_scale
                blue_score /= self.heuristic_score_scale
                if verbose:
                    print(f'{blue.uniqueId} {red.uniqueId} blue score {blue_score} red score {red_score}')
                action_score += blue_score - red_score
        city_base = 50
        city_sd = 60
        if self.role == "blue":
            for blue in [x for x in blueUnits if (not x.ineffective)]:
                iblue = self.arrayIndex[blue.hex.id]
                for cityS in state["status"]["cityOwner"]:
                    icity = self.arrayIndex[cityS]
                    dist = self.paths[blue.type][iblue,icity]
                    action_score += city_base * math.exp(-dist**2/city_sd**2/2)*50
        else:
            for red in [x for x in redUnits if (not x.ineffective)]:
                ired = self.arrayIndex[red.hex.id]
                for cityS in state["status"]["cityOwner"]:
                    icity = self.arrayIndex[cityS]
                    dist = self.paths[red.type][ired,icity]
                    action_score -= city_base * math.exp(-dist**2/city_sd**2/2)
        score = action_score + state["status"]["score"]
        return self.score_sign * score
   