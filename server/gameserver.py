# Game server. Messages accepted only for on-move player, and player-specific
# observations are broadcast. 
#
# GameServer(game_dispenser, client_functions, 
#            first_player_role="blue", second_player_role="red", 
#            request_role_messageO={"type":"request-role"}, 
#            ip="127.0.0.1", port="9999", openSocket=False, verbose=False)
#
# client functions take and return strings, which code JSON Objects.
#
# game_dispenser supports get_next_game() method
#
# The dispensed game must implement the following methods:
#   players()
#   observation(state, player)
#   initial_state()
#   score(state)
#   max_player()
#   on_move(state)
#   is_terminal(state)
#   legal_actions(state)
#   is_legal(state, action)
#   transition(state, action)
#   parameters()
#
# New clients are sent the game parameters (fixed over the course of play). Client 
# must respond with a role-request (either blue or red). Players are sent an observation, 
# then the on-move player must respond with an action message, and then another observation 
# is sent. If the action message contains a debug property, it is appended to the next observation.

# Stops processing when special pause message received

from messageserver import MessageServer
from enum import Enum
import json
import asyncio
import sys
import signal
import game_dispenser

class State(Enum):
    ROLE_ASSIGNMENT = 0
    FIRST_PLAYER_TURN = 1
    SECOND_PLAYER_TURN = 2
    GAME_OVER = 3

async def do_exit(gs):
    gs.close_logs()
    asyncio.get_event_loop().stop()
    await asyncio.sleep(0)
    sys.exit(0)

async def do_get_next_game(gs):
    gs.game = gs.game_dispenser.get_next_game()
    gs.game_state = gs.game.initial_state()
    param = gs.game.parameters()
    await gs.message_server.broadcast({'type':'parameters', 'parameters':param})
    gs.state = State.ROLE_ASSIGNMENT
    gs.clear_roles()
    if gs.blue_logfile:
        gs.log_blue_param()
    if gs.red_logfile:
        gs.log_red_param()

def message_handler_factory(game_server):   
    async def message_handler(messageO, clientw, mserver):
        gs = game_server
        if messageO['type']=="gym-pause":
            asyncio.get_event_loop().stop()
            return  ### FIX Where does control go now? Presumably to where loop was set running.
        if messageO['type']=='next-game-request':
            await do_get_next_game(gs)
        elif game_server.state==State.ROLE_ASSIGNMENT:
            if messageO['type']!='role-request':
                raise Exception(f'Only role requests are valid during role assignment')
            role = messageO['role']
            gs.auto_next_game = messageO.get('auto_next_game',True)
            if role!=gs.first_player_role and role!=gs.second_player_role:
                raise Exception(f'Unknown role {role} requested')
            game_server.assign_role(clientw, role)
            if gs.first_player_role in gs.roleToClient and gs.second_player_role in gs.roleToClient:
                game_server.state = State.FIRST_PLAYER_TURN
                await gs.send_observations()
        elif messageO['type']=='reset-request':
            await gs.reset()
            await gs.message_server.broadcast( {"type":"reset"} )
        elif game_server.state==State.FIRST_PLAYER_TURN:
            if game_server.clientIdToRole[clientw.id]!=game_server.first_player_role:
                raise Exception(f'Only first player should send messages during the first player turn. Offending message {messageO}')
            if messageO['type']!='action':
                raise Exception(f'Only action messages should be sent during player turns. Bad message: {messageO}')
            gs.game_state = gs.game.transition(gs.game_state, messageO["action"])
            await gs.send_observations(messageO.get("debug"))
            # go to new state
            if gs.game.is_terminal(gs.game_state):
                gs.state = State.GAME_OVER
                if gs.n_reps >= 0:  # gs.n_reps==-1 is used for Gym emulation
                    print(gs.game.score(gs.game_state))
                gs.reps_done += 1
                if gs.n_reps>0 and gs.reps_done==gs.n_reps:
                    await do_exit(gs)
                elif gs.n_reps>=0 and gs.auto_next_game:
                    await do_get_next_game(gs)
            else:
                if gs.game.on_move(gs.game_state) == gs.second_player_role:
                    gs.state = State.SECOND_PLAYER_TURN
        elif game_server.state==State.SECOND_PLAYER_TURN:
            if game_server.clientIdToRole[clientw.id]!=game_server.second_player_role:
                raise Exception(f'Only second player should send messages during the second player turn')
            if messageO['type']!='action':
                raise Exception(f'Only action messages should be sent during player turns')
            gs.game_state = gs.game.transition(gs.game_state, messageO['action'])
            await gs.send_observations(messageO.get("debug"))
            # go to new state
            if gs.game.is_terminal(gs.game_state):
                gs.state = State.GAME_OVER
                if gs.n_reps >= 0:  # gs.n_reps==-1 is used for Gym emulation 
                    print(gs.game.score(gs.game_state))
                gs.reps_done += 1
                if gs.n_reps>0 and gs.reps_done==gs.n_reps:
                    await do_exit(gs)
                elif gs.n_reps>=0 and gs.auto_next_game:
                    await do_get_next_game(gs)
            else:
                if gs.game.on_move(gs.game_state) == gs.first_player_role:
                    gs.state = State.FIRST_PLAYER_TURN
        else: # State.GAME_OVER
            raise Exception(f'Game is over, should be no more player messages')
     
    return message_handler


