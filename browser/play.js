export var Play = {};

import {Map} from './map.js';
import {SVGCreateView} from './svg-create-view.js';
import {Unit} from './unit.js';
import {Mobility} from './mobility.js';
import {Combat} from './combat.js';
import {SVGUnitSymbol} from './svg-unit-symbol.js'
import {SVGSetupMarker} from './svg-setup-marker.js'
import {SVGGui} from './svg-gui.js'
import {HumanPlayerControl} from './human-player-control.js'

(function() { 

const State = Object.freeze(
    {"RoleSelect":0, "Waiting":1, "InputMove":2,"GameOver":3, "Disconnected":4}
)

var _state = State.Disconnected; // Currently unused

var _on_move = false; // Referenced by human-player-control.js
Play._on_move = _on_move;
var _setup_phase = false;  // Referenced by human-player-control.js
Play._setup_phase = _setup_phase;
var websocket = null;
var _faction = null; // Referenced by human-player-control.js
Play._faction = _faction;
var SS_phase = null; // Last known server phase count

function enterStateRoleSelect() {
    document.getElementById("blue").disabled=false;
    document.getElementById("red").disabled=false;
    document.getElementById("end-move").disabled=true;
    document.getElementById("reset").disabled=true;
    document.getElementById("next-game").disabled=false;
}

function enterStateWaiting() {
    document.getElementById("blue").disabled=true;
    document.getElementById("red").disabled=true;
    document.getElementById("end-move").disabled=true;
    document.getElementById("reset").disabled=false;
}

function enterStateInputMove() {
    document.getElementById("blue").disabled=true;
    document.getElementById("red").disabled=true;
    document.getElementById("end-move").disabled=false;
    document.getElementById("reset").disabled=false;
}

function enterStateGameOver() {    
    document.getElementById("blue").disabled=true;
    document.getElementById("red").disabled=true;
    document.getElementById("end-move").disabled=true;
    document.getElementById("reset").disabled=false;
}

function isSetupPhase(msgO) {
    return msgO.observation.status.setupMode;
}

function newPhase(msgO) {
    SVGUnitSymbol.setAllUnitBrightness("normal");
    if (isSetupPhase(msgO))
        SVGSetupMarker.setAllVisible(true);
    else   // move phase
        SVGSetupMarker.setAllVisible(false);
}

// Message handlers

function resetHandler(msgO) {
}

function observationHandler(msgO) {
    if (msgO.type !== "observation")
        alert(`Expecting message type observation, received ${msgO.type}`);
    // New phase?
    if (msgO.observation.phaseCount !== SS_phase) {
        SS_phase = msgO.observation.phaseCount;
        newPhase(msgO);
    }

    _setup_phase = isSetupPhase(msgO);

    // Text field updates
    let span = document.getElementById("onmove");
    if (msgO.observation.status.isTerminal)
        span.textContent = "terminal";
    else
        span.textContent = msgO.observation.status.onMove;
    span = document.getElementById("phase");
    if (msgO.observation.status.setupMode)
        span.textContent = "setup";
    else
        span.textContent = msgO.observation.status.phaseCount;
    SVGUnitSymbol.setAllUnitBrightness("normal");
    span = document.getElementById("score");
    span.textContent = msgO.observation.status.score; 

    SVGSetupMarker.setAllVisible(isSetupPhase(msgO));

    for (let unitObs of msgO.observation.units) {
        let uniqueId = unitObs.faction+" "+unitObs.longName
        let unit = Unit.unitIndex[uniqueId];
        unit.partialObsUpdate(unitObs); 
        SVGUnitSymbol.partialObsUpdate(uniqueId, unitObs); 
    }  
    SVGGui.clearMarks(); // Clear setup markers
  

    Play._on_move = msgO.observation.status.onMove === _faction;  // Defined at top
    if (Play._on_move) enterStateInputMove();
    else enterStateWaiting();
    if (msgO.observation.status.isTerminal) enterStateGameOver();
}

function messageHandler(message) {
    let msgO = JSON.parse(message);
    if (msgO.type == "parameters")
        parametersHandler(msgO);
    else if (msgO.type == "observation")
        observationHandler(msgO);
    else if (msgO.type == "reset")
        resetHandler(msgO);
    else
        throw 'Unknown message type: '+msgO.type;
}

function parametersHandler(msgO) {

    Map.fromPortable(msgO.parameters.map);

    var width = 5;  // Hardcoded width for now
    var x_hex_margin = 6;
    var y_hex_margin = 1;
    var palette_width = 4;
    var x_palette_margin = 0.5;
    var y_palette_margin = 0.5;
    var param = {
        width:width,
        x_hex_margin:x_hex_margin,
        y_hex_margin:y_hex_margin,
        palette_width:palette_width,
        x_palette_margin:x_palette_margin,
        y_palette_margin:y_palette_margin
    };
    SVGCreateView.createUnitPlacementView(param);

    Unit.init();
    Unit.fromPortable2(msgO.parameters.units,HumanPlayerControl.unitMouseDownHandler);

    // Text field updates
    let span = document.getElementById("onmove");
    span.textContent = "None";
    span = document.getElementById("phase");
    span.textContent = "None";
    SVGUnitSymbol.setAllUnitBrightness("normal");
    span = document.getElementById("score");
    span.textContent = "None"; 

    let btn = document.getElementById("blue");
    btn.style.backgroundColor = "lightgray";
    btn = document.getElementById("red");
    btn.style.backgroundColor = "lightgray";
    
    enterStateRoleSelect();
}

// Functions to send data back to server

function sendMove(hex) {
    let msg = {type:"action", action:{type:"move", mover:HumanPlayerControl.selectedUnit.uniqueId, destination:hex.id}};
    websocket.send(JSON.stringify(msg));
}
Play.sendMove = sendMove;

function sendFire(targetUnit) {
    let msg = {type:"action", action:{type:"fire", source:HumanPlayerControl.selectedUnit.uniqueId, target:targetUnit.uniqueId}};
    websocket.send(JSON.stringify(msg));
}
Play.sendFire = sendFire;

function sendReset() {
    let msg = {type:"reset-request"};
    websocket.send(JSON.stringify(msg));
}
Play.sendReset = sendReset;

function sendNextGame() {
    let msg = {type:"next-game-request"};
    websocket.send(JSON.stringify(msg));
}
Play.sendNextGame = sendNextGame;

function sendSetupMove(hex) {
    let msg = {type:"action", action:{type:"setup-move", mover:HumanPlayerControl.selectedUnit.uniqueId, destination:hex.id}};
    websocket.send(JSON.stringify(msg));
}

function sendSetupExchange(friendlyUnit) {
    let msg = {type:"action", action:{type:"setup-exchange", mover:HumanPlayerControl.selectedUnit.uniqueId, friendly:friendlyUnit.uniqueId}};
    websocket.send(JSON.stringify(msg));
}

function bluePressed(btn) {
    websocket.send('{ "type" : "role-request", "role" : "blue", "auto_next_game" : false }');
    btn.style.backgroundColor = "blue";
    _faction = "blue";
    enterStateWaiting();
}
Play.bluePressed = bluePressed;

function redPressed(btn) {
    websocket.send('{ "type" : "role-request", "role" : "red", "auto_next_game" : false }');
    btn.style.backgroundColor = "red";
    _faction = "red";
    enterStateWaiting();
}
Play.redPressed = redPressed;

function endMovePressed() {
    HumanPlayerControl.resetGuiState();
    let msg = { type:"action", action:{type:"pass"} };
    websocket.send(JSON.stringify(msg));
}
Play.endMovePressed = endMovePressed;

function init() {
    var SERVER_WEBSOCKET_URL = "ws://localhost:9999";
    websocket = new WebSocket(SERVER_WEBSOCKET_URL); // Defined above
    websocket.onopen = function(evt){
        let span = document.getElementById("status");
        span.textContent = "Connected";
        console.log("Opened websocket");
    };
    websocket.onclose = function(evt){
        let span = document.getElementById("status");
        span.textContent = "Socket closed";
        console.log("Websocket closed");
    };
    websocket.onerror = function(evt){console.log("Websocket error");};

    websocket.onmessage = function(evt) {
        console.log("Message from network:",evt.data);
        messageHandler(evt.data);
    };
}
Play.init = init;


}())