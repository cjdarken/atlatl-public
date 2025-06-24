import scenario

scenario_generator_registry = {
    "clear-inf-6" : (scenario.clear_square_factory, {'size':6, 'min_units':2, 'max_units':4}),
    "clear-inf-5" : (scenario.clear_square_factory, {'size':5, 'min_units':2, 'max_units':4}),
    "city-inf-5" : (scenario.clear_square_factory, {'size':5, 'min_units':2, 'max_units':4, 'num_cities':1}),
    "city-inf-5-bal" : (scenario.clear_square_factory, {'size':5, 'min_units':2, 'max_units':4, 'num_cities':1, 'balance':True}),
    "fog-inf-5" : (scenario.clear_square_factory, {'size':5, 'min_units':1, 'max_units':4, 'num_cities':0, 'max_phases':10, 'fog_of_war':True}),
    "fog-inf-7" : (scenario.clear_square_factory, {'size':7, 'min_units':1, 'max_units':4, 'num_cities':0, 'max_phases':15, 'fog_of_war':True}),
    "city-inf-10" : (scenario.clear_square_factory, {'size':10, 'min_units':5, 'max_units':10, 'num_cities':3}),
    "city-inf-25" : (scenario.clear_square_factory, {'size':25, 'min_units':50, 'max_units':50, 'num_cities':5, 'max_phases':40}),
    "hierarchy-inf-10" : (scenario.hierarchy_factory, {'size':10, 'min_parents':2, 'max_parents':4, 'hierarchy_depth':3, 'hierarchy_branching':3, 'num_cities':0, 'balance':False, 'max_phases':40, 'fog_of_war':False}),
    "hierarchy-inf-30" : (scenario.hierarchy_factory, {'size':30, 'min_parents':1, 'max_parents':3, 'hierarchy_depth':4, 'hierarchy_branching':4, 'num_cities':3, 'balance':False, 'max_phases':40, 'fog_of_war':False}),
    "hierarchy-inf-10-d2-b3" : (scenario.hierarchy_factory, {'size':10, 'min_parents':2, 'max_parents':4, 'hierarchy_depth':2, 'hierarchy_branching':3, 'num_cities':3, 'balance':False, 'max_phases':40, 'fog_of_war':False}),
    "invasion" : (scenario.invasion_factory, {"n_blue":8, "fog_of_war":False, "city_score":24}),
    "city-fog-5" : (scenario.clear_square_factory, {'size':5, 'min_units':2, 'max_units':4, 'num_cities':4, 'max_phases':10, 'fog_of_war':True}),
    "hierarchy-inf-20-d2-b4" : (scenario.hierarchy_factory, {'size':20, 'min_parents':1, 'max_parents':2, 'hierarchy_depth':3, 'hierarchy_branching':4, 'num_cities':3, 'balance':False, 'max_phases':40, 'fog_of_war':False}),
}