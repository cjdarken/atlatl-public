export var Playback = {};

import {Map} from "./map.js";
import {Unit} from "./unit.js";
import {SVGCreateView} from "./svg-create-view.js";
// import {SVGUtil} from "./svg-util.js";
import {SVGMapView} from "./svg-map-view.js";
import {SVGUnitSymbol} from "./svg-unit-symbol.js";
// import {SVGGui} from "./svg-gui.js";
// import {SVGSetupMarker} from "./svg-setup-marker.js";
// import {Style} from "./style.js";
// import {Terrain} from "./terrain.js";
// import {HumanPlayerControl} from "./human-player-control.js";
// import {Mobility} from "./mobility.js";
// import {Combat} from "./combat.js";
// import {UnitPlacementControl} from "./unit-placement-control.js";

(function() { 

const TileState = {
    Terrain: ['Terrain'],
    FalseColor: ['FalseColor'],
    Orders: ['Orders']
  };
  var tileState = TileState.Terrain;
  var displayEchelon = 0;
  var nEchelons = 3;
  var playMode = false;
  
  function processScenarioJSON(str) {
      let scenarioJson = JSON.parse(str).parameters;
      
      Map.fromPortable(scenarioJson.map);
      
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
  
      Unit.fromPortable2(scenarioJson.units,a=>{});
  }
  
  var messages;
  var message_index = 0;
  var colors = {};
  var debugData = null;
  
  function colorsForEchelon(k) {
      if (!debugData || !debugData.echelons)
          return {};
      if ( debugData.echelons.length < k+1)
          return {};
      var colors = {};
      echelonColorData = debugData.echelons[k];
      for (var datum of echelonColorData) {
          colors[datum.hex] = datum.color;
      }
      return colors;
  }
  
  function falseColors() {
      if (!debugData || !debugData.colors)
          return {}
      return debugData.colors;
  }

  function set_play_mode(val) {
    playMode = val;
  }
  Playback.set_play_mode = set_play_mode;
  
  function play() {
      if (playMode) {
          if (!next_message())
              playMode = false;
          else
              requestAnimationFrame(play);
      }
  }
  Playback.play = play;

  function next_message() {
      if (message_index >= messages.length) {
          console.log("No more messages");
          return false;
      }
  
      let messageO = JSON.parse(messages[message_index])
  
      if (messageO.type=="parameters") {
          processScenarioJSON(messages[message_index]);
          ++ message_index;
          messageO = JSON.parse(messages[message_index]);
          console.log(messages[message_index])
      }
      if ("debug" in messageO) 
          debugData = messageO.debug;
      else
          debugData = null;
  
      let msgO = messageO.observation;
      if (msgO.type === "role-assigned") {
          init();
          return;
      }
      ++ message_index;
      for (let unitObs of msgO.units) {
          let uniqueId = unitObs.faction+" "+unitObs.longName;
          let unit = Unit.unitIndex[uniqueId];
          unit.partialObsUpdate(unitObs);
          SVGUnitSymbol.partialObsUpdate(uniqueId, unitObs);
      } 
      if (tileState == TileState.FalseColor)
          SVGMapView.set_colors(falseColors());
      else if (tileState == TileState.Orders)
          SVGMapView.set_colors(colorsForEchelon(displayEchelon));
      return true;
  }
  Playback.next_message = next_message;
  
  function init() {
      messages = replayData;
      console.log("num messages = "+messages.length);
      processScenarioJSON(messages[message_index]);
      ++ message_index;
      document.getElementById("orders_echelon").value = "NA";
      SVGMapView.terrain_color();
  }
  Playback.init = init;
  
  function false_color() {
      SVGMapView.set_colors(colors);
      tileState = TileState.FalseColor;
      document.getElementById("orders_echelon").value = "NA"; 
      SVGMapView.set_colors(falseColors());
  }
  Playback.false_color = false_color;
  
  function terrain_color() {
      SVGMapView.terrain_color();
      tileState = TileState.Terrain;
      document.getElementById("orders_echelon").value = "NA";
  }
  Playback.terrain_color = terrain_color;
  
  function orders_color() {
      SVGMapView.terrain_color();
      if (tileState==TileState.Orders)
          displayEchelon = (displayEchelon+1)%nEchelons
      tileState = TileState.Orders;
      document.getElementById("orders_echelon").value = displayEchelon; 
      SVGMapView.set_colors(colorsForEchelon(displayEchelon));
  }
  Playback.orders_color = orders_color;

}())