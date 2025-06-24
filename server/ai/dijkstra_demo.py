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

import colorsys
import numpy as np
import scipy
from scipy.sparse import dok_matrix
import mobility

class AI:
    def __init__(self, role, kwargs={}):
        self.role = role
        self.mapData = None
        self.unitData = None
    def colorsFromDistTo(self, goal_hex):
        max_dist = float('-inf')
        min_dist = float('inf')
        i = self.arrayIndex[goal_hex.id]
        for hex_id in self.arrayIndex:
            j = self.arrayIndex[hex_id]
            max_dist = max( self.dist_matrix[i, j], max_dist)
            min_dist = min( self.dist_matrix[i, j], min_dist)
        # Set color
        colors = {}
        for hex_id in self.arrayIndex:
            j = self.arrayIndex[hex_id]
            dist = self.dist_matrix[i,j]
            sat = 0.5
            val = 1.0
            if max_dist == min_dist:
                hue = 0
            elif max_dist == float('inf'):
                hue = 0
            else:
                hue = (dist - min_dist) / (max_dist - min_dist) * 250 / 360
            rgb = tuple(round(x * 255) for x in colorsys.hsv_to_rgb(hue,sat,val))
            color = '#'
            for k in rgb:
                s = str(hex(int(k)))
                if len(s)==3:
                    color += '0' + s[-1:]
                else:
                    color += s[-2]
            colors[hex_id] = color
        return colors 
    def runDijkstra(self):
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
                cost = mobility.cost["armor"][neigh.terrain]
                i = self.arrayIndex[hexId]
                j = self.arrayIndex[neigh.id]
                mat[i,j] = cost
        self.dist_matrix = scipy.sparse.csgraph.dijkstra(mat)
    def takeRandomAction(self):
        for unt in self.unitData.units():
            if unt.faction == self.role and unt.canMove and not unt.ineffective:
                colors = self.colorsFromDistTo(unt.hex)
                moveTargets = unt.findMoveTargets(self.mapData, self.unitData)
                fireTargets = unt.findFireTargets(self.unitData)
                numTargets = len(moveTargets) + len(fireTargets)
                if numTargets == 0:
                    continue
                if random.randint(1,numTargets) <= len(moveTargets):
                    return {"type":"action", "action":{"type":"move", "mover":unt.uniqueId, "destination":random.choice(moveTargets).id}, "debug":{"colors":colors}}
                else:
                    return {"type":"action", "action":{"type":"fire", "source":unt.uniqueId, "target":random.choice(fireTargets).uniqueId}, "debug":{"colors":colors}}
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
            self.runDijkstra()
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
    