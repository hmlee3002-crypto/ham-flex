"""
Analyzer 테스트 - 유형별 정답률 계산 및 취약 영역 분류
"""
from datetime import datetime
from hypothesis import given, settings
from hypothesis import strategies as st

from flex_agent.components.analyzer import Analyzer
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


st_subtype = st.sampled_from(ReadingSubtype)
st_bool = st.booleans()


# ── 속성 7: 유형별 정답률 계산 정확성 ────────────────────────────
# Feature: flex-ai-learning-agent, Property 7: 유형별 정답률 계산 정확성
@given(
    subtype=st_subtype,
    corrects=st.lists(st.booleans(), min_size=1, max_size=20),
)
@settings(max_examples=100)
def test_subtype_accuracy_calculation(subtype, corrects):
    analyzer = Analyzer()
    results = [make_result(subtype, c) for c in corrects]
    analysis = analyzer.analyze(results)
    expected = sum(corrects) / len(corrects)
    assert abs(analysis.subtype_accuracies[subtype] - expected) < 1e-9


# ── 속성 8: 취약 영역 분류 정확성 ────────────────────────────────
# Feature: flex-ai-learning-agent, Property 8: 취약 영역 분류 정확성
@given(
    data=st.lists(
        st.tuples(st_subtype, st_bool),
        min_size=1,
        max_size=30,
    )
)
@settings(max_examples=100)
def test_weakness_classification(data):
    analyzer = Analyzer()
    results = [make_result(s, c) for s, c in data]
    analysis = analyzer.analyze(results)

    for subtype, acc in analysis.subtype_accuracies.items():
        if acc < 0.6:
            assert subtype in analysis.weak_subtypes
        else:
            assert subtype not in analysis.weak_subtypes


# ── 단위 테스트: 데이터 5개 미만 경고 ────────────────────────────
def test_warning_when_less_than_5_results():
    analyzer = Analyzer()
    results = [make_result(ReadingSubtype.TOPIC, True) for _ in range(4)]
    analysis = analyzer.analyze(results)
    assert analysis.warning_message is not None


def test_no_warning_when_5_or_more_results():
    analyzer = Analyzer()
    results = [make_result(ReadingSubtype.TOPIC, True) for _ in range(5)]
    analysis = analyzer.analyze(results)
    assert analysis.warning_message is None


def test_empty_results_returns_zero_accuracy():
    analyzer = Analyzer()
    analysis = analyzer.analyze([])
    assert analysis.total_accuracy == 0.0
    assert analysis.weak_subtypes == []
