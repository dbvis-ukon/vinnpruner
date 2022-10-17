import torch
import torch.nn as nn
import torch.nn.functional as F

from network.base_model import BaseModel
from network.masked_modules import MaskedLinear, MaskedConv2d

class MaskedAlexNet(BaseModel):
    def __init__(self, num_classes: int = 10, init_scheme=nn.init.xavier_normal_) -> None:
        super(MaskedAlexNet, self).__init__(init_scheme=init_scheme)
        self.features = nn.Sequential(
            MaskedConv2d(3, 64, kernel_size=3, stride=2, padding=1),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(kernel_size=2),
            MaskedConv2d(64, 192, kernel_size=3, padding=1),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(kernel_size=2),
            MaskedConv2d(192, 384, kernel_size=3, padding=1),
            nn.ReLU(inplace=True),
            MaskedConv2d(384, 256, kernel_size=3, padding=1),
            nn.ReLU(inplace=True),
            MaskedConv2d(256, 256, kernel_size=3, padding=1),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(kernel_size=2),
        )
        self.classifier = nn.Sequential(
            nn.Dropout(),
            MaskedLinear(256 * 2 * 2, 4096),
            nn.ReLU(inplace=True),
            nn.Dropout(),
            MaskedLinear(4096, 4096),
            nn.ReLU(inplace=True),
            MaskedLinear(4096, num_classes),
        )

    def forward(self, x):
        x = self.features(x)
        x = x.view(x.size(0), 256 * 2 * 2)
        x = self.classifier(x)
        return x