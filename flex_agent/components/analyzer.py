"""
FLEX AI 학습 에이전트 - 오답 분석기

채점 데이터를 집계하여 세부 유형별 정답률과 취약 영역을 도출한다.
"""

from collections import defaultdict
from typing import Dict, List, Tuple

from flex_agent.models.data_models import AnalysisResult, GradeResult, ReadingSubtype

# 취약 영역 기준 정답률
_WEAKNESS_THRESHOLD = 0.6

# 데이터 부족 경고 기준
_MIN_DATA_COUNT = 5


class Analyzer:
    """
    채점 데이터 집계 및 취약 영역 도출 컴포넌트.

    세부 유형별 정답률을 계산하고, 정답률 0.6 미만인 유형을 취약 영역으로 분류한다.
    """

    def analyze(self, results: List[GradeResult]) -> AnalysisResult:
        """
        채점 결과를 분석하여 세부 유형별 정답률과 취약 영역을 반환한다.

        Args:
            results: 채점 결과 목록

        Returns:
            AnalysisResult 객체 (데이터 5개 미만 시 warning_message 포함)
        """
        # 데이터 부족 경고 메시지 설정
        warning_message = None
        if len(results) < _MIN_DATA_COUNT:
            warning_message = (
                f"분석에 충분한 데이터가 없습니다 (현재 {len(results)}개, 최소 {_MIN_DATA_COUNT}개 필요). "
                "더 많은 문제를 풀어주세요."
            )

        # 세부 유형별 정답/전체 집계
        subtype_correct: Dict[ReadingSubtype, int] = defaultdict(int)
        subtype_total: Dict[ReadingSubtype, int] = defaultdict(int)

        for r in results:
            subtype_total[r.subtype] += 1
            if r.is_correct:
                subtype_correct[r.subtype] += 1

        # 세부 유형별 정답률 계산
        subtype_accuracies: Dict[ReadingSubtype, float] = {}
        for subtype in subtype_total:
            subtype_accuracies[subtype] = subtype_correct[subtype] / subtype_total[subtype]

        # 취약 영역 분류 (정답률 < 0.6, 정답률 오름차순 정렬)
        weak_subtypes = [
            subtype
            for subtype, acc in sorted(subtype_accuracies.items(), key=lambda x: x[1])
            if acc < _WEAKNESS_THRESHOLD
        ]

        # 전체 정답률 계산
        total_accuracy = sum(r.is_correct for r in results) / len(results) if results else 0.0

        return AnalysisResult(
            subtype_accuracies=subtype_accuracies,
            weak_subtypes=weak_subtypes,
            total_accuracy=total_accuracy,
            warning_message=warning_message,
        )

    def get_weakness_subtypes(self, results: List[GradeResult]) -> List[ReadingSubtype]:
        """
        취약 세부 유형 목록을 정답률 오름차순으로 반환한다.

        Args:
            results: 채점 결과 목록

        Returns:
            취약 유형 목록 (정답률 오름차순 정렬)
        """
        analysis = self.analyze(results)
        return analysis.weak_subtypes
