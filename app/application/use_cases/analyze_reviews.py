from __future__ import annotations

from typing import Dict

from app.application.ports.analysis_port import AnalysisPort
from app.schemas.models import (
    AnalyzeRequest,
    AnalyzeResponse,
    BatchAnalyzeRequest,
    BatchAnalyzeResponse,
)


class AnalyzeReviewsUseCase:
    def __init__(self, analyzer: AnalysisPort) -> None:
        self._analyzer = analyzer

    def execute(self, request: AnalyzeRequest) -> AnalyzeResponse:
        return self._analyzer.analyze(request)

    def execute_batch(self, request: BatchAnalyzeRequest) -> BatchAnalyzeResponse:
        return self._analyzer.analyze_batch(request)

    def model_status(self) -> Dict[str, bool]:
        return self._analyzer.models_loaded_status()
