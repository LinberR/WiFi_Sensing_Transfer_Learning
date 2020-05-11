import torch.nn as nn
import math
import torch.utils.model_zoo as model_zoo
import DAN.mmd as mmd
import torch


class DANNet(nn.Module):
    def __init__(self, config):
        super(DANNet, self).__init__()
        self.sharedNet = SharedNet(config)
        self.cls_fc = nn.Linear(128, config['n_class'])

    def forward(self, source, target):
        loss = 0
        source = self.sharedNet(source)
        if self.training == True:
            target = self.sharedNet(target)
            # loss += mmd.mmd_rbf_accelerate(source, target)
            loss += mmd.mmd_rbf_noaccelerate(source, target)

        source = self.cls_fc(source)
        # target = self.cls_fc(target)

        return source, loss


class SharedNet(nn.Module):
    def __init__(self, config):
        super(SharedNet, self).__init__()
        self.config = config

        if self.config['model_type'] == 'lstm':
            # lstm
            self.bidirectional = True
            self.num_layers = 2
            self.base_network = nn.LSTM(input_size=config['input_feature'], hidden_size=config['hidden_size'],
                                        num_layers=self.num_layers, bidirectional=self.bidirectional,
                                        dropout=0.5, batch_first=True)
            if self.bidirectional:
                self.bottleneck = nn.Linear(config['hidden_size'] * 2, 128)
            else:
                self.bottleneck = nn.Linear(config['hidden_size'], 128)
        elif self.config['model_type'] == 'conv1d':
            # conv1d
            self.base_network = nn.Sequential(
                nn.Conv1d(in_channels=180,out_channels=128, kernel_size=8, padding_mode='circular'),
                nn.BatchNorm1d(num_features = 128),
                nn.ReLU(),
                nn.Conv1d(in_channels=128, out_channels=256, kernel_size=5, padding_mode='circular'),
                nn.BatchNorm1d(num_features = 256),
                nn.ReLU(),
                nn.Conv1d(in_channels=256, out_channels=128, kernel_size=3, padding_mode='circular'),
                nn.BatchNorm1d(num_features = 128),
                nn.ReLU(),
                nn.AdaptiveAvgPool1d(output_size = 128)
            )
        else:
            # conv
            self.base_network = nn.Sequential(
                nn.Conv2d(1, 16, kernel_size=3),
                nn.MaxPool2d(kernel_size=2, stride=2),
                nn.ReLU(),
                nn.Conv2d(16, 32, kernel_size=3),
                nn.MaxPool2d(kernel_size=2, stride=2),
                nn.ReLU(),
                nn.Conv2d(32, 64, kernel_size=3),
                nn.MaxPool2d(kernel_size=2, stride=2),
                nn.ReLU(),
            )
            self.bottleneck = nn.Linear(config['batch_size'] * 3680, 128)

    def forward(self, input):
        # lstm
        if self.config['model_type'] == 'lstm':
            x, _ = self.base_network(input)
            output = self.bottleneck(x[:, -1, :])
        elif self.config['model_type'] == 'conv1d':
            # conv1d
            x = self.base_network(input)
            output = x.view(self.config['batch_size'], -1)
        else:
            # conv
            x = self.base_network(input)
            x = x.view(self.config['batch_size'], -1)
            output = self.bottleneck(x)
        return output
