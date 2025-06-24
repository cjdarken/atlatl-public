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
    Designed to aggressively advance units into range of the enemy. AI compiles a list 
    of friendly units that can move within range of an enemy unit and scores potential 
    movement destinations. Potential movement targets are scored by subtracting the 
    number of adjacent enemy units and adding the number of friendly supporting units 
    already adjacent to a potential enemy or able to make such a move. Movement is 
    selected to the highest scoring hex for each unit. Movement order is prioritized 
    with the friendly unit with the highest currentStrength value moving first.

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
        MIN_ASSAULT_STRENGTH = 75
        # TODO consider Terrain

        ownUnits = set()
        enyUnits = set()
        for unt in self.unitData.units():
            if unt.ineffective:
                continue
            if unt.faction != self.role:
                enyUnits.add(unt)
                continue
            ownUnits.add(unt)
            
        
        if not ownUnits:
            return {"type":"pass"}
        
        if not enyUnits:
            return {"type":"pass"}
        
        assaultUnits = set()
        assaultTargets = set()

        for unt in ownUnits:
            if not unt.canMove:
                continue
            if unt.currentStrength < MIN_ASSAULT_STRENGTH:
                continue
            moveTargets = unt.findMoveTargets(self.mapData, self.unitData)
            for hex in moveTargets:
                for eny in enyUnits:
                    distance = map.gridDistance(hex.x_grid, hex.y_grid, eny.hex.x_grid, eny.hex.y_grid)
                    if distance <= combat.range[unt.type]:
                        assaultTargets.add(hex)
                        assaultUnits.add(unt)
                        break
        
        if not assaultUnits:
            return {"type":"pass"}
        if not assaultTargets:
            return {"type":"pass"}
        
        bestTarget = None
        bestScore = float("-inf")
        
        for target in assaultTargets:
            targetScore = 0
            consideredUnits = set()
            for eny in enyUnits:
                distance = map.gridDistance(target.x_grid, target.y_grid, eny.hex.x_grid, eny.hex.y_grid)
                if distance <= combat.range[eny.type]:
                    targetScore -= 1
                    for unt in ownUnits:
                        if not consideredUnits.isdisjoint({unt}):
                            continue
                        distance = map.gridDistance(unt.hex.x_grid, unt.hex.y_grid, eny.hex.x_grid, eny.hex.y_grid)
                        if distance <= combat.range[unt.type]:
                            targetScore += 1
                            consideredUnits.add(unt)
                    for unt in assaultUnits:
                        if not consideredUnits.isdisjoint({unt}):
                            continue
                        moveTargets = unt.findMoveTargets(self.mapData, self.unitData)
                        for hex in moveTargets:
                            distance = map.gridDistance(hex.x_grid, hex.y_grid, eny.hex.x_grid, eny.hex.y_grid)
                            if distance <= combat.range[unt.type]:
                                targetScore += 1
                                consideredUnits.add(unt)
                                break
            
            if targetScore > bestScore:
                bestScore = targetScore
                bestTarget = target
        
        if not bestTarget:
            return {"type":"pass"}
        
        bestStrength = float("-inf")
        bestUnit = None
        for unt in assaultUnits:
            moveTargets = unt.findMoveTargets(self.mapData, self.unitData)
            if bestTarget in moveTargets:
                if unt.currentStrength > bestStrength:
                    bestStrength = unt.currentStrength
                    bestUnit = unt
        
        if not bestUnit:
            return {"type":"pass"}
        
        return {"type":"move", "mover":bestUnit.uniqueId, "destination":bestTarget.id}
    
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
    
 