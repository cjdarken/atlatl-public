import math

Infinity = math.inf

cost = {}
    
cost["infantry"] = {
    "clear": 100,
    "water": Infinity,
    "rough": 100,
    "unused": Infinity,
    "marsh": 100,
    "urban": 100
}

cost["armor"] = {
    "clear": 50,
    "water": Infinity,
    "rough": 100,
    "unused": Infinity,
    "marsh": 100,
    "urban" : 100
}

cost["mechinf"] = cost["armor"]

cost["artillery"] = {
    "clear": 50,
    "water": Infinity,
    "rough": 100,
    "unused": Infinity,
    "marsh": Infinity,
    "urban": 100
}

stackingLimit = 1
