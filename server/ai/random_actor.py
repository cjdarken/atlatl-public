import asyncio
import websockets
import json
import argparse
import random

# This AI has a representation of the map and units, and updates the unit representation as it changes
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import map
import unit

class AI:
    def __init__(self, role, kwargs={}):
        self.role = role
        self.mapData = None
        self.unitData = None
    def takeRandomAction(self):
        for unt in self.unitData.units():
            if unt.faction == self.role and unt.canMove and not unt.ineffective:
                moveTargets = unt.findMoveTargets(self.mapData, self.unitData)
                fireTargets = unt.findFireTargets(self.unitData)
                numTargets = len(moveTargets) + len(fireTargets)
                if numTargets == 0:
                    continue
                if random.randint(1,numTargets) <= len(moveTargets):
                    return {"type":"action", "action":{"type":"move", "mover":unt.uniqueId, "destination":random.choice(moveTargets).id}}
                else:
                    return {"type":"action", "action":{"type":"fire", "source":unt.uniqueId, "target":random.choice(fireTargets).uniqueId}}
        return { "type":"action", "action":{"type":"pass"} }
    def process(self, message, response_fn=None):
        msgD = json.loads(message)
        ######### Change this function only to create new AIs ########  
        if msgD['type'] == "parameters":
            param = msgD['parameters']
            self.mapData = map.MapData()
            self.unitData = unit.UnitData()
            map.fromPortable(param['map'], self.mapData)
            unit.fromPortable(param['units'], self.unitData, self.mapData)
            responseD = { "type":"role-request", "role":self.role}
        elif msgD['type'] == 'observation':
            obs = msgD['observation']
            if not obs['status']['isTerminal'] and obs['status']['onMove'] == self.role:
                if obs['status']['setupMode']:
                    responseD = { "type":"action", "action":{"type":"pass"} }
                else:
                    for unitObs in obs['units']:
                        uniqueId = unitObs['faction'] + " " + unitObs['longName']
                        un = self.unitData.unitIndex[ uniqueId ]
                        un.partialObsUpdate( unitObs, self.unitData, self.mapData )
                    responseD = self.takeRandomAction()
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
    