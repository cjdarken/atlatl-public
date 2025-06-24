import random
import math
import json
import map
import unit
import copy


def from_file_factory(filename, scenario_dir="scenarios/"):
    scenario_S = open(scenario_dir+filename).read()
    scenarioPo = json.loads(scenario_S)
    def inner():
        return scenarioPo
    return inner  

def flip_colors(scenario):
    flipped_units = []
    for unit in scenario['units']:
        flipped_unit = copy.copy(unit)
        if unit['faction']=="red":
            flipped_unit['faction']="blue"
        else:
            flipped_unit['faction']="red"
        flipped_units.append(flipped_unit)
    flipped_scenario = copy.copy(scenario)
    flipped_scenario['units'] = flipped_units
    return flipped_scenario

def clear_square_factory(size=6, min_units=2, max_units=4, num_cities=0, scenarioSeed=None, scenarioCycle=0, balance=False, max_phases=10, fog_of_war=False):
    balance_next = False
    last_scenario = None
    priorstate = random.getstate()
    random.seed(scenarioSeed)
    randstate = random.getstate()
    random.setstate(priorstate)
    count = 0
    def inner():
        nonlocal randstate, scenarioSeed, scenarioCycle, count, balance_next, last_scenario
        if balance:
            if balance_next:
                balance_next = False
                return flip_colors(last_scenario)
            else:
                balance_next = True
        priorstate = random.getstate()
        random.setstate(randstate)
        if size<4:
            raise Exception(f'Requested size ({size}) too small (minimum is 4)')
        mapData = map.MapData()
        mapData.createHexGrid(size,size)
        unitData = unit.UnitData()
        def _add_units(faction,start_hexes):
            n = random.randint(min_units,max_units)
            for i in range(n):
                hex = random.choice(start_hexes)
                start_hexes.remove(hex)
                u_param = {"hex":hex,"type":"infantry","longName":str(i),"faction":faction,"currentStrength":100}
                unt = unit.Unit(u_param,unitData,mapData)
            return n
        blue_side, red_side = random.choice((("north","south"),("south","north"),("east","west"),("west","east")))
        blue_hexes = get_setup_hex_ids(size,blue_side)
        red_hexes = get_setup_hex_ids(size,red_side)
        n_blue = _add_units("blue",blue_hexes)
        n_red = _add_units("red",red_hexes)
        for i in range(num_cities):
            def place_city(city_loc):
                city_hexes = get_setup_hex_ids(size,city_loc)
                hex_id = random.choice(city_hexes)
                hex = mapData.hexIndex[hex_id]
                hex.terrain = "urban"
            if n_blue<n_red:
                place_city(blue_side)
            elif n_red<n_blue:
                place_city(red_side)
            else: # n_blue==n_red
                if blue_side in ["north", "south"]:
                    city_loc = "ns-middle"
                else:
                    city_loc = "ew-middle"
                place_city(city_loc)  
        count = count + 1
        if scenarioCycle:
            count %= scenarioCycle
        if scenarioCycle!=0 and count==0:
            random.seed(scenarioSeed)
        randstate = random.getstate()    
        score = {"maxPhases":max_phases,"lossPenalty":-1,"cityScore":24}
        random.setstate(priorstate)
        scenario = {"map":mapData.toPortable(), "units":unitData.toPortable(), "score":score}
        scenario["map"]["fogOfWar"] = fog_of_war
        last_scenario = scenario
        return scenario
    return inner

def get_setup_hex_ids(size, side, margin=1):
    low_setup_margin = math.floor(size/2)-margin
    high_setup_margin = math.floor(size/2)+margin
    hexes = []
    if side == "north":
        i_min, i_max, j_min, j_max = 0, size-1, 0, low_setup_margin
    elif side == "east":
        i_min, i_max, j_min, j_max = high_setup_margin, size-1, 0, size-1
    elif side == "south":
        i_min, i_max, j_min, j_max = 0, size-1, high_setup_margin, size-1
    elif side == "west":
        i_min, i_max, j_min, j_max = 0, low_setup_margin, 0, size-1
    elif side == "ns-middle":
        i_min, i_max, j_min, j_max = 0, size-1, low_setup_margin+1, high_setup_margin-1
    else: # "ew-middle"
        i_min, i_max, j_min, j_max = low_setup_margin+1, high_setup_margin-1, 0, size-1
    for i in range(i_min,i_max+1):
        for j in range(j_min,j_max+1):
            hexes.append("hex-"+str(i)+"-"+str(j))
    return hexes

