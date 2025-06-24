import asyncio
import websockets
import json
import argparse

# This AI has a representation of the map and units, and updates the unit representation as it changes
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import map
import unit
import status

class AI:
    def __init__(self, role, kwargs={}):
        self.role = role
        self.mapData = None
        self.unitData = None
    def _hexesToClosestCity(self,hx,cityOwnerD):
        hx_x, hx_y = hx.x_offset, hx.y_offset
        closestDist = float('inf')
        for city_id in cityOwnerD:
            city_hex = self.mapData.hexIndex[city_id]
            dist = map.hexDistance(hx_x,hx_y,city_hex.x_offset,city_hex.y_offset)
            closestDist = min(closestDist,dist)
        return closestDist
    def _setupActions(self,cityOwnerD):
        actions = []
        setup_hexes = self.mapData.getSetupHexes(self.role)
        for hx in setup_hexes:
            hx.closestCityDist = self._hexesToClosestCity(hx,cityOwnerD)
        setup_hexes.sort(reverse=True,key=lambda x:x.closestCityDist)
        units = self.unitData.getFaction(self.role)
        while units:
            moving_unit = units.pop()
            destination = setup_hexes.pop()
            actions.append( (moving_unit.uniqueId, destination.id) )
        return actions
    def process(self, message, response_fn=None):
        msgD = json.loads(message)
        ######### Change this function only to create new AIs ########  
        if msgD['type'] == "parameters":
            self.param = msgD['parameters']
            self.mapData = map.MapData()
            self.unitData = unit.UnitData()
            map.fromPortable(self.param['map'], self.mapData)
            unit.fromPortable(self.param['units'], self.unitData, self.mapData)
            responseD = { "type":"role-request", "role":self.role}
            self.action_queue = []
            self.doSetup = True
        elif msgD['type'] == 'observation':
            obs = msgD['observation']
            if not obs['status']['isTerminal'] and obs['status']['onMove'] == self.role:
                if obs['status']['setupMode']:
                    # Update status and unit data based on observation
                    self.statusData = status.Status.fromPortable(obs["status"], self.param, self.mapData)
                    for unitObs in obs['units']:
                        uniqueId = unitObs['faction'] + " " + unitObs['longName']
                        un = self.unitData.unitIndex[ uniqueId ]
                        un.partialObsUpdate( unitObs, self.unitData, self.mapData )
                    if self.doSetup:
                        self.action_queue = self._setupActions(obs['status']['cityOwner'])
                        self.doSetup = False
                    if len(self.action_queue)>0:
                        unit_id, hex_id = self.action_queue.pop()
                        if hex_id in self.unitData.occupancy and len(self.unitData.occupancy[hex_id])>0:
                            # Setup hex is occupied. Switch the units
                            actionD = {"type":"setup-exchange","mover":unit_id,"friendly":self.unitData.occupancy[hex_id][0].uniqueId}                      
                        else:
                            # Setup hex is empty. Just move there.
                            actionD = {"type":"setup-move","mover":unit_id,"destination":hex_id}
                    else:
                        # All setup actions have been taken
                        actionD = {"type":"pass"}
                else:
                    actionD = {"type":"pass"}
                responseD = {"type":"action", "action":actionD}
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
