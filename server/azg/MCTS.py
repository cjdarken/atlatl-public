import logging
import math
import hashlib

import numpy as np

EPS = 1e-8

log = logging.getLogger(__name__)


class MCTS():
    """
    This class handles the MCTS tree.
    """

    def __init__(self, game, nnet, args):
        self.game = game
        self.nnet = nnet
        self.args = args
        self.Qsa = {}  # stores Q values for s,a (as defined in the paper)
        self.Nsa = {}  # stores #times edge s,a was visited
        self.Ns = {}  # stores #times board s was visited
        self.Ps = {}  # stores initial policy (returned by neural net)

        #self.Es = {}  # stores game.getGameEnded ended for board s
        self.Ts = {}  # stores game.IsTerminal for board s
        self.Ss = {}  # stores game.Score for board s
        self.Vs = {}  # stores game.getValidMoves for board s

    def getActionProb(self, canonicalBoard, temp=1, verbose=False):
        """
        This function performs numMCTSSims simulations of MCTS starting from
        canonicalBoard.

        Returns:
            probs: a policy vector where the probability of the ith action is
                   proportional to Nsa[(s,a)]**(1./temp)
        """
        for i in range(self.args.numMCTSSims):
            self.search(canonicalBoard)

        s = self.game.stringRepresentation(canonicalBoard)
        counts = [self.Nsa[(s, a)] if (s, a) in self.Nsa else 0 for a in range(self.game.getActionSize())]

        if verbose:
            for i in range(len(counts)):
                if counts[i]>0:
                    print(f'{i} {self.game.vectorIndexActionToAtlatl(i, canonicalBoard)} counts {counts[i]}')

        if temp == 0:
            bestAs = np.array(np.argwhere(counts == np.max(counts))).flatten()
            bestA = np.random.choice(bestAs)
            probs = [0] * len(counts)
            probs[bestA] = 1
            return probs

        counts = [x ** (1. / temp) for x in counts]
        counts_sum = float(sum(counts))
        probs = [x / counts_sum for x in counts]
        return probs

    def search(self, actualBoard, verbose=False):
        """
        This function performs one iteration of MCTS. It is recursively called
        till a leaf node is found. The action chosen at each node is one that
        has the maximum upper confidence bound as in the paper.

        Once a leaf node is found, the neural network is called to return an
        initial policy P and a value v for the state. This value is propagated
        up the search path. In case the leaf node is a terminal state, the
        outcome is propagated up the search path. The values of Ns, Nsa, Qsa are
        updated.

        Returns:
            v: the value of the current canonicalBoard to the max player (player 1)
        """

        canonicalBoard = self.game.getCanonicalForm(actualBoard)
        s = self.game.stringRepresentation(canonicalBoard)
        if verbose:
            print( f'searching hash {hashlib.sha256(s.encode("utf-8")).hexdigest()}' )
            print(s)

        if s not in self.Ts:
            self.Ts[s] = self.game.getIsTerminal(canonicalBoard)
            self.Ss[s] = self.game.getScore(canonicalBoard)
        if self.Ts[s]:
            # terminal node
            if verbose:
                print(f'*** Terminal node with value {self.Ss[s]} ***')
            return self.Ss[s]

        if s not in self.Ps:
            # leaf node
            self.Ps[s], v = self.nnet.predict(canonicalBoard)
            if self.args.heuristicEvalFn:
                scenarioPo = canonicalBoard["param"]
                statePo = canonicalBoard["state"]
                blueAI = self.args.blueAI
                redAI = self.args.redAI
                value = self.args.heuristicEvalFn(scenarioPo, statePo, blueAI, redAI)
                if verbose:
                    print(f'Heuristic value estimate: {value}')
                v += value
            valids = self.game.getValidMoves(canonicalBoard)
            self.Ps[s] = self.Ps[s] * valids  # masking invalid moves
            sum_Ps_s = np.sum(self.Ps[s])
            if sum_Ps_s > 0:
                self.Ps[s] /= sum_Ps_s  # renormalize
            else:
                # if all valid moves were masked make all valid moves equally probable

                # NB! All valid moves may be masked if either your NNet architecture is insufficient or you've get overfitting or something else.
                # If you have got dozens or hundreds of these messages you should pay attention to your NNet and/or training process.   
                log.error("All valid moves were masked, doing a workaround.")
                self.Ps[s] = self.Ps[s] + valids
                self.Ps[s] /= np.sum(self.Ps[s])

            self.Vs[s] = valids
            self.Ns[s] = 0
            if verbose:
                print(f'*** Leaf node with estimated value {v} ***')
            return v

        valids = self.Vs[s]
        cur_best = -float('inf')
        best_act = -1

        # pick the action with the highest upper confidence bound
        for a in range(self.game.getActionSize()):
            if valids[a]:
                if (s, a) in self.Qsa:
                    u = self.Qsa[(s, a)] + self.args.cpuct * self.Ps[s][a] * math.sqrt(self.Ns[s]) / (
                            1 + self.Nsa[(s, a)])
                    if verbose:
                        print(f'For action below: N {self.Nsa[(s,a)]} Q {self.Qsa[(s,a)]}')
                else:
                    u = self.args.cpuct * self.Ps[s][a] * math.sqrt(self.Ns[s] + EPS)  # Q = 0 ?
                if verbose:
                    actionPo = self.game.vectorIndexActionToAtlatl(a, canonicalBoard)
                    if verbose:
                        print(f'{actionPo} nnet prob {self.Ps[s][a]} beauty {u}')

                if u > cur_best:
                    cur_best = u
                    best_act = a

        a = best_act
        if verbose:
            actionPo = self.game.vectorIndexActionToAtlatl(a, canonicalBoard)
            print(f'searching child with action {actionPo}')
        next_s = self.game.getNextState(canonicalBoard, a)
        #next_s = self.game.getCanonicalForm(next_s)

        v = self.search(next_s)
        canonical_player = self.game.getPlayerOnMove(canonicalBoard)
        next_player = self.game.getPlayerOnMove(next_s)
        if canonical_player != next_player:
            v = -v

        if verbose:
            print( f'search result for {hashlib.sha256(s.encode("utf-8")).hexdigest()} is value {v}' )

        if (s, a) in self.Qsa:
            self.Qsa[(s, a)] = (self.Nsa[(s, a)] * self.Qsa[(s, a)] + v) / (self.Nsa[(s, a)] + 1)
            self.Nsa[(s, a)] += 1

        else:
            self.Qsa[(s, a)] = v
            self.Nsa[(s, a)] = 1

        self.Ns[s] += 1
        return v
