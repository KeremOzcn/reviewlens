"""
Tokenization pipeline wrapping HuggingFace tokenizers for DistilBERT.

Provides both single-text and batch tokenization with truncation/padding,
ready to feed directly into PyTorch DataLoaders.
"""

import os
from typing import Dict, List, Optional, Union

import torch
from transformers import AutoTokenizer

_DEFAULT_MODEL = os.getenv("SENTIMENT_MODEL_NAME", "distilbert-base-uncased")
_MAX_LENGTH = int(os.getenv("TOKENIZER_MAX_LENGTH", "256"))


class ReviewTokenizer:
    """
    Thin wrapper around a HuggingFace tokenizer tailored for review text.

    Attributes:
        model_name: HuggingFace model identifier used to load the tokenizer.
        max_length: Maximum token sequence length (truncated/padded to this).
        tokenizer: Underlying HuggingFace fast tokenizer instance.
    """

    def __init__(
        self,
        model_name: str = _DEFAULT_MODEL,
        max_length: int = _MAX_LENGTH,
    ) -> None:
        self.model_name = model_name
        self.max_length = max_length
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def encode(
        self,
        text: Union[str, List[str]],
        padding: Union[bool, str] = True,
        truncation: bool = True,
        return_tensors: Optional[str] = "pt",
    ) -> Dict[str, torch.Tensor]:
        """
        Tokenize one or more review texts.

        Args:
            text: A single string or list of strings.
            padding: Padding strategy ('max_length', True, False).
            truncation: Whether to truncate to max_length.
            return_tensors: Return format; 'pt' for PyTorch tensors.

        Returns:
            Dict with keys 'input_ids', 'attention_mask' (and optionally
            'token_type_ids' for BERT-based models).
        """
        return self.tokenizer(
            text,
            padding=padding,
            truncation=truncation,
            max_length=self.max_length,
            return_tensors=return_tensors,
        )

    def encode_batch(
        self,
        texts: List[str],
        batch_size: int = 32,
    ) -> List[Dict[str, torch.Tensor]]:
        """
        Tokenize a large list in mini-batches to avoid OOM errors.

        Args:
            texts: Full list of review strings.
            batch_size: Number of texts per tokenization batch.

        Returns:
            List of encoding dicts, one per batch.
        """
        batches = []
        for i in range(0, len(texts), batch_size):
            chunk = texts[i : i + batch_size]
            batches.append(self.encode(chunk))
        return batches

    def decode(self, token_ids: torch.Tensor, skip_special_tokens: bool = True) -> str:
        """
        Decode a tensor of token IDs back to a string.

        Args:
            token_ids: 1-D tensor of integer token IDs.
            skip_special_tokens: Strip [CLS], [SEP], [PAD] tokens.

        Returns:
            Decoded string.
        """
        return self.tokenizer.decode(token_ids, skip_special_tokens=skip_special_tokens)

    @property
    def vocab_size(self) -> int:
        """Number of tokens in the vocabulary."""
        return self.tokenizer.vocab_size

    @property
    def pad_token_id(self) -> int:
        """Token ID used for padding."""
        return self.tokenizer.pad_token_id

    @property
    def cls_token_id(self) -> int:
        """Token ID for the [CLS] classification token."""
        return self.tokenizer.cls_token_id

    @property
    def sep_token_id(self) -> int:
        """Token ID for the [SEP] separator token."""
        return self.tokenizer.sep_token_id


# ---------------------------------------------------------------------------
# Module-level convenience instance (lazy-initialized on first use)
# ---------------------------------------------------------------------------

_default_tokenizer: Optional[ReviewTokenizer] = None


def get_default_tokenizer() -> ReviewTokenizer:
    """
    Return a module-level singleton ReviewTokenizer.

    Initialised lazily on first call so that importing this module does not
    immediately download weights.
    """
    global _default_tokenizer
    if _default_tokenizer is None:
        _default_tokenizer = ReviewTokenizer()
    return _default_tokenizer
