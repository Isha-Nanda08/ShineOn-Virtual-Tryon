import abc
import argparse
import os.path as osp
from pprint import pformat
from typing import Union, List, Iterable

import pytorch_lightning as pl
import torch
from tensorboardX import SummaryWriter
from torch.optim import Adam
from torch.utils.data import DataLoader

from datasets import find_dataset_using_name, VVTDataset, CappedDataLoader
from datasets.tryon_dataset import TryonDataset
import logging

logger = logging.getLogger("logger")


class BaseModel(pl.LightningModule, abc.ABC):
    @classmethod
    def modify_commandline_options(cls, parser: argparse.ArgumentParser, is_train):
        # network dimensions
        parser.add_argument(
            "--person_inputs",
            nargs="+",
            required=True,
            help="List of what type of items are passed as person input. Dynamically"
            "sets input tensors and number of channels. See TryonDataset for "
            "options.",
        )
        parser.add_argument(
            "--cloth_inputs",
            nargs="+",
            default=("cloth",),
            help="List of items to pass as the cloth inputs.",
        )
        parser.add_argument("--ngf", type=int, default=64)
        parser.add_argument(
            "--self_attn", action="store_true", help="Add self-attention"
        )
        parser.add_argument(
            "--no_self_attn",
            action="store_false",
            dest="self_attn",
            help="No self-attention",
        )
        parser.add_argument("--flow", action="store_true", help="Add flow")
        return parser

    def __init__(self, hparams, *args, **kwargs):
        if isinstance(hparams, dict):
            hparams = argparse.Namespace(**hparams)
        super().__init__(*args, **kwargs)
        self.hparams = hparams
        self.n_frames_total = hparams.n_frames_total

        self.person_channels = parse_num_channels(hparams.person_inputs)
        self.cloth_channels = parse_num_channels(hparams.cloth_inputs)

        self.isTrain = self.hparams.isTrain
        if not self.isTrain:
            ckpt_name = osp.basename(hparams.checkpoint)
            self.test_results_dir = osp.join(
                hparams.result_dir, hparams.name, ckpt_name, hparams.datamode
            )

    def prepare_data(self) -> None:
        # hacky, log hparams to tensorboard; lightning currently has problems with
        # this: https://github.com/PyTorchLightning/pytorch-lightning/issues/1228
        board: SummaryWriter = self.logger.experiment
        board.add_text("hparams", pformat(self.hparams, indent=4, width=1))

        # ----- actual data preparation ------
        dataset_cls = find_dataset_using_name(self.hparams.dataset)
        self.train_dataset: TryonDataset = dataset_cls(self.hparams)
        logger.info(f"Train dataset initialized: {len(self.train_dataset)} samples.")
        self.val_dataset = self.train_dataset.make_validation_dataset(self.hparams)
        logger.info(f"Val dataset initialized: {len(self.val_dataset)} samples.")

    def train_dataloader(self) -> DataLoader:
        # create dataloader
        train_loader = CappedDataLoader(
            self.train_dataset,
            self.hparams,
        )
        return train_loader

    def val_dataloader(self) -> DataLoader:
        # create dataloader
        val_loader = CappedDataLoader(
            self.val_dataset,
            self.hparams,
        )
        return val_loader

    def test_dataloader(self) -> DataLoader:
        # same loader type. test paths will be defined in hparams
        return self.train_dataloader()

    def configure_optimizers(self):
        optimizer = Adam(self.parameters(), self.hparams.lr)
        scheduler = self._make_step_scheduler(optimizer)
        return [optimizer], [scheduler]

    def _make_step_scheduler(self, optimizer):
        scheduler = torch.optim.lr_scheduler.LambdaLR(
            optimizer,
            lr_lambda=lambda e: 1.0
            - max(0, e - self.hparams.keep_epochs)
            / float(self.hparams.decay_epochs + 1),
        )
        return scheduler


def parse_num_channels(list_of_inputs: Iterable[str]):
    """ Get number of in channels for each input"""
    if isinstance(list_of_inputs, str):
        list_of_inputs = [list_of_inputs]
    channels = sum(
        getattr(TryonDataset, f"{inp.upper()}_CHANNELS") for inp in list_of_inputs
    )
    return channels


def get_and_cat_inputs(batch, names):
    inputs = torch.cat([batch[inp] for inp in names], dim=1)
    return inputs
