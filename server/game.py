# Zero-sum two player wargame
# Game(scenarioPo, redFixed=False)
#   players() # returns list of player names
#   observation(state, player)
#   initial_state()
#   score(state)
#   max_player() # returns name of the player who maximizes score
#   on_move(state) # returns name of player on move
#   is_terminal(state)
#   legal_actions(state) # optional, some games have large action spaces
#   is_legal(state, action)
#   transition(state, action)
#   parameters() # returns the variant of the game to be played or empty object


import map
import status
import json
import copy
import combat
import random
from unit import UnitData, fromPortable

class Game:
    # Implements zero-sum game API
    def __init__(self, scenarioPo):
        self.scenarioPo = scenarioPo
        self.mapData = map.MapData()
        map.fromPortable(scenarioPo["map"], self.mapData)
    def initial_state(self):
        state = {}
        state["status"] = status.Status(self.scenarioPo, self.mapData).toPortable()
        state["units"] = copy.deepcopy( self.scenarioPo["units"] )
        self._setCanMove(state, "blue", value=True)
        return state
    def players(self):
        return ["blue", "red"]
    def on_move(self, state):
        return state["status"]["onMove"]
    def observation(self, state, player):
        unitData = UnitData()
        fromPortable(state['units'], unitData, self.mapData)
        fog_of_war = False
        if 'fogOfWar' in self.scenarioPo['map']:
            fog_of_war = self.scenarioPo['map']['fogOfWar']
        if not fog_of_war:
            observer = "white"
        else:
            observer = player
        obs = {}
        obs['units'] = unitData.toPortable(observer)
        obs['status'] = state['status']
        return obs
    def is_terminal(self, state):
        return state['status']['isTerminal']
    def parameters(self):
        return self.scenarioPo
    def score(self, state):
        return state['status']['score']
    def max_player(self):
        return "blue"
    def legal_actions(self, state):
        unitData = UnitData()
        fromPortable(state["units"], unitData, self.mapData)
        actions = []
        actions.append({"type":"pass"})
        if state["status"]["setupMode"]:
            return actions # Lie and say only passing is legal in setup mode
        for unitPo in state['units']:
            uniqueId = unitPo["faction"]+" "+unitPo["longName"]
            unit = unitData.unitIndex[ uniqueId ]
            if not unit.canMove or unit.ineffective:
                continue
            for hex in unit.findMoveTargets(self.mapData, unitData):
                actions.append( {"type":"move", "mover":unit.uniqueId, "destination":hex.id} )
            for target in unit.findFireTargets(unitData):
                actions.append( {"type":"fire", "source":unit.uniqueId, "target":target.uniqueId} )
        return actions
    def _is_legal_setup(self, state, action):
        if action['type']=="pass":
            return True
        unitData = UnitData()
        fromPortable(state["units"], unitData, self.mapData)
        mover_u = unitData.unitIndex[ action['mover'] ]
        # Is correct faction being moved?
        if mover_u.faction != state['status']['onMove']:
            return False
        if action['type']=="setup-move":
            hex = self.mapData.hexIndex[ action['destination'] ]
        elif action['type']=="setup-exchange":
            exchange_u = unitData.unitIndex[ action['friendly'] ]
            hex = exchange_u.hex
        else:
            return False
        # Is target a setup hex?
        if mover_u.faction=="red" and hex.setup != "setup-type-red":
            return False
        elif mover_u.faction=="blue" and hex.setup != "setup-type-blue":
            return False
        return True
    def _is_legal_move(self, state, action):
        def _actions_match(user_action, legal_action):
            for key in legal_action:
                if user_action[key] != legal_action[key]:
                    return False
            return True
        for legal_action in self.legal_actions(state):
            if _actions_match(action, legal_action):
                return True
        return False
    def transition(self, state, action):
        if action is None:
            raise Exception("action is None")
        unitData = UnitData()
        fromPortable(state["units"], unitData, self.mapData)
        statusO = status.Status.fromPortable(state["status"], self.scenarioPo, self.mapData)
        if state["status"]["setupMode"]:
            self._transition_setup(state, action, unitData)
        else:
            self._transition_move(state, action, unitData, statusO)
        if statusO.phaseComplete(unitData) or action['type']=="pass":
            statusO.advancePhase(unitData)   
        newState = {}
        newState['units'] = unitData.toPortable()
        newState['status'] = statusO.toPortable()
        return newState
    def _transition_setup(self, state, action, unitData):
        if not self._is_legal_setup(state, action):
            raise Exception( "Action is not legal in this state" )
        if action['type']=="pass":
            return
        elif action['type']=="setup-move":
            hex = self.mapData.hexIndex[ action['destination'] ]
            mover_u = unitData.unitIndex[ action['mover'] ]
            mover_u.remove(unitData)
            mover_u.setHex(hex, unitData)
        elif action['type']=="setup-exchange":
            mover_u = unitData.unitIndex[ action['mover'] ]
            exchange_u = unitData.unitIndex[ action['friendly'] ]
            mover_h = mover_u.hex
            exchange_h = exchange_u.hex
            mover_u.remove(unitData)
            exchange_u.remove(unitData)
            mover_u.setHex(exchange_h, unitData)
            exchange_u.setHex(mover_h, unitData)
    def _transition_move(self, state, action, unitData, statusO):
        if not self._is_legal_move(state, action):
            print(f'nonsetup phase, action {action} legal actions {self.legal_actions(state)}')
            raise Exception( f"Action {action} is not legal in this state" )
        if action['type']=="move":
            mover_u = unitData.unitIndex[ action['mover'] ]
            hex = self.mapData.hexIndex[ action['destination'] ]
            mover_u.setHex(hex, unitData)
            mover_u.canMove = False
        elif action['type'] == "exchange":
            mover_u = unitData.unitIndex[ action['mover'] ]
            target_u = unitData.unitIndex[ action['target'] ]
            hex_mover = mover_u.hex
            hex_target = target_u.hex
            mover_u.setHex(hex_target, unitData)
            target_u.setHex(hex_mover, unitData)
        elif action['type'] == "fire":
            shooter_u = unitData.unitIndex[ action['source'] ]
            target_u = unitData.unitIndex[ action['target'] ]
            firepower = combat.firepower[shooter_u.type][target_u.type]
            defensivefp = combat.defensivefp[target_u.type][shooter_u.type]
            terrain_multiplier = combat.terrain_multiplier[target_u.type][target_u.hex.terrain]
            scale = combat.firepower_scaling
            dstrength = shooter_u.currentStrength * firepower * terrain_multiplier
            dstrength -= target_u.currentStrength * defensivefp
            dstrength *= scale
            if dstrength < 0:
                dstrength = 0
            target_u.currentStrength -= dstrength
            fullStrength = 100.0
            if target_u.currentStrength / fullStrength < combat.ineffectiveThreshold:
                dstrength += max(target_u.currentStrength,0)
                target_u.ineffective = True
                target_u.remove(unitData)
            statusO.dscoreKill(target_u.faction, dstrength)
            shooter_u.canMove = False  
    def _setCanMove(self, state, faction, value=True):
        for unit in state['units']:
            if unit['faction']==faction:
                unit['canMove'] = value

