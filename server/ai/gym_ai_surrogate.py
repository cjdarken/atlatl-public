import asyncio
import websockets
import json
import argparse
import numpy as np

# This AI has a representation of the map and units, and updates the unit representation as it changes
import map
import unit

action_count = 0

class NoNegativesRewArt:
    def __init__(self, own_faction=None):
        self.negative_rewards = 0
    def engineeredReward(self, reward, unitData=None, is_terminal = False):
        # Make this function just "return(reward)" to use raw rewards
        if reward < 0:
            self.negative_rewards += 1
            # Negative rewards turn into zero
            return 0
        # Positive rewards get discounted based on the number of negative rewards
        base = 10
        reward_discount = base / (base + self.negative_rewards)
        return reward * reward_discount

class BoronRewArt:
    # Boron did not use a terminal bonus (equiv. to terminal_bonus=0)
    def __init__(self, own_faction, terminal_bonus=25):
        self.own_faction = own_faction
        self.original_strength = None
        self.terminal_bonus = terminal_bonus
    def _totalFriendlyStrength(self, ownFaction, unitData):
        sum = 0
        for unt in unitData.units():
            if not unt.ineffective and unt.faction==ownFaction:
                sum += unt.currentStrength
        return sum
    def engineeredReward(self, raw_reward, unitData, is_terminal = False):
        if self.original_strength is None:
            self.original_strength = self._totalFriendlyStrength(self.own_faction, unitData)
        current_strength = self._totalFriendlyStrength(self.own_faction, unitData)
        if raw_reward < 0:
            raw_reward = 0
        if is_terminal:
            # Experimental
            raw_reward += self.terminal_bonus
        return raw_reward * current_strength / self.original_strength

