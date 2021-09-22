import math
import pprint
from dataclasses import dataclass

from pytorch_lightning import Trainer
from pytorch_lightning.loggers import TensorBoardLogger
from pytorch_lightning.trainer import optimizers
from torch.utils.data import DataLoader, Subset

import torch
import torch.nn.functional as F

from proofreader.data.splitter import SplitterDataset
from proofreader.data.augment import Augmentor
from proofreader.model.classifier import Classifier
from proofreader.model.pointnet import PointNetCls
from proofreader.utils.all import get_cpu_count


@dataclass
class AugmentorConfig:
    shuffle: bool = False
    center: bool = False
    rotate: bool = False
    scale: bool = False
    jitter: bool = False
    normalize: tuple = (125, 1250, 1250)


@dataclass
class DatasetConfig:
    dataset: str = 'cremi'
    num_classes: int = 2
    num_slices = [1, 4]
    radius: int = 96
    context_slices: int = 6
    num_points: int = 1024
    batch_size: int = 64
    val_split: float = 0.15
    epoch_multplier: int = 1


@dataclass
class ModelConfig:
    model: str = 'pointnet'
    loss = str = 'nll'
    optimizer: str = 'AdamW'
    dim: int = 256
    learning_rate: float = 1e-3


@dataclass
class TrainerConfig:
    deterministic: bool = True


@dataclass
class ExperimentConfig:
    name: str
    dataset: DatasetConfig = DatasetConfig()
    model: ModelConfig = ModelConfig()
    trainer: TrainerConfig = TrainerConfig()
    augmentor: AugmentorConfig = AugmentorConfig()

    def toString(self):
        d = pprint.pformat(self.dataset)
        m = pprint.pformat(self.model)
        return f'NAME\n{self.name}\nDATASET{d}\nMODEL\n{m}\n'


def build_dataset_from_config(dataset_config: DatasetConfig, aug_config: AugmentorConfig, vols):

    # build augmentor
    augmentor = Augmentor(center=aug_config.center, shuffle=aug_config.shuffle,
                          rotate=aug_config.rotate, scale=aug_config.scale,
                          jitter=aug_config.jitter, normalize=aug_config.normalize)

    # build dataset
    dataset = SplitterDataset(
        vols, dataset_config.num_slices, dataset_config.radius, dataset_config.context_slices,
        num_points=dataset_config.num_points, Augmentor=augmentor, open_vol=True, epoch_multplier=dataset_config.epoch_multplier, shuffle=True, torch=True)

    # split into train and val
    split = math.floor(len(dataset)*dataset_config.val_split)
    train_split = list(range(split, len(dataset)-1))
    val_split = list(range(0, split))
    ds_train = Subset(dataset, train_split)
    ds_val = Subset(dataset, val_split)
    print(f'# train: {len(ds_train)}, # val: {len(ds_val)}')

    return ds_train, ds_val


def build_dataloader_from_config(dataset_config: DatasetConfig, aug_config: AugmentorConfig, vols):

    # build augmentor
    augmentor = Augmentor(center=aug_config.center, shuffle=aug_config.shuffle,
                          rotate=aug_config.rotate, scale=aug_config.scale,
                          jitter=aug_config.jitter, normalize=aug_config.normalize)

    # build dataset
    dataset = SplitterDataset(
        vols, dataset_config.num_slices, dataset_config.radius, dataset_config.context_slices,
        num_points=dataset_config.num_points, Augmentor=augmentor, open_vol=True, epoch_multplier=dataset_config.epoch_multplier, shuffle=True, torch=True)

    # split into train and val
    split = math.floor(len(dataset)*dataset_config.val_split)
    train_split = list(range(split, len(dataset)-1))
    val_split = list(range(0, split))
    ds_train = Subset(dataset, train_split)
    ds_val = Subset(dataset, val_split)
    print(f'# train: {len(ds_train)}, # val: {len(ds_val)}')

    # build dataloader
    cpus = get_cpu_count()
    dl_train = DataLoader(
        dataset=ds_train, batch_size=dataset_config.batch_size, num_workers=cpus, shuffle=True, drop_last=True)
    dl_val = DataLoader(
        dataset=ds_val, batch_size=dataset_config.batch_size, num_workers=cpus, drop_last=True)

    return dl_train, dl_val


def build_model_from_config(model_config: ModelConfig, dataset_config: DatasetConfig):
    if model_config.loss == 'nll':
        loss = F.nll_loss
    elif model_config.loss == 'ce':
        loss = F.cross_entropy

    if model_config.model == 'pointnet':
        backbone = PointNetCls(num_points=dataset_config.num_points)

    model = Classifier(backbone=backbone, loss=loss,
                       learning_rate=model_config.learning_rate)
    return model


def build_full_model_from_config(model_config: ModelConfig, dataset_config: DatasetConfig):
    if model_config.loss == 'nll':
        loss = F.nll_loss
    elif model_config.loss == 'ce':
        loss = F.cross_entropy

    if model_config.model == 'pointnet':
        model = PointNetCls(num_points=dataset_config.num_points)
    if model_config.optimizer == 'AdamW':
        optimizer = torch.optim.AdamW(
            model.parameters(), lr=model_config.learning_rate, betas=(0.9, 0.999), weight_decay=0.05)

    return model, loss, optimizer


def build_trainer_from_config(config: TrainerConfig, args):
    logger = TensorBoardLogger(save_dir='~/ceph/pf', name=args.config)

    trainer = Trainer.from_argparse_args(
        args, deterministic=config.deterministic, log_every_n_steps=100, logger=logger, num_sanity_val_steps=0)
    return trainer


def get_config(name):
    for c in CONFIGS:
        if c.name == name:
            return c
    raise ValueError(f'config {name} not found.')


CONFIGS = [
    ExperimentConfig('default'),
]