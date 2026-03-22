"""
FLEX AI 학습 에이전트 - 예상 점수 예측기

정답률 기반으로 FLEX 읽기 영역 예상 점수를 계산한다.
"""

from collections import defaultdict
from datetime import datetime
from typing import Dict, List

from flex_agent.models.data_models import (
    Difficulty,
    GradeResult,
    ReadingSubtype,
    ScorePrediction,
)
from flex_agent.storage.session_store import SessionStore

# 최대 점수
_MAX_SCORE = 600.0

# 신뢰도 기준 데이터 수
_MIN_RELIABLE_COUNT = 10

# 세부 유형별 균등 가중치 (1/6)
_SUBTYPE_WEIGHT = 1.0 / len(ReadingSubtype)


class ScorePredictor:
    """
    정답률 기반 FLEX 예상 점수 계산 컴포넌트.

    기본 예상 점수(전체 정답률 × 600)와
    세부 유형별 가중치를 적용한 가중 예상 점수를 모두 계산한다.
    """

    def __init__(self, session_store: SessionStore) -> None:
        """
        Args:
            session_store: 세션 저장소
        """
        self._session_store = session_store

    def _weighted_score(
        self, subtype_accuracies: Dict[ReadingSubtype, float]
    ) -> float:
        """
        세부 유형별 균등 가중치(1/6)를 적용한 예상 점수를 계산한다.

        Args:
            subtype_accuracies: 세부 유형별 정답률 딕셔너리

        Returns:
            가중 예상 점수 (0~600 범위)
        """
        if not subtype_accuracies:
            return 0.0

        total = sum(
            acc * _SUBTYPE_WEIGHT * _MAX_SCORE
            for acc in subtype_accuracies.values()
        )
        # 데이터가 없는 유형은 0점으로 처리 (이미 가중치 합이 1이 되도록 균등 배분)
        return max(0.0, min(_MAX_SCORE, total))

    def predict(self, results: List[GradeResult]) -> ScorePrediction:
        """
        채점 결과를 기반으로 예상 점수를 계산한다.

        Args:
            results: 채점 결과 목록

        Returns:
            ScorePrediction 객체

        Note:
            데이터 10개 미만 시 is_reliable=False
        """
        data_count = len(results)

        if data_count == 0:
            prediction = ScorePrediction(
                basic_score=0.0,
                weighted_score=0.0,
                data_count=0,
                is_reliable=False,
            )
        else:
            # 기본 예상 점수: 전체 정답률 × 600
            total_correct = sum(r.is_correct for r in results)
            basic_score = (total_correct / data_count) * _MAX_SCORE

            # 세부 유형별 정답률 계산
            subtype_correct: Dict[ReadingSubtype, int] = defaultdict(int)
            subtype_total: Dict[ReadingSubtype, int] = defaultdict(int)
            for r in results:
                subtype_total[r.subtype] += 1
                if r.is_correct:
                    subtype_correct[r.subtype] += 1

            subtype_accuracies: Dict[ReadingSubtype, float] = {
                subtype: subtype_correct[subtype] / subtype_total[subtype]
                for subtype in subtype_total
            }

            # 가중 예상 점수 계산
            weighted = self._weighted_score(subtype_accuracies)

            prediction = ScorePrediction(
                basic_score=round(basic_score, 2),
                weighted_score=round(weighted, 2),
                data_count=data_count,
                is_reliable=(data_count >= _MIN_RELIABLE_COUNT),
            )

        # 예상 점수를 세션에 저장
        session = self._session_store.load()
        if session is not None:
            session.predicted_score = prediction.weighted_score
            session.updated_at = datetime.now()
            self._session_store.save(session)

        return prediction