class AI:
    evenXOffsets18 = ((0,-1), (1,-1), (1,0), (0,1), (-1,0), (-1,-1),
                        (0,-2), (1,-2), (2,-1), (2,0), (2,1), (1,1), 
                        (0,2), (-1,1), (-2,1), (-2,0), (-2,-1), (-1,-2))
    oddXOffsets18 = ((0,-1), (1,0), (1,1), (0,1), (-1,1), (-1,0),
                        (0,-2), (1,-1), (2,-1), (2,0), (2,1), (1,2), 
                        (0,2), (-1,2), (-2,1), (-2,0), (-2,-1), (-1,-1))
    def __init__(self, role, kwargs={}):
        self.role = role
        self.rewart_class = BoronRewArt
        self.reset()
    def reset(self):
        self.accumulated_reward = 0
        self.last_terminal = None
        self.attempted_moveD = {}
        self.response_fn = None
        self.last_score = 0
        self.mapData = None
        self.unitData = None
        self.phaseCount = 0
        self.rewArt = self.rewart_class(self.role)
    def getNFeatures(self):
        return 3
    def nextMover(self):
        for un in self.unitData.units():
            if un.faction==self.role and not self.attempted_moveD[un.uniqueId] and not un.ineffective:
                return un
        return None
    def sendToServer(self, messageO):
        if self.response_fn:
            self.response_fn(messageO)
    def updateLocalState(self, obs):
        for unitObs in obs['units']:
            uniqueId = unitObs['faction'] + " " + unitObs['longName']
            un = self.unitData.unitIndex[ uniqueId ]
            un.partialObsUpdate( unitObs, self.unitData, self.mapData )
        reward = obs['status']['score'] - self.last_score
        # Reward must have its sign flipped if red is to be trained
        is_terminal = obs['status']['isTerminal']
        self.accumulated_reward += self.rewArt.engineeredReward(reward, self.unitData, is_terminal)
        self.last_score = obs['status']['score']
        self.city_owners = obs['status']['cityOwner']
    def process(self, message, response_fn):
        self.response_fn = response_fn # Store for later use
        msgD = json.loads(message)
        if msgD['type'] == "parameters":
            paramD = msgD['parameters']
            # reset state variables
            self.reset()
            self.mapData = map.MapData()
            self.unitData = unit.UnitData()
            self.rewArt = self.rewart_class(self.role)
            self.phase = None
            for unt in self.unitData.units():
                if unt.faction == self.role:
                    self.attempted_moveD[unt.uniqueId] = False           
            map.fromPortable(paramD['map'], self.mapData)
            unit.fromPortable(paramD['units'], self.unitData, self.mapData)
            self.maxPhases = paramD['score']['maxPhases']
            responseD = { "type":"role-request", "role":self.role}
        elif msgD['type'] == 'observation':
            obs = msgD['observation']
            self.last_terminal = obs['status']['isTerminal']
            self.score = obs['status']['score']
            if self.last_terminal:
                # Needed to provide final observation to gym agents
                self.updateLocalState(obs)
                responseD = {"type":"gym-pause"}
            elif obs['status']['onMove'] == self.role:
                if obs['status']['setupMode']:
                    self.phase = "setup"
                    responseD = { "type":"action", "action":{"type":"pass"} }
                else:
                    if self.phase != "move":
                        self.phase = "move"
                        self.phaseCount = obs['status']['phaseCount']
                        for unt in self.unitData.units():
                            if unt.faction == self.role:
                                self.attempted_moveD[unt.uniqueId] = False
                    self.updateLocalState(obs)
                    if self.nextMover():
                        responseD = {"type":"gym-pause"}
                    else: # Possibly no friendlies left alive
                        responseD = { "type":"action", "action":{"type":"pass"} }
            else:
                self.phase = "wait"
                responseD = None       
        elif msgD['type'] == 'reset':
            self.reset()
            responseD = None
        else:
            raise Exception(f'Unknown message type {msgD["type"]}')
        if responseD:
            return json.dumps(responseD)
    def feature(self, fn, type):
        count = 0
        self.arrayIndex = {}
        self.inverseIndex = []
        for hexId in self.mapData.hexIndex:
            self.arrayIndex[hexId] = count
            self.inverseIndex.append(hexId)
            count += 1
        dim = self.mapData.getDimensions()
        mat = np.zeros((dim['height'],dim['width']))
        if type=="hex":
            for hexId in self.mapData.hexIndex:
                hex = self.mapData.hexIndex[hexId]
                mat[hex.y_offset, hex.x_offset] = fn(hex)
        elif type=="unit":
            for unitId in self.unitData.unitIndex:
                unt = self.unitData.unitIndex[unitId]
                hex = unt.hex
                if hex:
                    mat[hex.y_offset, hex.x_offset] = fn(unt)
        else: # type=="owner"
            for hexId in self.city_owners:
                hex = self.mapData.hexIndex[hexId]
                mat[hex.y_offset, hex.x_offset] = fn(hexId, self.city_owners)
        return mat
    def action_result(self):
        done = self.last_terminal 
        reward = self.accumulated_reward
        self.accumulated_reward = 0
        info = {'score':self.last_score}
        return (self.observation(), reward, done, info)
    def observation(self):
        next_mover = self.nextMover()
        # if next_mover:
        #     mover_feature = self.feature(moverFeatureFactory(next_mover),"unit")
        # else:
        #     mover_feature = self.feature(lambda x:0,"hex")
        return np.stack( [
                            self.feature(moverFeatureFactory(next_mover),"unit"),
                            self.feature(blueUnitFeature,"unit"), 
                            self.feature(redUnitFeature,"unit")
                         ] )
    def noneOrEndMove(self):
        if self.nextMover():
            return None
        else:
            return { "type":"action", "action":{"type":"pass"} }
    def actionMessageDiscrete(self, action):
        # Action represents the six or 18 most adjacent hexes plus wait,
        # either in range 0..6 or 0..18
        global action_count
        action_count += 1
        mover = self.nextMover()
        self.attempted_moveD[mover.uniqueId] = True  
        if action==0:
            return self.noneOrEndMove() # wait
        hex = mover.hex
        moveTargets = mover.findMoveTargets(self.mapData, self.unitData)
        moveTargetIds = [hex.id for hex in moveTargets]
        fireTargets = mover.findFireTargets(self.unitData)
        if not moveTargets and not fireTargets:
            # No legal moves
            return self.noneOrEndMove()
        if hex.x_offset%2:
            delta = AI.oddXOffsets18[action-1]
        else:
            delta = AI.evenXOffsets18[action-1]
        to_hex_id = f'hex-{hex.x_offset+delta[0]}-{hex.y_offset+delta[1]}'
        if not to_hex_id in self.mapData.hexIndex:
            # Off-map move.
            return self.noneOrEndMove()
        to_hex = self.mapData.hexIndex[to_hex_id]
        if to_hex in moveTargets:
            return {"type":"action", "action":{"type":"move", "mover":mover.uniqueId, "destination":to_hex_id}}
        for fireTarget in fireTargets:
            if to_hex == fireTarget.hex:
                return {"type":"action", "action":{"type":"fire", "source":mover.uniqueId, "target":fireTarget.uniqueId}}
        # Illegal move request
        return self.noneOrEndMove()


