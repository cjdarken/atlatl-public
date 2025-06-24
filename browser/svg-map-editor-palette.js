export var MapEditorPalette = {};

import { SVGUtil } from "./svg-util.js";
import { MapEditorControl } from "./map-editor-control.js";
import { Terrain } from "./terrain.js";
import { Style } from "./style.js";

(function() {
    
function add(param, svg) {  

    var VerticalCenteredLayout = SVGUtil.VerticalCenteredLayout;
    var makeLabel = SVGUtil.makeLabel;
    var makeRect = SVGUtil.makeRect;
    var makeLineInRect = SVGUtil.makeLineInRect;
    var makeRectInRect = SVGUtil.makeRectInRect;
    var gridToSVG = SVGUtil.gridToSVG;
    
    let boxSize = 2;
    
    // Draw palette
    let x_tm = param.x_palette_margin+param.palette_width/2;
    let y_tm = param.y_palette_margin;
    var palette = new VerticalCenteredLayout(svg, {x:x_tm,y:y_tm});    
    
    palette.add( makeLabel("Setup"), true );
    palette.addSmallSpace();
    
    let rect = makeRectInRect(0,0,boxSize,boxSize,"transparent");
    rect.setAttributeNS(null, 'id', "setup-type-erase");
    rect.setAttributeNS(null, 'style', 'pointer-events:all;');
    palette.add( rect );
    rect.addEventListener("mousedown",MapEditorControl.paletteSetupMouseDown);
    palette.addSmallSpace();
    rect = makeRectInRect(0,0,boxSize,boxSize,"blue");
    rect.setAttributeNS(null, 'id', "setup-type-blue");
    rect.setAttributeNS(null, 'style', 'pointer-events:all;');
    palette.add( rect );
    rect.addEventListener("mousedown",MapEditorControl.paletteSetupMouseDown);
    palette.addSmallSpace();
    rect = makeRectInRect(0,0,boxSize,boxSize,"red");
    rect.setAttributeNS(null, 'id', "setup-type-red");
    rect.setAttributeNS(null, 'style', 'pointer-events:all;');
    palette.add( rect );
    rect.addEventListener("mousedown",MapEditorControl.paletteSetupMouseDown);
    
    palette.add( makeLabel("Fills"), true );
    for (let fill of Terrain.fills) {
        palette.addSmallSpace();
        let rect = makeRect(0,0,boxSize,boxSize,Style.terrainFillIndex[fill.name]);
        rect.setAttributeNS(null, 'id', fill.getUniqueID());
        rect.setAttributeNS(null, 'style', 'pointer-events:all;');
        palette.add( rect );
        rect.addEventListener("mousedown",MapEditorControl.paletteFillMouseDown);
    }
    palette.add( makeLabel("Edges"), true );
    for (let edge of Terrain.edges) {
        palette.addSmallSpace();
        let style = Style.terrainEdgeIndex[edge.name];
        let rect = makeLineInRect(0,0,boxSize,boxSize,style);
        rect.setAttributeNS(null, 'id', edge.getUniqueID());
        rect.setAttributeNS(null, 'style', 'pointer-events:all;');
        palette.add( rect );
        rect.addEventListener("mousedown",MapEditorControl.paletteEdgeMouseDown);
    }
    palette.add( makeLabel("Paths"), true );
    palette.addSmallSpace();
    rect = makeRect(0,0,boxSize,boxSize,"transparent");
    rect.setAttributeNS(null, 'id', "path-type-erase");
    rect.setAttributeNS(null, 'style', 'pointer-events:all;');
    palette.add( rect );
    rect.addEventListener("mousedown",MapEditorControl.palettePathMouseDown);
    for (let path of Terrain.paths) {
        palette.addSmallSpace();
        let style = Style.terrainPathIndex[path.name];
        let rect = makeLineInRect(0,0,boxSize,boxSize,style);
        rect.setAttributeNS(null, 'id', path.getUniqueID());
        rect.setAttributeNS(null, 'style', 'pointer-events:all;');
        palette.add( rect );
        rect.addEventListener("mousedown",MapEditorControl.palettePathMouseDown);
    }
   
    palette.drawFrame();
}

MapEditorPalette.add = add;
}())