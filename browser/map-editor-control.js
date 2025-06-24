export var MapEditorControl = {};

import { Terrain } from "./terrain.js";
import { Map } from "./map.js";
import { SVGUtil } from "./svg-util.js";
import { Style } from "./style.js";
import { SVGSetupMarker } from "./svg-setup-marker.js";

(function() {

var Mode = {
    PaintFill : 0,
    PaintEdge : 1,
    PaintPath : 2,
    PaintSetup : 3
};

var mode = Mode.PaintFill;
var mouse_down = false;
var newFillName = "clear";
var newEdgeName = "bob";
var newPathName = "none";
var newSetupMarkerName = null;
var lastHexID = null;

function ControlState(mode,value) {
    this.mode = mode;
    this.value = value;
}

function svgMouseDownHandler(evt) {
    mouse_down = true;
}
MapEditorControl.svgMouseDownHandler = svgMouseDownHandler;

function svgMouseUpHandler(evt) {
    mouse_down = false;
    lastHexID = null;
}
MapEditorControl.svgMouseUpHandler = svgMouseUpHandler;

function hexMouseDownHandler(evt) {
    mouse_down = true;
    hexMouseOverHandler.call(this,evt);
}
MapEditorControl.hexMouseDownHandler = hexMouseDownHandler;

function hexMouseOverHandler(evt) {
    if (mouse_down && mode==Mode.PaintFill) {
        let hex = Map.hexIndex[this.id];
        hex.setTerrain(newFillName);
        SVGUtil.setFill(this, Style.terrainFillIndex[hex.terrain]);
    }
    if (mouse_down && mode==Mode.PaintPath) {
        if (lastHexID === null) {
            lastHexID = this.id;
            return;
        }
        if (lastHexID && this.id !== lastHexID) {
            let hex = Map.hexIndex[this.id];
            let lastHex = Map.hexIndex[lastHexID];
            let old_path = Map.removePath(lastHex, hex);
            if (old_path)
                SVGUtil.removePath(old_path);
            if (newPathName !== "erase") {
                let path = Map.addPath(lastHex, hex, newPathName);
                SVGUtil.makePath(path);
            }
            lastHexID = this.id;
        }
    }
    if (mouse_down && mode==Mode.PaintSetup) {
        let hex = Map.hexIndex[this.id];
        if (newSetupMarkerName === "setup-type-erase") {
            hex.setup = null;
            SVGSetupMarker.removeMarker(hex);
        }
        else {
            hex.setup = newSetupMarkerName;
            SVGSetupMarker.addMarker(hex, newSetupMarkerName);
        }
    }
}
MapEditorControl.hexMouseOverHandler = hexMouseOverHandler;


function edgeMouseOver(evt) {
    if (mouse_down && mode==Mode.PaintEdge) {
        let edge = Map.edgeIndex[this.id];
        edge.type = newEdgeName;
        SVGUtil.setPathStyle(this, Style.terrainEdgeIndex[edge.type]);
    }
}
MapEditorControl.edgeMouseOver = edgeMouseOver;

function paletteFillMouseDown(evt) {
    newFillName = Terrain.idToName(this.id);
    mode = Mode.PaintFill;
}
MapEditorControl.paletteFillMouseDown = paletteFillMouseDown;

function paletteEdgeMouseDown(evt) {
    newEdgeName = Terrain.idToName(this.id);
    mode = Mode.PaintEdge;
}
MapEditorControl.paletteEdgeMouseDown = paletteEdgeMouseDown;

function palettePathMouseDown(evt) {
    newPathName = Terrain.idToName(this.id);
    mode = Mode.PaintPath;
}
MapEditorControl.palettePathMouseDown = palettePathMouseDown;

function paletteSetupMouseDown(evt) {
    newSetupMarkerName = this.id;
    mode = Mode.PaintSetup;
}
MapEditorControl.paletteSetupMouseDown = paletteSetupMouseDown;

}())
