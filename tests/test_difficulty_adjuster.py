"""
난이도 자동 조절 테스트
"""
from datetime import datetime
from unittest.mock import MagicMock
from hypothesis import given, settings
from hypothesis import strategies as st

from flex_agent.agent import Agent
from flex_agent.models.data_models import Difficulty, GradeResult, ReadingSubtype, Session


def make_result(is_correct):
    return GradeResult(
        question_id="q1",
        subtype=ReadingSubtype.TOPIC,
        difficulty=Difficulty.MEDIUM,
        user_answer=1,
        correct_answer=1 if is_correct else 2,
        is_correct=is_correct,
        graded_at=datetime.now(),
    )


def make_agent_with_session(results, difficulty):
    session = Session(
        target_score=400,
        current_difficulty=difficulty,
        grade_results=results,
    )
    mock_store = MagicMock()
    mock_store.load.return_value = session
    mock_store.save = MagicMock()

    agent = Agent(
        session_store=mock_store,
        question_generator=MagicMock(),
        grader=MagicMock(),
        analyzer=MagicMock(),
        recommender=MagicMock(),
        score_predictor=MagicMock(),
        report_generator=MagicMock(),
    )
    agent._session = session
    return agent


# ── 속성 11: 난이도 자동 조절 방향성 ─────────────────────────────
# Feature: flex-ai-learning-agent, Property 11: 난이도 자동 조절 방향성
@given(
    corrects=st.lists(st.booleans(), min_size=5, max_size=5),
    difficulty=st.sampled_from(Difficulty),
)
@settings(max_examples=100)
def test_difficulty_adjustment_direction(corrects, difficulty):
    results = [make_result(c) for c in corrects]
    agent = make_agent_with_session(results, difficulty)
    accuracy = sum(corrects) / 5

    new_difficulty = agent.adjust_difficulty()

    if accuracy >= 0.8:
        if difficulty == Difficulty.HARD:
            assert new_difficulty is None  # 이미 최고 난이도
        else:
            assert new_difficulty is not None
            assert new_difficulty.value > difficulty.value or (
                [Difficulty.EASY, Difficulty.MEDIUM, Difficulty.HARD].index(new_difficulty) >
                [Difficulty.EASY, Difficulty.MEDIUM, Difficulty.HARD].index(difficulty)
            )
    elif accuracy < 0.4:
        if difficulty == Difficulty.EASY:
            assert new_difficulty is None  # 이미 최저 난이도
        else:
            assert new_difficulty is not None
    else:
        assert new_difficulty is None  # 변경 없음


# ── 단위 테스트: 경계 조건 ────────────────────────────────────────
def test_hard_does_not_upgrade():
    results = [make_result(True) for _ in range(5)]  # 100% 정답률
    agent = make_agent_with_session(results, Difficulty.HARD)
    result = agent.adjust_difficulty()
    assert result is None


def test_easy_does_not_downgrade():
    results = [make_result(False) for _ in range(5)]  # 0% 정답률
    agent = make_agent_with_session(results, Difficulty.EASY)
    result = agent.adjust_difficulty()
    assert result is None


def test_medium_upgrades_on_high_accuracy():
    results = [make_result(True) for _ in range(5)]  # 100%
    agent = make_agent_with_session(results, Difficulty.MEDIUM)
    result = agent.adjust_difficulty()
    assert result == Difficulty.HARD


def test_medium_downgrades_on_low_accuracy():
    results = [make_result(False) for _ in range(5)]  # 0%
    agent = make_agent_with_session(results, Difficulty.MEDIUM)
    result = agent.adjust_difficulty()
    assert result == Difficulty.EASY


def test_no_adjustment_when_less_than_5_results():
    results = [make_result(True) for _ in range(4)]
    agent = make_agent_with_session(results, Difficulty.MEDIUM)
    result = agent.adjust_difficulty()
    assert result is None
