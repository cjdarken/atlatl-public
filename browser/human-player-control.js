export var HumanPlayerControl = {};
var HPC = HumanPlayerControl;

import {Play} from './play.js';
import {Unit} from './unit.js';
import {SVGGui} from './svg-gui.js';

(function() {

var Mode = {
    SelectUnit : 0,
    TakeAction : 1
};

var mode = Mode.SelectUnit;
HPC.selectedUnit = null;

var markIndex = {};

function resetGuiState() {
    mode = Mode.SelectUnit;
    SVGGui.clearMarks();
}
HPC.resetGuiState = resetGuiState;

function hexMouseDownHandler(evt) {
    if (mode === Mode.TakeAction) {
        let hex = Map.hexIndex[this.id];
        if (!Play._setup_phase) {
            if (!moveTargets.includes(hex))
                return;
            moveTargets = [];
            fireTargets = [];
            SVGGui.clearMarks();
            HPC.selectedUnit.setHex(hex);
            SVGUnitSymbol.moveSymbolToHex(HPC.selectedUnit.uniqueId, hex);
            mode = Mode.SelectUnit;
        }
        else { // _setup_phase
            // If a hex that is tagged as startup for same faction, move
            if (hex.setup && hex.setup.substr(11) === Play._faction) {
               sendSetupMove(hex);
               mode = Mode.SelectUnit;
            }
        }
    }
}
HPC.hexMouseDownHandler = hexMouseDownHandler;

function hexMouseOverHandler(evt) {
}
HPC.hexMouseOverHandler = hexMouseOverHandler;

function edgeMouseOver(evt) {
}
HPC.edgeMouseOver = edgeMouseOver;

function markerMouseDown(evt) {
    if (Play._on_move) {
        let markData = markIndex[this.id];
        if (markData.type==="hex") {
            console.log("Send move request to server, target hex id: "+markData.value.id);
            Play.sendMove(markData.value);
        }
        else if (markData.type==="unit") {
            console.log("Send shoot request to server, target id: "+markData.value.uniqueId);
            Play.sendFire(markData.value);
        }
        else if (markData.type==="self") {
            SVGGui.clearMarks();
        }
        mode = Mode.SelectUnit;
    }
}
HPC.markerMouseDown = markerMouseDown;

function unitMouseDownHandler(evt) {
    if (!Play._on_move)  return;
    if (mode === Mode.SelectUnit) {
        HPC.selectedUnit = Unit.unitIndex[this.id];
        if (!HPC.selectedUnit.canMove)  return;
        let markID = "mark "+HPC.selectedUnit.hex.id;
        SVGGui.markHex(HPC.selectedUnit.hex,"green",markID);
        markIndex[markID] = {type:"self", value:HPC.selectedUnit.hex};
        mode = Mode.TakeAction;
        if (!Play._setup_phase) {
            for (let hex of HPC.selectedUnit.findMoveTargets()) {
                let markID = "mark "+hex.id;
                SVGGui.markHex(hex,"blue",markID);
                markIndex[markID] = {type:"hex", value:hex};
            }
            for (let unit of HPC.selectedUnit.findFireTargets()) {
                let markID = "mark "+unit.uniqueId;
                SVGGui.markHex(unit.hex,"red",markID);
                markIndex[markID] = {type:"unit", value:unit};
            }
        }
    }
    else if (mode === Mode.TakeAction) {
        if (Play._setup_phase) {
            let exchangeTarget = Unit.unitIndex[this.id];
            if (Play._faction == exchangeTarget.faction) {
                sendSetupExchange(exchangeTarget);
                mode = Mode.SelectUnit;
            }
        }
    }
}
HPC.unitMouseDownHandler = unitMouseDownHandler;

}())