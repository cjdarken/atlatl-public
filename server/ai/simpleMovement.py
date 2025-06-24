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
    Designed for moving friendly units based on different scoring functions. The scoring 
    function depends on the given mode. The movement action with the highest score is 
    output. Only target hex that are out of range of enemy units are considered.

    If such an action is not possible, a pass action is returned.

    Notes
    -----
    To use this AI, a mode must be provided as an argument. The simplest implementation 
    works via the AI registry (e.g., "simpleFlee" : (ai.simpleMovement.AI, {"mode":"Flee"})).
    
    This is a highly specialized AI. It is not intended that this AI be used as a 
    stand-alone AI. Rather, this AI should serve as a sub-AI for another higher-level AI.

    Modes
    -----
    'Capture'
        Designed to facilitate capture of cities not already occupied by that side. For each unit a score is given to each potential movement target not within enemy range. The score is calculated as the remaining movement phases available to that unit minus the distance to the nearest unoccupied city. A negative score would indicate that the city cannot be reached before the end of the game. Movement is made to the highest scoring destination. 
    'DefendCity'
        Designed to facilitate defense of cities that have already been occupied. Logic is the same as simpleCapture except the score is calculated for occupied rather than unoccupied cities.
    'DefendUnits'
        Designed to facilitate mutual support of friendlies. Logic is identical to SimpleOffensive except that scores are relative to friendly rather than enemy units.
    'Flee'
        Designed to facilitate a general retreat from contact. Logic is like SimpleOffensive with an inverted score; that is, it is calculated as distance to nearest effective enemy minus remaining total phases. A positive score indicates the enemy cannot reach the unit. The highest score is still preferred.
    'Offensive'
        Designed to facilitate an advance toward enemy units while out of range. Logic is the same as for SimpleCapture, except score is calculated with respect to the nearest effective enemy unit rather than a city. 
           
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

    def _hexesToClosestEnemyCity(self,hx):
        hx_x, hx_y = hx.x_offset, hx.y_offset
        closestDist = float('inf')
        closestHex = None
        for city_id in self.statusData.ownerD:
            if self.statusData.ownerD[city_id] == self.role:
                continue
            city_hex = self.mapData.hexIndex[city_id]
            dist = map.hexDistance(hx_x,hx_y,city_hex.x_offset,city_hex.y_offset)
            if dist < closestDist:
                closestDist = dist
                closestHex = city_hex
        return closestDist, closestHex
    
    def _hexesToClosestOwnCity(self,hx):
        hx_x, hx_y = hx.x_offset, hx.y_offset
        closestDist = float('inf')
        closestHex = None
        for city_id in self.statusData.ownerD:
            if self.statusData.ownerD[city_id] != self.role:
                continue
            city_hex = self.mapData.hexIndex[city_id]
            dist = map.hexDistance(hx_x,hx_y,city_hex.x_offset,city_hex.y_offset)
            if dist < closestDist:
                closestDist = dist
                closestHex = city_hex
        return closestDist, closestHex
    
    def _hexesToClosestEnemy(self,hx):
        hx_x, hx_y = hx.x_offset, hx.y_offset
        closestDist = float('inf')
        closestHex = None
        for unt in self.unitData.units():
            if unt.ineffective:
                continue
            if unt.faction == self.role:
                continue
            dist = map.hexDistance(hx_x,hx_y,unt.hex.x_offset,unt.hex.y_offset)
            if dist < closestDist:
                closestDist = dist
                closestHex = unt.hex
        return closestDist, closestHex
    
    def _hexesToClosestFriend(self,hx, ownUnit = None):
        hx_x, hx_y = hx.x_offset, hx.y_offset
        closestDist = float('inf')
        closestHex = None
        for unt in self.unitData.units():
            if unt.ineffective:
                continue
            if unt.faction != self.role:
                continue
            if ownUnit == unt:
                continue
            dist = map.hexDistance(hx_x,hx_y,unt.hex.x_offset,unt.hex.y_offset)
            if dist < closestDist:
                closestDist = dist
                closestHex = unt.hex
        return closestDist, closestHex

    def getScore(self, mode, game, state, hex, ownUnit):
        remainingOwnPhases = math.ceil((self.param["score"]["maxPhases"] - state["status"]["phaseCount"]) / 2)
        remainingTotalPhases = (self.param["score"]["maxPhases"] - state["status"]["phaseCount"])
        if mode == "Capture":
            distClosestEnyCity, _ = self._hexesToClosestEnemyCity(hex)
            score = remainingOwnPhases - distClosestEnyCity
            return score
        elif mode == "DefendCity":
            distClosestOwnCity, _ = self._hexesToClosestOwnCity(hex)
            score = remainingOwnPhases - distClosestOwnCity
            return score
        elif mode == "Offensive":
            distClosestEnemy, _ = self._hexesToClosestEnemy(hex)
            score = remainingTotalPhases - distClosestEnemy
            return score
        elif mode == "DefendUnits":
            distClosestFriend, _ = self._hexesToClosestFriend(hex, ownUnit)
            score = remainingTotalPhases - distClosestFriend
            return score
        elif mode == "Flee":
            distClosestEnemy, _ = self._hexesToClosestEnemy(hex)
            score = distClosestEnemy - remainingTotalPhases
            return score
        else:
            return -1
    
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

        bestMover = None
        bestHex = None
        bestScore = float("-inf")
        
        for unt in ownUnits:
            if not unt.canMove:
                continue

            moveTargets = unt.findMoveTargets(self.mapData, self.unitData)         
            for hex in moveTargets:
                safe = True
                for eny in enyUnits:
                    range = map.gridDistance(eny.hex.x_grid, eny.hex.y_grid, hex.x_grid, hex.y_grid)
                    if range <= combat.range[eny.type]:
                        safe = False
                        break
                if not safe:
                    continue
                score = self.getScore(self.mode, game, state, hex, unt)
                if score > bestScore:
                    bestHex = hex
                    bestMover = unt
                    bestScore = score
        
        if not bestMover:
            return {"type":"pass"}
        if not bestHex:
            return {"type":"pass"}
        
        return {"type":"move", "mover":bestMover.uniqueId, "destination":bestHex.id}


    
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
    
 