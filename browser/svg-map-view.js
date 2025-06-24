export var SVGMapView = {};

import {Map} from './map.js';
import {SVGUtil} from './svg-util.js';
import {SVGSetupMarker} from './svg-setup-marker.js';
import {Style} from './style.js';
import {MapEditorControl} from './map-editor-control.js';

(function() {

SVGMapView.add = function(param, svg, hexMouseOverHandler, hexMouseDownHandler) {

    var svgNS = SVGUtil.svgNS;
    var gridToSVG = SVGUtil.gridToSVG;
    var makePath = SVGUtil.makePath;

    // Draw hexes
    for (let hex of Map.hexes) {
        const points = hex.getPoints();
        var elem = document.createElementNS('http://www.w3.org/2000/svg', 'path');
        let start = points[points.length-1];
        const {x,y} = gridToSVG(start.x, start.y, param.x_hex_margin, param.y_hex_margin, param.width);
        let d_str = `M ${x} ${y} `;
        for (let p of points) {
            const {x,y} = gridToSVG(p.x, p.y, param.x_hex_margin, param.y_hex_margin, param.width);
            d_str += `L ${x} ${y} `;
        }
        
        elem.setAttributeNS(null, 'd', d_str);
        elem.setAttributeNS(null, 'stroke', 'transparent');
        
        elem.setAttributeNS(null, 'fill', Style.terrainFillIndex[hex.terrain] );
        elem.setAttributeNS(null, 'id', hex.id);
        svg.appendChild(elem);
        // Handlers defined in html file (our "controller")
        elem.addEventListener("mouseover",hexMouseOverHandler);
        elem.addEventListener("mousedown",hexMouseDownHandler);
    }
            
    //  Draw hex grid
    for (let e of Map.edges) {
        var elem = document.createElementNS(svgNS, 'path');
        //elem.id = "edge "+e.xa_grid+" "+e.ya_grid+" "+e.xb_grid+" "+e.yb_grid;
        elem.setAttributeNS(null, 'id', e.id);
        const {x:xa,y:ya} = gridToSVG(e.xa_grid, e.ya_grid, param.x_hex_margin, param.y_hex_margin, param.width);
        const {x:xb,y:yb} = gridToSVG(e.xb_grid, e.yb_grid, param.x_hex_margin, param.y_hex_margin, param.width);
        elem.setAttributeNS(null, 'd', 'M '+xa+" "+ya+" L "+xb+" "+yb);
        elem.setAttributeNS(null, 'stroke', Style.terrainEdgeIndex[e.type].color);
        elem.setAttributeNS(null, 'fill', 'transparent');
        elem.setAttributeNS(null, 'stroke-linecap', 'round');
        elem.setAttributeNS(null, 'stroke-width', Style.terrainEdgeIndex[e.type].width);
        svg.appendChild(elem);
        // Handlers defined in html file (our "controller")
        elem.addEventListener("mouseover",MapEditorControl.edgeMouseOver);
    }
    
    // Draw paths
    for (let path_id in Map.pathIndex) {
        makePath(Map.pathIndex[path_id]);
    }
    
    SVGSetupMarker.init(param);
    for (let hex of Map.hexes) {
        if (hex.setup) {
            SVGSetupMarker.addMarker(hex, hex.setup);
        }
    }       
}

SVGMapView.set_colors = function(colors) {
    for (let hexId in Map.hexIndex) {
        let elem = document.getElementById(hexId);
        if (hexId in colors)
            elem.setAttributeNS(null, 'fill', colors[hexId]);
        else
            elem.setAttributeNS(null, 'fill', "white");
    }
}

SVGMapView.terrain_color = function() {
    for (let hexId in Map.hexIndex) {
        let elem = document.getElementById(hexId);
        let hex = Map.hexIndex[hexId];
        elem.setAttributeNS(null, 'fill', Style.terrainFillIndex[hex.terrain]);
    }
}
    
}())