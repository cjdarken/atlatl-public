class Game():
    """
    This class specifies the base Game class. To define your own game, subclass
    this class and implement the functions below. This works when the game is
    two-player, adversarial and turn-based.

    Use 1 for player1 and -1 for player2.

    See othello/OthelloGame.py for an example implementation.
    """
    def __init__(self):
        pass

    def getInitBoard(self):
        """
        Returns:
            startBoard: a representation of the board (ideally this is the form
                        that will be the input to your neural network)
        """
        pass

    def getBoardSize(self):
        """
        Returns:
            (x,y): a tuple of board dimensions
        """
        pass

    def getActionSize(self):
        """
        Returns:
            actionSize: number of all possible actions
        """
        pass

    def getNextState(self, board, action):
        """
        Input:
            board: current board
            action: action taken by current player

        Returns:
            nextBoard: board after applying action
        """
        pass

    def getValidMoves(self, board):
        """
        Input:
            board: current board

        Returns:
            validMoves: a binary vector of length self.getActionSize(), 1 for
                        moves that are valid from the current board and player,
                        0 for invalid moves
        """
        pass

    def getGameEnded(self, board):
        """
        Input:
            board: current board

        Returns:
            r: 0 if game has not ended. 1 if current player won, -1 if player lost,
               small non-zero value for draw.
               
        """
        raise Exception('getGameEnded has been replaced by getIsTerminal and getScore')

    def getIsTerminal(self, board):
        """
        Input:
            board: current board

        Returns:
            r: False if game has not ended, otherwise True. 
               
        """
        pass

    def getScore(self, board):
        """
        Input:
            board: current board

        Returns:
            r: Current game score
               
        """
        pass

    def getCanonicalForm(self, board):
        """
        Input:
            board: current board

        Returns:
            canonicalBoard: returns canonical form of board. The canonical form
                            should be independent of player. For e.g. in chess,
                            the canonical form can be chosen to be from the pov
                            of white. When the player is white, we can return
                            board as is. When the player is black, we can invert
                            the colors and return the board.
        """
        pass

    def getSymmetries(self, board, pi):
        """
        Input:
            board: current board
            pi: policy vector of size self.getActionSize()

        Returns:
            symmForms: a list of [(board,pi)] where each tuple is a symmetrical
                       form of the board and the corresponding pi vector. This
                       is used when training the neural network from examples.
        """
        pass

    def getPlayerOnMove(self, board):
        """
        Input:
            board: current board

        Returns:
            player: current player (1 or -1)
        """
        pass

    def stringRepresentation(self, board):
        """
        Input:
            board: current board

        Returns:
            boardString: a quick conversion of board to a string format.
                         Required by MCTS for hashing.
        """
        pass
