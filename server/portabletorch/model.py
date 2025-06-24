import torch
from torch import nn
from collections import OrderedDict

class Model(nn.Module):
    def __init__(self):
        super(Model, self).__init__()
        input_dim = 2
        output_dim = 1
        hidden_units_per_layer = 10
        self.layers = OrderedDict()
        layer_name = "mlp1"
        self.layers.update( {layer_name: nn.Sequential(nn.Linear(input_dim,hidden_units_per_layer), nn.ReLU())} )
        for i in range(3):
            layer_name = "mlp"+str(i+2)
            self.layers.update( {layer_name: nn.Sequential(nn.Linear(hidden_units_per_layer,hidden_units_per_layer), nn.ReLU())} )
        self.layers.update({"linear": nn.Linear(hidden_units_per_layer,output_dim)})
        self.nnet = nn.Sequential(self.layers)

    def forward(self,obs):
        return self.nnet(obs)
