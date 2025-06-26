import sys
sys.path.append("..")
import unit
import map
import numpy as np

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
    
def nnetObservation(board):
    paramD = board["param"]
    obsD = board["state"]
    mapData = map.MapData()
    unitData = unit.UnitData()        
    map.fromPortable(paramD['map'], mapData)
    unit.fromPortable(paramD['units'], unitData, mapData)
    return make_observation(paramD, obsD, mapData, unitData)

def make_observation(paramD, obsD, mapData, unitData):
    
    movingFaction = obsD["status"]["onMove"]
    score = float( obsD["status"]["score"] ) 
    normalized_score = score / 1000.0

    def _nextMover():
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
    if movingFaction == "blue":
        return np.stack( [
                            #_feature(moverFeatureFactory(next_mover),"unit"),
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
                            _feature(constantFeatureFactory(phase_indicator),"hex"),
                            _feature(constantFeatureFactory(normalized_score),"hex")
                            ] )
    else:
        return np.stack( [
                            #_feature(moverFeatureFactory(next_mover),"unit"),
                            _feature(canMoveFeature,"unit"),
                            _feature(legalMoveFeatureFactory(legal_move_hexes),"hex"),
                            _feature(redUnitFeature,"unit"),
                            _feature(blueUnitFeature,"unit"), 
                            _feature(unitTypeFeatureFactory("infantry"),"unit"),
                            _feature(unitTypeFeatureFactory("mechinf"),"unit"),
                            _feature(unitTypeFeatureFactory("armor"),"unit"),
                            _feature(unitTypeFeatureFactory("artillery"),"unit"),
                            _feature(terrainFeatureFactory("clear"),"hex"),
                            _feature(terrainFeatureFactory("water"),"hex"),
                            _feature(terrainFeatureFactory("rough"),"hex"),
                            _feature(terrainFeatureFactory("urban"),"hex"),
                            _feature(cityOwnerFeatureFactory("red"),"owner"),
                            _feature(cityOwnerFeatureFactory("blue"),"owner"),
                            _feature(constantFeatureFactory(phase_indicator),"hex"),
                            _feature(constantFeatureFactory(normalized_score),"hex")
                            ] )
