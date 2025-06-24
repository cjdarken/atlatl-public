from game import Game
from unit import UnitData, fromPortable
import numpy as np
import torch
import map
import combat

SCORE_SCALE_FACTOR = 0.01

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

def feature(fn, type, mapData, unitData, city_owners={}):
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
            x_mat, y_mat = hex.x_offset, hex.y_offset
            mat[y_mat, x_mat] = fn(hex)
    elif type=="unit":
        for unitId in unitData.unitIndex:
            unt = unitData.unitIndex[unitId]
            hex = unt.hex
            if hex:
                x_mat, y_mat = hex.x_offset, hex.y_offset
                mat[y_mat, x_mat] = fn(unt)
    else: # type=="owner"
        for hexId in city_owners:
            hex = mapData.hexIndex[hexId]
            mat[hex.y_offset, hex.x_offset] = fn(hexId, city_owners)
    return mat

def observation(game, state, flipFactions=False, appendFeatures=[]):
    unitData = UnitData()
    fromPortable(state["units"], unitData, game.mapData)
    phase_indicator = 1.0-0.9**state['status']['phaseCount']
    normalized_score = state["status"]["score"]/1000.0
    city_owners = state['status']['cityOwner']
    mdat = game.mapData
    udat = unitData
    if not flipFactions:
        x = np.stack( [
                        feature(canMoveFeature,"unit",mdat,udat),
                        feature(blueUnitFeature,"unit",mdat,udat), 
                        feature(redUnitFeature,"unit",mdat,udat),
                        feature(unitTypeFeatureFactory("infantry"),"unit",mdat,udat),
                        feature(unitTypeFeatureFactory("mechinf"),"unit",mdat,udat),
                        feature(unitTypeFeatureFactory("armor"),"unit",mdat,udat),
                        feature(unitTypeFeatureFactory("artillery"),"unit",mdat,udat),
                        feature(terrainFeatureFactory("clear"),"hex",mdat,udat),
                        feature(terrainFeatureFactory("water"),"hex",mdat,udat),
                        feature(terrainFeatureFactory("rough"),"hex",mdat,udat),
                        feature(terrainFeatureFactory("urban"),"hex",mdat,udat),
                        feature(terrainFeatureFactory("marsh"),"hex",mdat,udat),
                        feature(terrainFeatureFactory("unused"),"hex",mdat,udat),
                        feature(cityOwnerFeatureFactory("blue"),"owner",mdat,udat,city_owners),
                        feature(cityOwnerFeatureFactory("red"),"owner",mdat,udat,city_owners),
                        feature(constantFeatureFactory(phase_indicator),"hex",mdat,udat),
                        feature(constantFeatureFactory(normalized_score),"hex",mdat,udat)
                        ] + appendFeatures )
    else: # flipFactions is True
        x = np.stack( [
                        feature(canMoveFeature,"unit",mdat,udat),
                        feature(redUnitFeature,"unit",mdat,udat), # changed
                        feature(blueUnitFeature,"unit",mdat,udat), # changed
                        feature(unitTypeFeatureFactory("infantry"),"unit",mdat,udat),
                        feature(unitTypeFeatureFactory("mechinf"),"unit",mdat,udat),
                        feature(unitTypeFeatureFactory("armor"),"unit",mdat,udat),
                        feature(unitTypeFeatureFactory("artillery"),"unit",mdat,udat),
                        feature(terrainFeatureFactory("clear"),"hex",mdat,udat),
                        feature(terrainFeatureFactory("water"),"hex",mdat,udat),
                        feature(terrainFeatureFactory("rough"),"hex",mdat,udat),
                        feature(terrainFeatureFactory("urban"),"hex",mdat,udat),
                        feature(terrainFeatureFactory("marsh"),"hex",mdat,udat),
                        feature(terrainFeatureFactory("unused"),"hex",mdat,udat),
                        feature(cityOwnerFeatureFactory("red"),"owner",mdat,udat,city_owners), # changed
                        feature(cityOwnerFeatureFactory("blue"),"owner",mdat,udat,city_owners), # changed
                        feature(constantFeatureFactory(phase_indicator),"hex",mdat,udat),
                        feature(constantFeatureFactory(-normalized_score),"hex",mdat,udat) # changed
                        ] + appendFeatures )
    return torch.tensor(x,dtype=torch.float32)

