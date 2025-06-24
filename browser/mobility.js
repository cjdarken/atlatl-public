export var Mobility = {};

(function() {
    
    Mobility.cost = {};
        
    Mobility.cost["infantry"] = {
        "clear": 100,
        "water": Infinity,
        "rough": 100,
        "unused": Infinity,
        "marsh": 100,
        "urban": 100
    };
    
    Mobility.cost["armor"] = {
        "clear": 50,
        "water": Infinity,
        "rough": 100,
        "unused": Infinity,
        "marsh": 100,
        "urban" : 100
    };
    
    Mobility.cost["mechinf"] = Mobility.cost["armor"];
    
    Mobility.cost["artillery"] = {
        "clear": 50,
        "water": Infinity,
        "rough": 100,
        "unused": Infinity,
        "marsh": Infinity,
        "urban": 100
    };
    
    Mobility.stackingLimit = 1;
        
    
}())