def statePlusParamHashKey(state, param):
    mapData = map.MapData()
    map.fromPortable(param["map"], mapData)
    unitData = UnitData()
    fromPortable(state["units"], unitData, mapData)
    statusData = status.Status.fromPortable(state["status"], param, mapData)
    phase = statusData.phases_complete
    if statusData.setup_mode:
        phase = state["status"]["onMove"] + " setup"
    score = statusData.score
    result = f'phase {phase} score {score}\n' # cityOwnership shown on map
    def hexStr(x,y):
        hex_name = "hex-"+str(x)+"-"+str(y)
        hex = mapData.hexIndex[hex_name]
        terrainCodes = {"clear":"c", "urban":"u", "rough":"r", "marsh":"m", "water":"w"}
        code = terrainCodes[hex.terrain]
        result = code
        if code=="u":
            owner = statusData.ownerD[hex_name]
            if owner=="blue":
                result += "b"
            elif owner=="red":
                result += "r"
        if hex_name in unitData.occupancy:
            unit = unitData.occupancy[hex_name][0]
            unitStr = str(int(unit.currentStrength))
            if unit.type=="infantry":
                unitStr += "i"
            elif unit.type=="armor":
                unitStr += "t"
            elif unit.type=="mechinf":
                unitStr += "m"
            elif unit.type=="artillery":
                unitStr += "a"
            if unit.faction=="blue":
                unitStr += "b"
            else:
                unitStr += "r"
            if unit.canMove:
                unitStr += "o"
            result += unitStr
        return result

    dim = mapData.getDimensions()
    width = dim["width"]
    height = dim["height"]
    for y in range(height):
        # odd columns
        for x in range(width):
            if (x+1)%2:
                result += hexStr(x,y)
            if x<width-1:
                result +="\t\t"
            else:
                result += "\n"
        # even columns
        for x in range(width):
            if x%2:
                result += hexStr(x,y)
            if x<width-1:
                result +="\t\t"
            else:
                result += "\n"
    return result


                
if __name__ == "__main__":
    random.seed(12345)
    stateD = {}
    scenarioName = "atomic.scn"
    scenarioPo = json.load( open("scenarios/"+scenarioName) )
    game = Game(scenarioPo)
    state = game.initial_state()
    stateD[json.dumps(state)] = True
    # Take some random actions
    nTransitions = 10000
    for i in range(nTransitions):
        if game.is_terminal(state):
            state = game.initial_state()
        chosenAction = random.choice( game.legal_actions(state) )
        state = game.transition(state,chosenAction)
        stateD[json.dumps(state)] = True
    print( f'num states visited: {len(stateD.keys())}' )