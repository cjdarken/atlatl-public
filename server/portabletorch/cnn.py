import hexagdly
import torch
from torch import nn as nn
from collections import OrderedDict

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
    def __init__(self, n_input_channels, mlp_layers = 2, mlp_size = 8000, square_channel_size: int = 5):
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
        mlp_hiddens = [mlp_size] * mlp_layers
        n_flatten = square_channel_size * square_channel_size * convs_per_layer
        mlp_hiddens.insert(0,n_flatten)

        for i in range(len(mlp_hiddens)-1):
            layer_name = "mlp"+str(i+1)
            self.layers.update( {layer_name: nn.Sequential(nn.Linear(mlp_hiddens[i],mlp_hiddens[i+1]), nn.ReLU())} )
       
        layer_name = "linear"
        self.layers.update( {layer_name: nn.Linear(mlp_hiddens[len(mlp_hiddens)-1],1)} )

        self.cnn = nn.Sequential(self.layers)
        #print(f"Model print demo: {self.cnn}")
        #model = self.cnn
        #pytorch_total_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
        #print(f"Parameter count {pytorch_total_params}")
        self.print_toggle = False

    def forward(self, observations: torch.Tensor) -> torch.Tensor:
        if self.print_toggle:
            #print(observations)
            self.print_toggle = False
        return self.cnn(observations)
    
def train(dataloader, model, loss_fn, optimizer):
    size = len(dataloader.dataset)
    model.train()
    sum = 0
    count = 0
    for batch, (X, y) in enumerate(dataloader):
        X, y = X.to(device), y.to(device)

        # Compute prediction error
        pred = model(X)
        pred = torch.squeeze(pred)
        y = torch.squeeze(y)
        loss = loss_fn(pred, y)

        sum += abs(pred-y)
        count += 1

        # Backpropagation
        loss.backward()
        optimizer.step()
        optimizer.zero_grad()

        # if batch % 100 == 0:
        #     loss, current = loss.item(), (batch + 1) * len(X)
        #     print(f"loss: {loss:>7f}  [{current:>5d}/{size:>5d}]")
    print(f'mean absolute error this epoch {sum/count}')
