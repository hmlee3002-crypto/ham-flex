"""
FLEX AI 학습 에이전트 - 유틸리티 함수

점수 유효성 검사 및 난이도 결정 등 공통 유틸리티를 제공한다.
"""

from flex_agent.exceptions import InvalidScoreError
from flex_agent.models.data_models import Difficulty


def validate_score(score: int) -> None:
    """
    점수 유효성 검사.

    Args:
        score: 검사할 점수 (0~600 범위여야 함)

    Raises:
        InvalidScoreError: 0~600 범위를 벗어난 경우
    """
    if not (0 <= score <= 600):
        raise InvalidScoreError(
            f"점수는 0~600 범위여야 합니다. 입력값: {score}"
        )


def determine_difficulty(score: int) -> Difficulty:
    """
    현재 예상 점수를 기반으로 초기 난이도를 결정한다.

    Args:
        score: 현재 예상 점수 (0~600)

    Returns:
        Difficulty: 결정된 난이도 (EASY / MEDIUM / HARD)
    """
    if score <= 350:
        return Difficulty.EASY
    elif score <= 450:
        return Difficulty.MEDIUM
    else:
        return Difficulty.HARD
