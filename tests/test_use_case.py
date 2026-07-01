from app.application.use_cases.analyze_reviews import AnalyzeReviewsUseCase


class _FakeAnalyzer:
    def analyze(self, request):
        return {"ok": True, "request": request}

    def analyze_batch(self, request):
        return {"batch": True, "request": request}

    def models_loaded_status(self):
        return {"sentiment_analyzer": True}


def test_use_case_delegates_single_analyze() -> None:
    use_case = AnalyzeReviewsUseCase(_FakeAnalyzer())
    result = use_case.execute({"reviews": ["a"]})
    assert result["ok"] is True


def test_use_case_delegates_batch_and_health() -> None:
    use_case = AnalyzeReviewsUseCase(_FakeAnalyzer())
    batch_result = use_case.execute_batch({"products": []})
    health_result = use_case.model_status()
    assert batch_result["batch"] is True
    assert health_result["sentiment_analyzer"] is True
