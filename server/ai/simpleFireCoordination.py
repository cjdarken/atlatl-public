import asyncio
import websockets
import json
import argparse
import random
import operator
import colorsys
import itertools
import math


import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import map
import unit
import combat
import status
from game import Game

class AI:
    """
    Designed for attacking when enemy units are in range of friendly units. The AI 
    compiles a list of fireTargets for all friendly units, and prioritizes order of 
    attack so units with only one target fire first (to avoid losing their target). 
    After that, prioritization is based on the highest damage caused. 

    If such an action is not possible, a pass action is returned.
    
    Notes
    -----
    This is a highly specialized AI. It is not intended that this AI be used as a 
    stand-alone AI. Rather, this AI should serve as a sub-AI for another higher-level AI.
        
    References
    ----------
    Initial source code was based on simon_says.py

    @author Simon Schnitzler
    """
    def __init__(self, role, kwargs={}):
        self.role = role
        self.mapData = None
        self.unitData = None
        self.mode = kwargs.get("mode",None)
    
    def findNewBestAction(self, game, state):
        firstPriority = set()
        secondPriority = set()

        # find potential units which have enemy units in range
        for unt in self.unitData.units():
            if unt.faction != self.role:
                continue
            if not unt.canMove:
                continue
            if unt.ineffective:
                continue
            fireTargets = unt.findFireTargets(self.unitData)
            if  not fireTargets:
                continue
            if len(fireTargets) == 1:
                firstPriority.add(unt.uniqueId)
            else:
                secondPriority.add(unt.uniqueId)
        
        if not (firstPriority or secondPriority):
            return {"type":"pass"}
        
        legalActions = game.legal_actions(state)
        firstPriorityActions = []
        secondPriorityActions = []

        for action in legalActions:
            if action["type"]!="fire":
                continue
            if not firstPriority.isdisjoint({action["source"]}):
                firstPriorityActions.append(action)
                continue
            if not secondPriority.isdisjoint({action["source"]}):
                secondPriorityActions.append(action)
                continue
        
        if firstPriorityActions:
            consideredActions = firstPriorityActions
        else:
            consideredActions = secondPriorityActions

        bestAction = {"type":"pass"}
        if self.role == "blue":
            best_score = float("-inf")
            comparison_op = operator.gt
        else:
            best_score = float("inf")
            comparison_op = operator.lt

        for action in consideredActions:
            postactionState = game.transition(state, action)
            score = postactionState["status"]["score"] - state["status"]["score"]
            if comparison_op(score,best_score):
                bestAction, best_score = action, score

        return bestAction

    
    def process(self, message, response_fn=None):
        msgD = json.loads(message)
        ######### Change this function to create new AIs ########  
        if msgD['type'] == "parameters":
            self.param = msgD['parameters']
            self.mapData = map.MapData()
            self.unitData = unit.UnitData()
            map.fromPortable(self.param['map'], self.mapData)
            unit.fromPortable(self.param['units'], self.unitData, self.mapData)
            responseD = { "type":"role-request", "role":self.role }
            self.action_queue = []
            self.doSetup = True
        elif msgD['type'] == 'observation':
            obs = msgD['observation']
            if not obs['status']['isTerminal'] and obs['status']['onMove'] == self.role:
                if obs['status']['setupMode']:
                    responseD = {"type":"action", "action":{"type":"pass"}}
                else:
                    # update status data (i.e. CityOwnerD)
                    self.statusData = status.Status.fromPortable(obs["status"], self.param, self.mapData)
                    game = Game(self.param)
                    state = {}
                    state["status"] = obs["status"]
                    for unitObs in obs['units']:
                        uniqueId = unitObs['faction'] + " " + unitObs['longName']
                        un = self.unitData.unitIndex[ uniqueId ]
                        un.partialObsUpdate( unitObs, self.unitData, self.mapData )
                    state["units"] = self.unitData.toPortable()

                    action = self.findNewBestAction(game, state)

                    responseD = { "type":"action", "action":action }
          
            else:
                responseD = None
        elif msgD['type'] == 'reset':
            responseD = None
            self.action_queue = []
            self.doSetup = True
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
    
 