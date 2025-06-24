export var Unit = {};

import { Map } from './map.js';
import { SVGUnitSymbol } from './svg-unit-symbol.js';
import { Mobility } from './mobility.js';
import { Combat } from './combat.js';

(function() {
    
    Unit.init = function() {
        Unit.units = [];    
        Unit.unitIndex = {}; // id to Unit
        Unit.occupancy = {}; // hex id to Unit list
    }

    Unit.init();

    Unit.placeUnits = function() {
        for (let unit of Unit.units)
            unit.placeUnit();
    }
    
    Unit.createSVG = function(unitMouseDownHandler) {
        for (let unit of Unit.units)
            SVGUnitSymbol.create(unit,unitMouseDownHandler);
    }
    
    Unit.Unit = function(param) {
        this.type = param.type;
        this.echelon = param.echelon;
        this.name = param.name;
        this.longName = param.longName;
        this.uniqueId = param.uniqueId;
        this.faction = param.faction;
        this.currentStrength = param.currentStrength;
        this.fullStrength = param.fullStrength;
        this.homeOrgId = param.homeOrgId;
        this.taskOrgId = param.taskOrgId;
        this.hex = null;
        this.canMove = false;
        this.ineffective = false;
        Unit.unitIndex[this.uniqueId] = this;
    };
    
    Unit.Unit.prototype.portableCopy = function() {
        let copy = {};
        copy.type = this.type;
        copy.echelon = this.echelon;
        copy.name = this.name;
        copy.longName = this.longName;
        copy.uniqueId = this.uniqueId;
        copy.faction = this.faction;
        copy.currentStrength = this.currentStrength;
        copy.fullStrength = this.fullStrength;
        copy.homeOrgId = this.homeOrgId;
        copy.taskOrgId = this.taskOrgId;
        copy.hex = this.hex.id;
        copy.canMove = this.canMove;
        copy.ineffective = this.ineffective;
        return copy;
    }
    
    Unit.Unit.prototype.setHex = function(hex) {
        if (this.hex) {
            let occupants = Unit.occupancy[this.hex.id];
            if (occupants) {
                const index = occupants.indexOf(this);
                occupants.splice(index, 1);
            }
        }
        this.hex = hex;
        if (this.hex && !Unit.occupancy[this.hex.id])
            Unit.occupancy[this.hex.id] = [];
        Unit.occupancy[this.hex.id].push(this);
    }
    
    Unit.Unit.prototype.remove = function() {
        if (this.hex) {
            let occupants = Unit.occupancy[this.hex.id];
            if (occupants) {
                const index = occupants.indexOf(this);
                occupants.splice(index, 1);
            }
        }
        this.hex = null;
    }
    
    Unit.Unit.prototype.findMoveTargets = function() {
        let origin = this.hex;
        let moveTargets = [];
        let moveCost = {};
        let agenda = [this.hex]; // Check if children of these hexes are valid move targets
        moveCost[this.hex.id] = 0;
        while (agenda.length) {
            let hex = agenda.shift();
            for (let neigh of Map.getNeighborHexes(hex)) {
                if (moveCost[neigh.id]!==undefined)  continue;
                if (Unit.occupancy[neigh.id] && Unit.occupancy[neigh.id].length + 1 > Mobility.stackingLimit)  continue;
                let deltaCost = Mobility.cost[this.type][neigh.terrain];
                let totalCost = moveCost[hex.id] + deltaCost;
                if (totalCost <= 100) {
                    moveCost[neigh.id] = totalCost;
                    moveTargets.push( neigh );
                    if (totalCost < 100)
                        agenda.push( neigh );
                }
            }
        }
        return moveTargets;
    }
    
    Unit.Unit.prototype.findFireTargets = function() {
        let fireTargets = [];
        let maxRange = Combat.range[this.type];
        for (let unit of Unit.units) {
            if (unit.faction === this.faction)
                continue;
            if (unit.ineffective)
                continue;
            if (unit.hex === null)
                continue
            let range = Map.gridDistance(this.hex.x_grid, this.hex.y_grid, unit.hex.x_grid, unit.hex.y_grid);
            if (range<=maxRange)
                fireTargets.push(unit);
        }
        return fireTargets;
    }
    
    Unit.Unit.prototype.partialObsUpdate = function(obs) {
        this.currentStrength = obs.currentStrength;
        this.canMove = obs.canMove;
        this.ineffective = obs.ineffective;
        if (!this.ineffective && obs.hex!=="fog") {
            let hex = Map.hexIndex[obs.hex];
            this.setHex(hex);
        }
        else
            this.remove();
    }   
    
    Unit.Unit.prototype.placeUnit = function() {
        for (let hexId in Map.hexIndex) {
            let hex = Map.hexIndex[hexId];
            // Check if hex is empty and marked as a setup hex
            if ((!Unit.occupancy[hexId] || !Unit.occupancy[hexId].length) && hex.setup && hex.setup.substring(11)==this.faction) {
                this.setHex(hex);
                return;
            }
        }
        throw "No available setup hex for unit";
    }
    
    Unit.toPortable = function() {
        let portable_units = [];
        for (let unit of Unit.units) {
            portable_units.push( unit.portableCopy() );
        }
        return portable_units;
    }
    
    Unit.fromPortable = function(pUnits,unitMouseDownHandler) {
        Unit.units = [];
        for (let pUnit of pUnits) {
            let param = {};
            param.type = pUnit.type;        
            param.echelon = pUnit.echelon;
            param.name = pUnit.name;
            param.longName = pUnit.longName;
            param.uniqueId = pUnit.uniqueId;
            param.faction = pUnit.faction;
            param.currentStrength = pUnit.currentStrength;
            param.fullStrength = pUnit.fullStrength;
            param.homeOrgId = pUnit.homeOrgId;
            param.taskOrgId = pUnit.taskOrgId;
            let unit = new Unit.Unit(param);
            Unit.units.push( unit );
            if (pUnit.hex) {
                unit.setHex( Map.hexIndex[ pUnit.hex ] );
                SVGUnitSymbol.create(unit,unitMouseDownHandler);
            }
        }
    }

    // As compared to fromPortable, substitutes arbitrary values for unknown fields
    Unit.fromPortable2 = function(pUnits,unitMouseDownHandler) {
        Unit.units = [];
        for (let pUnit of pUnits) {
            let param = {};
            param.type = pUnit.type; //
            param.echelon = "regiment"; //
            param.name = "1"; //
            param.longName = pUnit.longName; //
            param.uniqueId = pUnit.faction+" "+pUnit.longName;
            param.faction = pUnit.faction;
            param.currentStrength = pUnit.currentStrength;
            param.fullStrength = 100; //
            param.homeOrgId = null; //
            param.taskOrgId = null; //
            let unit = new Unit.Unit(param);
            Unit.units.push( unit );
            if (pUnit.hex) {
                unit.setHex( Map.hexIndex[ pUnit.hex ] );
                SVGUnitSymbol.create(unit,unitMouseDownHandler);
            }
        }
    }
    
}())