export var SVGUnitSymbol = {};

import { SVGCreateView } from './svg-create-view.js';
import { Style } from './style.js';
import { Unit } from './unit.js';
import { SVGUtil } from './svg-util.js';

(function() {
    
var svgNS = 'http://www.w3.org/2000/svg';
SVGUnitSymbol.unitSymbolIndex = {};

function makeCapsule(p) {
    let rw = p.width - p.height;
    let [x_ul, y_ul] = [p.x - rw/2, p.y - p.height/2];
    let [x_ur, y_ur] = [p.x + rw/2, y_ul]
    let [x_lr, y_lr] = [x_ur, p.y + p.height/2];
    let [x_ll, y_ll] = [x_ul, y_lr];
    let elem = document.createElementNS(svgNS, 'path');
    let str = `M ${x_ur} ${y_ur} `;
    str += `A ${p.height/2} ${p.height/2}, 0, 0, 1, ${x_lr} ${y_lr} `;
    str += `L ${x_ll} ${y_ll} `;
    str += `A ${p.height/2} ${p.height/2}, 0, 0, 1, ${x_ul} ${y_ul} `;
    str += "Z";
    elem.setAttributeNS(null, 'd', str);
    elem.setAttributeNS(null, 'stroke', p.stroke);
    elem.setAttributeNS(null, 'fill', p.fill);
    elem.setAttributeNS(null, 'stroke-width', p.stroke_width);
    return elem;
}

function makeEllipse(p) {
    let element = document.createElementNS(svgNS, 'ellipse');
    element.setAttributeNS(null, 'cx', p.cx);
    element.setAttributeNS(null, 'cy', p.cy);
    element.setAttributeNS(null, 'rx', p.rx);
    element.setAttributeNS(null, 'ry', p.ry);
    element.setAttributeNS(null, 'stroke', p.stroke);
    element.setAttributeNS(null, 'fill', p.fill);
    element.setAttributeNS(null, 'stroke-width', p.stroke_width);
    return element;
}

function makeRect( param ) {
    // param.x, param.y is rectangle's center
    let x = param.x - param.width/2;
    let y = param.y - param.height/2;
    let element = document.createElementNS(svgNS, 'rect');
    element.setAttributeNS(null, 'x', x);
    element.setAttributeNS(null, 'y', y);
    element.setAttributeNS(null, 'width', param.width);
    element.setAttributeNS(null, 'height', param.height);
    element.setAttributeNS(null, 'stroke', param.stroke);
    element.setAttributeNS(null, 'fill', param.fill);
    element.setAttributeNS(null, 'stroke-width', param.stroke_width);
    return element;
}

function armorIcon(boxWidth, boxHeight, strokeWidth) {
    let rx = boxWidth/48*35/2;
    let ry = boxHeight/30*20/2;
    let param = { cx:0, cy:0, rx:rx, ry:ry, stroke:"black", fill:"transparent", stroke_width: strokeWidth };
    // Capsule variant
    //param = { x:0, y:0, width:boxWidth*0.7, height:boxHeight*0.7, stroke:"black", fill:"transparent", stroke_width: strokeWidth };
    //return makeCapsule(param);
    return makeEllipse(param);
}

function infantryIcon(boxWidth, boxHeight, strokeWidth) {
    let elem = document.createElementNS(svgNS, 'path');
    elem.setAttributeNS(null, 'stroke', "black");
    elem.setAttributeNS(null, 'stroke-width', strokeWidth);
    let str = `M ${-boxWidth/2} ${-boxHeight/2} `
    str += `L ${boxWidth/2} ${boxHeight/2} `;
    str += `M ${boxWidth/2} ${-boxHeight/2} `;
    str += `L ${-boxWidth/2} ${boxHeight/2}`;
    elem.setAttributeNS(null, 'd', str);
    return elem;
}

function USMCIcon(boxWidth, boxHeight, strokeWidth) {
    let elem = document.createElementNS(svgNS, 'g');
    elem.appendChild( infantryIcon(boxWidth, boxHeight, strokeWidth) );
    elem.appendChild( makeAmphib() );
    return elem;
}

function planeIcon(boxWidth, boxHeight, strokeWidth) {
    let elem = document.createElementNS(svgNS, 'path');
    elem.setAttributeNS(null, 'stroke', "transparent");
    elem.setAttributeNS(null, 'fill', "black");
    let str = "m 1.5466128,0.00326371 -0.07892,0.01 v 0.069 l -0.145564,0.054 -0.184146,0.03 h 0.257805 v 0.082 h 0.02456 v 0.3455 l -0.05612,0.039 h -0.170116 l -0.32444898,-0.3752 H 0.62764086 V 1.0554637 h 0.05787 v 0.1195 h -0.07204 l -0.0402,-0.041 h -0.436592 v 0.017 h -0.01984 l -0.02108,-0.018 h -0.09177 l -0.01674,-0.016 0.02232,-0.013 h 0.08557 l 0.04154,-0.033 v 0.031 h 0.0069 v -0.026 l 0.0684,-0.016 h 0.147317 l -0.267012,-0.32159999 h -0.0798 v -0.027 h 0.05568 l -0.209904,-0.2602 h -0.08557 v -0.03 h 0.05953 l -0.07272,-0.083 -0.1859,-0.031 -0.16485497,-0.052 -0.378816,-0.077 -0.19291609,-0.025 -0.01052,-0.022 -0.217468,-0.01 -0.249991,-0.042 -0.209499,-0.0799999977 0.209499,-0.0810000023 0.249991,-0.042 0.217468,-0.01 0.01052,-0.021 0.19291609,-0.025 0.378816,-0.077 0.16485497,-0.052 0.1859,-0.032 0.07272,-0.083 h -0.05953 v -0.03 h 0.08557 l 0.209904,-0.2599 h -0.05568 v -0.027 h 0.0798 l 0.267012,-0.32310001 h -0.147315 l -0.0684,-0.016 v -0.025 h -0.0069 v 0.031 l -0.04154,-0.033 h -0.08557 l -0.02232,-0.012 0.01674,-0.016 h 0.09177 l 0.02108,-0.018 h 0.01984 v 0.017 h 0.436585 l 0.0402,-0.041 h 0.07204 v 0.1195 h -0.05787 v 0.79790001 h 0.24202096 l 0.32444898,-0.3753 h 0.170117 l 0.05612,0.039 v 0.3455 h -0.02456 v 0.082 h -0.257807 l 0.184147,0.03 0.145563,0.054 v 0.069 l 0.07892,0.01 0.05436,0.01 z";
    elem.setAttributeNS(null, 'd', str);
    return elem;
}

function shipIcon(boxWidth, boxHeight, strokeWidth) {
    let elem = document.createElementNS(svgNS, 'path');
    elem.setAttributeNS(null, 'stroke', "transparent");
    elem.setAttributeNS(null, 'fill', "black");
    let str = "m 2.0840208,-0.06025048 -0.1622663,-0.05523754 -0.1432778,-0.0448864 -0.2088751,-0.050062 -0.1570876,-0.0258968 -0.1553616,-0.0155361 -0.1467302,-0.008658 -0.19333867,-0.003425 -0.0414301,-0.0103606 -0.18815991,-0.003425 -0.26411448,0.001712 -0.27965062,-0.003425 v 0.008658 l -0.18298142,-0.001712 -0.43846463,-0.005137 -0.21232724,0.001712 -0.33143767,0.005137 -0.2761984,0.008658 -0.2261374,0.006945 v 0.0189897 l -0.1916123,0.008658 -0.1847075,0.0120826 -0.1639924,0.0155361 -0.1778031,0.0224432 v 0.184708 0.18470704 l 0.1778031,0.0224432 0.1639924,0.0155362 0.1847075,0.0120826 0.1916123,0.008658 v 0.0189897 l 0.2261374,0.006945 0.2761984,0.008658 0.33143767,0.005137 0.21232724,0.001712 0.43846463,-0.005137 0.18298142,-0.001713 v 0.008658 l 0.27965062,-0.003425 0.26411448,0.001712 0.18815991,-0.003425 0.0414301,-0.0103606 0.19333863,-0.003425 0.1467302,-0.008658 0.1553616,-0.0155362 0.1570876,-0.0258968 0.2088751,-0.050062 0.1432778,-0.0448864 0.1622663,-0.05523753 0.131194,-0.06732015 z";
    elem.setAttributeNS(null, 'd', str);
    return elem;
}

function makeAmphib() {
    let elem = document.createElementNS(svgNS, 'path');
    elem.setAttributeNS(null, 'stroke', "black");
    elem.setAttributeNS(null, 'stroke-width', "0.2");
    elem.setAttributeNS(null, 'fill', "transparent");
    let str = "m 2.1035665,0.74386842 c -0.1449071,0 -0.2623776,-0.11747043 -0.262712,-0.25868544 C 1.84052,0.39513658 1.7905115,0.30851871 1.7093312,0.26164939 c -0.08118,-0.0468694 -0.1811976,-0.0468694 -0.2623775,0 -0.08118,0.0468694 -0.1311888,0.13348716 -0.1311888,0.22689827 0,0.14457969 -0.1174704,0.26205016 -0.2623774,0.26205016 -0.14490722,0 -0.2623776,-0.11747047 -0.26271214,-0.2586854 -3.3445e-4,-0.0900464 -0.0503431,-0.17666436 -0.13152318,-0.22353359 -0.0811798,-0.0468694 -0.18119771,-0.0468694 -0.26237756,0 -0.0811798,0.0468694 -0.13118882,0.13348716 -0.13118882,0.22689827 0,0.14457968 -0.11747038,0.26205012 -0.26237747,0.26205012 -0.14490717,0 -0.26237755,-0.11747044 -0.26271209,-0.25868544 -3.3445e-4,-0.0900463 -0.0503431,-0.17666428 -0.13152318,-0.22353351 -0.0811798,-0.0468694 -0.18119775,-0.0468694 -0.26237755,0 -0.08118,0.0468694 -0.1311887,0.13348716 -0.1311887,0.22689827 0,0.14457968 -0.1174705,0.26205018 -0.26237761,0.26205018 -0.1449071,0 -0.2623775,-0.1174705 -0.2627121,-0.2586855 -3.344e-4,-0.0900464 -0.050343,-0.17666428 -0.1315232,-0.2235336 -0.08118,-0.0468694 -0.1811977,-0.0468694 -0.2623775,0 -0.08118,0.0468694 -0.1311887,0.13348716 -0.1311887,0.22689827 0,0.14457969 -0.1174705,0.26205013 -0.2623776,0.26205013";
    elem.setAttributeNS(null, 'd', str);
    return elem;
}

function eabIcon(boxWidth, boxHeight, strokeWidth) {
    let icon = document.createElementNS(svgNS, 'g');
    let param = {x:0, y:-0.5, width:1.6, height:0.7, fill:"black", stroke:"transparent", stroke_width:0};
    icon.appendChild( makeRect(param) );
    icon.appendChild( makeAmphib() );
    return icon;
}

function mechInfIcon(boxWidth, boxHeight, strokeWidth) {
    let icon = document.createElementNS(svgNS, 'g');
    icon.appendChild( armorIcon(boxWidth, boxHeight, strokeWidth) );
    icon.appendChild( infantryIcon(boxWidth, boxHeight, strokeWidth) );
    return icon;
}

function artilleryIcon(boxWidth) {
    let radius = boxWidth * 0.05;
    let p = {cx:0, cy:0, rx:radius, ry:radius, stroke:"black", fill:"black", stroke_width:0};
    return makeEllipse(p);
}

function HIMARSIcon(strokeWidth) {
    let icon = document.createElementNS(svgNS, 'g');
    let offset = -1;

    // Upper chevron
    let uc_elem = document.createElementNS(svgNS, 'path');
    uc_elem.setAttributeNS(null, 'stroke', "black");
    uc_elem.setAttributeNS(null, 'fill', "none");
    uc_elem.setAttributeNS(null, 'stroke-width', 0.1);
    let y = offset + 0.98478;
    let str = "m -0.93567391,"+y+" 0.95088812,-0.60856 0.95088812,0.60856";
    uc_elem.setAttributeNS(null, 'd', str);

    let lc_elem = document.createElementNS(svgNS, 'path');
    lc_elem.setAttributeNS(null, 'stroke', "black");
    lc_elem.setAttributeNS(null, 'fill', "none");
    lc_elem.setAttributeNS(null, 'stroke-width', 0.1);
    y = offset + 0.61964;
    str = "m -0.93567391,"+y+" 0.95088812,-0.60856 0.95088812,0.60856";
    lc_elem.setAttributeNS(null, 'd', str);

    let cy = offset + 1.47162;
    let p = {cx:0.01521421, cy:cy, rx:0.59335417, ry:0.59335417, stroke:"black", fill:"black", stroke_width:strokeWidth};
    let circ = makeEllipse(p);

    icon.appendChild( uc_elem );
    icon.appendChild( lc_elem );
    icon.appendChild( circ );
    return icon;
}

function makeProp(strokeWidth) {
    let elem = document.createElementNS(svgNS, 'path');
    elem.setAttributeNS(null, 'stroke', "black");
    elem.setAttributeNS(null, 'fill', "none");
    elem.setAttributeNS(null, 'stroke-width', strokeWidth);
    let str = "m 0.94898635,0.06657 c 0.18888485,0 0.36342115,-0.10077 0.45786235,-0.26435 0.094441,-0.16358 0.094441,-0.36511 0,-0.52869 -0.094441,-0.16358 -0.2689775,-0.26435 -0.45786235,-0.26435 l -1.86754433,1.05739 c -0.18888472,0 -0.36342092,-0.10077 -0.45786222,-0.26435 -0.094441,-0.16358 -0.094441,-0.36511 0,-0.52869 0.094441,-0.16358 0.2689775,-0.26435 0.45786225,-0.26435 z";
    elem.setAttributeNS(null, 'd', str);
    return elem;
}

function fighterIcon(strokeWidth) {
    let icon = document.createElementNS(svgNS, 'g');
    icon.appendChild( makeProp(strokeWidth) );
    let fontSize="1.06px";
    let {element:label} = makeLabel("F",fontSize);
    icon.appendChild(label);
    let bb = label.getBBox();
    label.setAttributeNS(null, 'x', -0.15-bb.width/2);
    label.setAttributeNS(null, 'y', 1+bb.height/3);
    icon.appendChild( label );
    return icon;
}

function bomberIcon(strokeWidth) {
    let icon = document.createElementNS(svgNS, 'g');
    icon.appendChild( makeProp(strokeWidth) );
    let fontSize="1.06px";
    let {element:label} = makeLabel("B",fontSize);
    icon.appendChild(label);
    let bb = label.getBBox();
    label.setAttributeNS(null, 'x', -0.15-bb.width/2);
    label.setAttributeNS(null, 'y', 1+bb.height/3);
    icon.appendChild( label );
    return icon;
}

function atkheloIcon(strokeWidth) {
    let elem = document.createElementNS(svgNS, 'path');
    elem.setAttributeNS(null, 'stroke', "black");
    elem.setAttributeNS(null, 'fill', "none");
    elem.setAttributeNS(null, 'stroke-width', strokeWidth);
    let offset = -1;
    let y = 0.38954 + offset;
    let str = "m 0.94898635,"+y+" -1.86754433,1.05739 3e-8,-1.05739 1.8675443,1.05739 z";
    elem.setAttributeNS(null, 'd', str);
    return elem;
}

function makeShip(strokeWidth, isSub) {
    if (isSub===undefined)
        isSub = false;
    let icon = document.createElementNS(svgNS, 'g');
    let elem = document.createElementNS(svgNS, 'path');
    elem.setAttributeNS(null, 'stroke', "black");
    elem.setAttributeNS(null, 'fill', "none");
    elem.setAttributeNS(null, 'stroke-width', strokeWidth);
    let offset = -297.1;
    let y = 298.38954 + offset;
    let str = "m -0.04303231,"+y+" -0.89809659,-0.372 -0.3720038,-0.8981 0.37200375,-0.8981 0.89809657,-0.372 0.89809658,0.372 0.3720038,0.8981 -0.37200375,0.8981 z";
    elem.setAttributeNS(null, 'd', str);
    icon.appendChild(elem);

    elem = document.createElementNS(svgNS, 'path');
    elem.setAttributeNS(null, 'stroke', "black");
    elem.setAttributeNS(null, 'fill', "none");
    elem.setAttributeNS(null, 'stroke-width', strokeWidth);
    if (isSub)
        elem.setAttributeNS(null, 'stroke-dasharray',"0.08,0.08");
    y = 296.39903 + offset;
    str = "M -1.0611911,"+y+" H 0.98131653";
    elem.setAttributeNS(null, 'd', str);
    icon.appendChild(elem);

    elem = document.createElementNS(svgNS, 'path');
    elem.setAttributeNS(null, 'stroke', "black");
    elem.setAttributeNS(null, 'fill', "none");
    elem.setAttributeNS(null, 'stroke-width', strokeWidth);
    if (isSub)
        elem.setAttributeNS(null, 'stroke-dasharray',"0.08,0.08");
    y = 297.60476 + offset;
    str = "M -1.0611911,"+y+" H 0.98131653";
    elem.setAttributeNS(null, 'd', str);
    icon.appendChild(elem);
    return icon;
}

function acCarrierIcon(strokeWidth) {
    let icon = document.createElementNS(svgNS, 'g');
    icon.appendChild( makeShip(strokeWidth) );
    let elem = document.createElementNS(svgNS, 'path');
    elem.setAttributeNS(null, 'stroke', "none");
    elem.setAttributeNS(null, 'fill', "black");
    elem.setAttributeNS(null, 'stroke-width', 0);
    let offset = -297.1;
    let y = 296.4094 + offset;
    let str = "m -0.6407532,"+y+" v 0.59425 l 0.59426128,0.59428 0.59426128,-0.59428 H -0.04649192 V "+y+" H -0.6407532";
    elem.setAttributeNS(null, 'd', str);
    icon.appendChild( elem );
    return icon;
}

function destroyerIcon(strokeWidth) {
    let icon = document.createElementNS(svgNS, 'g');
    icon.appendChild( makeShip(strokeWidth) );
    let fontSize="1.3px";
    let {element:label} = makeLabel("DD",fontSize,"bold");
    icon.appendChild(label);
    let bb = label.getBBox();
    label.setAttributeNS(null, 'x', -0.95-bb.width/2);
    label.setAttributeNS(null, 'y', 0.35+bb.height/3);
    icon.appendChild( label );
    return icon;
}

function corvetteIcon(strokeWidth) {
    let icon = document.createElementNS(svgNS, 'g');
    icon.appendChild( makeShip(strokeWidth) );
    let fontSize="1.3px";
    let {element:label} = makeLabel("FS",fontSize,"bold");
    icon.appendChild(label);
    let bb = label.getBBox();
    label.setAttributeNS(null, 'x', -0.8-bb.width/2);
    label.setAttributeNS(null, 'y', 0.35+bb.height/3);
    icon.appendChild( label );
    return icon;
}

function frigateIcon(strokeWidth) {
    let icon = document.createElementNS(svgNS, 'g');
    icon.appendChild( makeShip(strokeWidth) );
    let fontSize="1.3px";
    let {element:label} = makeLabel("FF",fontSize,"bold");
    icon.appendChild(label);
    let bb = label.getBBox();
    label.setAttributeNS(null, 'x', -0.8-bb.width/2);
    label.setAttributeNS(null, 'y', 0.35+bb.height/3);
    icon.appendChild( label );
    return icon;
}

function cruiserIcon(strokeWidth) {
    let icon = document.createElementNS(svgNS, 'g');
    icon.appendChild( makeShip(strokeWidth) );
    let fontSize="1.3px";
    let {element:label} = makeLabel("CG",fontSize,"bold");
    icon.appendChild(label);
    let bb = label.getBBox();
    label.setAttributeNS(null, 'x', -0.9-bb.width/2);
    label.setAttributeNS(null, 'y', 0.35+bb.height/3);
    icon.appendChild( label );
    return icon;
}

function subIcon(strokeWidth) {
    let icon = document.createElementNS(svgNS, 'g');
    icon.appendChild( makeShip(strokeWidth,true) );
    let elem = document.createElementNS(svgNS, 'path');
    elem.setAttributeNS(null, 'stroke', "none");
    elem.setAttributeNS(null, 'fill', "black");
    elem.setAttributeNS(null, 'stroke-width', 0);
    let offset = -297.1;
    let y = 297 + offset;
    let str = "m -0.92525976,"+y+" 0.4411137,-0.24556 h 0.88222742 l 0.4411137,0.24556 l -0.4411137,0.24556 h -0.88222742 z";
    elem.setAttributeNS(null, 'd', str);
    icon.appendChild( elem );
    return icon;
}

function amphibshipIcon(strokeWidth) {
    let icon = document.createElementNS(svgNS, 'g');
    icon.appendChild( makeShip(strokeWidth) );
    let elem = document.createElementNS(svgNS, 'path');
    elem.setAttributeNS(null, 'stroke', "none");
    elem.setAttributeNS(null, 'fill', "black");
    elem.setAttributeNS(null, 'stroke-width', 0);
    let offset = -297.1;
    let y = 296.40132 + offset;
    let str = "m -0.38664425,"+y+" v 0.67747 h -0.2366781 l 0.5860108,0.52194 h 0.7529256 v -0.14004 h -0.5953125 l 0.4289144,-0.3819 h -0.2366781 v -0.67747 z";
    elem.setAttributeNS(null, 'd', str);
    icon.appendChild( elem );
    return icon;
}

function aaIcon(strokeWidth) {
    let elem = document.createElementNS(svgNS, 'path');
    elem.setAttributeNS(null, 'stroke', "black");
    elem.setAttributeNS(null, 'fill', "none");
    elem.setAttributeNS(null, 'stroke-width', strokeWidth);
    let offset = 1;
    let y = 0.18674 + offset;
    let str = "m 1.2856007,"+y+" c 0,0 -0.2029987,-0.89349 -0.3239709,-1.21717 -0.12097212,-0.32368 -0.14288756,-0.43826 -0.34992682,-0.73027 -0.20703926,-0.29202 -0.34992683,-0.36517 -0.5835108,-0.35756 -0.23358401,-0.008 -0.37647158,0.0655 -0.58351084,0.35756 -0.20703926,0.29201 -0.2289547,0.40659 -0.34992682,0.73027 -0.12097212,0.32368 -0.32397082,1.21717 -0.32397082,1.21717";
    elem.setAttributeNS(null, 'd', str);
    return elem;
}

function companyEchelon(boxWidth, boxHeight) {
    let width = 0.1;
    let height = 0.55;
    let vspace = 0.2;
    let element = document.createElementNS(svgNS, 'rect');
    element.setAttributeNS(null, 'x', 0-width/2);
    element.setAttributeNS(null, 'y', -boxHeight/2-height-vspace);
    element.setAttributeNS(null, 'width', width);
    element.setAttributeNS(null, 'height', height);
    element.setAttributeNS(null, 'stroke', "black");
    element.setAttributeNS(null, 'fill', "black");
    element.setAttributeNS(null, 'stroke-width', strokeWidth);
    return element;
}

function regimentEchelon(boxWidth, boxHeight) {
    let width = 0.1;
    let height = 0.55;
    let vspace = 0.2;
    let hspace = 0.1;
    let group = document.createElementNS(svgNS, 'g');
    let elem = document.createElementNS(svgNS, 'rect');
    elem.setAttributeNS(null, 'x', 0-width/2);
    elem.setAttributeNS(null, 'y', -boxHeight/2-height-vspace);
    elem.setAttributeNS(null, 'width', width);
    elem.setAttributeNS(null, 'height', height);
    elem.setAttributeNS(null, 'stroke', "black");
    elem.setAttributeNS(null, 'fill', "black");
    elem.setAttributeNS(null, 'stroke-width', 0);
    group.appendChild(elem);
    
    elem = document.createElementNS(svgNS, 'rect');
    elem.setAttributeNS(null, 'x', 0-width/2-width-hspace);
    elem.setAttributeNS(null, 'y', -boxHeight/2-height-vspace);
    elem.setAttributeNS(null, 'width', width);
    elem.setAttributeNS(null, 'height', height);
    elem.setAttributeNS(null, 'stroke', "black");
    elem.setAttributeNS(null, 'fill', "black");
    elem.setAttributeNS(null, 'stroke-width', 0);
    group.appendChild(elem);
    
    elem = document.createElementNS(svgNS, 'rect');
    elem.setAttributeNS(null, 'x', 0-width/2+width+hspace);
    elem.setAttributeNS(null, 'y', -boxHeight/2-height-vspace);
    elem.setAttributeNS(null, 'width', width);
    elem.setAttributeNS(null, 'height', height);
    elem.setAttributeNS(null, 'stroke', "black");
    elem.setAttributeNS(null, 'fill', "black");
    elem.setAttributeNS(null, 'stroke-width', 0);
    group.appendChild(elem);
    return group;
}

function battalionEchelon(boxWidth, boxHeight) {
    let width = 0.1;
    let height = 0.55;
    let vspace = 0.2;
    let hspace = 0.1;
    let group = document.createElementNS(svgNS, 'g');
    let elem;
    //let elem = document.createElementNS(svgNS, 'rect');
    // elem.setAttributeNS(null, 'x', 0-width/2);
    // elem.setAttributeNS(null, 'y', -boxHeight/2-height-vspace);
    // elem.setAttributeNS(null, 'width', width);
    // elem.setAttributeNS(null, 'height', height);
    // elem.setAttributeNS(null, 'stroke', "black");
    // elem.setAttributeNS(null, 'fill', "black");
    // elem.setAttributeNS(null, 'stroke-width', 0);
    // group.appendChild(elem);
    
    elem = document.createElementNS(svgNS, 'rect');
    elem.setAttributeNS(null, 'x', 0-width/2-width-hspace);
    elem.setAttributeNS(null, 'y', -boxHeight/2-height-vspace);
    elem.setAttributeNS(null, 'width', width);
    elem.setAttributeNS(null, 'height', height);
    elem.setAttributeNS(null, 'stroke', "black");
    elem.setAttributeNS(null, 'fill', "black");
    elem.setAttributeNS(null, 'stroke-width', 0);
    group.appendChild(elem);
    
    elem = document.createElementNS(svgNS, 'rect');
    elem.setAttributeNS(null, 'x', 0-width/2+width+hspace);
    elem.setAttributeNS(null, 'y', -boxHeight/2-height-vspace);
    elem.setAttributeNS(null, 'width', width);
    elem.setAttributeNS(null, 'height', height);
    elem.setAttributeNS(null, 'stroke', "black");
    elem.setAttributeNS(null, 'fill', "black");
    elem.setAttributeNS(null, 'stroke-width', 0);
    group.appendChild(elem);
    return group;
}

function addHqIcon(parent, boxWidth, boxHeight) {
    let fontSize="1.6px";
    let {element:label} = makeLabel("HQ",fontSize);
    parent.appendChild(label);
    let bb = label.getBBox();
    label.setAttributeNS(null, 'x', 0-bb.width/2);
    label.setAttributeNS(null, 'y', 0+bb.height/3);
    return label;
}

function makeLabel(txt, fontSize, fontWeight) {
    if (!fontWeight)
        fontWeight = "normal";
    if (fontSize===undefined)  fontSize="0.8px";
    var label = document.createElementNS(svgNS, 'text');
    label.setAttributeNS(null, 'style', `font: ${fontSize} sans-serif;font-weight: ${fontWeight};`);
    label.setAttributeNS(null, 'stroke', 'black');
    label.setAttributeNS(null, 'stroke-width', '0');
    label.setAttributeNS(null, 'font-weight', fontWeight);
    var textNode = document.createTextNode(txt);
    label.appendChild(textNode);
    return {"element":label, "textNode":textNode};
}

SVGUnitSymbol.moveSymbolToHex = function(unitId, hex) {
    let unitSymbol = SVGUnitSymbol.unitSymbolIndex[unitId].whole;
    let id = hex.id;
    let svg_hex = document.getElementById(id);
    let bbox = svg_hex.getBBox();
    let x = bbox.x + bbox.width/2;
    let y = bbox.y + bbox.height/2;
    // FIX: fixed scale 
    unitSymbol.setAttributeNS(null, 'transform', `translate(${x} ${y}) scale(0.6 0.6)`);
};

SVGUnitSymbol.create = function(unit,unitMouseDownHandler) {
    let parentElem = SVGCreateView.svg;
    let color = Style.factionIndex[unit.faction].normal;
    let name = unit.longName;
    let symbolElements = create(parentElem,color,unit.echelon,unit.type,name,unit.currentStrength,unit.uniqueId);
    SVGUnitSymbol.unitSymbolIndex[ unit.uniqueId ] = symbolElements;
    symbolElements.whole.addEventListener("mousedown",unitMouseDownHandler);
    SVGUnitSymbol.moveSymbolToHex(unit.uniqueId, unit.hex);
}

SVGUnitSymbol.partialObsUpdate = function(unitId, msgO) { 
    let symbolElements = SVGUnitSymbol.unitSymbolIndex[unitId];
    let unit = Unit.unitIndex[unitId];
    if (symbolElements.whole.parentNode === null) {
        let parentElem = SVGCreateView.svg;
        parentElem.appendChild(symbolElements.whole);
    }
    if (msgO.ineffective || unit.hex==null) {
        symbolElements.whole.remove();
        return;
    }
    // Position
    SVGUnitSymbol.moveSymbolToHex(unitId, unit.hex);

    // Strength
    symbolElements.strength.nodeValue = unit.currentStrength;

    // Brightness
    let level;
    if (unit.canMove)  level = "normal";
    else               level = "dim";
    SVGUnitSymbol.setBrightness(unitId, level);
}

// Obsolete??
SVGUnitSymbol.setFactionBrightness = function(faction, level) {
    for (let unit of Unit.units) {
        if (unit.faction == faction)
            SVGUnitSymbol.setBrightness(unit.uniqueId, level);
    }
}

SVGUnitSymbol.setAllUnitBrightness = function(level) {
    for (let unit of Unit.units)
        SVGUnitSymbol.setBrightness(unit.uniqueId, level);
}

function create(parentElem,color,echelon,type,name,strength,uniqueID) {
    let symbolElements = {};
    let unitSymbol = document.createElementNS(svgNS, 'g');
    unitSymbol.setAttributeNS(null, 'pointer-events', "all");
    unitSymbol.setAttributeNS(null, 'id', uniqueID);
    parentElem.appendChild( unitSymbol );
    
    let box = document.createElementNS(svgNS, 'g');
    box.setAttributeNS(null, 'pointer-events', "all");
    unitSymbol.appendChild( box );
    
    let [boxWidth, boxHeight] = [4.7, 2.9];
    let strokeWidth = 0.1;
    
    let param = { x:0, y:0, width:boxWidth, height:boxHeight, stroke:"black", fill:color, stroke_width: strokeWidth };
    let background = makeRect(param)
    box.appendChild( background );
    symbolElements.background = background;
    
    switch (type) {
        case "armor":
            box.appendChild( armorIcon(boxWidth, boxHeight, strokeWidth) );
            break;
        case "mechinf":
        case "heavy":
            box.appendChild( mechInfIcon(boxWidth, boxHeight, strokeWidth) );
            break;
        case "infantry":
        case "light":
            box.appendChild( infantryIcon(boxWidth, boxHeight, strokeWidth) );
            break;
        case "artillery":
            box.appendChild( artilleryIcon(boxWidth) );
            break;
        case "hq":
        case "tisr":
            addHqIcon(box, boxWidth, boxHeight);
            break;
        case "usmc":
            box.appendChild( USMCIcon(boxWidth, boxHeight, strokeWidth) );
            break;
        case "himars":
        case "df26":
            box.appendChild( HIMARSIcon(strokeWidth) );
            break;
        case "fighter":
            box.appendChild( fighterIcon(strokeWidth) );
            break;
        case "bomber":
        case "p8":
            box.appendChild( bomberIcon(strokeWidth) );
            break;
        case "atkhelo":
            box.appendChild( atkheloIcon(strokeWidth) );
            break;
        case "accarrier":
        case "clf":
            box.appendChild( acCarrierIcon(strokeWidth) );
            break;
        case "destroyer":
        case "ddg":
            box.appendChild( destroyerIcon(strokeWidth) );
            break;
        case "corvette":
        case "msc":
            box.appendChild( corvetteIcon(strokeWidth) );
            break;
        case "frigate":
            box.appendChild( frigateIcon(strokeWidth) );
            break;
        case "cruiser":
            box.appendChild( cruiserIcon(strokeWidth) );
            break;
        case "sub":
        case "ssk":
        case "ssn":
            box.appendChild( subIcon(strokeWidth) );
            break;
        case "amphibship":
            box.appendChild( amphibshipIcon(strokeWidth) );
            break;
        case "aa":
            box.appendChild( aaIcon(strokeWidth) );
            break;           
    }
            
    if (echelon==="company")
        unitSymbol.appendChild( companyEchelon(boxWidth, boxHeight) );
    else if (echelon==="regiment")
        unitSymbol.appendChild( regimentEchelon(boxWidth, boxHeight) );
    else if (echelon==="battalion"||echelon==="squadron")
        unitSymbol.appendChild( battalionEchelon(boxWidth, boxHeight) );

    let usbb = unitSymbol.getBBox();

    let {element:label} = makeLabel(name); 
    unitSymbol.appendChild(label);
    let lbb = label.getBBox();
    label.setAttributeNS(null, 'x', boxWidth/2-lbb.width);
    label.setAttributeNS(null, 'y', usbb.y+usbb.height+lbb.height);

    let {element:str_label, textNode:tnode} = makeLabel(strength,"1.0px");
    symbolElements.strength = tnode; 
    unitSymbol.appendChild(str_label);
    let lbb2 = label.getBBox();
    const leftPad = 0.2;
    const topPad = 0.1;
    str_label.setAttributeNS(null, 'x', -boxWidth/2+leftPad);
    str_label.setAttributeNS(null, 'y', usbb.y+usbb.height+lbb2.height+topPad);
    
    symbolElements.whole = unitSymbol;
    symbolElements.strengthBarMaxWidth = boxWidth;
    return symbolElements;
}


var selectionMarker = null;
SVGUnitSymbol.selectionMarker = selectionMarker;

SVGUnitSymbol.markSelected = function(elem) {
    let bbox = SVGUtil.getTransformedBBox(elem);
    let mg = 0.05 * bbox.width;
    selectionMarker = SVGUtil.makeRect(bbox.x-mg,bbox.y-mg,bbox.width+2*mg,bbox.height+2*mg,"transparent","red");
    SVGCreateView.svg.appendChild(selectionMarker);
}

SVGUnitSymbol.unmarkSelected = function() {
    selectionMarker.remove();
}

SVGUnitSymbol.setBrightness = function(unitId, level) {
    let elems = SVGUnitSymbol.unitSymbolIndex[unitId];
    let unit = Unit.unitIndex[unitId];
    let color = Style.factionIndex[unit.faction][level];
    elems.background.setAttributeNS(null, 'fill', color);
}



}())