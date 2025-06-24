export var Terrain = {};

import {Style} from './style.js'

(function(){
    
    Terrain.index = {};
    Terrain.idToName = function(id) { return id.substring(10); };
    
    // fills
    function FillType(name) {
        this.name = name;
        Terrain.index[this.name] = this;
    }
    
    FillType.prototype.getUniqueID = function() { return "fill-type-"+this.name; }
    
    Terrain.fills = [];
    for (let type in Style.terrainFillIndex) 
        Terrain.fills.push( new FillType(type) );
    for (let type in Style.terrainFillIndex) {
        Terrain.defaultFillName = type;
        break;
    }

    // edges
    function EdgeType(name) {
        this.name = name;
        Terrain.index[this.name] = this;
    }
        
    EdgeType.prototype.getUniqueID = function() { return "edge-type-"+this.name; }
    
    Terrain.edges = [
        new EdgeType("normal"),
        new EdgeType("stream"),
        new EdgeType("river")
    ];
    
    // paths
    function PathType(name) {
        this.name = name;
        Terrain.index[this.name] = this;
    }
        
    PathType.prototype.getUniqueID = function() { return "path-type-"+this.name; }
    
    Terrain.paths = [
        new EdgeType("road"),
        new EdgeType("path")
    ];
    
}())