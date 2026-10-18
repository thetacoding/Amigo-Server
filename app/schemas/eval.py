"""Unified evaluation gateway schemas."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

from app.schemas.base import AppBaseInfo, DeviceInfo, SessionInfo, SystemSetting, UserInfo

EvalScene = Literal["nlp"]
EvalTask = Literal["intent_classification"]


class EvalInputs(BaseModel):
    """Gateway inputs. `queries` is batch-first; `query` is backward-compatible."""

    query: str | None = Field(default=None, description="Single query input")
    queries: list[str] | None = Field(default=None, description="Batch query inputs")

    @model_validator(mode="after")
    def _validate_and_normalize(self) -> "EvalInputs":
        if self.queries is None and self.query is None:
            raise ValueError("inputs.query 或 inputs.queries 至少提供一个")
        if self.queries is None:
            self.queries = [self.query or ""]
        self.queries = [q for q in (self.queries or []) if isinstance(q, str)]
        if not self.queries:
            raise ValueError("inputs.queries 不能为空")
        return self


class EvalOptions(BaseModel):
    debug: bool = False
    top_k: int | None = Field(default=None, ge=1, description="每条 query 返回的最大标签数")
    continue_on_error: bool = True


class EvalRunRequest(BaseModel):
    """Unified eval gateway request."""

    sessionInfo: SessionInfo
    userInfo: UserInfo
    DeviceInfo: DeviceInfo
    AppBaseInfo: AppBaseInfo
    SystemSetting: SystemSetting
    scene: EvalScene
    task: EvalTask
    inputs: EvalInputs
    options: EvalOptions = Field(default_factory=EvalOptions)


class EvalRunResponse(BaseModel):
    """Unified eval gateway response payload."""

    scene: str
    task: str
    summary: dict[str, Any]
    items: list[dict[str, Any]]
    threshold: dict[str, Any]
    meta: dict[str, Any]
