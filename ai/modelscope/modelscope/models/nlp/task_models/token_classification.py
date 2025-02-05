# Copyright (c) Alibaba, Inc. and its affiliates.
from typing import Any, Dict

import numpy as np
import torch

from modelscope.metainfo import TaskModels
from modelscope.models.builder import MODELS
from modelscope.models.nlp.task_models.task_model import \
    SingleBackboneTaskModelBase
from modelscope.outputs import OutputKeys, TokenClassifierOutput
from modelscope.utils.constant import Tasks
from modelscope.utils.hub import parse_label_mapping
from modelscope.utils.tensor_utils import (torch_nested_detach,
                                           torch_nested_numpify)

__all__ = ['TokenClassificationModel']


@MODELS.register_module(
    Tasks.token_classification, module_name=TaskModels.token_classification)
@MODELS.register_module(
    Tasks.part_of_speech, module_name=TaskModels.token_classification)
class TokenClassificationModel(SingleBackboneTaskModelBase):

    def __init__(self, model_dir: str, *args, **kwargs):
        """initialize the token classification model from the `model_dir` path.

        Args:
            model_dir (str): the model path.
        """
        super().__init__(model_dir, *args, **kwargs)
        if 'base_model_prefix' in kwargs:
            self._base_model_prefix = kwargs['base_model_prefix']

        # get the num_labels
        num_labels = kwargs.get('num_labels')
        if num_labels is None:
            label2id = parse_label_mapping(model_dir)
            if label2id is not None and len(label2id) > 0:
                num_labels = len(label2id)
            self.id2label = {id: label for label, id in label2id.items()}
        self.head_cfg['num_labels'] = num_labels

        self.build_backbone(self.backbone_cfg)
        self.build_head(self.head_cfg)

    def forward(self, **input: Dict[str, Any]) -> Dict[str, np.ndarray]:
        labels = None
        if OutputKeys.LABEL in input:
            labels = input.pop(OutputKeys.LABEL)
        elif OutputKeys.LABELS in input:
            labels = input.pop(OutputKeys.LABELS)

        outputs = super().forward(input)
        sequence_output = outputs[0]
        logits = self.head.forward(sequence_output)
        loss = None
        if labels in input:
            loss = self.compute_loss(outputs, labels)

        return TokenClassifierOutput(
            loss=loss,
            logits=logits,
            hidden_states=outputs.hidden_states,
            attentions=outputs.attentions,
            offset_mapping=input['offset_mapping'],
        )

    def extract_logits(self, outputs):
        return outputs[OutputKeys.LOGITS].cpu().detach()
