from game import Game
import random
import time
import json
import operator
import scenario
import torch
from observation import observation

from torch import nn as nn
import hexagdly
from collections import OrderedDict

import sys
sys.path.append("portabletorch")
import portabletorch

class AtlatlDataset(torch.utils.data.Dataset):
    def __init__(self,x_examples,y_examples):
        self.x = torch.tensor(x_examples, dtype=torch.float32)
        self.y = torch.tensor(y_examples, dtype=torch.float32)
    def __len__(self):
        return len(self.x)
    def __getitem__(self,idx):
        return self.x[idx],self.y[idx]
    
class HexBlock(nn.Module):
    def __init__(self, in_channels, out_channels, residual=True):
        super().__init__()
        self.in_channels, self.out_channels = in_channels, out_channels
        self.hexConv2d = hexagdly.Conv2d(in_channels, out_channels, kernel_size=1, stride=1)
        #self.norm = nn.BatchNorm2d(out_channels)
        self.relu = nn.ReLU()
        self.residual = residual

    def forward(self, x):
        residual = x
        x = self.hexConv2d(x)
        #x = self.norm(x)
        if self.residual:
            x += residual
        x = self.relu(x)
        return x

class CNN(nn.Module):
    def __init__(self, n_input_channels, mlp_hiddens = [8000,8000], square_channel_size: int = 5):
        print(f'dlalphabeta.CNN.__init__')
        super(CNN, self).__init__()
        # We assume CxHxW images (channels first)
        n_residual_layers = 6
        convs_per_layer = 128
        self.layers = OrderedDict()
        self.layers.update( {'conv': HexBlock(n_input_channels, convs_per_layer, residual=False)} )
        for i in range(n_residual_layers):
            layer_name = "resid"+str(i+1)
            self.layers.update( {layer_name: HexBlock(convs_per_layer, convs_per_layer, residual=True)} ) 
        self.layers.update( {'flatten': nn.Flatten()})

        # Compute shape by doing one forward pass
        #with torch.no_grad():
        #    n_flatten = self.cnn(torch.as_tensor(observation_space.sample()[None]).float()).shape[1]
        n_flatten = square_channel_size * square_channel_size * convs_per_layer
        mlp_hiddens.insert(0,n_flatten)

        for i in range(len(mlp_hiddens)-1):
            layer_name = "mlp"+str(i+1)
            self.layers.update( {layer_name: nn.Sequential(nn.Linear(mlp_hiddens[i],mlp_hiddens[i+1]), nn.ReLU())} )
       
        layer_name = "linear"
        self.layers.update( {layer_name: nn.Linear(mlp_hiddens[len(mlp_hiddens)-1],1)} )

        self.cnn = nn.Sequential(self.layers)
        print(f"Model print demo: {self.cnn}")
        #model = self.cnn
        #pytorch_total_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
        #print(f"Parameter count {pytorch_total_params}")
        self.print_toggle = False

    def forward(self, observations: torch.Tensor) -> torch.Tensor:
        if self.print_toggle:
            #print(observations)
            self.print_toggle = False
        return self.cnn(observations)
  

def _state_value(game, state, depth_limit, nnValueFn, alpha, beta):
    if game.is_terminal(state):
        return game.score(state)
    if depth_limit==0:
        obs = observation(game, state)
        obs = torch.unsqueeze(obs,0)
        with torch.no_grad():
            value = nnValueFn(obs)
        return value
    if game.on_move(state) == game.max_player():
        best_value = float('-inf')
    else:
        best_value = float('inf')
    for action in game.legal_actions(state):
        child_state = game.transition(state, action)
        child_value = _state_value(game, child_state, depth_limit-1, nnValueFn, alpha, beta)
        if game.on_move(state) == game.max_player():
            if child_value > best_value:
                best_value = child_value
            if best_value >= beta:
                return best_value
            alpha = max(alpha, best_value)
        else:
            if child_value < best_value:
                best_value = child_value
            if best_value <= alpha:
                return best_value
            beta = min(beta, best_value)
    return best_value

def fakeValueFn(state):
    return random.random()

def dlab(game, state, depth_limit, nnValueFn): # returns best action in this state
    alpha = float('-inf')
    beta = float('inf')
    if depth_limit < 1:
        raise ValueError('depth_limit is less than 1, no actions to consider')
    if game.is_terminal(state):
        raise ValueError('Starting state is already terminal, no actions to consider')
    best_action = None
    if game.on_move(state) == game.max_player():
        best_value = float('-inf')
        better_value = operator.gt
    else:
        best_value = float('inf')
        better_value = operator.lt
    action_values = []
    for action in game.legal_actions(state):
        child_state = game.transition(state, action)
        value = _state_value(game, child_state, depth_limit, nnValueFn, alpha, beta)
        action_values.append((action,value))
        if better_value(value, best_value):
            best_value = value
            best_action = action
    return best_action, best_value, action_values

if __name__ == "__main__":
    random.seed(12345)
    stateD = {}
    # scenarioName = "atomic.scn"
    # scenarioName = "column2x3.scn"
    # scenarioName = "column2v1.scn"
    # scenarioName = "Test4.scn"
    # scenarioName = "harder.scn"
    # scenarioName = "solver2v2.scn"
    # scenarioName = "solver3x3.scn"
    # scenarioName = "atomic-city.scn"
    # scenarioName = "rough1v1.scn"
    # scenarioName = "symmetric3x3.scn"
    # scenarioName = "2v1-5x5.scn"
    # scenarioName = "column-5x5-water.scn"


    n_input_channels = 17 # num features as defined in extract-replay-data.py
    nnValueFn = CNN(n_input_channels)

    portable = portabletorch.PortableTorch.load("cnn-save")
    nnValueFn = portable.model
    
    #nnValueFn.load_state_dict(torch.load("cnn.tch",map_location=torch.device('cpu')))
    #nnValueFn = torch.load("cnn.tch")
    #nnValueFn.eval()

    # city-inf-5
    scen_gen = scenario.clear_square_factory(size=5, min_units=2, max_units=4, num_cities=1, scenarioSeed=4025, scenarioCycle=10, balance=False, max_phases=10, fog_of_war=False)
    game = Game(scen_gen())
    
    # scenarioPo = json.load( open("scenarios/"+scenarioName) )
    # game = Game(scenarioPo)

    start = time.time()
    depth_limit = 1
    action, value, avs = dlab(game, game.initial_state(), depth_limit, nnValueFn)
    end = time.time()
    print(f"Game solved in {end-start} seconds")
    print(f"The best action is {action} with value {value}")
    print(f'Action-value list {avs}')
