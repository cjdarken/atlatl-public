from . import base
import random
import json
import unit

def _to_portable(actionO):
    if actionO["type"]=="pass": 
        return actionO
    elif actionO["type"]=="move": 
        mover = actionO["mover"].uniqueId
        hex_id = actionO["destination"].id
        return {"type":"move", "mover":mover, "destination":hex_id}
    elif actionO["type"]=="fire":
        source = actionO["source"].uniqueId
        target = actionO["target"].uniqueId
        return {"type":"fire", "source":source, "target":target}
    
def _to_object(action, unitData, mapData):
    if action["type"]=="pass": 
        return action
    elif action["type"]=="move": 
        mover = unitData.unitIndex[ action["mover"] ]
        hex = mapData.hexIndex[ action["destination"] ]
        return {"type":"move", "mover":mover, "destination":hex}
    elif action["type"]=="fire":
        source = unitData.unitIndex[ action["source"] ]
        target = unitData.unitIndex[ action["target"] ]
        return {"type":"fire", "source":source, "target":target}
        
    


class AI(base.AI):
    def __init__(self, role, kwargs={}):
        super().__init__(role,kwargs)
        self.search_method = kwargs["search"] # fixed, random, greedy, full
        self.score_is_Q = False# For red, more negative is better
        self.score_sign = 1 - 2 * (self.role=="red")
    def unitData_from_state(self, state):
        unitData = unit.UnitData()
        unit.fromPortable(state['units'], unitData, self.mapData)
        return unitData
    def score_fn(self, game, state):
        return 0
    def action_score(self, game, state, action):
        if self.score_is_Q:
            #print(f'action {_to_portable(action)} score {self.score_fn(game,state,action)}')
            return self.score_fn(game,state,action)
        if action["type"] == "wait":
            postaction_state = state # Being compared to states after opponent moves!!!
        else:
            action = _to_portable(action)
            postaction_state = game.transition(state, action)
        score = self.score_fn(game,postaction_state,None)
        #print(f'action_score score {score} state {game.observation(postaction_state,"blue")}\n')
        return score
    def all_nonpass_actions(self, game, state, actor):
        unitData = self.unitData_from_state(state)
        actionOs = []
        for ft in actor.findFireTargets(unitData):
            actionOs.append({"type":"fire","source":actor,"target":ft})
        for mt in actor.findMoveTargets(self.mapData, unitData):
            actionOs.append( {"type":"move", "mover":actor, "destination":mt} )
        return actionOs     
    def all_actions(self, game, state, actor):
        # "wait" means this one unit does nothing. "pass" means all remaining forces do nothing.
        null_action = {"type":"wait","mover":actor}
        if len(self.all_unmoved_units(state))==1:
            null_action = {"type":"pass"}
        return [null_action] + self.all_nonpass_actions(game,state,actor)
    def all_unmoved_units(self, state):
        unitData = self.unitData_from_state(state)
        unts = []
        for unt in unitData.units():
            if unt.faction == self.role and unt.canMove and not unt.ineffective:
                unts.append(unt)
        return unts
    def best_action(self, game, state, actor):
        actions = self.all_actions(game,state,actor)
        best_score = float('-inf')
        best_actions = []
        for action in actions:
            score = self.action_score(game, state, action)
            if score == best_score:
                best_score = score
                best_actions.append(action)
            elif score > best_score:
                best_score = score
                best_actions = [action]
        return random.choice(best_actions)
    def best_action_any_unit(self, game, state):
        units = self.all_unmoved_units(state)
        if not units:
            return {"type":"pass"}
        best_score = float('-inf')
        best_actions = []
        for actor in units:
            for action in self.all_actions(game,state,actor):
                score = self.action_score(game, state, action)
                if score == best_score:
                    best_actions.append(action)
                elif score > best_score:
                    best_score = score
                    best_actions = [action]
        action = random.choice(best_actions)
        if action["type"] == "wait":
            action = {"type":"pass"} # What if some other unit has a better choice than "wait"?
        return action
    def _legalActionSequences(self, game, state, partialSequence=[], verbose=False):     
        # state_str = json.dumps(state).encode()
        # state_hashobj = hashlib.sha1(state_str)
        # state_hex = state_hashobj.hexdigest()
        # print(f'in state {state_hex[:5]}')
        legal_actions = game.legal_actions(state)
        if not legal_actions or state["status"]["onMove"]!=self.role:
            yield state, partialSequence
            return
        for action in legal_actions:
            postaction_state = game.transition(state, action)
            yield from self._legalActionSequences(game,postaction_state,partialSequence+[action],verbose)  
    def best_full_move(self, game, state, verbose=False):
        best_actions = []
        best_score = float("-inf")
        for resulting_state, actions in self._legalActionSequences(game,state):
            actionO = _to_object( actions[-1], self.unitData, self.mapData )
            score = self.score_fn(game, resulting_state, actionO)
            if score > best_score: # Break ties randomly instead?
                best_actions, best_score = actions, score
        best_actions.reverse()
        return best_actions  
    def best_single_unit_action(self, game, state, random_unit=False):
        units = self.all_unmoved_units(state)
        if not units:
            return {"type":"pass"}
        if random_unit: random.shuffle(units)
        for actor in units:
            action = self.best_action(game, state, actor)
            if action["type"] != "wait":
                return action
        return {"type":"pass"}
    def findBestActions(self, game, state):     
        # If fixed, the best action for the next unit is selected
        if self.search_method == "fixed":
            actionO = self.best_single_unit_action(game, state, random_unit=False)
            actions = [ _to_portable(actionO) ]
        # If random, the best action for one random unit is selected
        elif self.search_method == "random":
            actionO = self.best_single_unit_action(game, state, random_unit=True)
            actions = [ _to_portable(actionO) ]
        # If greedy, every single action is scored for all units, then the unit with the highest scored action is moved
        elif self.search_method == "greedy":
            actionO = self.best_action_any_unit(game,state)
            actions = [ _to_portable(actionO) ]
        # If full, every move combination is examined and scored. A full ply of moves is returned.
        elif self.search_method == "full":
            actions = self.best_full_move(game,state)
        return actions
