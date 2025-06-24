import asyncio
import websockets
import json
import argparse
import random
import colorsys

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
    def euclideanDistanceToFriend(self, actor, hex):
        # this function will determine the distance from a hex to another friendly unit
        # this funciton is just a modified version of euclideanDistanceToOpfor
        xA = hex.x_grid
        yA = hex.y_grid
        closest = None
        closest_dist = float('inf')
        for target in self.unitData.units():
            if target.faction != actor.faction or target.ineffective:   # here we are continuing if the target is not the same faction as our actor
                continue
            xB = target.hex.x_grid
            yB = target.hex.y_grid
            dist = map.gridDistance(xA,yA,xB,yB)
            if dist < closest_dist:
                closest_dist = dist
                closest = target
        return closest_dist    
    def euclideanDistanceToCities(self, actor, hex):
        if actor.faction=="red":
            opfor = "blue"
        else:
            opfor = "red"
        xA = hex.x_grid
        yA = hex.y_grid
        closest_dist = float('inf')
        if self.statusData.ownerD:
            for city_id in self.statusData.ownerD:
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
    def getPosture(self):
        str_red = 0
        str_blue = 0
        for unt in self.unitData.units():
            if unt.ineffective:
                continue
            if unt.faction=="red":
                str_red += unt.currentStrength
            elif unt.faction=="blue":
                str_blue += unt.currentStrength
        if self.role=="red" and str_red>=str_blue:
            posture = "attack"
        elif self.role=="blue" and str_blue>=str_red:
            posture = "attack"
        else:
            posture = "defense"
        return posture       
    def takeBestAction(self):
        dists = {}
        posture = self.getPosture()
        for unt in self.unitData.units():
            if unt.faction == self.role and unt.canMove and not unt.ineffective:
                fireTargets = unt.findFireTargets(self.unitData)
                if fireTargets:
                    # Shoot at a random target, if we have at least one
                    return {"type":"action", "action":{"type":"fire", "source":unt.uniqueId, "target":random.choice(fireTargets).uniqueId}}
                def scoreHex(unt,hex):
                    # score = float('inf') we are no longer starting with an infinite score for each hex, but the number of neighbor hexes
                    # this implies that we prefer to occupy hexes that have fewer hexes around them and therefore are harder to surround
                    score = len(map.getNeighborHexes(hex, self.mapData)) # in map.js the function getNeighbors returns an array of all neighboring hexes the built in python function len() will return the number of elements in a 1d array 
                    dist1 = self.euclideanDistanceToOpfor(unt, hex)
                    dist2 = self.euclideanDistanceToCities(unt, hex)
                    dist3 = self.euclideanDistanceToFriend(unt, hex) # we have added the distance to a friend into our calculations
                    if posture=="attack" and dist1<float('inf'):
                        score += (5*dist1) # adding a weight of 5
                    if dist2<float('inf'):
                        if score<float('inf'):
                            score += (10*dist2) # adding a weight of 10
                        else:
                            score = (10*dist2)
                    if dist3<float('inf'):
                        if score<float('inf'):
                            score += (4*dist3) # adding a weight of 3
                        else:
                            score = (3*dist3)
                    return score
                currentHexScore = scoreHex(unt,unt.hex)
                moveTargets = unt.findMoveTargets(self.mapData, self.unitData)
                if moveTargets:
                    closest_dist = float('inf')
                    best_hex = None
                    for hex in moveTargets:
                        score = scoreHex(unt,hex)
                        dists[hex.id] = score
                        if score < closest_dist:
                            closest_dist = score
                            best_hex = hex
                    if closest_dist < currentHexScore:
                        colors = self.colorsFromDists(dists)
                        return {"type":"action", "action":{"type":"move", "mover":unt.uniqueId, "destination":best_hex.id, }, "debug":{"colors":colors}}
        return { "type":"action", "action":{"type":"pass"} }
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
    
 