class AIx2(AI):
    def __init__(self, role, kwargs):
        AI.__init__(self, role, kwargs)
    def observation(self):
        obs = AI.observation(self)
        shp = obs.shape
        new_shape = (shp[0], shp[1]*2+1, shp[2])
        mat = np.zeros(new_shape)
        for z in range(shp[0]):
            for y in range(shp[1]):
                for x in range(shp[2]):
                    mat[z, 2*y+(x%2), x] = obs[z,y,x]
        return mat

class AITwelve(AI):
    def __init__(self, role, kwargs):
        AI.__init__(self, role, kwargs)
    def observation(self):
        next_mover = self.nextMover()
        legal_move_hexes = self.legalMoveHexes(next_mover)
        return np.stack( [
                            self.feature(moverFeatureFactory(next_mover),"unit"),
                            self.feature(legalMoveFeatureFactory(legal_move_hexes),"hex"),
                            self.feature(blueUnitFeature,"unit"), 
                            self.feature(redUnitFeature,"unit"),
                            self.feature(unitTypeFeatureFactory("infantry"),"unit"),
                            self.feature(unitTypeFeatureFactory("mechinf"),"unit"),
                            self.feature(unitTypeFeatureFactory("armor"),"unit"),
                            self.feature(unitTypeFeatureFactory("artillery"),"unit"),
                            self.feature(terrainFeatureFactory("clear"),"hex"),
                            self.feature(terrainFeatureFactory("water"),"hex"),
                            self.feature(terrainFeatureFactory("rough"),"hex"),
                            self.feature(terrainFeatureFactory("urban"),"hex")
                         ] )
    def legalMoveHexes(self, mover):
        result = {}
        if mover:
            fireTargets = mover.findFireTargets(self.unitData)
            for unt in fireTargets:
                result[unt.hex.id] = True
            moveTargets = mover.findMoveTargets(self.mapData, self.unitData)
            for hex in moveTargets:
                result[hex.id] = True
        return result
    def getNFeatures(self):
        return 12


class AI13(AI):
    def __init__(self, role, kwargs):
        AI.__init__(self, role, kwargs)
    def observation(self):
        next_mover = self.nextMover()
        legal_move_hexes = self.legalMoveHexes(next_mover)
        phase_indicator = 0.9**self.phaseCount
        return np.stack( [
                            self.feature(moverFeatureFactory(next_mover),"unit"),
                            self.feature(legalMoveFeatureFactory(legal_move_hexes),"hex"),
                            self.feature(blueUnitFeature,"unit"), 
                            self.feature(redUnitFeature,"unit"),
                            self.feature(unitTypeFeatureFactory("infantry"),"unit"),
                            self.feature(unitTypeFeatureFactory("mechinf"),"unit"),
                            self.feature(unitTypeFeatureFactory("armor"),"unit"),
                            self.feature(unitTypeFeatureFactory("artillery"),"unit"),
                            self.feature(terrainFeatureFactory("clear"),"hex"),
                            self.feature(terrainFeatureFactory("water"),"hex"),
                            self.feature(terrainFeatureFactory("rough"),"hex"),
                            self.feature(terrainFeatureFactory("urban"),"hex"),
                            self.feature(constantFeatureFactory(phase_indicator),"hex")
                         ] )
    def legalMoveHexes(self, mover):
        result = {}
        if mover:
            fireTargets = mover.findFireTargets(self.unitData)
            for unt in fireTargets:
                result[unt.hex.id] = True
            moveTargets = mover.findMoveTargets(self.mapData, self.unitData)
            for hex in moveTargets:
                result[hex.id] = True
        return result
    def getNFeatures(self):
        return 13

