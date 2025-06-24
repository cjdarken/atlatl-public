export var Map = {};

import {SVGUtil} from './svg-util.js';
import {SVGSetupMarker} from './svg-setup-marker.js';
import {Terrain} from './terrain.js';
import {Style} from './style.js';

// The grid coordinates is a rectangular grid with horizontal spacing width/4
//  and vertical spacing height/2. Note that height = sqrt(3)/2*width, so
//  vertical spacing can be written width*sqrt(3)/4.

(function() {
    Map.edgeIndex = {};  // Values are indexes into Map.edges
    Map.hexIndex = {}; // Values are Hex objects
    Map.pathIndex = {}; // Values are Path objects
    
    Map.createHexGrid = function(rows,cols) {
        Map.hexes = [];
        Map.edges = [];
        Map.hexIndex = {};
        Map.edgeIndex = {};  // Point pairs to edgesvar 
        let terrain = Terrain.defaultFillName;
        for (let r=0;r<rows;r++) {
            for (let c=0;c<cols;c++) {
                Map.hexes.push( new Hex(c,r,terrain) );
            }
        }
    };
    
    Map.toString = function() {
        return JSON.stringify( Map.toPortable() );
    }
    
    Map.toPortable = function() {
        let portable_hexes = [];
        for (let hex of Map.hexes)
            portable_hexes.push( hex.portableCopy() );
        let portable_paths = [];
        for (let path_id in Map.pathIndex) {
            let path = Map.pathIndex[path_id];
            portable_paths.push( path.portableCopy() );
        }
        return {hexes:portable_hexes, edges:Map.edges, paths:portable_paths};
    }
    
    Map.fromPortable = function( obj ) {
        Map.hexes = [];
        Map.edges = [];
        //Map.paths = []; // Created below
        Map.edgeIndex = {};
        for (let edge_obj of obj.edges)
            Map.edges.push( edgeFromGenericObject(edge_obj) );
        for (let hex_obj of obj.hexes)
            Map.hexes.push( hexFromGenericObject(hex_obj) );
        for (let path_obj of obj.paths)
            pathFromGenericObject(path_obj);
    }
    
    Map.fromString = function(str) {
        let obj = JSON.parse(str);
        Map.fromPortable(obj);
    }
    
    Map.addPath = function(hexA, hexB, type) {
        let path = new Path(hexA, hexB, type);
        //Map.paths.push( path );
        let dir = directionFrom(hexA, hexB);
        hexA.paths[dir] = path;
        hexB.paths[(dir+3)%6] = path;
        return path;
    }
    
    Map.removePath = function(hexA, hexB) {
        let path = getPathFromHexes(hexA, hexB);
        if (!path)  return;
        hexA.removePath(path);
        hexB.removePath(path);
        let keyAB = `path-${hexA.id}-${hexB.id}`;
        let keyBA = `path-${hexB.id}-${hexA.id}`;
        let pathAB = Map.pathIndex[keyAB];
        let pathBA = Map.pathIndex[keyBA];
        if (pathAB)  delete Map.pathIndex[keyAB];
        if (pathBA)  delete Map.pathIndex[keyBA];
        
        return path;
    }
    
    function indexEdge(edge) {
        let [xa, ya, xb, yb] = [edge.xa_grid, edge.ya_grid, edge.xb_grid, edge.yb_grid];
        let str = ""+xa+" "+ya+" "+xb+" "+yb;
        Map.edgeIndex[str]  = edge;
        str = ""+xb+" "+yb+" "+xa+" "+ya;
        Map.edgeIndex[str]  = edge;
    }

    // Neighbor locations in offset coordinates
    var oddXOffsets = [ [0,-1], [1,0], [1,1], [0,1], [-1,1], [-1,0] ];
    var evenXOffsets = [ [0,-1], [1,-1], [1,0], [0,1], [-1,0], [-1,-1] ];
    
    Map.getNeighborHexes = function(hex) {
        let neighbors = [];
        let offsets = evenXOffsets;
        if (hex.x_offset%2)
            offsets = oddXOffsets;
        for (let offset of offsets) {
            let x = hex.x_offset + offset[0];
            let y = hex.y_offset + offset[1];
            let id = `hex-${x}-${y}`;
            var neigh = Map.hexIndex[id];
            if (neigh)
                neighbors.push(neigh);
        }
        return neighbors;
    }
    
    function directionFrom(hexA, hexB) {
        let xa = hexA.x_offset;
        let xb = hexB.x_offset;
        let ya = hexA.y_offset;
        let yb = hexB.y_offset;
        let offsets = evenXOffsets;
        if (hexA.x_offset%2)
            offsets = oddXOffsets;
        for (let i=0; i<6; i++) {
            if (xa + offsets[i][0] === xb && ya + offsets[i][1] === yb)
                return i;
        }
        return null;
    }

    function offsetToGridCenters(x_off, y_off) {
        let x_grid = 2 + x_off * 3;
        let y_grid = 2 + y_off * 2 + (x_off%2);
        return [x_grid, y_grid];
    }

    var vertexOffsets = [ [-1,-1], [1,-1], [2,0], [1,1], [-1,1], [-2,0] ]; // grid

    function Hex(x_offset,y_offset,terrain) {
        this.x_offset = x_offset;
        this.y_offset = y_offset;
        this.setup = null;
        this.terrain = terrain;
        [this.x_grid,this.y_grid] = offsetToGridCenters(x_offset,y_offset);
        this.addEdges(); // Sets this.edges
        this.paths = [null,null,null,null,null,null];
        this.id = `hex-${this.x_offset}-${this.y_offset}`;
        Map.hexIndex[this.id] = this;
    }
    
    function hexFromGenericObject(obj) {
        let hex = new Hex(obj.x_offset, obj.y_offset, obj.terrain);
        hex.setup = obj.setup;
        let edges = [];
        for (let edge_id of obj.edges)
            edges.push( Map.edgeIndex[edge_id] );
        Map.hexIndex[hex.id] = hex;
        return hex;
    }
    
    function getEdgeFromEndpoints(a,b) {
        let keyAB = `edge-${a.x}-${a.y}-${b.x}-${b.y}`;
        let keyBA = `edge-${a.x}-${a.y}-${b.x}-${b.y}`;
        let edgeAB = Map.edgeIndex[keyAB];
        let edgeBA = Map.edgeIndex[keyBA];
        if (edgeAB !== undefined)
            return edgeAB;
        if (edgeBA !== undefined)
            return edgeBA;
        return null;
    }
    
    Hex.prototype.addEdges = function() {
        this.edges = [];
        let points = this.getPoints();
        for (let i=0;i<6;i++) {
            let j = (i+1)%6;
            let a = points[i];
            let b = points[j];
            let edge = getEdgeFromEndpoints(a,b);
            if ( edge===null ) {
                edge = new Edge(a.x,a.y,b.x,b.y,"normal");
                Map.edges.push( edge );
            }
            this.edges.push( edge );
        }
    }
    
    Hex.prototype.getPoints = function() {
        let points = [];
        for (let i=0;i<6;i++) {
            let x = this.x_grid + vertexOffsets[i][0];
            let y = this.y_grid + vertexOffsets[i][1];
            points.push( {x:x, y:y} );
        }
        return points;
    }
    
    Hex.prototype.setTerrain = function(value) {
        this.terrain = value;
    }
    
    Hex.prototype.portableCopy = function() {
        let copy = {};
        copy.x_offset = this.x_offset;
        copy.y_offset = this.y_offset;
        copy.terrain = this.terrain;
        copy.x_grid = this.x_grid;
        copy.y_grid = this.y_grid;
        copy.setup = this.setup;
        // Replace edge objects by their unique IDs and omit paths
        copy.edges = [];
        for (let edge of this.edges)
            copy.edges.push( edge.id );
        return copy;
    }
    
    Hex.prototype.removePath = function(path) {
        for (let i=0; i<6; i++)
            if (this.paths[i]===path)
                this.paths[i] = null;
    }

    function Edge(xa_grid, ya_grid, xb_grid, yb_grid, type) {
        this.id = `edge-${xa_grid}-${ya_grid}-${xb_grid}-${yb_grid}`
        this.xa_grid = xa_grid;
        this.xb_grid = xb_grid;
        this.ya_grid = ya_grid;
        this.yb_grid = yb_grid;
        this.type = type;
        Map.edgeIndex[this.id] = this;
    }
    
    function edgeFromGenericObject(obj) {
        let edge = new Edge(obj.xa_grid, obj.ya_grid, obj.xb_grid, obj.yb_grid, obj.type);
        Map.edgeIndex[edge.id] = edge;
        return edge;
    }
    
    function Path(hexA, hexB, type) {
        this.id = `path-${hexA.id}-${hexB.id}`
        this.hexA = hexA;
        this.hexB = hexB;
        this.type = type;
        Map.pathIndex[this.id] = this;
    }
    
    Path.prototype.portableCopy = function() {
        let copy = {};
        copy.id = this.id;
        copy.hexA = this.hexA.id;
        copy.hexB = this.hexB.id;
        copy.type = this.type;
        return copy;
    }
    
    function pathFromGenericObject(obj) {
        let hexA = Map.hexIndex[obj.hexA];
        let hexB = Map.hexIndex[obj.hexB];
        let path = new Path(hexA, hexB, obj.type);
        let dir = directionFrom(hexA, hexB);
        hexA.paths[dir] = path;
        hexB.paths[(dir+3)%6] = path;
        Map.pathIndex[path.id] = path;
    }
    
    function getPathFromHexes(hexA, hexB) {
        let keyAB = `path-${hexA.id}-${hexB.id}`;
        let keyBA = `path-${hexB.id}-${hexA.id}`;
        let pathAB = Map.pathIndex[keyAB];
        let pathBA = Map.pathIndex[keyBA];
        if (pathAB !== undefined)
            return pathAB;
        if (pathBA !== undefined)
            return pathBA;
        return null;
    }
    
    Map.getDimensions = function() {
        let width = 0, height = 0;
        for (let id in Map.hexIndex) {
            let hex = Map.hexIndex[id];
            if ( hex.x_offset + 1 > width )
                width = hex.x_offset + 1;
            if ( hex.y_offset + 1 > height )
                height = hex.y_offset + 1;
        }
        return {width:width, height:height};
    };
    
    Map.hexFromOffsetCoordinates = function(x_offset, y_offset) {
        let id = `hex-${x_offset}-${y_offset}`;
        return Map.hexIndex[id];
    };
    
    Map.SQRT3 = Math.sqrt(3);
    
    Map.gridDistance = function(xA,yA,xB,yB) {
        // Returns Euclidean distance in units of hex width
        let dx = (xB-xA)/6*Map.SQRT3;
        let dy = (yB-yA)/2;
        return Math.sqrt( dx*dx + dy*dy );
    };

    function shuffle(arr) {
        for (let i=0;i<arr.length;i++) {
            let j = i + Math.floor( Math.random() * (arr.length-i) )
            let value = arr[j];
            arr[j] = arr[i];
            arr[i] = value;
        }      
    }

    // Standard Normal variate using Box-Muller transform.
    // From stackoverflow 25582882
    function randnBm() {
        var u = 0, v = 0;
        while(u === 0) u = Math.random(); //Converting [0,1) to (0,1)
        while(v === 0) v = Math.random();
        return Math.sqrt( -2.0 * Math.log( u ) ) * Math.cos( 2.0 * Math.PI * v );
    }
    
    function randomDiscreteDistribution(n) {
        let result = [];
        let mag = 0;
        for (let i=0;i<n;i++) {
            let x = randnBm();
            if (x<0) x=-x;
            result[i] = x;
            mag += x*x;
        }
        mag = Math.sqrt(mag);
        for (let i=0;i<n;i++)
            result[i] /= mag;
        return result;
    }
    
    Map.randomize = function() {
        const types = ["clear", "rough", "marsh", "water"];
        const dist = randomDiscreteDistribution( types.length );
        const modDist = [0.3+0.7*dist[0], 0.7*dist[1], 0.7*dist[2], 0.7*dist[3]];
        let cumDist = [];
        let sum = 0;
        for (let i=0;i<modDist.length;i++) {
            cumDist[i] = sum + modDist[i];
            sum += modDist[i];
        }
        let nHexes = Object.keys(Map.hexIndex).length;
        let terrainValues = [];
        let terrainIndex = 0;
        for (let i=0;i<nHexes;i++) {
            if (i > cumDist[terrainIndex] * nHexes)
                ++ terrainIndex;
            terrainValues[i] = types[terrainIndex];
        }
        shuffle(terrainValues);
        let i=0;
        for (let hexId in Map.hexIndex) {
            let hex = Map.hexIndex[hexId];
            hex.setTerrain(terrainValues[i]);
            ++i;
            let elem = document.getElementById(hex.id);
            SVGUtil.setFill(elem, Style.terrainFillIndex[hex.terrain]);
        }
        let {width,height} = Map.getDimensions();
        let nCities = 1+Math.floor(3*Math.random());
        let minX = 0;
        let minY = 0;
        let minXSetup = 0;
        let minYSetup = 0;
        let maxXSetup = width-1;
        let maxYSetup = height-1;
        if (Math.random()<0.5) {
            // Cities in the east
            minX = 6;
            minXSetup = width-3;
            maxXSetup = 2;
        }
        else {
            minY = 6;
            minYSetup = height-3;
            maxYSetup = 2;
        }
        for (let i=0;i<nCities;i++) {
            let x = minX + Math.floor(Math.random()*(width-minX));
            let y = minY + Math.floor(Math.random()*(height-minY));
            let id = `hex-${x}-${y}`;
            let hex = Map.hexIndex[id];
            hex.setTerrain("urban");
            let elem = document.getElementById(hex.id);
            SVGUtil.setFill(elem, Style.terrainFillIndex[hex.terrain]);
        }
        SVGSetupMarker.removeAllMarkers();
        for (let x=minXSetup;x<width;x++) {
            for (let y=minYSetup;y<height;y++) {
                let id = `hex-${x}-${y}`;
                let hex = Map.hexIndex[id];
                if (hex.terrain !== "water") {
                    hex.setup = "setup-type-red";
                    SVGSetupMarker.addMarker(hex, "setup-type-red");
                }
            }
        }
        for (let x=0;x<=maxXSetup;x++) {
            for (let y=0;y<=maxYSetup;y++) {
                let id = `hex-${x}-${y}`;
                let hex = Map.hexIndex[id];
                if (hex.terrain !== "water") {
                    hex.setup = "setup-type-blue";
                    SVGSetupMarker.addMarker(hex, "setup-type-blue");
                }
            }
        }
    }

}());

