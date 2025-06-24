export var SVGGui = {};

import { HumanPlayerControl } from "./human-player-control.js";
import { SVGUtil } from "./svg-util.js";
import { Unit } from "./unit.js";
import { SVGUnitSymbol } from "./svg-unit-symbol.js";
import { SVGCreateView } from "./svg-create-view.js";

(function() {
    
var unitSymbolDimensions = null;
var hexMarks = [];

function setUnitSymbolDimensions() {
    // Use first unit that's still alive and on the map
    let id = null;
    for (const unit of Unit.units) {
        if (!unit.ineffective && unit.hex) {
            id = unit.uniqueId;
            break;
        }
    } 
    let elem = document.getElementById(id);
    let bbox = SVGUtil.getTransformedBBox(elem);
    unitSymbolDimensions = {width:bbox.width, height:bbox.height};
}

SVGGui.markHex = function(hex, color, id) {
    if (!unitSymbolDimensions)  setUnitSymbolDimensions();
    let {width,height} = unitSymbolDimensions;
    let usd = unitSymbolDimensions;
    let hexElem = document.getElementById(hex.id);
    let bbox = SVGUtil.getTransformedBBox(hexElem);
    let [x_center, y_center] = [bbox.x + bbox.width/2, bbox.y + bbox.height/2];
    let mg = 0.05 * width;
    let selectionMarker = SVGUnitSymbol.selectionMarker;
    selectionMarker = SVGUtil.makeRect(x_center-width/2-mg,y_center-height/2-mg,width+2*mg,height+2*mg,"transparent",color);
    selectionMarker.setAttributeNS(null, 'id', id);
    selectionMarker.addEventListener("mousedown",HumanPlayerControl.markerMouseDown);
    SVGCreateView.svg.appendChild(selectionMarker);
    hexMarks.push(selectionMarker);
}

SVGGui.clearMarks = function() {
    for (let mark of hexMarks)
        mark.remove();
}

}());