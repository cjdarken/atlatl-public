import asyncio
import websockets
import json
import argparse
import numpy as np

from stable_baselines3 import PPO, DQN

# This AI has a representation of the map and units, and updates the unit representation as it changes
import map
import unit

default_neural_net_file = "model_save.zip"
action_count = 0

def debugPrint(str):
    condition = False
    if condition:
        print(str)

class AI:
    evenXOffsets18 = ((0,-1), (1,-1), (1,0), (0,1), (-1,0), (-1,-1),
                        (0,-2), (1,-2), (2,-1), (2,0), (2,1), (1,1), 
                        (0,2), (-1,1), (-2,1), (-2,0), (-2,-1), (-1,-2))
    oddXOffsets18 = ((0,-1), (1,0), (1,1), (0,1), (-1,1), (-1,0),
                        (0,-2), (1,-1), (2,-1), (2,0), (2,1), (1,2), 
                        (0,2), (-1,2), (-2,1), (-2,0), (-2,-1), (-1,-1))
    def __init__(self, role, kwargs):
        self.role = role
        if "neuralNet" in kwargs:
            neural_net_file = kwargs["neuralNet"]
        else:
            neural_net_file = default_neural_net_file
        self.dqn = ("dqn" in kwargs) and kwargs["dqn"]
        if self.dqn:
            self.model = DQN.load(neural_net_file)
        else:
            self.model = PPO.load(neural_net_file)
        self.doubledCoordinates = kwargs["doubledCoordinates"]
        self.mapData = None
        self.unitData = None
        self.reset()
    def reset(self):
        self.attempted_moveD = {}
        self.phaseCount = 0
    def nextMover(self):
        for un in self.unitData.units():
            if un.faction==self.role and not self.attempted_moveD[un.uniqueId] and not un.ineffective:
                return un
        return None
    def moveMessage(self):
        while self.nextMover():
            debugPrint(f"processing next mover {self.nextMover().uniqueId}")
            action, _states = self.model.predict(self.observation())
            msg = self.actionMessageDiscrete(action)
            if msg != None:
                return msg
        # No next mover
        return { "type":"action", "action":{"type":"pass"} }
    def process(self, message, response_fn=None):
        msgD = json.loads(message)
        if msgD['type'] == "parameters":
            paramD = msgD['parameters']
            # reset state variables
            self.mapData = map.MapData()
            self.unitData = unit.UnitData()
            self.phase = None
            for unt in self.unitData.units():
                if unt.faction == self.role:
                    self.attempted_moveD[unt.uniqueId] = False           
            map.fromPortable(paramD['map'], self.mapData)
            unit.fromPortable(paramD['units'], self.unitData, self.mapData)
            responseD = { "type":"role-request", "role":self.role}
        elif msgD['type'] == 'observation':
            obs = msgD['observation']
            self.score = obs["status"]["score"]
            self.city_owners = obs["status"]["cityOwner"]
            if not obs['status']['isTerminal'] and obs['status']['onMove'] == self.role:
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
                    for unitObs in obs['units']:
                        uniqueId = unitObs['faction'] + " " + unitObs['longName']
                        un = self.unitData.unitIndex[ uniqueId ]
                        un.partialObsUpdate( unitObs, self.unitData, self.mapData )
                    responseD = self.moveMessage() # Might be a pass
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
        if self.doubledCoordinates:
            mat = np.zeros((2*dim['height']+1,dim['width']))
        else:
            mat = np.zeros((dim['height'],dim['width']))
        if type=="hex":
            for hexId in self.mapData.hexIndex:
                hex = self.mapData.hexIndex[hexId]
                x_mat, y_mat = hex.x_offset, hex.y_offset
                if self.doubledCoordinates:
                    y_mat = 2*y_mat + x_mat%2
                mat[y_mat, x_mat] = fn(hex)
        elif type=="unit":
            for unitId in self.unitData.unitIndex:
                unt = self.unitData.unitIndex[unitId]
                hex = unt.hex
                if hex:
                    x_mat, y_mat = hex.x_offset, hex.y_offset
                    if self.doubledCoordinates:
                        y_mat = 2*y_mat + x_mat%2
                    mat[y_mat, x_mat] = fn(unt)
        else: # type=="owner"
            for hexId in self.city_owners:
                hex = self.mapData.hexIndex[hexId]
                mat[hex.y_offset, hex.x_offset] = fn(hexId, self.city_owners)
        return mat
    def observation(self):
        next_mover = self.nextMover()
        return np.stack( [
                            self.feature(moverFeatureFactory(next_mover),"unit"),
                            self.feature(blueUnitFeature,"unit"), 
                            self.feature(redUnitFeature,"unit")
                         ] )
    def action_result(self):
        done = self.last_terminal
        reward = self.accumulated_reward
        self.last_terminal = None # Make False???
        self.accumulated_reward = 0
        debugPrint(f'action_result returning done {done}')
        return (self.observation(), reward, done, {})
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
        
        debugPrint(f'gym_ai_surrogate:actionMessageDiscrete mover {mover.uniqueId} hex {mover.hex.id} action {action}')
            
        if action==0:
            debugPrint("Action was wait")
            return self.noneOrEndMove() # wait
        hex = mover.hex
        moveTargets = mover.findMoveTargets(self.mapData, self.unitData)
        fireTargets = mover.findFireTargets(self.unitData)
        if not moveTargets and not fireTargets:
            # No legal moves
            debugPrint("No legal moves")
            return self.noneOrEndMove()
        if hex.x_offset%2:
            delta = AI.oddXOffsets18[action-1]
        else:
            delta = AI.evenXOffsets18[action-1]
        to_hex_id = f'hex-{hex.x_offset+delta[0]}-{hex.y_offset+delta[1]}'
        if not to_hex_id in self.mapData.hexIndex:
            # Off-map move.
            debugPrint("Off-map move")
            return self.noneOrEndMove()
        to_hex = self.mapData.hexIndex[to_hex_id]
        if to_hex in moveTargets:
            return {"type":"action", "action":{"type":"move", "mover":mover.uniqueId, "destination":to_hex_id}}
        for fireTarget in fireTargets:
            if to_hex == fireTarget.hex:
                return {"type":"action", "action":{"type":"fire", "source":mover.uniqueId, "target":fireTarget.uniqueId}}
        # Illegal move request
        debugPrint("Illegal move")
        return self.noneOrEndMove()

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
    # def getNFeatures(self):
    #     return 12  
    
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

def cityOwnerFeatureFactory(faction):
    def inner(hex, owners):
        if hex in owners and owners[hex]==faction:
            return 1.0
        return 0.0
    return inner

async def client(ai, uri):
    async with websockets.connect(uri) as websocket:
        await websocket.send( json.dumps( { "type" : "role-request", "requested-role" : ai.role } ) )
        #async for message_S in websocket:
        while True:
            message_S = await websocket.recv()
            print(f"Message received by TeamX over websocket: {message_S[:100]}")
            message = json.loads(message_S)
            result = ai.process(message)
            await websocket.send( json.dumps(result) )
    
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
