export var Combat = {};

(function() {

Combat.range = {
    "infantry" : 1,
    "mechinf" : 1,
    "armor" : 1,
    "artillery" : 2
};

Combat.firepower = {}

Combat.firepower["mechinf"] = {
    "infantry" : 1.0,
    "mechinf" : 1.0,
    "armor" : 0.5,
    "artillery" : 1.5
};

Combat.firepower["armor"] = {
    "infantry" : 0.5,
    "mechinf" : 1.0,
    "armor" : 0.5,
    "artillery" : 1.5
};

Combat.firepower["artillery"] = {
    "infantry" : 1.0,
    "mechinf" : 1.0,
    "armor" : 0.5,
    "artillery" : 1.5
};



}())