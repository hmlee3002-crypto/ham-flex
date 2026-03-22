"""
FLEX AI 학습 에이전트 - 학습 리포트 생성기

ScorePredictor와 Analyzer 결과를 종합하여 학습 리포트를 생성하고 출력한다.
"""

from datetime import datetime
from typing import Dict, List, Optional

from flex_agent.components.analyzer import Analyzer
from flex_agent.components.score_predictor import ScorePredictor
from flex_agent.models.data_models import (
    AnalysisResult,
    ReadingSubtype,
    Report,
    ScorePrediction,
    Session,
)
from flex_agent.storage.session_store import SessionStore

# 강점 영역 기준 정답률
_STRONG_THRESHOLD = 0.7

# 취약 영역 기준 정답률
_WEAK_THRESHOLD = 0.6

# 세부 유형 한국어 이름 매핑
_SUBTYPE_NAMES = {
    ReadingSubtype.TOPIC: "주제 찾기",
    ReadingSubtype.DETAIL: "세부 내용 파악",
    ReadingSubtype.TRUE_FALSE: "진위 판단",
    ReadingSubtype.LETTER: "편지글",
    ReadingSubtype.ADVERTISEMENT: "광고문",
    ReadingSubtype.ACADEMIC: "학술 지문",
}

# 세부 유형별 학습 방향 텍스트
_STUDY_DIRECTION_TEMPLATES = {
    ReadingSubtype.TOPIC: "주제 찾기 유형: 지문 전체의 핵심 내용을 파악하는 연습을 하세요. 첫 문장과 마지막 문장에 주목하세요.",
    ReadingSubtype.DETAIL: "세부 내용 파악 유형: 의문사(什么, 哪里, 为什么 등)에 집중하여 세부 정보를 빠르게 찾는 연습을 하세요.",
    ReadingSubtype.TRUE_FALSE: "진위 판단 유형: 지문의 내용과 선택지를 꼼꼼히 비교하는 연습을 하세요. 부정어와 수량 표현에 주의하세요.",
    ReadingSubtype.LETTER: "편지글 유형: 편지의 목적과 수신자/발신자 관계를 파악하는 연습을 하세요. 비즈니스 편지 형식에 익숙해지세요.",
    ReadingSubtype.ADVERTISEMENT: "광고문 유형: 광고의 핵심 정보(조건, 혜택, 연락처 등)를 빠르게 파악하는 연습을 하세요.",
    ReadingSubtype.ACADEMIC: "학술 지문 유형: 전문 어휘를 확장하고 논리적 흐름을 파악하는 연습을 하세요. HSK 5~6급 어휘를 집중 학습하세요.",
}


class ReportGenerator:
    """
    종합 학습 리포트 생성 컴포넌트.

    ScorePredictor와 Analyzer 결과를 종합하여 리포트를 생성하고
    SessionStore에 저장한다.
    """

    def __init__(
        self,
        score_predictor: ScorePredictor,
        analyzer: Analyzer,
        session_store: SessionStore,
    ) -> None:
        """
        Args:
            score_predictor: 예상 점수 예측기
            analyzer: 오답 분석기
            session_store: 세션 저장소
        """
        self._score_predictor = score_predictor
        self._analyzer = analyzer
        self._session_store = session_store

    def generate(self, session: Session) -> Optional[Report]:
        """
        세션 데이터를 기반으로 종합 학습 리포트를 생성한다.

        Args:
            session: 현재 학습 세션

        Returns:
            생성된 Report 객체, 채점 데이터 없으면 None
        """
        if not session.grade_results:
            return None

        # 예상 점수 계산
        prediction = self._score_predictor.predict(session.grade_results)
        predicted_score = prediction.weighted_score

        # 오답 분석
        analysis = self._analyzer.analyze(session.grade_results)

        # 달성률 계산
        achievement_rate = (predicted_score / session.target_score * 100) if session.target_score > 0 else 0.0

        # 강점/취약 영역 분류
        strong_subtypes = [
            subtype
            for subtype, acc in analysis.subtype_accuracies.items()
            if acc >= _STRONG_THRESHOLD
        ]
        weak_subtypes = [
            subtype
            for subtype, acc in sorted(analysis.subtype_accuracies.items(), key=lambda x: x[1])
            if acc < _WEAK_THRESHOLD
        ]

        # 학습 방향 텍스트 생성 (취약 영역 기반)
        study_directions = self._build_study_directions(weak_subtypes)

        report = Report(
            predicted_score=round(predicted_score, 2),
            target_score=session.target_score,
            achievement_rate=round(achievement_rate, 2),
            subtype_accuracies=analysis.subtype_accuracies,
            strong_subtypes=strong_subtypes,
            weak_subtypes=weak_subtypes,
            study_directions=study_directions,
            generated_at=datetime.now(),
        )

        # 리포트를 세션에 저장
        session.reports.append(report)
        session.updated_at = datetime.now()
        self._session_store.save(session)

        return report

    def _build_study_directions(self, weak_subtypes: List[ReadingSubtype]) -> List[str]:
        """
        취약 영역별 학습 방향 텍스트를 생성한다.

        Args:
            weak_subtypes: 취약 세부 유형 목록

        Returns:
            학습 방향 텍스트 목록
        """
        directions = []
        for subtype in weak_subtypes:
            template = _STUDY_DIRECTION_TEMPLATES.get(subtype)
            if template:
                directions.append(template)
        return directions

    def display(self, report: Optional[Report], target_score: int) -> None:
        """
        학습 리포트를 CLI에 출력한다.

        Args:
            report: 출력할 리포트 (None이면 안내 메시지 출력)
            target_score: 목표 점수
        """
        print("\n" + "=" * 60)
        print("📊 학습 리포트")
        print("=" * 60)

        if report is None:
            print("⚠️  학습 데이터가 없습니다.")
            print("   문제를 먼저 풀어주세요.")
            print("=" * 60)
            return

        # 예상 점수 및 달성률
        print(f"\n🎯 목표 점수: {report.target_score}점")
        print(f"📈 예상 점수: {report.predicted_score:.1f}점")
        print(f"✅ 달성률: {report.achievement_rate:.1f}%")

        # 세부 유형별 정답률
        print("\n📋 세부 유형별 정답률:")
        for subtype, acc in sorted(report.subtype_accuracies.items(), key=lambda x: x[1], reverse=True):
            name = _SUBTYPE_NAMES.get(subtype, subtype.value)
            bar = "█" * int(acc * 10) + "░" * (10 - int(acc * 10))
            print(f"  {name:12s} [{bar}] {acc:.0%}")

        # 강점 영역
        if report.strong_subtypes:
            strong_names = [_SUBTYPE_NAMES.get(s, s.value) for s in report.strong_subtypes]
            print(f"\n💪 강점 영역: {', '.join(strong_names)}")

        # 취약 영역
        if report.weak_subtypes:
            weak_names = [_SUBTYPE_NAMES.get(s, s.value) for s in report.weak_subtypes]
            print(f"\n⚠️  취약 영역: {', '.join(weak_names)}")

        # 학습 방향
        if report.study_directions:
            print("\n📚 학습 방향:")
            for direction in report.study_directions:
                print(f"  • {direction}")

        print("\n" + "=" * 60)
