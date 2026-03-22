"""
FLEX AI 학습 에이전트 - 맞춤 문제 추천기

취약 영역 기반으로 다음 문제 유형을 결정하고 추천 근거를 제공한다.
"""

from typing import List

from flex_agent.models.data_models import AnalysisResult, Difficulty, ReadingSubtype

# 모든 독해 세부 유형 목록 (균등 순환용)
_ALL_SUBTYPES: List[ReadingSubtype] = list(ReadingSubtype)

# 세부 유형 한국어 이름 매핑
_SUBTYPE_NAMES = {
    ReadingSubtype.TOPIC: "주제 찾기",
    ReadingSubtype.DETAIL: "세부 내용 파악",
    ReadingSubtype.TRUE_FALSE: "진위 판단",
    ReadingSubtype.LETTER: "편지글",
    ReadingSubtype.ADVERTISEMENT: "광고문",
    ReadingSubtype.ACADEMIC: "학술 지문",
}


class Recommender:
    """
    취약 영역 기반 맞춤 문제 추천 컴포넌트.

    같은 유형을 QUESTIONS_PER_SUBTYPE문제씩 연속 출제 후 다음 유형으로 순환한다.
    """

    QUESTIONS_PER_SUBTYPE = 3  # 유형당 연속 출제 문제 수

    def __init__(self) -> None:
        self._weak_index: int = 0       # 취약 유형 순환 인덱스
        self._all_index: int = 0        # 전체 유형 순환 인덱스
        self._current_subtype: ReadingSubtype = _ALL_SUBTYPES[0]
        self._count_in_subtype: int = 0  # 현재 유형에서 출제한 문제 수

    def recommend_subtype(
        self,
        analysis: AnalysisResult,
        current_difficulty: Difficulty,
    ) -> ReadingSubtype:
        """
        다음 문제 유형을 추천한다.

        같은 유형을 QUESTIONS_PER_SUBTYPE문제씩 연속 출제 후 다음 유형으로 순환한다.

        Args:
            analysis: 오답 분석 결과
            current_difficulty: 현재 난이도

        Returns:
            추천된 ReadingSubtype
        """
        pool = analysis.weak_subtypes if analysis.weak_subtypes else _ALL_SUBTYPES

        # 현재 유형이 pool에 있고 아직 연속 출제 횟수가 남아있으면 유지
        if (
            self._current_subtype in pool
            and self._count_in_subtype < self.QUESTIONS_PER_SUBTYPE
        ):
            self._count_in_subtype += 1
            return self._current_subtype

        # 다음 유형으로 순환
        if analysis.weak_subtypes:
            self._weak_index = (self._weak_index + 1) % len(pool)
            next_subtype = pool[self._weak_index]
        else:
            self._all_index = (self._all_index + 1) % len(pool)
            next_subtype = pool[self._all_index]

        self._current_subtype = next_subtype
        self._count_in_subtype = 1
        return next_subtype

    def get_recommendation_reason(
        self,
        subtype: ReadingSubtype,
        analysis: AnalysisResult,
    ) -> str:
        """
        추천 근거 텍스트를 반환한다.

        Args:
            subtype: 추천된 세부 유형
            analysis: 오답 분석 결과

        Returns:
            추천 근거 텍스트
        """
        subtype_name = _SUBTYPE_NAMES.get(subtype, subtype.value)

        if subtype in analysis.weak_subtypes:
            accuracy = analysis.subtype_accuracies.get(subtype)
            if accuracy is not None:
                return (
                    f"📌 추천 이유: '{subtype_name}' 유형의 정답률이 "
                    f"{accuracy:.0%}로 취약 영역입니다. 집중 연습이 필요합니다."
                )
            return f"📌 추천 이유: '{subtype_name}' 유형이 취약 영역으로 분류되었습니다."
        else:
            return (
                f"📌 추천 이유: 취약 영역이 없습니다. "
                f"'{subtype_name}' 유형으로 균등 학습을 진행합니다."
            )
