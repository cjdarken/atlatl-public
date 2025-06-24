import copy

class Status:
    def __init__(self, scenarioPo, mapData):
        self.all_city_hexes = mapData.getCityHexes()
        if 'score' in scenarioPo:
            score_params = scenarioPo['score']
            self.max_phases = score_params['maxPhases']
            self.total_city_score_per_phase = score_params['cityScore']
            self.score_per_blue_kill = score_params['lossPenalty']
        else:
            self.max_phases = 20
            self.total_city_score_per_phase = 24
            self.score_per_blue_kill = -2
        self.score_per_city_per_phase = 0
        if len(self.all_city_hexes):
            self.score_per_city_per_phase = self.total_city_score_per_phase / len(self.all_city_hexes)
        self.score_per_red_kill = 1
        initialCityStatus = scenarioPo["map"].get("initialCityOwnership","neutral")
        self.ownerD = {} 
        for hex in self.all_city_hexes:
            self.ownerD[hex.id] = initialCityStatus
        self.score = 0
        self.phases_complete = 0
        self.is_terminal = False
        self.on_move = "blue"
        self.setup_mode = False
        if mapData.hasSetupHexes():
            self.setup_mode = True
    @staticmethod
    def fromPortable(statusPo, scenarioPo, mapData):
        result = Status(scenarioPo, mapData)
        result.ownerD = copy.copy(statusPo['cityOwner'])
        result.score = statusPo['score']
        result.phases_complete = statusPo['phaseCount']
        result.is_terminal = statusPo['isTerminal']
        result.on_move = statusPo['onMove']
        result.setup_mode = statusPo['setupMode']
        return result
    def dscoreKill(self, killed_faction, dstrength):
        if killed_faction == "red":
            delta_score = self.score_per_red_kill * dstrength
        else:
            delta_score = self.score_per_blue_kill * dstrength
        self.score += delta_score
        return delta_score
    def _updateCityOwnership(self, unitData):
        for hex in self.ownerD:
            if hex in unitData.occupancy and unitData.occupancy[hex]:
                oneOccupier = unitData.occupancy[hex][0]
                self.ownerD[hex] = oneOccupier.faction
    def endPhaseDeltaCityScore(self, unitData):
        self._updateCityOwnership(unitData)
        delta_score = 0
        for city in self.ownerD:
            if self.ownerD[city] == "blue":
                delta_score += self.score_per_city_per_phase
            elif self.ownerD[city] == "red":
                delta_score -= self.score_per_city_per_phase
        return delta_score
    def matchComplete(self, unitData):
        max_turns_exceeded = self.phases_complete >= self.max_phases
        # count = {"red":0, "blue":0}
        # for unit in unitData.units():
            # if not unit.ineffective:
                # count[unit.faction] += 1
        # return max_turns_exceeded or count["red"]==0 or count["blue"]==0
        return max_turns_exceeded
    def toPortable(self):
        result = {}
        result['cityOwner'] = self.ownerD
        result['score'] = self.score
        result['phaseCount'] = self.phases_complete
        result['isTerminal'] = self.is_terminal
        result['onMove'] = self.on_move
        result['setupMode'] = self.setup_mode
        return result
    def _numUnitsCanMove(self, unitData):
        num = 0
        for unit in unitData.units():
            if unit.canMove and not unit.ineffective:
                num += 1
        return num
    def phaseComplete(self, unitData):
        numUnitsCanMove = self._numUnitsCanMove(unitData)
        if numUnitsCanMove==0:
            return True
        return False
    def advancePhase(self, unitData):
        # Add score for city possession
        if not self.setup_mode:
            delta = self.endPhaseDeltaCityScore(unitData)
            self.score += delta
        if self.setup_mode:
            if self.on_move=="red":
                self.setup_mode = False
        else:
            self.phases_complete += 1
        if self.on_move=="blue":
            self.on_move = "red"
            off_move = "blue"
        else:
            self.on_move = "blue"
            off_move = "red"
        if self.phases_complete == self.max_phases:
            self.is_terminal = True
            return
        unitData.setCanMove(True, self.on_move)
        unitData.setCanMove(False, off_move)
        
    