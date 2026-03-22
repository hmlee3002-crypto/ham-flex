"""
Recommender 테스트 - 취약 영역 우선 추천 및 순환 추천
"""
from hypothesis import given, settings
from hypothesis import strategies as st

from flex_agent.components.recommender import Recommender
from flex_agent.models.data_models import AnalysisResult, Difficulty, ReadingSubtype

st_subtype = st.sampled_from(ReadingSubtype)


def make_analysis(weak_subtypes, accuracies=None):
    if accuracies is None:
        accuracies = {s: 0.4 for s in weak_subtypes}
    return AnalysisResult(
        subtype_accuracies=accuracies,
        weak_subtypes=weak_subtypes,
        total_accuracy=0.5,
    )


# ── 속성 9: 취약 영역 우선 추천 ──────────────────────────────────
# Feature: flex-ai-learning-agent, Property 9: 취약 영역 우선 추천
@given(
    weak=st.lists(st_subtype, min_size=1, max_size=6, unique=True),
)
@settings(max_examples=100)
def test_recommends_from_weak_subtypes(weak):
    recommender = Recommender()
    analysis = make_analysis(weak)
    result = recommender.recommend_subtype(analysis, Difficulty.MEDIUM)
    assert result in weak


# ── 속성 10: 취약 영역 순환 추천 ─────────────────────────────────
# Feature: flex-ai-learning-agent, Property 10: 취약 영역 순환 추천
@given(
    weak=st.lists(st_subtype, min_size=2, max_size=6, unique=True),
)
@settings(max_examples=50)
def test_weak_subtypes_cycled_evenly(weak):
    recommender = Recommender()
    analysis = make_analysis(weak)
    n = len(weak) * 3  # 3 순환
    results = [recommender.recommend_subtype(analysis, Difficulty.MEDIUM) for _ in range(n)]
    counts = {s: results.count(s) for s in weak}
    max_count = max(counts.values())
    min_count = min(counts.values())
    assert max_count - min_count <= 1


# ── 단위 테스트: 취약 영역 없을 때 전체 유형 균등 추천 ────────────
def test_no_weak_subtypes_recommends_all():
    recommender = Recommender()
    analysis = make_analysis([], accuracies={s: 0.8 for s in ReadingSubtype})
    seen = set()
    for _ in range(len(ReadingSubtype) * 2):
        result = recommender.recommend_subtype(analysis, Difficulty.MEDIUM)
        seen.add(result)
    assert len(seen) == len(ReadingSubtype)


def test_recommendation_reason_contains_subtype_name():
    recommender = Recommender()
    weak = [ReadingSubtype.TOPIC]
    analysis = make_analysis(weak)
    reason = recommender.get_recommendation_reason(ReadingSubtype.TOPIC, analysis)
    assert "주제 찾기" in reason