class FadingTrailFeature:
    def __init__(self, observerRole, mapData, newValueWeight): 
        self.observerRole = observerRole
        dim = mapData.getDimensions()
        self.mat = np.zeros((dim['height'],dim['width']))
        self.mapData = mapData
        self.newValueWeight = newValueWeight
    def update(self, unitData):
        self.mat *= 1 - self.newValueWeight
        for unit in unitData.units():
            if unit.faction==self.observerRole or unit.ineffective or not unit.hex: continue
            x, y = unit.hex.x_offset, unit.hex.y_offset
            self.mat[y,x] = unit.currentStrength/100.0
        return self.mat

def fractionHiddenOpforFeature(observerRole, unitData, mapData):
    visible = 0
    hidden = 0
    for unit in unitData.units():
        if unit.faction==observerRole or unit.ineffective: continue
        if unit.hex: visible += 1
        else: hidden += 1
    return hidden,(visible+hidden)

class OpforDistrib:
    def __init__(self, epsilon, mapData, unitData, ownFaction, verbose=False):
        self.ownFaction = ownFaction
        self.verbose = verbose
        if self.ownFaction=="red":
            self.opforFaction = "blue"
        else:
            self.opforFaction = "red"
        self.epsilon = epsilon
        self.mapData = mapData
        # Arbitrary unit is used for mobility data
        for unit in unitData.units():
            if unit.faction==self.opforFaction:
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
    def add(self, unitData, priorUnitData):
        prior_n_hidden, _ = fractionHiddenOpforFeature(self.ownFaction, priorUnitData, self.mapData)
        for un in unitData.units():
            # Want living but hidden OPFOR
            if un.faction!=self.opforFaction or un.ineffective or un.hex: continue
            un0 = priorUnitData.unitIndex[un.uniqueId]
            # Want OPFOR that were recently visible
            if not un0.hex: continue
            # New value of distrib set to weight if it is currently less
            # This avoids too much density concentration at locations where
            #   entities are disappearing often (because it's likely the same entity)
            weight = self.sum/prior_n_hidden
            self.distr[un0.hex] = max(self.distr.get(un0.hex,0.0), weight)
            self.sum += weight
    def move(self, unitData):
        if self.verbose: print("In move")
        distrDelta = {}
        for hexId in self.distr:
            hex = self.mapData.hexIndex[hexId]
            if self.distr[hexId]==0.0:
                continue
            destinations =  self.opforUnitProto._findMoveTargets(hex, self.opforUnitProto.type, self.mapData, unitData)
            dp = self.epsilon*self.distr[hexId]
            if self.verbose: print(f'moving from {hexId}, destinations {destinations}')
            old_delta = distrDelta.get(hexId, 0.0)
            distrDelta[hexId] = old_delta - dp*len(destinations)
            for hex in destinations:
                old_delta = distrDelta.get(hex.id, 0.0)
                distrDelta[hex.id] = old_delta + dp
        for hexId in distrDelta:
            if self.verbose: print(f'hexId {hexId} delta {distrDelta[hexId]}')
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
                if self.verbose: print(f'culling {hex.id}')
    def update(self, currentUnitData, previousUnitData):
        self.add(currentUnitData, previousUnitData)
        self.move(currentUnitData)
        self.cull(currentUnitData)
    def getNormalizedDist(self):
        if self.sum>0:
            for hexId in self.distr:
                self.distr[hexId] /= self.sum
            self.sum = 1.0
        return self.distr

