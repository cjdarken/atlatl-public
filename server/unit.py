import map
import mobility
import combat
from random import random

class UnitData:
    def __init__(self):
        self.unitIndex = {} # id to Unit
        self.occupancy = {} # hex id to Unit list
    def units(self):
        return list(self.unitIndex.values())
    def setCanMove(self, value, faction):
        for unit in self.units():
            if unit.ineffective:
                unit.canMove = False
            elif unit.faction == faction:
                unit.canMove = value
    def toPortable(self, observer="white"):
        # Ground truth state if observer="white"
        self.updateDetectionStatus()
        result = []
        for unit in self.units():
            unitD = {}
            unitD['type'] = unit.type
            unitD['faction'] = unit.faction
            unitD['longName'] = unit.longName
            unitD['currentStrength'] = unit.currentStrength
            unitD['hex'] = None
            if unit.hex:
                unitD['hex'] = unit.hex.id
            unitD['canMove'] = unit.canMove
            unitD['ineffective'] = unit.ineffective
            if observer != "white" and unit.faction != observer and not unit.detected:
                unitD['hex'] = "fog"
            unitD['detected'] = unit.detected
            result.append(unitD)
        return result
    def updateDetectionStatus(self):
        units = self.units()
        # Keep old detection status. Detection is stochastic. Undetection is deterministic.
        wasDetected = {}
        for unit in units:
            wasDetected[unit.uniqueId] = unit.detected
            unit.detected = False
        n_units = len(units)
        for i in range(0,n_units):
            uA = units[i]
            if uA.ineffective:
                continue
            for j in range(0,i):
                uB = units[j]
                if uB.ineffective:
                    continue
                if uA.faction == uB.faction:
                    continue
                xA, yA = uA.hex.x_grid, uA.hex.y_grid
                xB, yB = uB.hex.x_grid, uB.hex.y_grid
                distAB = map.gridDistance(xA,yA,xB,yB)
                if distAB <= combat.sight[uA.type] and (wasDetected[uB.uniqueId] or random()<combat.pDetect):
                    uB.detected = True
                if distAB <= combat.sight[uB.type] and (wasDetected[uA.uniqueId] or random()<combat.pDetect):
                    uA.detected = True
    def getFaction(self,faction):
        result = []
        for unit in self.units():
            if unit.faction==faction:
                result.append(unit)
        return result

class Unit:
    def __init__(self, param, unitData, mapData=None):
        # Set by scenario
        self.type = param['type']
        self.longName = param['longName']
        self.faction = param['faction']
        self.currentStrength = param['currentStrength']
        self.detected = False
        if 'detected' in param:
            self.detected = param['detected']
        # Derived
        self.uniqueId = self.faction+" "+ self.longName
        self.hex = None
        if param['hex']:
            self.setHex( mapData.hexIndex[ param['hex'] ], unitData )
        # Set or derived
        if "canMove" in param:
            self.canMove = param['canMove']
        else:
            self.canMove = False
        if "ineffective" in param:
            self.ineffective = param['ineffective']
        else:
            self.ineffective = False
        # Register with static index
        unitData.unitIndex[self.uniqueId] = self
    def setHex(self, hex, unitData):
        occupancy = unitData.occupancy
        if self.hex:
            occupants = occupancy[self.hex.id]
            if occupants:
                occupants.remove(self)
        self.hex = hex
        if not self.hex.id in occupancy:
            occupancy[self.hex.id] = []
        occupancy[self.hex.id].append(self) 
    def remove(self, unitData):
        occupancy = unitData.occupancy
        if self.hex:
            occupants = occupancy[self.hex.id]
            if occupants:
                occupants.remove(self)
        self.hex = None
    def _findMoveTargets(self, hex, type, mapData, unitData):
        occupancy = unitData.occupancy
        origin = hex
        moveTargets = []
        moveCost = {}
        agenda = [origin] # Check if children of these hexes are valid move targets
        moveCost[hex.id] = 0
        while agenda:
            hex = agenda.pop(0)
            for neigh in map.getNeighborHexes(hex, mapData):
                if neigh.id in moveCost:
                    continue
                if neigh.id in occupancy and len(occupancy[neigh.id]) + 1 > mobility.stackingLimit:
                    continue
                deltaCost = mobility.cost[type][neigh.terrain]
                totalCost = moveCost[hex.id] + deltaCost
                if totalCost <= 100:
                    moveCost[neigh.id] = totalCost
                    moveTargets.append( neigh )
                    if totalCost < 100:
                        agenda.append( neigh )
        return moveTargets
    def findMoveTargets(self, mapData, unitData): 
        return self._findMoveTargets(self.hex, self.type, mapData, unitData)
    def findFireTargets(self, unitData):
        fireTargets = []
        maxRange = combat.range[self.type]
        for target in unitData.units():
            if target.faction == self.faction:
                continue
            if target.ineffective or not target.hex:
                continue
            range = map.gridDistance(self.hex.x_grid, self.hex.y_grid, target.hex.x_grid, target.hex.y_grid)
            if range <= maxRange:
                fireTargets.append(target)
        return fireTargets
    def portableCopy(self):
        copy = {}
        copy['type'] = self.type
        copy['longName'] = self.longName
        copy['faction'] = self.faction
        copy['currentStrength'] = self.currentStrength
        if self.hex:
            copy['hex'] = self.hex.id
        else:
            copy['hex'] = None
        copy['canMove'] = self.canMove
        copy['ineffective'] = self.ineffective
        return copy
    def partialObsUpdate(self, obs, unitData, mapData):
        self.currentStrength = obs['currentStrength']
        self.canMove = obs['canMove']
        self.ineffective = obs['ineffective']
        if not self.ineffective and not obs['hex']=="fog":
            hex = mapData.hexIndex[ obs['hex'] ]
            self.setHex(hex, unitData)
        else:
            self.remove(unitData)
    
def fromPortable(pUnits, unitData, mapData):
    for pUnit in pUnits:
        unit = Unit(pUnit, unitData, mapData)
        
    
