from torch import nn


class LinearModel(nn.Module):
    
    def __init__(self, input_size):
        super(LinearModel, self).__init__()
        self.lin1 = nn.Linear(input_size, 1)
    
    def forward(self, x):
        return self.lin1(x).squeeze()
