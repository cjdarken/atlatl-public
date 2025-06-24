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
    Designed for withdrawal of friendly units which are in range of the enemy out of 
    enemy range. The AI compiles a list of units in range of the enemy and their 
    available movements to hexes not in range. Movement order is prioritized by the 
    units with the lowest potential destinations, and then lowest currentStrength value.

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
        enemyUnits = set()

        for unt in self.unitData.units():
            if unt.ineffective:
                continue
            if unt.faction != self.role:
                enemyUnits.add(unt)
                continue
            if not unt.canMove:
                continue
            ownUnits.add(unt)

        threatenedUnits = set()
        for unt in enemyUnits:
            fireTargets = unt.findFireTargets(self.unitData)
            if fireTargets:
                threatenedUnits.update(fireTargets)

        if not threatenedUnits:
            return {"type":"pass"}
        
        # remove all own units, which are not threatened by an enemy unit
        ownUnits.intersection_update(threatenedUnits)

        numberMoveTargets = float("inf")
        strengthPoints = float("inf")
        prioritizedUnit = None
        prioritizedUnitMoveTargets = None

        # TODO add condition if the unit is threatened by potential death
        # potentialDeath = False

        for unt in ownUnits:
            moveTargets = unt.findMoveTargets(self.mapData, self.unitData)
            noGoHex = set()
            for target in moveTargets:
                for eny in enemyUnits:
                    range = map.gridDistance(eny.hex.x_grid, eny.hex.y_grid, target.x_grid, target.y_grid)
                    if range <= combat.range[eny.type]:
                        noGoHex.add(target)
                        continue
            for hex in noGoHex:
                moveTargets.remove(hex)
            if not moveTargets:
                continue
            if len(moveTargets) > numberMoveTargets:
                continue
            if len(moveTargets) < numberMoveTargets:
                numberMoveTargets = len(moveTargets)
                strengthPoints = unt.currentStrength
                prioritizedUnit = unt
                prioritizedUnitMoveTargets = moveTargets
                # TODO potentialDeath
            if unt.currentStrength < strengthPoints:
                numberMoveTargets = len(moveTargets)
                strengthPoints = unt.currentStrength
                prioritizedUnit = unt
                prioritizedUnitMoveTargets = moveTargets
        
        if not prioritizedUnit:
            return {"type":"pass"}

        legalActions = game.legal_actions(state)

        for action in legalActions:
            if action["type"]!="move":
                continue
            if action["mover"] != prioritizedUnit.uniqueId:
                continue
            for target in prioritizedUnitMoveTargets:
                if action["destination"] == target.id:
                    return action      

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
    
 