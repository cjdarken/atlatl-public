import logging

import coloredlogs

from Coach import Coach
from alphazero_game import AtlatlGame as Game
from alphazero_nnet import NNetWrapper as nn
from utils import *
import util

log = logging.getLogger(__name__)

coloredlogs.install(level='DEBUG')  # Change this to DEBUG to see more info.

args = dotdict({
    'numIters': 1,           # Was 1000
    'numEps': 1,              # Was 100. Number of complete self-play games to simulate during a new iteration.
    'tempThreshold': 15,        #
    'updateThreshold': 0.6,     # During arena playoff, new neural net will be accepted if threshold or more of games are won.
    'maxlenOfQueue': 200000,    # Number of game examples to train the neural networks.
    'numMCTSSims': 25,          # Was 25. Number of games moves for MCTS to simulate.
    'arenaCompare': 4,         # Was 40. Number of games to play during arena play to determine if new net will be accepted.
    'cpuct': 50,   # cjd Scale to max score?

    'checkpoint': './temp/',
    'load_model': False,
    'load_folder_file': ('/dev/models/8x100x50','best.pth.tar'),
    'numItersForTrainExamplesHistory': 20,
    'redAI': "pass-agg",
    'blueAI': "pass-agg",
    'heuristicEvalFn': util.playAndScore,
    'scenario_name':"2v1-5x5.scn",
})


def main():
    log.info('Loading %s...', Game.__name__)
    g = Game(args.scenario_name)

    log.info('Loading %s...', nn.__name__)
    nnet = nn(g)

    if args.load_model:
        log.info('Loading checkpoint "%s/%s"...', args.load_folder_file[0], args.load_folder_file[1])
        nnet.load_checkpoint(args.load_folder_file[0], args.load_folder_file[1])
    else:
        log.warning('Not loading a checkpoint!')

    log.info('Loading the Coach...')
    c = Coach(g, nnet, args)

    if args.load_model:
        log.info("Loading 'trainExamples' from file...")
        c.loadTrainExamples()

    log.info('Starting the learning process 🎉')
    c.learn()


if __name__ == "__main__":
    main()
