export var SVGCreateView = {};

import {MapEditorControl} from "./map-editor-control.js";
import {MapEditorPalette} from "./svg-map-editor-palette.js";
import {SVGMapView} from './svg-map-view.js';
import {SVGUtil} from './svg-util.js';
import {UnitPlacementControl} from './unit-placement-control.js';

(function() { 
    SVGCreateView.svgNS = 'http://www.w3.org/2000/svg';

    SVGCreateView.pathIndex = {};
    
    SVGCreateView.createMapEditorView = function(param) { 
        SVGCreateView.param = param;
        SVGCreateView.svg = SVGUtil.recreateMysvg();
        document.body.appendChild(SVGCreateView.svg);       
        
        SVGCreateView.svg.addEventListener("mouseup",MapEditorControl.svgMouseUpHandler);
        SVGCreateView.svg.addEventListener("mousedown",MapEditorControl.svgMouseDownHandler);
        
        MapEditorPalette.add(param, SVGCreateView.svg);
        SVGMapView.add(param, SVGCreateView.svg, MapEditorControl.hexMouseOverHandler, MapEditorControl.hexMouseDownHandler);
    };

    SVGCreateView.createUnitPlacementView = function(param) { 
        SVGCreateView.param = param;
        SVGCreateView.svg = SVGUtil.recreateMysvg();
        document.body.appendChild(SVGCreateView.svg); 
        
        SVGMapView.add(param, SVGCreateView.svg, UnitPlacementControl.hexMouseOverHandler, UnitPlacementControl.hexMouseDownHandler);

        SVGCreateView.svg.addEventListener("mousedown",UnitPlacementControl.svgMouseDownHandler);
    };
      
}())