class AI14(AI):
    def __init__(self, role, kwargs):
        AI.__init__(self, role, kwargs)
    def observation(self):
        next_mover = self.nextMover()
        legal_move_hexes = self.legalMoveHexes(next_mover)
        phase_indicator = 0.9**self.phaseCount
        return np.stack( [
                            self.feature(moverFeatureFactory(next_mover),"unit"),
                            self.feature(canMoveFeature,"unit"),
                            self.feature(legalMoveFeatureFactory(legal_move_hexes),"hex"),
                            self.feature(blueUnitFeature,"unit"), 
                            self.feature(redUnitFeature,"unit"),
                            self.feature(unitTypeFeatureFactory("infantry"),"unit"),
                            self.feature(unitTypeFeatureFactory("mechinf"),"unit"),
                            self.feature(unitTypeFeatureFactory("armor"),"unit"),
                            self.feature(unitTypeFeatureFactory("artillery"),"unit"),
                            self.feature(terrainFeatureFactory("clear"),"hex"),
                            self.feature(terrainFeatureFactory("water"),"hex"),
                            self.feature(terrainFeatureFactory("rough"),"hex"),
                            self.feature(terrainFeatureFactory("urban"),"hex"),
                            self.feature(constantFeatureFactory(phase_indicator),"hex")
                         ] )
    def legalMoveHexes(self, mover):
        result = {}
        if mover:
            fireTargets = mover.findFireTargets(self.unitData)
            for unt in fireTargets:
                result[unt.hex.id] = True
            moveTargets = mover.findMoveTargets(self.mapData, self.unitData)
            for hex in moveTargets:
                result[hex.id] = True
        return result
    def getNFeatures(self):
        return 14


class AI16(AI):
    def __init__(self, role, kwargs):
        AI.__init__(self, role, kwargs)
    def observation(self):
        next_mover = self.nextMover()
        legal_move_hexes = self.legalMoveHexes(next_mover)
        phase_indicator = 0.9**(self.maxPhases-1-self.phaseCount)
        return np.stack( [
                            self.feature(moverFeatureFactory(next_mover),"unit"),
                            self.feature(canMoveFeature,"unit"),
                            self.feature(legalMoveFeatureFactory(legal_move_hexes),"hex"),
                            self.feature(blueUnitFeature,"unit"), 
                            self.feature(redUnitFeature,"unit"),
                            self.feature(unitTypeFeatureFactory("infantry"),"unit"),
                            self.feature(unitTypeFeatureFactory("mechinf"),"unit"),
                            self.feature(unitTypeFeatureFactory("armor"),"unit"),
                            self.feature(unitTypeFeatureFactory("artillery"),"unit"),
                            self.feature(terrainFeatureFactory("clear"),"hex"),
                            self.feature(terrainFeatureFactory("water"),"hex"),
                            self.feature(terrainFeatureFactory("rough"),"hex"),
                            self.feature(terrainFeatureFactory("urban"),"hex"),
                            self.feature(cityOwnerFeatureFactory("blue"),"owner"),
                            self.feature(cityOwnerFeatureFactory("red"),"owner"),
                            self.feature(constantFeatureFactory(phase_indicator),"hex")
                         ] )
    def legalMoveHexes(self, mover):
        result = {}
        if mover:
            fireTargets = mover.findFireTargets(self.unitData)
            for unt in fireTargets:
                result[unt.hex.id] = True
            moveTargets = mover.findMoveTargets(self.mapData, self.unitData)
            for hex in moveTargets:
                result[hex.id] = True
        return result
    def getNFeatures(self):
        return 16

