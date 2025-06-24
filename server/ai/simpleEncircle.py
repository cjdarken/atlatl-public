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
    Designed to create a behavior wherein friendly units will attempt to encircle an 
    enemy before entering range. The AI calculates the smallest HexDistance. For each 
    potential movement target of each unit the AI checks if said target is within range 
    of the enemy. If it is not, the AI will make a move to the potential target which is 
    closer or the same distance from the closest enemy.

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

        for unt in ownUnits:
            if not unt.canMove:
                continue
            
            closestHexDist = float("inf")
            for eny in enyUnits:
                currentHexDist = map.hexDistance(unt.hex.x_offset, unt.hex.y_offset, eny.hex.x_offset, eny.hex.y_offset)
                if currentHexDist < closestHexDist:
                    closestHexDist = currentHexDist

            moveTargets = unt.findMoveTargets(self.mapData, self.unitData)         
            for hex in moveTargets:
                safe = True
                newClosestHexDist = float("inf")
                for eny in enyUnits:
                    range = map.gridDistance(eny.hex.x_grid, eny.hex.y_grid, hex.x_grid, hex.y_grid)
                    if range <= combat.range[eny.type]:
                        safe = False
                        break
                    hexDistance = map.hexDistance(hex.x_offset, hex.y_offset, eny.hex.x_offset, eny.hex.y_offset)
                    if hexDistance < newClosestHexDist:
                        newClosestHexDist = hexDistance
                if not safe:
                    continue
                if newClosestHexDist <= closestHexDist:
                    return {"type":"move", "mover":unt.uniqueId, "destination":hex.id}
        
        return {"type":"pass"}


    
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
    
 