def new_client_handler_factory(game_server, request_role_messageO, verbose):
    async def new_client_handler(clientw, mserver):
        param = game_server.game.parameters()
        await clientw.send_to_client({'type':'parameters', 'parameters':param}, verbose)
    return new_client_handler

# Server for two player games
class GameServer:
    def __init__(self, game_dispenser, client_functions, first_player_role="blue", second_player_role="red", request_role_messageO={"type":"request-role"}, ip="127.0.0.1", port="9999", open_socket=False, n_reps=0, verbose=False, blue_log=None, red_log=None):
        self.state = State.ROLE_ASSIGNMENT
        self.game_dispenser = game_dispenser
        self.game = game_dispenser.get_next_game()
        self.game_state = self.game.initial_state()
        self.first_player_role = first_player_role
        self.second_player_role = second_player_role
        self.n_reps = n_reps
        self.reps_done = 0
        self.auto_next_game = True
        message_handler = message_handler_factory(self)
        new_client_handler = new_client_handler_factory(self, request_role_messageO, verbose)
        self.message_server = MessageServer(client_functions, message_handler, new_client_handler, ip, port, open_socket, verbose)
        self.clientIdToRole = {}
        self.roleToClient = {}
        self.blue_logfile = None
        self.red_logfile = None
        if blue_log:
            self.blue_logfile = open(blue_log,"w")
            self.blue_logfile.write("replayData = [\n")
            self.log_blue_param()
        if red_log:
            self.red_logfile = open(red_log,"w")
            self.red_logfile.write("replayData = [\n")
            self.log_red_param()
        def signal_handler(sig, frame):
            print('gameserver received interrupt signal')
            self.close_logs()
            asyncio.get_event_loop().stop()
            sys.exit(0)
        signal.signal(signal.SIGINT, signal_handler)
    def observation_message(self, role):
        obs = self.game.observation(self.game_state, role)
        return {'type':'observation', 'observation':obs}
    def log_blue_param(self):
        param = self.game.parameters()
        self.log_blue({'type':'parameters', 'parameters':param})
    def log_red_param(self):
        param = self.game.parameters()
        self.log_red({'type':'parameters', 'parameters':param})
    def log_blue(self, msgO):
        self.blue_logfile.write("'"+json.dumps(msgO)+"',\n")
    def log_red(self, msgO):
        self.red_logfile.write("'"+json.dumps(msgO)+"',\n")
    def close_logs(self):
        # Close red and blue logs
        if self.blue_logfile:
            self.blue_logfile.write("]\n")
            self.blue_logfile.close()
        if self.red_logfile:
            self.red_logfile.write("]\n")
            self.red_logfile.close()
    async def reset(self):
        self.state = State.FIRST_PLAYER_TURN
        self.game_state = self.game.initial_state()
        await self.send_observations() 
    def run(self):
        self.message_server.run()
    def assign_role(self, clientw, role):
        self.clientIdToRole[clientw.id] = role
        self.roleToClient[role] = clientw
    def clear_roles(self):
        self.roleToClient.pop(self.first_player_role,None)
        self.roleToClient.pop(self.second_player_role,None)
    async def send_observations(self, debug=None):
        role1 = self.first_player_role
        msg1 = self.observation_message(role1)
        if debug:
            msg1["debug"] = debug
        await self.message_server.send(msg1, self.roleToClient[role1])
        role2 = self.second_player_role
        msg2 = self.observation_message(role2)
        if debug:
            msg2["debug"] = debug
        await self.message_server.send(msg2, self.roleToClient[role2])
        if role1=="blue":
            blue_msg = msg1
            red_msg = msg2
        else:
            blue_msg = msg2
            red_msg = msg1
        if self.blue_logfile:
            self.log_blue(blue_msg)
        if self.red_logfile:
            self.log_red(red_msg)        

