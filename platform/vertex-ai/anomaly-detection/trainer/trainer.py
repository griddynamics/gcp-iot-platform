import numpy as np
import os
import json
import re
import torch
from torch.utils.data import DataLoader
from typing import Dict, Optional #, Literal
from torch import nn


class Trainer:
    
    def __init__(self, experiment_name: str, model: nn.Module, optimizer: nn.Module, loss: nn.Module, parameters: Dict,
                 train_loader: torch.utils.data.DataLoader, val_loader: Optional[torch.utils.data.DataLoader] = None):
        self.experiment_name = experiment_name  # works also as save_folder
        if not os.path.exists(self.experiment_name):
            os.mkdir(experiment_name)

        self.optimizer = optimizer # ??
        self.loss_function = loss
        self.train_loader = train_loader
        self.val_loader = val_loader
        
        self.model = model
        self.model.zero_grad()
        self.model.eval()
        
        self.epoch = -1  # not trained
        self.history = { 'train_loss': [], 'val_loss': [] }
        self.best_epoch = -1

    def train_one_epoch(self):
        self.model.train()
        running_loss = 0.
        i = 0
        self.epoch += 1 
        for x, y in self.train_loader:
            i += 1
            self.model.zero_grad()
            yhat = self.model(x.float())
            loss = self.loss_function(y.float(), yhat)
            loss.backward()
            self.optimizer.step()
            running_loss += loss.detach().cpu().numpy().item()
        self.history['train_loss'].append(running_loss / (i * self.train_loader.batch_size))
        print("Training loss is:", self.history['train_loss'][-1])
        return self.history['train_loss'][-1]
    
    def validate(self, test_loader=None):
        """Assesses model metrics to check model quality on validation or test datasets"""
        # test_loader - loader for unseen data to use instead 
        self.model.eval()
        if test_loader is None:
            loader = self.val_loader 
        else: 
            loader = test_loader
            print('Testing model on the unseen data')
        assert loader is not None, "val_loader is required to validate the model"
        with torch.no_grad():
            running_loss = 0.
            i = 0
            for x, y in loader:
                i += 1
                yhat = self.model(x.float())
                loss = self.loss_function(y.float(), yhat)
                running_loss += loss.cpu().numpy().item()
        res_loss = running_loss / ((i-1) * loader.batch_size + len(x))
        print("test/val loss is:", res_loss)
        if test_loader is None:
            self.history['val_loss'].append(res_loss)
        return res_loss
        
    def train(self, epochs, early_stopping=5):            
        for e in range(epochs):
            self.train_one_epoch()
            if self.val_loader is not None:
                l_err = self.validate()
                if early_stopping and (self.best_epoch + early_stopping <= self.epoch):
                    print(f"Early stopped at epoch #{self.epoch}")
                    self.save_checkpoint(stage='after')
                    break
                elif self.history['val_loss'][self.best_epoch] > l_err or self.best_epoch == -1:
                    print(f"New best model at epoch #{self.epoch}")
                    self.best_epoch = self.epoch
                    self.save_checkpoint(stage='intermediate')
        self.save_checkpoint(stage='after')

    def clean_models(self, number_left=3):
        """Remove all but `number_left` best intermediate checkpoints"""
        checkpoints = [os.path.join(self.experiment_name, f) for f in os.listdir(self.experiment_name) if re.match(r'checkpoint\d+\.pt', f)]
        to_delete = sorted(checkpoints)[:-number_left]
        for old_checkpoint in to_delete:
            os.remove(os.path.join(self.experiment_name, old_checkpoint))

    def save_checkpoint(self, stage: str = 'intermediate'): #
        assert stage in ['intermediate', 'after'], 'Stage must be in [\'intermediate\', \'after\']'
        name = f'checkpoint'
        if stage == 'intermediate':
            name += f"{self.epoch:04}"
        name += '.pt'
        
        torch.save({
            'model_state_dict': self.model.state_dict(),
            'optimizer_state_dict': self.optimizer.state_dict(),
            'loss_state_dict': self.loss_function.state_dict(),
            'history': self.history,
        }, os.path.join(self.experiment_name, name))
        
        if stage == 'after':
            bounds = self.get_residuals_bounds()
            with open(os.path.join(self.experiment_name, 'config.json'),'w') as f:
                json.dump({
                    'experiment_name': self.experiment_name,
                    'epoch': self.epoch,
                    'loss': str(self.loss_function),
                    'train_dataset': str(self.train_loader.dataset),
                    'val_dataset': str(self.val_loader.dataset),
                    'best_epoch': self.best_epoch,
                    'best_val_loss': self.history['val_loss'][self.best_epoch],
                    'last_train_loss': self.history['train_loss'][-1],
                    'input_size': self.train_loader.dataset.points_before,
                    'mean': self.train_loader.dataset._mean,
                    'std': self.train_loader.dataset._std,
                    'bounds': bounds,
                    'period': self.train_loader.dataset.period
                }, f)            

    def load_checkpoint(self, folder=None, last: bool = True):
        if folder is None:
            folder = self.experiment_name
        if last:
            name = 'checkpoint.pt'
        else:
            files = [file for file in os.listdir(folder) if re.match(r'checkpoint\d+\.pt', file) is not None]
            name = sorted(files)[-1]
        
        checkpoint = torch.load(os.path.join(folder, name))
        self.model.load_state_dict(checkpoint['model_state_dict'])
        self.optimizer.load_state_dict(checkpoint['optimizer_state_dict'])
        self.loss_function.load_state_dict(checkpoint['loss_state_dict'])
        self.history = checkpoint['history']
        
        if os.path.exists(os.path.join(folder, 'config.json')):
            with open(os.path.join(folder, 'config.json')) as f:
                config = json.load(f)
            self.experiment_name = config['experiment_name']
            self.epoch = config['epoch']
            self.best_epoch = config['best_epoch']

    def get_residuals_bounds(self, confidence: float = 0.95, test_loader: Optional[DataLoader] = None):
        """Calculates expected confidence interval for model ouptut based on residuals and given confidence rate"""
        # TODO Room for improvement: bootstrapping aproach
        lower_q = (1. - confidence) / 2
        upper_q = 1. - lower_q
        self.model.eval()
        residuals = []
        if test_loader is None:
            loader = self.val_loader 
        else: 
            loader = test_loader
            print('getting residuals on the unseen data')
        assert loader is not None, "val_loader is required to validate the model"
        with torch.no_grad():
            for x, y in loader:
                yhat = self.model(x.float())
                residuals.append(yhat.cpu().numpy() - y.cpu().numpy())
        residuals = np.concatenate(residuals, axis=0)
        boundaries = np.quantile(residuals, [lower_q, upper_q])
        lower_bound_r, upper_bound_res = boundaries[0], boundaries[1]
        return lower_bound_r, upper_bound_res

    @staticmethod
    def seed_all(seed: int = 42):
        import random
        random.seed(seed)
        np.random.seed(seed)
