"""
ScorePredictor 테스트 - 기본/가중 예상 점수 계산
"""
from datetime import datetime
from unittest.mock import MagicMock
from hypothesis import given, settings
from hypothesis import strategies as st

from flex_agent.components.score_predictor import ScorePredictor
from flex_agent.models.data_models import Difficulty, GradeResult, ReadingSubtype


def make_result(subtype: ReadingSubtype, is_correct: bool) -> GradeResult:
    return GradeResult(
        question_id="q1",
        subtype=subtype,
        difficulty=Difficulty.MEDIUM,
        user_answer=1,
        correct_answer=1 if is_correct else 2,
        is_correct=is_correct,
        graded_at=datetime.now(),
    )


def make_predictor() -> ScorePredictor:
    mock_store = MagicMock()
    mock_store.load.return_value = None
    return ScorePredictor(session_store=mock_store)


st_subtype = st.sampled_from(ReadingSubtype)


# ── 속성 12: 기본 예상 점수 계산 ─────────────────────────────────
# Feature: flex-ai-learning-agent, Property 12: 기본 예상 점수 계산
@given(
    data=st.lists(
        st.tuples(st_subtype, st.booleans()),
        min_size=1,
        max_size=30,
    )
)
@settings(max_examples=100)
def test_basic_score_calculation(data):
    predictor = make_predictor()
    results = [make_result(s, c) for s, c in data]
    prediction = predictor.predict(results)

    expected = (sum(c for _, c in data) / len(data)) * 600
    assert abs(prediction.basic_score - expected) < 0.01
    assert 0 <= prediction.basic_score <= 600


# ── 속성 13: 가중 예상 점수 범위 ─────────────────────────────────
# Feature: flex-ai-learning-agent, Property 13: 가중 예상 점수 계산
@given(
    data=st.lists(
        st.tuples(st_subtype, st.booleans()),
        min_size=1,
        max_size=30,
    )
)
@settings(max_examples=100)
def test_weighted_score_in_range(data):
    predictor = make_predictor()
    results = [make_result(s, c) for s, c in data]
    prediction = predictor.predict(results)
    assert 0 <= prediction.weighted_score <= 600


# ── 단위 테스트 ───────────────────────────────────────────────────
def test_unreliable_when_less_than_10():
    predictor = make_predictor()
    results = [make_result(ReadingSubtype.TOPIC, True) for _ in range(9)]
    prediction = predictor.predict(results)
    assert prediction.is_reliable is False


def test_reliable_when_10_or_more():
    predictor = make_predictor()
    results = [make_result(ReadingSubtype.TOPIC, True) for _ in range(10)]
    prediction = predictor.predict(results)
    assert prediction.is_reliable is True


def test_empty_results_returns_zero():
    predictor = make_predictor()
    prediction = predictor.predict([])
    assert prediction.basic_score == 0.0
    assert prediction.weighted_score == 0.0
    assert prediction.is_reliable is False