def hierarchy_factory(size=10, min_parents=2, max_parents=4, hierarchy_depth=3, hierarchy_branching=3, num_cities=0, scenarioSeed=None, scenarioCycle=0, balance=False, max_phases=20, fog_of_war=False):
    sigmas = [1,2,3]
    balance_next = False
    last_scenario = None
    priorstate = random.getstate()
    random.seed(scenarioSeed)
    randstate = random.getstate()
    random.setstate(priorstate)
    count = 0
    def inner():
        nonlocal randstate, scenarioSeed, scenarioCycle, count, balance_next, last_scenario
        if balance:
            if balance_next:
                balance_next = False
                return flip_colors(last_scenario)
            else:
                balance_next = True
        priorstate = random.getstate()
        random.setstate(randstate)
        MIN_SIZE = 10
        if size<MIN_SIZE:
            raise Exception(f'Requested size ({size}) too small (minimum is {MIN_SIZE})')
        mapData = map.MapData()
        mapData.createHexGrid(size,size)
        unitData = unit.UnitData()
        def _add_units(faction,start_hexes):
            n_units = 0
            all_start_hexes = copy.copy(start_hexes)
            n_parents = random.randint(min_parents,max_parents)
            for i in range(n_parents):
                parent_id = str(i+1)
                cm_hex = random.choice(all_start_hexes)
                n_units += _add_subordinates(faction,start_hexes,all_start_hexes,cm_hex,parent_id,depth=1)
            return n_parents*hierarchy_branching**(hierarchy_depth-1)
        def _gaussian(center_hex,hex,sigma):
            dist = map.hexDistance(center_hex.x_offset,center_hex.y_offset,hex.x_offset,hex.y_offset)
            return math.exp(-dist**2/2/sigma**2)
        def _add_subordinates(faction,start_hexes,all_start_hexes,cm_hex_id,parent_id,depth): 
            if depth>=hierarchy_depth:
                return
            start_hex_objs = [mapData.hexIndex[hxid] for hxid in start_hexes]
            n_units = 0
            for i in range(hierarchy_branching):
                id = str(i+1)+"/"+parent_id
                cm_hex = mapData.hexIndex[cm_hex_id]
                weights = [_gaussian(cm_hex,hx,sigmas[hierarchy_depth-depth-1]) for hx in start_hex_objs]
                hex = random.choices(start_hex_objs, weights)[0]
                hex_id = hex.id
                if depth<hierarchy_depth-1: # Abstract unit
                    _add_subordinates(faction,start_hexes,all_start_hexes,hex_id,id,depth+1)
                else:
                    start_hex_objs.remove(hex)
                    u_param = {"hex":hex_id,"type":"infantry","longName":id,"faction":faction,"currentStrength":100}
                    unt = unit.Unit(u_param,unitData,mapData)
                    n_units += 1
            return n_units
        blue_side, red_side = random.choice((("north","south"),("south","north"),("east","west"),("west","east")))
        blue_hexes = get_setup_hex_ids(size,blue_side)
        red_hexes = get_setup_hex_ids(size,red_side)
        n_blue = _add_units("blue",blue_hexes)
        n_red = _add_units("red",red_hexes)
        for i in range(num_cities):
            def place_city(city_loc):
                city_hexes = get_setup_hex_ids(size,city_loc,margin=2)
                hex_id = random.choice(city_hexes)
                hex = mapData.hexIndex[hex_id]
                hex.terrain = "urban"
            if n_blue<n_red:
                place_city(blue_side)
            elif n_red<n_blue:
                place_city(red_side)
            else: # n_blue==n_red
                if blue_side in ["north", "south"]:
                    city_loc = "ns-middle"
                else:
                    city_loc = "ew-middle"
                place_city(city_loc)  
        count = count + 1
        if scenarioCycle:
            count %= scenarioCycle
        if scenarioCycle!=0 and count==0:
            random.seed(scenarioSeed)
        randstate = random.getstate()    
        score = {"maxPhases":max_phases,"lossPenalty":-1,"cityScore":24}
        random.setstate(priorstate)
        scenario = {"map":mapData.toPortable(), "units":unitData.toPortable(), "score":score}
        scenario["map"]["fogOfWar"] = fog_of_war
        last_scenario = scenario
        return scenario
    return inner

