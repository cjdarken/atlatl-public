from utils import *

import argparse
import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim

from alphazero_observation import nnetObservation

import hexagdly

from collections import OrderedDict

class HexBlock(nn.Module):
    def __init__(self, in_channels, out_channels, residual=True):
        super().__init__()
        self.in_channels, self.out_channels = in_channels, out_channels
        self.hexConv2d = hexagdly.Conv2d(in_channels, out_channels, kernel_size=1, stride=1)
        self.relu = nn.ReLU()
        self.residual = residual

    def forward(self, x):
        residual = x
        x = self.hexConv2d(x)
        if self.residual:
            x += residual
        x = self.relu(x)
        return x

class AtlatlNNet(nn.Module):
    def __init__(self, game, args):
        # game params
        self.board_x, self.board_y = game.getBoardSize()
        self.action_size = game.getActionSize()
        self.args = args

        super(AtlatlNNet, self).__init__()

        n_input_channels = 16
        convs_per_layer = 64
        n_residual_layers = 7
        use_residual = True
        linear_dim1 = 512
        linear_dim2 = 1024

        self.layers = OrderedDict()
        self.layers.update( {'conv': HexBlock(n_input_channels, convs_per_layer, residual=False)} )
        for i in range(n_residual_layers):
            layer_name = "resid"+str(i+1)
            self.layers.update( {layer_name: HexBlock(convs_per_layer, convs_per_layer, residual=use_residual)} ) 
        self.layers.update( {'flatten': nn.Flatten()})
        self.cnn = nn.Sequential(self.layers)
        model = self.cnn
        pytorch_total_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
        print(f"Parameter count {pytorch_total_params}")
        self.print_toggle = False

        # Compute shape by doing one forward pass
        with torch.no_grad():
            init_board = game.getInitBoard()
            init_obs = nnetObservation(init_board)
            #print(f'init_obs.shape {init_obs.shape}')
            n_flatten = self.cnn(torch.as_tensor([init_obs]).float()).shape[1] # Ok to wrap init_obs with list?

        self.fc1 = nn.Linear(n_flatten, 1024)
        self.fc_bn1 = nn.BatchNorm1d(1024)

        self.fc2 = nn.Linear(1024, 512)
        self.fc_bn2 = nn.BatchNorm1d(512)

        self.fc_pi = nn.Linear(512, self.action_size)
        mag = 0.001
        nn.init.uniform_(self.fc_pi.weight, a=-mag, b=mag)

        self.fc_v = nn.Linear(512, 1)

    def forward(self, observations: torch.Tensor) -> torch.Tensor:
        if self.print_toggle:
            print(f'observations {observations}')
            self.print_toggle = False

        s = self.cnn(observations)
        s = F.dropout(F.relu(self.fc_bn1(self.fc1(s))), p=0.3, training=True)  # batch_size x 1024
        s = F.dropout(F.relu(self.fc_bn2(self.fc2(s))), p=0.3, training=True)  # batch_size x 512
        features = s

        pi = self.fc_pi(features)
        v = self.fc_v(features)

        return F.log_softmax(pi, dim=1), v

