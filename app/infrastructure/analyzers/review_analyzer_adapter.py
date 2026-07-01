from __future__ import annotations

from typing import Dict

from app.schemas.models import (
    AnalyzeRequest,
    AnalyzeResponse,
    BatchAnalyzeRequest,
    BatchAnalyzeResponse,
)
from app.services import analyzer as analyzer_service


class ReviewAnalyzerAdapter:
    def analyze(self, request: AnalyzeRequest) -> AnalyzeResponse:
        return analyzer_service.analyze(request)

    def analyze_batch(self, request: BatchAnalyzeRequest) -> BatchAnalyzeResponse:
        return analyzer_service.analyze_batch(request)

    def models_loaded_status(self) -> Dict[str, bool]:
        return analyzer_service.models_loaded_status()