if __name__=="__main__":
    class RoState:
        class StateType(Enum):
            PLAYER_ONES_MOVE = 1
            PLAYER_TWOS_MOVE = 2
            GAME_OVER = 3
        def __init__(self):
            self.state_type = RoState.StateType.PLAYER_ONES_MOVE
            self.p1_move = None
            self.p2_move = None
            self.score = None
        def clone(self):
            result = RoState()
            result.state_type = self.state_type
            result.p1_move = self.p1_move 
            result.p2_move = self.p2_move
            result.score = self.score
            return result
    class Roshambo:
        @staticmethod
        def players():
            return ['first', 'second']
        @staticmethod
        def observation(state, player):
            if state.state_type == RoState.StateType.PLAYER_ONES_MOVE:
                return {'type':'observation', 'on_move':'first', 'is_terminal':False, 'score':None}
            elif state.state_type == RoState.StateType.PLAYER_TWOS_MOVE:
                return {'type':'observation', 'on_move':'second', 'is_terminal':False, 'score':None}
            else: # Rostate.StateType.GAME_OVER
                return {'type':'observation', 'is_terminal':True, 'score':state.score}
        @staticmethod
        def initial_state():
            return RoState()
        @staticmethod
        def score(state):
            return state.score
        @staticmethod
        def max_player():
            return 'first'
        @staticmethod
        def on_move(state):
            if state.state_type == RoState.StateType.PLAYER_ONES_MOVE:
                return 'first'
            elif state.state_type == RoState.StateType.PLAYER_TWOS_MOVE:
                return 'second'
            else: # game is over
                return None
        @staticmethod
        def is_terminal(state):
            return state.state_type == RoState.StateType.GAME_OVER
        @staticmethod
        def legal_actions(state):
            return ['rock', 'paper', 'scissors']
        @staticmethod
        def is_legal(state, action):
            if Roshambo.is_terminal(state):
                return False
            if action in Roshambo.legal_actions(state):
                return True
            return False
        @staticmethod
        def transition(state, action):
            result = state.clone()
            if state.state_type == RoState.StateType.PLAYER_ONES_MOVE:
                result.p1_move = action
                result.state_type = RoState.StateType.PLAYER_TWOS_MOVE
            elif state.state_type == RoState.StateType.PLAYER_TWOS_MOVE:
                result.p2_move = action
                if result.p1_move == result.p2_move:
                    result.score = 0
                elif result.p1_move=='rock' and result.p2_move=='paper':
                    result.score = -1
                elif result.p1_move=='rock' and result.p2_move=='scissors':
                    result.score = 1  
                elif result.p1_move=='paper' and result.p2_move=='rock':
                    result.score = 1
                elif result.p1_move=='paper' and result.p2_move=='scissors':
                    result.score = -1
                elif result.p1_move=='scissors' and result.p2_move=='rock':
                    result.score = -1
                elif result.p1_move=='scissors' and result.p2_move=='paper':
                    result.score = 1
                result.state_type = RoState.StateType.GAME_OVER
            return result
        @staticmethod
        def parameters():
            return {}
    def client_function_A(message, response_fn=None):
        messageO = json.loads(message)
        if messageO['type']=='parameters':
            role = 'first'
            return json.dumps( {'type':'role-request', 'role':role} )
        elif messageO['type']=='observation':
            obs = messageO['observation']
            if obs['is_terminal']==True:
                return None
            if obs['on_move']=='first':
                return json.dumps( {'type':'action', 'action':'rock'})
        return None
    def client_function_B(message, response_fn=None):
        messageO = json.loads(message)
        if messageO['type']=='parameters':
            role = 'second'
            return json.dumps( {'type':'role-request', 'role':role} )
        elif messageO['type']=='observation':
            obs = messageO['observation']
            if obs['is_terminal']==True:
                return None
            if obs['on_move']=='second':
                return json.dumps( {'type':'action', 'action':'paper'})
        return None
    client_functions = [client_function_A, client_function_B]
    roshambo_dispenser = game_dispenser.ConstantGameDispenser(Roshambo)
    gs = GameServer(roshambo_dispenser, client_functions, "first", "second", verbose=True)
    gs.run()