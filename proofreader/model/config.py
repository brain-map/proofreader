import math
import pprint
from typing import Tuple
from dataclasses import dataclass
from torch.utils import data

from torch.utils.data import Subset

import torch
import torch.nn.functional as F
import torch.nn as nn

from proofreader.data.splitter import NeuriteDataset, SliceDataset
from proofreader.data.augment import Augmentor
from proofreader.model.pointnet import PointNet
from proofreader.model.curvenet import CurveNet
from proofreader.utils.data import equivariant_shuffle


@dataclass
class AugmentorConfig:
    shuffle: bool = True
    center: bool = True
    rotate: bool = False
    scale: bool = False
    jitter: bool = False
    normalize: tuple = (125, 1250, 1250)


@dataclass
class DatasetConfig:
    dataset: str = 'slice'
    num_slices = 2
    radius: int = 96
    context_slices: int = 3
    num_points: int = 2048
    val_split: float = 0.15
    verbose: bool = False
    add_batch_id: bool = True
    drop_false: bool = True
    path: str = None


@dataclass
class ModelConfig:
    model: str = 'curvenet'
    loss: str = 'nll'
    optimizer: str = 'AdamW'
    learning_rate: float = 1e-3
    num_classes: int = 2
    loss_weights: Tuple = (1.0, 1.0)


@dataclass
class ExperimentConfig:
    name: str
    dataset: DatasetConfig = DatasetConfig()
    model: ModelConfig = ModelConfig()
    augmentor: AugmentorConfig = AugmentorConfig()

    def toString(self):
        d = pprint.pformat(self.dataset)
        m = pprint.pformat(self.model)
        return f'NAME\n{self.name}\nDATASET{d}\nMODEL\n{m}\n'


def load_dataset_from_disk(path):

    # assume its a path
    x, y = torch.load(f'{path}_train.pt')
    train_dataset = SimpleDataset(x, y, shuffle=True)
    x, y = torch.load(f'{path}_val.pt')
    val_dataset = SimpleDataset(x, y, shuffle=True)
    x, y = torch.load(f'{path}_test.pt')
    test_dataset = SimpleDataset(x, y, shuffle=False)
    print(
        f'# train: {len(train_dataset)}, # val: {len(val_dataset)}, # test: {len(test_dataset)}')
    return train_dataset, val_dataset, test_dataset


def build_dataset_from_config(dataset_config: DatasetConfig, aug_config: AugmentorConfig, vols):

    # build augmentor
    augmentor = Augmentor(center=aug_config.center, shuffle=aug_config.shuffle,
                          rotate=aug_config.rotate, scale=aug_config.scale,
                          jitter=aug_config.jitter, normalize=aug_config.normalize)
    # build dataset
    if dataset_config.dataset == 'neurite':
        dataset = NeuriteDataset(
            vols, dataset_config.num_slices, dataset_config.radius, dataset_config.context_slices,
            num_points=dataset_config.num_points, Augmentor=augmentor, open_vol=True,  verbose=dataset_config.verbose, shuffle=True, torch=True)
    elif dataset_config.dataset == 'slice':
        dataset = SliceDataset(vols, dataset_config.num_slices, dataset_config.radius, dataset_config.context_slices,
                               num_points=dataset_config.num_points, Augmentor=augmentor, add_batch_id=dataset_config.add_batch_id,
                               drop_false=dataset_config.drop_false, verbose=False)
        return dataset

    # split into train and val
    split = math.floor(len(dataset)*dataset_config.val_split)
    train_split = list(range(split, len(dataset)-1))
    val_split = list(range(0, split))
    ds_train = Subset(dataset, train_split)
    ds_val = Subset(dataset, val_split)
    print(f'# train: {len(ds_train)}, # val: {len(ds_val)}')

    return ds_train, ds_val


class SimpleDataset(torch.utils.data.Dataset):
    def __init__(self, x, y, shuffle=False):
        if shuffle:
            x, y = equivariant_shuffle(x, y)
        self.x = x
        self.y = y

    def __getitem__(self, i):
        return self.x[i], self.y[i]

    def __len__(self):
        return len(self.x)


def build_full_model_from_config(model_config: ModelConfig, dataset_config: DatasetConfig):
    # loss
    if model_config.loss == 'nll':
        loss = F.nll_loss
    elif model_config.loss == 'bce':
        loss = F.cross_entropy

    # optimizer
    if model_config.model == 'pointnet':
        model = PointNet(num_points=dataset_config.num_points,
                         classes=model_config.num_classes)
    elif model_config.model == 'curvenet':
        model = CurveNet()

    # optimizer
    if model_config.optimizer == 'AdamW':
        optimizer = torch.optim.AdamW(
            model.parameters(), lr=model_config.learning_rate, betas=(0.9, 0.999), weight_decay=0.05)

    return model, loss, optimizer


def get_config(name):
    for c in CONFIGS:
        if c.name == name:
            return c
    raise ValueError(f'config {name} not found.')


CONFIGS = [
    ExperimentConfig('default'),
    ExperimentConfig('pointnet_ns=1_cs=2', model=ModelConfig(model='pointnet'), dataset=DatasetConfig(
        path='/mnt/home/jberman/ceph/pf/dataset/ns=1|r=128|cs=2|np=2048_dataset')),
    ExperimentConfig('pointnet_ns=2_cs=2', model=ModelConfig(model='pointnet'), dataset=DatasetConfig(
        path='/mnt/home/jberman/ceph/pf/dataset/ns=2|r=128|cs=2|np=2048_dataset')),
    ExperimentConfig('curvenet_ns=1_cs=2', model=ModelConfig(model='curvenet'), dataset=DatasetConfig(
        path='/mnt/home/jberman/ceph/pf/dataset/ns=1|r=128|cs=2|np=2048_dataset')),
]
