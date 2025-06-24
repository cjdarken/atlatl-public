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

class AI:
    def __init__(self, role, kwargs={}):
        self.role = role
        self.mapData = None
        self.unitData = None
        self.best_action_list = []
        self.heuristic_score_scale = 100.0
        self.partialPly = False
        if "partialPly" in kwargs:
            self.partialPly = kwargs["partialPly"]
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
        return action_score
    def findSingleBestAction(self, game, state, starting_score=None, verbose=False):  
        if starting_score is None:
            starting_score = state["status"]["score"]      
        legal_actions = game.legal_actions(state)
        if not legal_actions or state["status"]["onMove"]!=self.role:
            #print(f"no legal actions in state {state_hex}")
            return [], None
        best_action = None
        if self.role == "blue":
            best_score = float("-inf")
            comparison_op = operator.gt
        else:
            best_score = float("inf")
            comparison_op = operator.lt
        for action in legal_actions:
            postaction_state = game.transition(state, action)
            if action["type"]!="pass":
                # Get credit for city captures
                postaction_state = game.transition(postaction_state,{"type":"pass"})
            score = self.getScore(postaction_state)+postaction_state["status"]["score"]-starting_score
            if verbose:
                print(f"action {action} comparing new score {score} with best score {best_score}")
            if comparison_op(score,best_score):
                best_action, best_score = action, score
        return [best_action], best_score  
    def findBestActions(self, game, state, starting_score=None, verbose=False):  
        if starting_score is None:
            starting_score = state["status"]["score"]      
        state_str = json.dumps(state).encode()
        state_hashobj = hashlib.sha1(state_str)
        state_hex = state_hashobj.hexdigest()
        legal_actions = game.legal_actions(state)
        if not legal_actions or state["status"]["onMove"]!=self.role:
            #print(f"no legal actions in state {state_hex}")
            return [], self.getScore(state)+state["status"]["score"]-starting_score
        best_actions = []
        if self.role == "blue":
            best_score = float("-inf")
            comparison_op = operator.gt
        else:
            best_score = float("inf")
            comparison_op = operator.lt
        for action in legal_actions:
            postaction_state = game.transition(state, action)
            pa_state_str = json.dumps(postaction_state).encode()
            pa_state_hashobj = hashlib.sha1(pa_state_str)
            pa_state_hex = pa_state_hashobj.hexdigest()
            #print(f'from state {state_hex}, searching state {pa_state_hex} via action {action}')
            actions, score = self.findBestActions(game,postaction_state,starting_score)
            actions.append(action)
            if verbose:
                print(f"comparing new score {score} with best score {best_score}")
            if comparison_op(score,best_score):
                best_actions, best_score = actions, score
        return best_actions, best_score    
    def process(self, message, response_fn=None):
        msgD = json.loads(message)
        ######### Change this function only to create new AIs ########  
        if msgD['type'] == "parameters":
            self.scenarioPo = msgD['parameters']

            self.mapData = map.MapData()
            self.unitData = unit.UnitData()
            map.fromPortable(self.scenarioPo['map'], self.mapData)
            unit.fromPortable(self.scenarioPo['units'], self.unitData, self.mapData)
            self.runDijkstra()
            responseD = { "type":"role-request", "role":self.role}
        elif msgD['type'] == 'observation':
            obs = msgD['observation']
            if not obs['status']['isTerminal'] and obs['status']['onMove'] == self.role:
                if obs['status']['setupMode']:
                    responseD = { "type":"action", "action":{"type":"pass"} }
                else:
                    if not self.best_action_list:
                        game = Game(self.scenarioPo)
                        state = {}
                        state["status"] = obs["status"]
                        for unitObs in obs['units']:
                            uniqueId = unitObs['faction'] + " " + unitObs['longName']
                            un = self.unitData.unitIndex[ uniqueId ]
                            un.partialObsUpdate( unitObs, self.unitData, self.mapData )
                        state["units"] = self.unitData.toPortable()
                        if self.partialPly:
                            self.best_action_list, _ = self.findSingleBestAction(game, state)
                        else:
                            self.best_action_list, _ = self.findBestActions(game, state)
                        #print(f'best action list returned: {self.best_action_list}')
                    responseD = { "type":"action", "action":self.best_action_list.pop() }
            else:
                responseD = None
        elif msgD['type'] == 'reset':
            responseD = None
        if responseD:
            return json.dumps(responseD)
 

async def client(ai, uri):
    async with websockets.connect(uri) as websocket:
        while True:
            message = await websocket.recv()
            print(f"Message received by AI over websocket: {message[:100]}")
            result = ai.process(message)
            if result:
                await websocket.send( result )

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("faction")
    parser.add_argument("--uri")
    args = parser.parse_args()
    
    ai = AI(args.faction)
    uri = args.uri
    if not uri:
        uri = "ws://localhost:9999"
    asyncio.get_event_loop().run_until_complete(client(ai, uri))
    