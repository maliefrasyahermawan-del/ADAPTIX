"""Strict model contract for the static code audit.

Ported shape from ADAPTIX-V2's engine/schema.py. Only read-only source tools are
available: the schema itself makes network, terminal, and file-write actions
unrepresentable, so a prompt-injected source file cannot ask for them.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Action(BaseModel):
    model_config = ConfigDict(extra='forbid')
    tool: Literal['list_source', 'read_source']
    target: str = Field(default='', max_length=2048)
    arguments: dict = Field(default_factory=dict)


class Finding(BaseModel):
    model_config = ConfigDict(extra='forbid')
    title: str = Field(min_length=1, max_length=240)
    severity: Literal['critical', 'high', 'medium', 'low', 'info']
    evidence_ids: list[str] = Field(min_length=1, max_length=10)
    description: str = Field(min_length=1, max_length=6000)
    impact: str = Field(min_length=1, max_length=4000)
    remediation: str = Field(min_length=1, max_length=4000)
    cwe: str = Field(default='', max_length=40)


class Patch(BaseModel):
    model_config = ConfigDict(extra='forbid')
    path: str = Field(min_length=1, max_length=1024)
    search: str = Field(min_length=1, max_length=20000)
    replace: str = Field(default='', max_length=20000)
    rationale: str = Field(min_length=1, max_length=1000)


class Report(BaseModel):
    model_config = ConfigDict(extra='forbid')
    title: str = Field(min_length=1, max_length=240)
    executive_summary: str = Field(min_length=1, max_length=8000)
    methodology: str = Field(min_length=1, max_length=5000)
    findings: list[Finding] = Field(default_factory=list, max_length=50)
    patches: list[Patch] = Field(default_factory=list, max_length=20)
    limitations: str = Field(min_length=1, max_length=5000)
    next_steps: str = Field(min_length=1, max_length=5000)


class Turn(BaseModel):
    model_config = ConfigDict(extra='forbid')
    commentary: str = Field(min_length=1, max_length=1600)
    notes: str = Field(default='', max_length=5000)
    action: Action | None = None
    report: Report | None = None

    @model_validator(mode='after')
    def one_choice(self):
        if (self.action is None) == (self.report is None):
            raise ValueError('Choose exactly one action or final report.')
        return self
