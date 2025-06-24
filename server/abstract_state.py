import json
from game import Game
from unit import UnitData, fromPortable, Unit
import map
import math
import copy

SQRT3 = math.sqrt(3)

def getCM(units):
    cm = (0,0)
    total_strength = 0
    for unit in units:
        if unit.ineffective:
            continue
        # Get offset coordinates and strength
        # Convert to Euclidean coordinates
        # Compute weighted average
        hex = unit.hex
        col = hex.x_offset
        row = hex.y_offset
        x = 3*col
        y = (2*row+col%2)*SQRT3
        strength = unit.currentStrength
        total_strength += strength
        cm =(cm[0]+strength*x, cm[1]+strength*y)
    if total_strength == 0:
        return None
    cm = (cm[0]/total_strength, cm[1]/total_strength)
    return cm

def getContainingHex(pos):
    x,y = pos[0],pos[1]
    # Convert to rectangular lattice coordinates
    xl = x + 2
    yl = y + SQRT3
    c = math.floor(xl/3) # rectangle's column
    row_float = yl/2/SQRT3
    r = math.floor(yl/2/SQRT3) # rectangle's row
    if row_float == r:
        r -= 1 # If on the boundary line, round down
    # Coords relative to middle of left side of rectangle
    x_rel = xl - 3*c
    y_rel = yl - 2*SQRT3*(r+0.5)
    # Tall hex extends from top to bottom of rectangle
    tall_hex = (2*math.floor(c/2),r)
    if c%2: # odd column
        # Majority hex is on left
        # UR = upper right, etc.
        LR = (tall_hex[0]+1, tall_hex[1])
        UR = (tall_hex[0]+1, tall_hex[1]-1)
        # Fix rare problem with hex being outside map
        if LR[1] == -1:
            LR = (LR[0],0)
        if UR[1] == -1:
            UR = (UR[0],0)
        if x_rel < 1 - abs(y_rel)/SQRT3:
            return tall_hex
        elif y_rel <= 0:
            return UR
        else:
            return LR
    else: # even column
        # Majority hex is on right
        LL = (tall_hex[0]-1, tall_hex[1])
        UL = (tall_hex[0]-1, tall_hex[1]-1)
        # Fix rare problem with hex being outside map
        if LL[1] == -1:
            LL = (LL[0],0)
        if UL[1] == -1:
            UL = (UL[0],0)
        if x_rel > abs(y_rel)/SQRT3:
            return tall_hex
        elif y_rel>=0:
            return UL
        else:
            return LL

def subUnits(unitData, faction):
    allUnits = unitData.getFaction(faction)
    # Get all subunit id substrings
    subunits = {}
    for unit in allUnits:
        index = unit.longName.find('/')
        id = unit.longName[(index+1):]
        ids = subunits.get(id,[])
        ids.append(unit)
        subunits[id] = ids
    return subunits

def abstractUnitData(unitData, mapData, faction):
    dim = mapData.getDimensions()
    width = dim["width"]
    height = dim["height"]
    if faction=="blue":
        other_faction="red"
    else:
        other_faction="blue"
    absUnitData = UnitData()
    for unit in unitData.getFaction(other_faction):
        param = unit.portableCopy()
        Unit(param, absUnitData, mapData)
    subunits = subUnits(unitData, faction)
    for su in subunits:
        cm = getCM(subunits[su])
        if cm is None:
            continue
        col,row = getContainingHex(cm)
        # Ensure hex is in-bounds
        col = max(0,col)
        row = max(0,row)
        col = min(width-1,col)
        row = min(height-1,row)
        pos = (col,row)
        hex_id = f'hex-{pos[0]}-{pos[1]}'
        param = {}
        param['type'] = "infantry"
        param['longName'] = su
        param['faction'] = faction
        currentStrength = 0
        for un in subunits[su]:
            currentStrength += un.currentStrength
        param['currentStrength'] = currentStrength
        param['hex'] = hex_id
        param['canMove'] = True
        param['ineffective'] = False
        param['girth'] = 2
        Unit(param,absUnitData,mapData)

    return absUnitData

def createScenario(unitData, scenarioPo):
    vizOutput = copy.deepcopy(scenarioPo)
    vizOutput["units"] = abstate.toPortable()
    return json.dumps(vizOutput)


if __name__=="__main__":
    # Create scenario
    # Get CM of red and blue units
    #scenarioName = "column-5x5-water.scn"
    scenarioName = "subunit-test.scn"
    
    scenarioPo = json.load( open("scenarios/"+scenarioName) )
    mapData = map.MapData()
    map.fromPortable(scenarioPo["map"], mapData)
    game = Game(scenarioPo)
    state = game.initial_state()
    unitData = UnitData()
    fromPortable(state["units"], unitData, mapData)

    reds = unitData.getFaction("red")
    blues = unitData.getFaction("blue")
    cm_red = getCM(reds)
    cm_blue = getCM(blues)
    print(f'red cm {cm_red}  blue cm {cm_blue}')
    cm_red_hex = getContainingHex(cm_red)
    cm_blue_hex = getContainingHex(cm_blue)
    print(f'red containing hex {cm_red_hex} blue {cm_blue_hex}')

    subunits = subUnits(unitData, "blue")
    print(f'subunits {subunits}')
    for su in subunits:
        print(f'subUnit {su} cm {getContainingHex(getCM(subunits[su]))}')

    abstate = abstractUnitData(unitData,mapData,"blue")
    #print(f'abstract state {abstate.toPortable()}')

    #print(createScenario(abstate,scenarioPo))