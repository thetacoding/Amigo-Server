"""Schemas for intent classifier capability."""

from __future__ import annotations

from pydantic import BaseModel, Field


class IntentScoreItem(BaseModel):
    """Single intent score item."""

    label: str = Field(..., description="Intent label")
    score_max: float = Field(..., description="Max similarity score across utterances")
    score_mean: float = Field(..., description="Mean similarity score across utterances")
    utterance_hits: int = Field(..., description="How many utterances were hit for this label")


class IntentClassifyResult(BaseModel):
    """Normalized intent classification output."""

    text: str = Field(..., description="Original input text")
    intent: str = Field(..., description="Matched intent label or fallback")
    score: float | None = Field(default=None, description="Similarity score")
    matched: bool = Field(..., description="Whether match passed threshold")
    fallback_intent: str = Field(..., description="Fallback intent label")


class IntentClassifyDetailedResult(IntentClassifyResult):
    """Classification output with all candidate scores and threshold."""

    scores: list[IntentScoreItem] = Field(default_factory=list, description="Per-intent scores")
    threshold: float | None = Field(default=None, description="Active threshold")
