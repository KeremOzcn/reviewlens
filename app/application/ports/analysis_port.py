from __future__ import annotations

from typing import Dict, Protocol

from app.schemas.models import (
    AnalyzeRequest,
    AnalyzeResponse,
    BatchAnalyzeRequest,
    BatchAnalyzeResponse,
)


class AnalysisPort(Protocol):
    def analyze(self, request: AnalyzeRequest) -> AnalyzeResponse:
        ...

    def analyze_batch(self, request: BatchAnalyzeRequest) -> BatchAnalyzeResponse:
        ...

    def models_loaded_status(self) -> Dict[str, bool]:
        ...
