from game import Game, statePlusParamHashKey
import random
import json
import time
import pickle

# Blue is max player

class Agenda:
    def __init__(self):
        self.stack = []
    def addState(self, game, state, alpha, beta):
        actionL = game.legal_actions(state)
        if game.on_move(state) == game.max_player():
            val = float('-inf')
        else:
            val = float('inf')
        if game.is_terminal(state):
            val = game.score(state)
        self.push( (state, val, actionL, alpha, beta) )
    def push(self, frame):
        self.stack.append(frame)
    def pop(self):
        return self.stack.pop()
    def isEmpty(self):
        return len(self.stack)==0

def perfectGame(game,memoD):
    state = game.initial_state()
    stateS = statePlusParamHashKey(state, game.scenarioPo)
    value = memoD[stateS]
    print(f"Reconstructing game with value {value}")
    while not game.is_terminal(state):
        mover = game.on_move(state)
        for action in game.legal_actions(state):
            nextState = game.transition(state, action)
            nextStateS = statePlusParamHashKey(nextState, game.scenarioPo)
            if nextStateS in memoD:
                nextValue = memoD[nextStateS]
                if nextValue == value:
                    print(f'{mover} {action}')
                    state = nextState
                    break

def minimax(game, alphaBeta=False):
    agenda = Agenda()
    alpha = float('-inf')
    beta = float('inf')
    agenda.addState( game, game.initial_state(), alpha, beta)
    stateD = {}
    memoD = {}
    stepCounter = 0
    stateCount = 0
    pruneCounter = 0
    while not agenda.isEmpty():
        stepCounter += 1
        state, val, actionL, alpha, beta = agenda.pop()
        stateS = statePlusParamHashKey(state, game.scenarioPo)
        if not stateS in stateD:
            stateD[stateS] = stateCount
            stateCount += 1
        if stepCounter % 10000 == 0:
                print(f'{stepCounter} steps, states visited: {len(stateD.keys())}')
        if game.is_terminal(state) or len(actionL)==0:
            memoD[stateS] = val
            if agenda.isEmpty(): 
                print(f'Solved! {stepCounter} steps, states visited: {len(stateD.keys())} prunes {pruneCounter} value {val}')
                return memoD
            stateParent, valParent, actionLParent, alphaParent, betaParent = agenda.pop()
            if game.on_move(stateParent)==game.max_player():
                valParent = max(valParent, val)
                alphaParent = max(alphaParent, val)
                if alphaBeta and alphaParent > betaParent:
                    pruneCounter += 1
                    actionLParent = [] # Work is effectively finished on parent state
            else:
                valParent = min(valParent, val)
                betaParent = min(betaParent, val)
                if alphaBeta and betaParent < alphaParent:
                    pruneCounter += 1
                    actionLParent = [] # Work is effectively finished on parent state
            agenda.push( (stateParent, valParent, actionLParent, alphaParent, betaParent) )
            continue
        if stateS in memoD:
            agenda.push( (state, memoD[stateS], [], alpha, beta))
            continue
        action = actionL.pop()
        agenda.push( (state, val, actionL, alpha, beta) )
        newState = game.transition(state, action)
        agenda.addState(game, newState, alpha, beta)
    print("Agenda was empty")

if __name__ == "__main__":
    random.seed(12345)
    stateD = {}
    # scenarioName = "atomic.scn"
    # scenarioName = "Test4.scn"
    # scenarioName = "harder.scn" # more than 7 min
    # scenarioName = "solver2v2.scn"
    # scenarioName = "solver3x3.scn" # Takes more than 2 min
    # scenarioName = "atomic-city.scn"
    # scenarioName = "2v1-5x5.scn"
    # scenarioName = "column-5x5-water.scn"
    scenarioName = "solver1v1.scn"
    
    scenarioPo = json.load( open("scenarios/"+scenarioName) )
    game = Game(scenarioPo)
    start = time.time()
    memoD = minimax(game, alphaBeta=True)
    end = time.time()
    print(f"Game solved in {end-start} seconds")
    perfectGame(game, memoD)
    print("Writing solution to file")
    outfile = open("solution.pkl",'wb')
    pickle.dump(memoD,outfile)
    outfile.close()
