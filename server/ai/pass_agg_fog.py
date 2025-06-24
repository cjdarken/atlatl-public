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

import combat

# Note that the debug visualization can be updated only when blue takes an action.
# So simultaneous with blue's action, the state of mind behind it is visualized

def colorsFromDict(dictHexIdToFloat, range=None):
    if range:
        min_val, max_val = range
    else:
        max_val = float('-inf')
        min_val = float('inf')
        for hex_id in dictHexIdToFloat:
            max_val = max( dictHexIdToFloat[hex_id], max_val)
            min_val = min( dictHexIdToFloat[hex_id], min_val)
    # Set color
    colors = {}
    for hex_id in dictHexIdToFloat:
        x = dictHexIdToFloat[hex_id]
        sat = 0.5
        val = 1.0
        if max_val == min_val:
            hue = 250 / 360
        elif max_val == float('inf'):
            hue = 0
        else:
            hue = (max_val - x) / (max_val - min_val) * 250 / 360
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

class OpforDistrib:
    def __init__(self, epsilon, mapData, unitData, ownFaction):
        if ownFaction=="red":
            opforFaction = "blue"
        else:
            opforFaction = "red"
        self.epsilon = epsilon
        self.mapData = mapData
        for unit in unitData.units():
            if unit.faction==opforFaction:
                self.opforUnitProto = unit
                break
        self.distr = {}
        self.sum = 0.0
        for hex in mapData.hexes():
            self.distr[hex.id] = 0.0
        for unit in unitData.units():
            if unit.faction == self.opforUnitProto.faction:
                self.distr[unit.hex.id] = 1.0
                self.sum += 1.0
        self.cull(unitData)
    def move(self, unitData):
        distrDelta = {}
        for hexId in self.distr:
            hex = self.mapData.hexIndex[hexId]
            if self.distr[hexId]==0.0:
                continue
            destinations =  self.opforUnitProto._findMoveTargets(hex, self.opforUnitProto.type, self.mapData, unitData)
            dp = self.epsilon*self.distr[hexId]
            old_delta = distrDelta.get(hexId, 0.0)
            distrDelta[hexId] = old_delta - dp*len(destinations)
            for hex in destinations:
                old_delta = distrDelta.get(hex.id, 0.0)
                distrDelta[hex.id] = old_delta + dp
        for hexId in distrDelta:
            self.distr[hexId] += distrDelta[hexId]
    def cull(self, unitData):
        for hex in self.mapData.hexes():
            cull = False
            xA, yA = hex.x_grid, hex.y_grid
            if self.distr[hex.id]==0.0:
                continue
            for unit in unitData.units():
                if unit.faction==self.opforUnitProto.faction:
                    continue
                if unit.ineffective:
                    continue
                xB, yB = unit.hex.x_grid, unit.hex.y_grid
                distAB = map.gridDistance(xA,yA,xB,yB)
                if distAB <= combat.sight[unit.type]:
                    cull = True
                    break
            if cull:
                self.sum -= self.distr[hex.id]
                self.distr[hex.id] = 0.0
    def getNormalizedDist(self):
        if self.sum>0:
            for hexId in self.distr:
                self.distr[hexId] /= self.sum
            self.sum = 1.0
        return self.distr
        

class AI:
    def __init__(self, role, kwargs={}):
        self.role = role
        self.mapData = None
        self.unitData = None
        self.opforDistrib = None
        self.lastPhase = None
    def euclideanDistanceToOpfor(self, actor, hex):
        xA = hex.x_grid
        yA = hex.y_grid
        closest = None
        closest_dist = float('inf')
        if not self.unitData.units():
            return float('inf')
        for target in self.unitData.units():
            if target.faction == actor.faction or target.ineffective or not target.hex:                 
                continue
            xB = target.hex.x_grid
            yB = target.hex.y_grid
            dist = map.gridDistance(xA,yA,xB,yB)
            if dist < closest_dist:
                closest_dist = dist
                closest = target
        for hex_id in self.opforDistrib.distr:
            if self.opforDistrib.distr[hex_id]==0:
                continue
            hex = self.mapData.hexIndex[hex_id]
            xB = hex.x_grid
            yB = hex.y_grid
            dist = map.gridDistance(xA,yA,xB,yB)
            if dist < closest_dist:
                closest_dist = dist
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
    def takeRandomAction(self):
        colors = colorsFromDict(self.opforDistrib.getNormalizedDist(), range=None)
        for unt in self.unitData.units():
            if unt.faction == self.role and unt.canMove and not unt.ineffective:
                moveTargets = unt.findMoveTargets(self.mapData, self.unitData)
                fireTargets = unt.findFireTargets(self.unitData)
                numTargets = len(moveTargets) + len(fireTargets)
                if numTargets == 0:
                    continue
                if random.randint(1,numTargets) <= len(moveTargets):
                    return {"type":"action", "action":{"type":"move", "mover":unt.uniqueId, "destination":random.choice(moveTargets).id}, "debug":{"colors":colors}}
                else:
                    return {"type":"action", "action":{"type":"fire", "source":unt.uniqueId, "target":random.choice(fireTargets).uniqueId}, "debug":{"colors":colors}}
        return { "type":"action", "action":{"type":"pass"}, "debug":{"colors":colors} }      
    def takeBestAction(self):
        colors = colorsFromDict(self.opforDistrib.getNormalizedDist(), range=None)
        dists = {}
        posture = self.getPosture()
        for unt in self.unitData.units():
            if unt.faction == self.role and unt.canMove and not unt.ineffective:
                fireTargets = unt.findFireTargets(self.unitData)
                if fireTargets:
                    # Shoot at a random target, if we have at least one
                    return {"type":"action", "action":{"type":"fire", "source":unt.uniqueId, "target":random.choice(fireTargets).uniqueId}, "debug":{"colors":colors}}
                def scoreHex(unt,hex):
                    score = float('inf')
                    dist1 = self.euclideanDistanceToOpfor(unt, hex)
                    dist2 = self.euclideanDistanceToCities(unt, hex)
                    if posture=="attack" and dist1<float('inf'):
                        score = dist1
                    if dist2<float('inf'):
                        if score<float('inf'):
                            score += dist2
                        else:
                            score = dist2
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
                        return {"type":"action", "action":{"type":"move", "mover":unt.uniqueId, "destination":best_hex.id, }, "debug":{"colors":colors}}
        return { "type":"action", "action":{"type":"pass"}, "debug":{"colors":colors} }
    def process(self, message, response_fn=None):
        msgD = json.loads(message)
        ######### Change this function to create new AIs ########  
        opfor_distrib = {}
        if msgD['type'] == "parameters":
            self.param = msgD['parameters']
            self.mapData = map.MapData()
            self.unitData = unit.UnitData()
            map.fromPortable(self.param['map'], self.mapData)
            unit.fromPortable(self.param['units'], self.unitData, self.mapData)
            responseD = { "type":"role-request", "role":self.role }
            self.opforDistrib = OpforDistrib(0.05, self.mapData, self.unitData, self.role)
            self.lastPhase = 0
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
                    phase = obs['status']['phaseCount'] 
                    if phase > self.lastPhase:  # It's a new phase. Opfor may have moved.
                        self.opforDistrib.move(self.unitData)
                        self.lastPhase = phase
                    self.opforDistrib.cull(self.unitData)
                    responseD = self.takeBestAction()
                    #responseD = self.takeRandomAction() # Alternative to above line for stress testing
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
    
 