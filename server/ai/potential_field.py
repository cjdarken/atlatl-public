import asyncio
import websockets
import json
import argparse
import random
import colorsys

# This AI has a representation of the map and units, and updates the unit representation as it changes
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import map
import unit
import status

class AI:
    def __init__(self, role, kwargs={}):
        self.role = role
        self.mapData = None
        self.unitData = None
    def euclideanDistanceToOpfor(self, actor, hex):
        xA = hex.x_grid
        yA = hex.y_grid
        closest = None
        closest_dist = float('inf')
        for target in self.unitData.units():
            if target.faction == actor.faction or target.ineffective:
                continue
            xB = target.hex.x_grid
            yB = target.hex.y_grid
            dist = map.gridDistance(xA,yA,xB,yB)
            if dist < closest_dist:
                closest_dist = dist
                closest = target
        return closest_dist
    def euclideanDistanceToOpforCities(self, actor, hex):
        if actor.faction=="red":
            opfor = "blue"
        else:
            opfor = "red"
        xA = hex.x_grid
        yA = hex.y_grid
        closest_dist = float('inf')
        if self.statusData.ownerD:
            for city_id in self.statusData.ownerD:
                if self.statusData.ownerD[city_id]==opfor:
                    xB = self.mapData.hexIndex[city_id].x_grid
                    yB = self.mapData.hexIndex[city_id].y_grid
                    dist = map.gridDistance(xA,yA,xB,yB)
                    if dist < closest_dist:
                        closest_dist = dist  
        return closest_dist
    def colorsFromDists(self, dists):
        max_dist = float('-inf')
        min_dist = float('inf')
        for hex_id in dists:
            max_dist = max( dists[hex_id], max_dist)
            min_dist = min( dists[hex_id], min_dist)
        # Set color
        colors = {}
        for hex_id in dists:
            sat = 0.5
            val = 1.0
            if max_dist == min_dist:
                hue = 0
            else:
                hue = (dists[hex_id] - min_dist) / (max_dist - min_dist) * 250 / 360
            rgb = tuple(round(x * 255) for x in colorsys.hsv_to_rgb(hue,sat,val))
            color = '#'
            for i in rgb:
                s = str(hex(i))
                if len(s)==3:
                    color += '0' + s[-1:]
                else:
                    color += s[-2]
            colors[hex_id] = color
        return colors 
    def takeBestAction(self):
        dists = {}
        for unt in self.unitData.units():
            if unt.faction == self.role and unt.canMove and not unt.ineffective:
                fireTargets = unt.findFireTargets(self.unitData)
                if fireTargets:
                    # Shoot at a random target, if we have at least one
                    return {"type":"action", "action":{"type":"fire", "source":unt.uniqueId, "target":random.choice(fireTargets).uniqueId}}
                moveTargets = unt.findMoveTargets(self.mapData, self.unitData)
                if moveTargets:
                    closest_dist = float('inf')
                    best_hex = None
                    for hex in moveTargets:
                        score = float('inf')
                        dist1 = self.euclideanDistanceToOpfor(unt, hex)
                        dist2 = self.euclideanDistanceToOpforCities(unt, hex)
                        if dist1<float('inf'):
                            score = dist1
                        if dist2<float('inf'):
                            if score<float('inf'):
                                score += dist2
                            else:
                                score = dist2
                        dists[hex.id] = score
                        if score < closest_dist:
                            closest_dist = score
                            best_hex = hex
                    if closest_dist < float('inf'):
                        colors = self.colorsFromDists(dists)
                        return {"type":"action", "action":{"type":"move", "mover":unt.uniqueId, "destination":best_hex.id, }, "debug":{"colors":colors}}
        return { "type":"action", "action":{"type":"pass"} }
    def process(self, message, response_fn=None):
        msgD = json.loads(message)
        ######### Change this function only to create new AIs ########  
        if msgD['type'] == "parameters":
            self.param = msgD['parameters']
            self.mapData = map.MapData()
            self.unitData = unit.UnitData()
            map.fromPortable(self.param['map'], self.mapData)
            unit.fromPortable(self.param['units'], self.unitData, self.mapData)
            responseD = { "type":"role-request", "role":self.role}
        elif msgD['type'] == 'observation':
            obs = msgD['observation']
            if not obs['status']['isTerminal'] and obs['status']['onMove'] == self.role:
                if obs['status']['setupMode']:
                    responseD = { "type":"action", "action":{"type":"pass"} }
                else:
                    self.statusData = status.Status.fromPortable(obs["status"], self.param, self.mapData)
                    for unitObs in obs['units']:
                        uniqueId = unitObs['faction'] + " " + unitObs['longName']
                        un = self.unitData.unitIndex[ uniqueId ]
                        un.partialObsUpdate( unitObs, self.unitData, self.mapData )
                    responseD = self.takeBestAction()
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
    
 