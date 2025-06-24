range = {
    "infantry" : 1,
    "mechinf" : 1,
    "armor" : 1,
    "artillery" : 2
}

sight = {
    "infantry" : 2,
    "mechinf" : 2,
    "armor" : 2,
    "artillery" : 2
}

pDetect = 1.0

ineffectiveThreshold = 0.50 # 50%

firepower_scaling = 0.5

firepower = {}

firepower["infantry"] = {
    "infantry" : 1.0,
    "mechinf" : 1.0,
    "armor" : 0.5,
    "artillery" : 1.5
}

firepower["mechinf"] = {
    "infantry" : 0.75,
    "mechinf" : 1.0,
    "armor" : 0.75,
    "artillery" : 1.5
}

firepower["armor"] = {
    "infantry" : 0.5,
    "mechinf" : 0.75,
    "armor" : 1.0,
    "artillery" : 1.0
}

firepower["artillery"] = {
    "infantry" : 1.0,
    "mechinf" : 0.75,
    "armor" : 0.5,
    "artillery" : 1.5
}

defensivefp = {}

defensivefp["infantry"] = {
    "infantry" : 0,
    "mechinf" : 0,
    "armor" : 0,
    "artillery" : 0
}

defensivefp["mechinf"] = {
    "infantry" : 0,
    "mechinf" : 0,
    "armor" : 0,
    "artillery" : 0
}

defensivefp["armor"] = {
    "infantry" : 0,
    "mechinf" : 0,
    "armor" : 0,
    "artillery" : 0
}

defensivefp["artillery"] = {
    "infantry" : 0,
    "mechinf" : 0,
    "armor" : 0,
    "artillery" : 0
}

terrain_multiplier = {}

terrain_multiplier["infantry"] = {
    "clear": 1,
    "water": 1,
    "rough": 0.5,
    "unused": 1,
    "marsh": 1,
    "urban": 0.5
}

terrain_multiplier["armor"] = {
    "clear": 1,
    "water": 1,
    "rough": 1,
    "unused": 1,
    "marsh": 2,
    "urban": 1
}

terrain_multiplier["mechinf"] = terrain_multiplier["armor"]

terrain_multiplier["artillery"] = terrain_multiplier["armor"]