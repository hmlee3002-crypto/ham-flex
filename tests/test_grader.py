"""
Grader 테스트 - 채점 정확성 및 유효하지 않은 답안 거부
"""
import pytest
from unittest.mock import MagicMock
from hypothesis import given, settings
from hypothesis import strategies as st

from flex_agent.components.grader import Grader
from flex_agent.exceptions import InvalidAnswerError
from flex_agent.models.data_models import Difficulty, Question, ReadingSubtype


def make_question(correct_answer: int = 2) -> Question:
    return Question(
        id="test-id",
        subtype=ReadingSubtype.TOPIC,
        difficulty=Difficulty.MEDIUM,
        passage="测试文章",
        question_text="这篇文章的主题是什么？",
        choices=["选项A", "选项B", "选项C", "选项D"],
        correct_answer=correct_answer,
        explanation="解释说明",
    )


def make_grader() -> Grader:
    mock_store = MagicMock()
    mock_store.load.return_value = None  # 저장 로직 스킵
    return Grader(session_store=mock_store)


# ── 속성 5: 채점 정확성 ───────────────────────────────────────────
# Feature: flex-ai-learning-agent, Property 5: 채점 정확성
@given(
    correct=st.integers(min_value=1, max_value=4),
    user=st.integers(min_value=1, max_value=4),
)
@settings(max_examples=100)
def test_grading_accuracy(correct, user):
    grader = make_grader()
    question = make_question(correct_answer=correct)
    result = grader.grade(question, user)
    assert result.is_correct == (user == correct)


# ── 속성 6: 유효하지 않은 답안 입력 거부 ─────────────────────────
# Feature: flex-ai-learning-agent, Property 6: 유효하지 않은 답안 입력 거부
@given(answer=st.one_of(st.integers(max_value=0), st.integers(min_value=5)))
@settings(max_examples=100)
def test_invalid_answer_raises(answer):
    grader = make_grader()
    question = make_question()
    with pytest.raises(InvalidAnswerError):
        grader.grade(question, answer)


# ── 단위 테스트 ───────────────────────────────────────────────────
def test_correct_answer_returns_true():
    grader = make_grader()
    q = make_question(correct_answer=3)
    result = grader.grade(q, 3)
    assert result.is_correct is True


def test_wrong_answer_returns_false():
    grader = make_grader()
    q = make_question(correct_answer=3)
    result = grader.grade(q, 1)
    assert result.is_correct is False


def test_grade_result_stores_user_answer():
    grader = make_grader()
    q = make_question(correct_answer=2)
    result = grader.grade(q, 4)
    assert result.user_answer == 4
    assert result.correct_answer == 2
