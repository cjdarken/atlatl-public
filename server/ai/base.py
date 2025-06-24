import json
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import map
import unit
import status
from game import Game

class AI:
    def __init__(self, role, kwargs={}):
        self.role = role
        self.scenarioPo = None
        self.mapData = None
        self.unitData = None
        self.best_action_list = []
        self.heuristic_score_scale = 100.0
        self.skipSetup = True
    def scenario_available(self):
        return
    def process(self, message, response_fn=None):
        msgD = json.loads(message)
        ######### Change this function only to create new AIs ########  
        if msgD['type'] == "parameters":
            self.scenarioPo = msgD['parameters']
            self.game = Game(self.scenarioPo)
            self.mapData = map.MapData()
            self.unitData = unit.UnitData()
            map.fromPortable(self.scenarioPo['map'], self.mapData)
            unit.fromPortable(self.scenarioPo['units'], self.unitData, self.mapData)
            self.scenario_available()
            responseD = { "type":"role-request", "role":self.role }
        elif msgD['type'] == 'observation':
            obs = msgD['observation']
            self.obs = obs
            if not obs['status']['isTerminal'] and obs['status']['onMove'] == self.role:
                if obs['status']['setupMode'] and self.skipSetup:
                    responseD = { "type":"action", "action":{"type":"pass"} }
                else:
                    self.statusData = status.Status.fromPortable(obs["status"], self.scenarioPo, self.mapData)
                    if not self.best_action_list:
                        state = {}
                        state["status"] = obs["status"]
                        for unitObs in obs['units']:
                            uniqueId = unitObs['faction'] + " " + unitObs['longName']
                            un = self.unitData.unitIndex[ uniqueId ]
                            un.partialObsUpdate( unitObs, self.unitData, self.mapData )
                        state["units"] = self.unitData.toPortable()
                        self.best_action_list = self.findBestActions(self.game, state)
                    responseD = { "type":"action", "action":self.best_action_list.pop() }
            else:
                responseD = None # State is terminal or it's not our move
        elif msgD['type'] == 'reset':
            responseD = None
        if responseD:
            return json.dumps(responseD)
  