class AI17(AI):
    def __init__(self, role, kwargs):
        AI.__init__(self, role, kwargs)
        self.score_normalizer = 1000.0
    def observation(self):
        next_mover = self.nextMover()
        legal_move_hexes = self.legalMoveHexes(next_mover)
        phase_indicator = 0.9**(self.maxPhases-1-self.phaseCount)
        normalized_score = self.score / self.score_normalizer
        return np.stack( [
                            self.feature(moverFeatureFactory(next_mover),"unit"),
                            self.feature(canMoveFeature,"unit"),
                            self.feature(legalMoveFeatureFactory(legal_move_hexes),"hex"),
                            self.feature(blueUnitFeature,"unit"), 
                            self.feature(redUnitFeature,"unit"),
                            self.feature(unitTypeFeatureFactory("infantry"),"unit"),
                            self.feature(unitTypeFeatureFactory("mechinf"),"unit"),
                            self.feature(unitTypeFeatureFactory("armor"),"unit"),
                            self.feature(unitTypeFeatureFactory("artillery"),"unit"),
                            self.feature(terrainFeatureFactory("clear"),"hex"),
                            self.feature(terrainFeatureFactory("water"),"hex"),
                            self.feature(terrainFeatureFactory("rough"),"hex"),
                            self.feature(terrainFeatureFactory("urban"),"hex"),
                            self.feature(cityOwnerFeatureFactory("blue"),"owner"),
                            self.feature(cityOwnerFeatureFactory("red"),"owner"),
                            self.feature(constantFeatureFactory(phase_indicator),"hex"),
                            self.feature(constantFeatureFactory(normalized_score),"hex")
                         ] )
    def legalMoveHexes(self, mover):
        result = {}
        if mover:
            fireTargets = mover.findFireTargets(self.unitData)
            for unt in fireTargets:
                result[unt.hex.id] = True
            moveTargets = mover.findMoveTargets(self.mapData, self.unitData)
            for hex in moveTargets:
                result[hex.id] = True
        return result
    def getNFeatures(self):
        return 17
    
class AI18(AI):
    def __init__(self, role, kwargs):
        AI.__init__(self, role, kwargs)
    def observation(self):
        next_mover = self.nextMover()
        legal_move_hexes = self.legalMoveHexes(next_mover)
        phase_indicator = 0.9**self.phaseCount
        normalized_score = self.score/1000.0
        return np.stack( [
                            self.feature(moverFeatureFactory(next_mover),"unit"),
                            self.feature(canMoveFeature,"unit"),
                            self.feature(blueUnitFeature,"unit"), 
                            self.feature(redUnitFeature,"unit"),
                            self.feature(unitTypeFeatureFactory("infantry"),"unit"),
                            self.feature(unitTypeFeatureFactory("mechinf"),"unit"),
                            self.feature(unitTypeFeatureFactory("armor"),"unit"),
                            self.feature(unitTypeFeatureFactory("artillery"),"unit"),
                            self.feature(terrainFeatureFactory("clear"),"hex"),
                            self.feature(terrainFeatureFactory("water"),"hex"),
                            self.feature(terrainFeatureFactory("rough"),"hex"),
                            self.feature(terrainFeatureFactory("urban"),"hex"),
                            self.feature(terrainFeatureFactory("marsh"),"hex"),
                            self.feature(terrainFeatureFactory("unused"),"hex"),
                            self.feature(cityOwnerFeatureFactory("blue"),"owner"),
                            self.feature(cityOwnerFeatureFactory("red"),"owner"),
                            self.feature(constantFeatureFactory(phase_indicator),"hex"),
                            self.feature(constantFeatureFactory(normalized_score),"hex")
                         ] )
    def legalMoveHexes(self, mover):
        result = {}
        if mover:
            fireTargets = mover.findFireTargets(self.unitData)
            for unt in fireTargets:
                result[unt.hex.id] = True
            moveTargets = mover.findMoveTargets(self.mapData, self.unitData)
            for hex in moveTargets:
                result[hex.id] = True
        return result
    def getNFeatures(self):
        return 18

async def client(ai, uri):
    async with websockets.connect(uri) as websocket:
        while True:
            message = await websocket.recv()
            print(f"Message received by AI over websocket: {message[:100]}")
            result = ai.process(message)
            if result:
                await websocket.send( result )

def strengthUnitFeature(unt, faction):
    if not unt.ineffective and unt.faction == faction:
        return unt.currentStrength/100.0
    else:
        return 0.0
        
def blueUnitFeature(unt):
    return strengthUnitFeature(unt,"blue")
    
def redUnitFeature(unt):
    return strengthUnitFeature(unt,"red")