def get_rect_region_ids(i_min, i_max, j_min, j_max):
    return ["hex-"+str(i)+"-"+str(j) for i in range(i_min,i_max+1) for j in range(j_min,j_max+1)]

def invasion_factory(width=24, height=8, n_blue=10, n_red=4, num_cities=6, scenarioSeed=None, scenarioCycle=0, max_phases=16, fog_of_war=True, city_score=24):
    priorstate = random.getstate()
    random.seed(scenarioSeed)
    randstate = random.getstate()
    random.setstate(priorstate)
    count = 0
    def inner():
        nonlocal randstate, scenarioSeed, scenarioCycle, count
        priorstate = random.getstate()
        random.setstate(randstate)
        mapData = map.MapData()
        mapData.createHexGrid(height,width)
        unitData = unit.UnitData()
        def _add_units(faction,start_hexes,n_units):
            n = n_units
            for i in range(n):
                hex = random.choice(start_hexes)
                start_hexes.remove(hex)
                u_param = {"hex":hex,"type":"infantry","longName":str(i),"faction":faction,"currentStrength":100}
                unt = unit.Unit(u_param,unitData,mapData)
            return n
        blue_side, red_side = random.choice((("north","south"),("south","north")))
        i_min, i_max = 0, width-1
        if blue_side=="north": j_min, j_max = 0, 1
        else:  j_min, j_max = height-2, height-1
        blue_hexes = get_rect_region_ids(i_min, i_max, j_min, j_max)
        if red_side=="north": j_min, j_max = 0, round(height/2)-1
        else:  j_min, j_max = round(height/2), height-1
        red_hexes = get_rect_region_ids(i_min, i_max, j_min, j_max)
        for hex_id in blue_hexes:
            hex = mapData.hexIndex[hex_id]
            hex.setup = "setup-type-blue"
        for hex_id in red_hexes:
            hex = mapData.hexIndex[hex_id]
            hex.setup = "setup-type-red"
        _add_units("blue",blue_hexes,n_blue)
        _add_units("red",red_hexes,n_red)
        for i in range(num_cities):
            def place_city(city_loc):
                city_hexes = red_hexes
                hex_id = random.choice(city_hexes)
                hex = mapData.hexIndex[hex_id]
                hex.terrain = "urban"
            place_city(red_side)
        count = count + 1
        if scenarioCycle:
            count %= scenarioCycle
        if scenarioCycle!=0 and count==0:
            random.seed(scenarioSeed)
        randstate = random.getstate()    
        score = {"maxPhases":max_phases,"lossPenalty":-1,"cityScore":city_score}
        random.setstate(priorstate)
        scenario = {"map":mapData.toPortable(), "units":unitData.toPortable(), "score":score}
        scenario["map"]["fogOfWar"] = fog_of_war
        scenario["map"]["initialCityOwnership"] = "red"
        return scenario
    return inner


if __name__=="__main__":
    #print( clear_square_factory(num_cities=1)() )
    print( hierarchy_factory(size=10, min_parents=2, max_parents=4, hierarchy_depth=3, hierarchy_branching=3, num_cities=0, scenarioSeed=None, scenarioCycle=0, balance=False, max_phases=20, fog_of_war=False)() )
