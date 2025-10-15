#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Mock pour la bibliothèque torch.

Ce module fournit des mocks pour les fonctionnalités de torch utilisées dans les tests.
"""

from unittest.mock import MagicMock
import numpy as np

# Classes et fonctions de base
tensor = lambda data: np.array(data) if hasattr(data, "__iter__") else data
nn = MagicMock()
cuda = MagicMock()
device = MagicMock()


# Fonction no_grad
class NoGrad:
    def __enter__(self):
        return None

    def __exit__(self, *args):
        pass


def no_grad():
    return NoGrad()


# Fonction pour simuler le chargement d'un modèle
def load(path, map_location=None):
    return MagicMock()


# Fonction pour simuler la sauvegarde d'un modèle
def save(obj, path):
    pass


# Classes pour les modèles
class Module:
    def __init__(self):
        self.training = True

    def __call__(self, *args, **kwargs):
        return tensor([0.1, 0.2, 0.3, 0.4])

    def train(self, mode=True):
        self.training = mode
        return self

    def eval(self):
        self.training = False
        return self

    def to(self, device):
        return self

    def parameters(self):
        return []


# Fonctions d'activation
def relu(x):
    return np.maximum(0, x) if isinstance(x, np.ndarray) else max(0, x)


def softmax(x, dim=None):
    if isinstance(x, np.ndarray):
        exp_x = np.exp(x - np.max(x, axis=dim, keepdims=True))
        return exp_x / np.sum(exp_x, axis=dim, keepdims=True)
    else:
        return [0.1, 0.2, 0.3, 0.4]


# Classes pour les couches
class Linear(Module):
    def __init__(self, in_features, out_features, bias=True):
        super().__init__()
        self.in_features = in_features
        self.out_features = out_features
        self.bias = bias


class Conv2d(Module):
    def __init__(self, in_channels, out_channels, kernel_size, stride=1, padding=0):
        super().__init__()
        self.in_channels = in_channels
        self.out_channels = out_channels
        self.kernel_size = kernel_size
        self.stride = stride
        self.padding = padding


# Classes pour les optimiseurs
class Optimizer:
    def __init__(self, params, lr=0.01):
        self.params = params
        self.lr = lr

    def zero_grad(self):
        pass

    def step(self):
        pass


class Adam(Optimizer):
    def __init__(self, params, lr=0.001, betas=(0.9, 0.999), eps=1e-8, weight_decay=0):
        super().__init__(params, lr)
        self.betas = betas
        self.eps = eps
        self.weight_decay = weight_decay


# Classes pour les fonctions de perte
class CrossEntropyLoss(Module):
    def __init__(self, weight=None, reduction="mean"):
        super().__init__()
        self.weight = weight
        self.reduction = reduction


# Configuration de nn
nn.Module = Module
nn.Linear = Linear
nn.Conv2d = Conv2d
nn.CrossEntropyLoss = CrossEntropyLoss
nn.functional = MagicMock()
nn.functional.relu = relu
nn.functional.softmax = softmax

# Version simulée
__version__ = "2.0.1"