def canMoveFeature(unt):
    if not unt.ineffective and unt.canMove:
        return 1.0
    else:
        return 0.0
    
def moverFeatureFactory(moving_unit):
    def inner(unt):
        if unt==moving_unit:
            return 1.0
        return 0.0
    return inner

def unitTypeFeatureFactory(type):
    def inner(unt):
        if unt.type == type:
            return 1.0
        return 0.0
    return inner

def terrainFeatureFactory(terrain):
    def inner(hex):
        if hex.terrain == terrain:
            return 1.0
        return 0.0
    return inner 

def cityOwnerFeatureFactory(faction):
    def inner(hex, owners):
        if hex in owners and owners[hex]==faction:
            return 1.0
        return 0.0
    return inner

def legalMoveFeatureFactory(legal_move_hexes):
    def inner(hex):
        if hex.id in legal_move_hexes:
            return 1.0
        return 0.0
    return inner

def constantFeatureFactory(value):
    def inner(hex):
        return value
    return inner

def nnetObservation(paramD, obsD):
    mapData = map.MapData()
    unitData = unit.UnitData()        
    map.fromPortable(paramD['map'], mapData)
    unit.fromPortable(paramD['units'], unitData, mapData)

    def _nextMover():
        movingFaction = obsD["status"]["onMove"]
        for un in unitData.units():
            if un.faction==movingFaction and un.canMove and not un.ineffective:
                return un
        return None

    def _legalMoveHexes(mover):
        result = {}
        if mover:
            fireTargets = mover.findFireTargets(unitData)
            for unt in fireTargets:
                result[unt.hex.id] = True
            moveTargets = mover.findMoveTargets(mapData, unitData)
            for hex in moveTargets:
                result[hex.id] = True
        return result

    def _feature(fn, type):
        count = 0
        arrayIndex = {}
        inverseIndex = []
        for hexId in mapData.hexIndex:
            arrayIndex[hexId] = count
            inverseIndex.append(hexId)
            count += 1
        dim = mapData.getDimensions()
        mat = np.zeros((dim['height'],dim['width']))
        if type=="hex":
            for hexId in mapData.hexIndex:
                hex = mapData.hexIndex[hexId]
                mat[hex.y_offset, hex.x_offset] = fn(hex)
        elif type=="unit":
            for unitId in unitData.unitIndex:
                unt = unitData.unitIndex[unitId]
                hex = unt.hex
                if hex:
                    mat[hex.y_offset, hex.x_offset] = fn(unt)
        else: # type=="owner"
            city_owners = obsD['status']['cityOwner']
            for hexId in city_owners:
                hex = mapData.hexIndex[hexId]
                mat[hex.y_offset, hex.x_offset] = fn(hexId, city_owners)
        return mat

    maxPhases = paramD['score']['maxPhases']
    phaseCount = obsD['status']['phaseCount']

    next_mover = _nextMover()
    legal_move_hexes = _legalMoveHexes(next_mover)
    phase_indicator = 0.9**(maxPhases-1-phaseCount)
    return np.stack( [
                        _feature(moverFeatureFactory(next_mover),"unit"),
                        _feature(canMoveFeature,"unit"),
                        _feature(legalMoveFeatureFactory(legal_move_hexes),"hex"),
                        _feature(blueUnitFeature,"unit"), 
                        _feature(redUnitFeature,"unit"),
                        _feature(unitTypeFeatureFactory("infantry"),"unit"),
                        _feature(unitTypeFeatureFactory("mechinf"),"unit"),
                        _feature(unitTypeFeatureFactory("armor"),"unit"),
                        _feature(unitTypeFeatureFactory("artillery"),"unit"),
                        _feature(terrainFeatureFactory("clear"),"hex"),
                        _feature(terrainFeatureFactory("water"),"hex"),
                        _feature(terrainFeatureFactory("rough"),"hex"),
                        _feature(terrainFeatureFactory("urban"),"hex"),
                        _feature(cityOwnerFeatureFactory("blue"),"owner"),
                        _feature(cityOwnerFeatureFactory("red"),"owner"),
                        _feature(constantFeatureFactory(phase_indicator),"hex")
                        ] )
    
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
