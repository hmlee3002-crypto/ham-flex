"""
유틸리티 함수 테스트 - 점수 유효성 검사 및 난이도 결정
"""
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from flex_agent.exceptions import InvalidScoreError
from flex_agent.models.data_models import Difficulty
from flex_agent.utils import determine_difficulty, validate_score


# ── 속성 1: 점수 범위 → 난이도 매핑 ──────────────────────────────
# Feature: flex-ai-learning-agent, Property 1: 점수 범위 → 난이도 매핑
@given(score=st.integers(min_value=0, max_value=350))
@settings(max_examples=100)
def test_easy_range(score):
    assert determine_difficulty(score) == Difficulty.EASY


@given(score=st.integers(min_value=351, max_value=450))
@settings(max_examples=100)
def test_medium_range(score):
    assert determine_difficulty(score) == Difficulty.MEDIUM


@given(score=st.integers(min_value=451, max_value=600))
@settings(max_examples=100)
def test_hard_range(score):
    assert determine_difficulty(score) == Difficulty.HARD


# ── 속성 2: 유효하지 않은 점수 입력 거부 ─────────────────────────
# Feature: flex-ai-learning-agent, Property 2: 유효하지 않은 점수 입력 거부
@given(score=st.one_of(st.integers(max_value=-1), st.integers(min_value=601)))
@settings(max_examples=100)
def test_invalid_score_raises(score):
    with pytest.raises(InvalidScoreError):
        validate_score(score)


@given(score=st.integers(min_value=0, max_value=600))
@settings(max_examples=100)
def test_valid_score_no_raise(score):
    validate_score(score)  # 예외 없이 통과해야 함


# ── 경계값 단위 테스트 ────────────────────────────────────────────
def test_boundary_350_is_easy():
    assert determine_difficulty(350) == Difficulty.EASY


def test_boundary_351_is_medium():
    assert determine_difficulty(351) == Difficulty.MEDIUM


def test_boundary_450_is_medium():
    assert determine_difficulty(450) == Difficulty.MEDIUM


def test_boundary_451_is_hard():
    assert determine_difficulty(451) == Difficulty.HARD


def test_boundary_0_is_easy():
    assert determine_difficulty(0) == Difficulty.EASY


def test_boundary_600_is_hard():
    assert determine_difficulty(600) == Difficulty.HARD
