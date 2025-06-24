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
import abstract_state

class AI:
    def __init__(self, role, kwargs={}):
        self.role = role
        self.mapData = None
        self.unitData = None
        self.mode = kwargs.get("mode",None)
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
        return closest_dist
    def bossId(self, unit):
        index = unit.longName.find('/')
        id = unit.longName[(index+1):]
        return unit.faction+" "+id
    def crowdingPenalty(self, actor, hex):
        netPenalty = 0
        penalties = [300, 200, 100]
        xA = hex.x_offset
        yA = hex.y_offset
        for unt in self.abstractUnitData.units():
            if unt==actor or unt.faction != actor.faction or unt.ineffective or not unt.hex:                 
                continue
            xB = unt.hex.x_offset
            yB = unt.hex.y_offset
            dist = map.hexDistance(xA,yA,xB,yB)
            if dist < len(penalties):
                netPenalty += penalties[dist]
        return netPenalty
    def euclideanDistanceToCommandHex(self, unit, hex):
        xA, yA = hex.x_grid, hex.y_grid
        boss_id = self.bossId(unit)
        boss = self.abstractUnitData.unitIndex[boss_id]
        xB, yB = boss.hex.x_grid, boss.hex.y_grid
        return map.gridDistance(xA,yA,xB,yB)
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
    def spacedHuePallete(self,n_colors,sat=1.0,val=1.0):
        # Uniform-spaced hues from red to blue
        # Saturation and value fixed to values provided
        colors = []
        for i in range(n_colors):
            if n_colors==1:
                hue = 0
            else:
                hue = float(i)/(n_colors-1) * 250 / 360
            rgb = tuple(round(x * 255) for x in colorsys.hsv_to_rgb(hue,sat,val))
            color = '#'
            for i in rgb:
                s = str(hex(i))
                if len(s)==3:
                    color += '0' + s[-1:]
                else:
                    color += s[-2:]
            colors.append(color)
        return colors
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
        if self.mode=="pass":
            return "defense"
        elif self.mode=="agg":
            return "attack"
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
    def takeBestAction(self, colors):
        dists = {}
        posture = self.getPosture()
        for unt in self.unitData.units():
            if unt.faction == self.role and unt.canMove and not unt.ineffective:
                fireTargets = unt.findFireTargets(self.unitData)
                if fireTargets:
                    # Shoot at a random target, if we have at least one
                    return {"type":"action", "action":{"type":"fire", "source":unt.uniqueId, "target":random.choice(fireTargets).uniqueId}}
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
                    if self.mode!="ignore_commander":
                        score += 2*self.euclideanDistanceToCommandHex(unt, hex)
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
        return { "type":"action", "action":{"type":"pass"} }
    def moveAbstractUnits(self):
        dists = {}
        posture = self.getPosture()
        for unt in self.abstractUnitData.units():
            if unt.faction == self.role and not unt.ineffective:
                def scoreHex(unt,hex):
                    score = self.crowdingPenalty(unt, hex)
                    dist1 = self.euclideanDistanceToOpfor(unt, hex)
                    dist2 = self.euclideanDistanceToCities(unt, hex)
                    if posture=="attack" and dist1<float('inf'):
                        score += dist1
                    if dist2<float('inf'):
                        score += dist2
                    return score
                currentHexScore = scoreHex(unt,unt.hex)
                moveTargets = unt.findMoveTargets(self.mapData, self.abstractUnitData)
                if moveTargets:                
                    if self.mode=="random_commander":
                        random_hex = random.choice(moveTargets)
                        unt.setHex(random_hex, self.abstractUnitData)
                    else:
                        closest_dist = float('inf')
                        best_hex = None
                        for hex in moveTargets:
                            score = scoreHex(unt,hex)
                            dists[hex.id] = score
                            if score < closest_dist:
                                closest_dist = score
                                best_hex = hex
                        if closest_dist < currentHexScore:
                            # Move unit to new hex
                            unt.setHex(best_hex, self.abstractUnitData)
    def process(self, message, response_fn=None):
        msgD = json.loads(message)
        ######### Change this function to create new AIs ########  
        if msgD['type'] == "parameters":
            self.param = msgD['parameters']
            self.mapData = map.MapData()
            self.unitData = unit.UnitData()
            self.abstractUnitData = unit.UnitData()
            self.commander_move = True
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

                    colors = {}
                    if self.commander_move:
                        self.abstractUnitData = abstract_state.abstractUnitData(self.unitData, self.mapData, self.role)              
                        absUnits = self.abstractUnitData.getFaction(self.role)
                        n_units = len(absUnits)
                        palette = self.spacedHuePallete(n_units,0.2,1.0)
                        for un,color in zip(absUnits,palette):
                            colors[un.hex.id] = color
                        self.moveAbstractUnits()
                        self.commander_move = False

                    absUnits = self.abstractUnitData.getFaction(self.role)
                    n_units = len(absUnits)
                    palette = self.spacedHuePallete(n_units,1.0,1.0)
                    for un,color in zip(absUnits,palette):
                        colors[un.hex.id] = color

                    responseD = self.takeBestAction(colors)
            else:
                self.commander_move = True
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
    
 