"""
ReportGenerator 테스트 - 리포트 내용 정확성
"""
from datetime import datetime
from unittest.mock import MagicMock

from flex_agent.components.analyzer import Analyzer
from flex_agent.components.report_generator import ReportGenerator
from flex_agent.components.score_predictor import ScorePredictor
from flex_agent.models.data_models import Difficulty, GradeResult, ReadingSubtype, Session


def make_session(results=None, target_score=400):
    return Session(
        target_score=target_score,
        current_difficulty=Difficulty.MEDIUM,
        grade_results=results or [],
    )


def make_result(subtype, is_correct):
    return GradeResult(
        question_id="q1",
        subtype=subtype,
        difficulty=Difficulty.MEDIUM,
        user_answer=1,
        correct_answer=1 if is_correct else 2,
        is_correct=is_correct,
        graded_at=datetime.now(),
    )


def make_report_generator():
    mock_store = MagicMock()
    mock_store.load.return_value = None
    score_predictor = ScorePredictor(session_store=mock_store)
    analyzer = Analyzer()
    return ReportGenerator(
        score_predictor=score_predictor,
        analyzer=analyzer,
        session_store=mock_store,
    )


# ── 속성 14: 리포트 내용 정확성 ──────────────────────────────────
# Feature: flex-ai-learning-agent, Property 14: 리포트 내용 정확성
def test_achievement_rate_calculation():
    rg = make_report_generator()
    results = [make_result(ReadingSubtype.TOPIC, True) for _ in range(10)]
    session = make_session(results, target_score=500)
    report = rg.generate(session)
    assert report is not None
    expected_rate = report.predicted_score / 500 * 100
    assert abs(report.achievement_rate - expected_rate) < 0.01


def test_strong_subtypes_threshold():
    rg = make_report_generator()
    # TOPIC: 10/10 = 100% (강점), DETAIL: 0/10 = 0% (취약)
    results = (
        [make_result(ReadingSubtype.TOPIC, True) for _ in range(10)] +
        [make_result(ReadingSubtype.DETAIL, False) for _ in range(10)]
    )
    session = make_session(results)
    report = rg.generate(session)
    assert ReadingSubtype.TOPIC in report.strong_subtypes
    assert ReadingSubtype.DETAIL not in report.strong_subtypes


def test_weak_subtypes_threshold():
    rg = make_report_generator()
    results = (
        [make_result(ReadingSubtype.TOPIC, True) for _ in range(10)] +
        [make_result(ReadingSubtype.DETAIL, False) for _ in range(10)]
    )
    session = make_session(results)
    report = rg.generate(session)
    assert ReadingSubtype.DETAIL in report.weak_subtypes
    assert ReadingSubtype.TOPIC not in report.weak_subtypes


def test_study_directions_not_empty_when_weak_exists():
    rg = make_report_generator()
    results = [make_result(ReadingSubtype.ACADEMIC, False) for _ in range(10)]
    session = make_session(results)
    report = rg.generate(session)
    assert len(report.study_directions) > 0


# ── 단위 테스트: 데이터 없을 때 None 반환 ────────────────────────
def test_returns_none_when_no_grade_results():
    rg = make_report_generator()
    session = make_session(results=[])
    report = rg.generate(session)
    assert report is None
