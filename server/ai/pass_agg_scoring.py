from  . import scoring
import map

WAIT_PREFERENCE = 0.001

class AI(scoring.AI):
    def __init__(self, role, kwargs={}):
        super().__init__(role,kwargs)
        self.mode = kwargs.get("mode",None)
        self.score_is_Q = kwargs.get("score_is_Q", True)
        if self.score_is_Q:
            self.score_fn = self.score_pseudo_q
        else:
            self.score_fn = self.score_state
    def getPosture(self):
        if self.mode=="pass":
            return "defense"
        elif self.mode=="agg":
            return "attack"
        str_red = 0
        str_blue = 0
        for unt in self.unitData.units():
            if unt.ineffective:
                continue
            if unt.faction=="red":
                str_red += unt.currentStrength
            elif unt.faction=="blue":
                str_blue += unt.currentStrength
        if self.role=="red" and str_red>=str_blue:
            posture = "attack"
        elif self.role=="blue" and str_blue>=str_red:
            posture = "attack"
        else:
            posture = "defense"
        return posture 
    def pass_score(self,state,posture):
        worst_score = float("inf")
        units = self.all_unmoved_units(state)
        for unt in units:
            score = self._scoreHex(state, unt.hex, posture)
            worst_score = min(worst_score, score)
        return worst_score
    def score_pseudo_q(self,game,state,action):
        # Due to scoring.py logic, will randomly choose between equal
        #   score hexes, unlike original pass agg, which favors the
        #   first hex computed
        posture = self.getPosture()
        if action["type"] == "fire":
            return 10.0 # All targets are equally good to pass-agg
        elif action["type"] == "move":
            return self._scoreHex(state, action["destination"], posture)
        elif action['type'] == "wait":
            actor = action["mover"]
            return self._scoreHex(state, actor.hex, posture) + WAIT_PREFERENCE
        elif action['type'] == "pass":
            return self.pass_score(state, posture) # Add WAIT_PREFERENCE here?
        raise ValueError(f'Unknown action type: {action["type"]}')
    def _scoreHex(self, state, hex, posture):
        score = 1/(1+self._hexDistanceToCities(state, hex))
        if posture=="attack":
            score += 1/(1+self._hexDistanceToOpfor(hex))
        return score
    def _hexDistanceToOpfor(self, hex):
        xA = hex.x_offset
        yA = hex.y_offset
        closest = None
        closest_dist = float('inf')
        if not self.unitData.units():
            return float('inf')
        for target in self.unitData.units():
            if target.faction == self.role or target.ineffective or not target.hex:                 
                continue
            xB = target.hex.x_offset
            yB = target.hex.y_offset
            dist = map.hexDistance(xA,yA,xB,yB)
            if dist < closest_dist:
                closest_dist = dist
                closest = target
        return closest_dist
    def _hexDistanceToCities(self, state, hex):
        xA = hex.x_offset
        yA = hex.y_offset
        closest_dist = float('inf')
        statusData = state["status"]
        if statusData['cityOwner']:
            for city_id in statusData['cityOwner']:
                xB = self.mapData.hexIndex[city_id].x_offset
                yB = self.mapData.hexIndex[city_id].y_offset
                dist = map.hexDistance(xA,yA,xB,yB)
                if dist < closest_dist:
                    closest_dist = dist  
        return closest_dist
    def score_state(self,game,state,action):
        # Will shoot target that gains most points, unlike original pass agg
        posture = self.getPosture()
        unitData = self.unitData_from_state(state)
        atlatl_score = self.score_sign * state["status"]["score"]
        #print(f'atlatl score {atlatl_score}')
        position_score = 0
        for unt in state["units"]:
            if unt["faction"]!=self.role or unt["ineffective"]:
                continue
            hex = self.mapData.hexIndex[unt["hex"]]
            delta = self._scoreHex(state, hex, posture)
            #print(f'{unt["faction"]} {unt["longName"]} {unt["hex"]} {delta}')
            position_score += delta
        return atlatl_score + position_score
