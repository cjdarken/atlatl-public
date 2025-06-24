export var Style = {};

(function() { 
    
    Style.terrainFillIndex = {
        'clear'     : 'white',
        'water'     : 'powderblue',
        'marsh'     : 'palegreen',
        'rough'     : 'wheat',
        'urban'     : 'lightgray',
        'unused'    : 'gray'
    };
    
    Style.terrainEdgeIndex = {
        'normal'    : {color:'black', width:0.1},
        'stream'    : {color:'blue', width:0.3},
        'river'     : {color:'blue', width:0.5}
    };
    
    Style.terrainPathIndex = {
        'road'    : {color:'black', width:0.2},
        'path'     : {color:'gray', width:0.2}
    };
    
    Style.factionIndex = {
        'red' : {dim:"#e0abab", normal:"#fcc5c5", bright:"#ffd4d4"},
        'blue' : {dim:"#ababe0", normal:"#c5c5fc", bright:"#d4d4ff"}
    };
      
}())