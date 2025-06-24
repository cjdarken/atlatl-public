import asyncio
import websockets
import json
import argparse
import mctsearch

# This AI has a representation of the map and units, and updates the unit representation as it changes
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import map
import unit
import math

import current_game_access
import time

class AI:
    def __init__(self, role, kwargs={}):
        self.role = role
        self.mapData = None
        self.unitData = None
        self.actionQueue = []
        # The merit constant is scenario specific!!
        game_max_score = 200
        game_min_score = -200
        self.merit_constant = 100 # Arbitrary default value
        self.debug = kwargs["debug"]
        self.max_rollouts = kwargs["max_rollouts"]
    def process(self, message, response_fn=None):
        msgD = json.loads(message)
        ######### Change this function only to create new AIs ########  
        if msgD['type'] == "parameters":
            #self.actionQueue = []
            param = msgD['parameters']
            self.mapData = map.MapData()
            self.unitData = unit.UnitData()
            map.fromPortable(param['map'], self.mapData)
            unit.fromPortable(param['units'], self.unitData, self.mapData)
            nCities = len(self.mapData.getCityHexes())
            maxCityScore = int(nCities>0)*param['score']['cityScore']*param['score']['maxPhases']
            def net_strength(units):
                result = 0
                for unit in units:
                    result += unit.currentStrength
                return result
            red_strength = net_strength(self.unitData.getFaction("red"))
            blue_strength = net_strength(self.unitData.getFaction("blue"))
            max_score = red_strength + maxCityScore
            min_score = param['score']['lossPenalty']*blue_strength - maxCityScore
            self.merit_constant = (max_score-min_score)/math.sqrt(2)
            responseD = { "type":"role-request", "role":self.role}
        elif msgD['type'] == 'observation':
            obs = msgD['observation']
            if obs['status']['onMove'] != self.role:
                self.actionQueue = []
            if not obs['status']['isTerminal'] and obs['status']['onMove'] == self.role:
                if not self.actionQueue:
                    game = current_game_access.get_current_game()
                    start = time.process_time()
                    self.actionQueue = mctsearch.uct_search(game, merit_const=self.merit_constant, max_rollouts=self.max_rollouts, init_state=obs, debug=self.debug)
                    end = time.process_time()
                    if self.debug:
                        print(f'time/move {end-start} rollouts/sec {self.max_rollouts/(end-start)}')
                action = self.actionQueue.pop(0)
                responseD = { "type":"action", "action":action }
            else:
                responseD = None
        elif msgD['type'] == 'reset':
            responseD = None
        if responseD:
            return json.dumps(responseD)
 

async def client(ai, uri):
    async with websockets.connect(uri) as websocket:
        while True:
            message = await websocket.recv()
            print(f"Message received by AI over websocket: {message[:100]}")
            result = ai.process(message)
            if result:
                await websocket.send( result )

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("faction")
    parser.add_argument("--uri")
    args = parser.parse_args()
    
    ai = AI(args.faction)
    uri = args.uri
    if not uri:
        uri = "ws://localhost:9999"
    asyncio.get_event_loop().run_until_complete(client(ai, uri))