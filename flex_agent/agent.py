"""
FLEX AI 학습 에이전트 - 전체 흐름 조율 에이전트

학습 세션 초기화, 문제 생성, 채점, 분석, 추천, 난이도 조절의
전체 학습 루프를 조율한다.
"""

import logging
from datetime import datetime
from typing import Optional

from flex_agent.components.analyzer import Analyzer
from flex_agent.components.grader import Grader
from flex_agent.components.question_generator import QuestionGenerator
from flex_agent.components.recommender import Recommender
from flex_agent.components.report_generator import ReportGenerator
from flex_agent.components.score_predictor import ScorePredictor
from flex_agent.exceptions import (
    InvalidAnswerError,
    InvalidScoreError,
    QuestionGenerationError,
)
from flex_agent.models.data_models import Difficulty, MenuChoice, Question, Session
from flex_agent.storage.session_store import SessionStore
from flex_agent.utils import determine_difficulty, validate_score

logger = logging.getLogger(__name__)

# 난이도 자동 조절 기준
_RECENT_COUNT = 5           # 최근 N문제 기준
_UPGRADE_THRESHOLD = 0.8    # 상향 조절 기준 정답률
_DOWNGRADE_THRESHOLD = 0.4  # 하향 조절 기준 정답률

# 난이도 순서 (하향/상향 조절용)
_DIFFICULTY_ORDER = [Difficulty.EASY, Difficulty.MEDIUM, Difficulty.HARD]


class Agent:
    """
    FLEX 학습 전체 흐름을 조율하는 중앙 에이전트.

    세션 초기화 → 문제 생성 → 채점 → 분석 → 추천 → 반복의
    학습 루프를 관리한다.
    """

    def __init__(
        self,
        session_store: SessionStore,
        question_generator: QuestionGenerator,
        grader: Grader,
        analyzer: Analyzer,
        recommender: Recommender,
        score_predictor: ScorePredictor,
        report_generator: ReportGenerator,
    ) -> None:
        self._session_store = session_store
        self._question_generator = question_generator
        self._grader = grader
        self._analyzer = analyzer
        self._recommender = recommender
        self._score_predictor = score_predictor
        self._report_generator = report_generator
        self._session: Optional[Session] = None

    def initialize_session(self, target_score: int, current_score: int) -> Session:
        """
        학습 세션을 초기화한다.

        Args:
            target_score: 목표 점수 (0~600)
            current_score: 현재 예상 점수 (0~600)

        Returns:
            초기화된 Session 객체

        Raises:
            InvalidScoreError: 점수가 0~600 범위를 벗어난 경우
        """
        validate_score(target_score)
        validate_score(current_score)

        difficulty = determine_difficulty(current_score)
        now = datetime.now()

        session = Session(
            target_score=target_score,
            current_difficulty=difficulty,
            created_at=now,
            updated_at=now,
        )

        self._session_store.save(session)
        self._session = session

        print(f"\n✅ 세션이 초기화되었습니다.")
        print(f"   목표 점수: {target_score}점")
        print(f"   현재 예상 점수: {current_score}점 → 초기 난이도: {difficulty.value}")

        return session

    def adjust_difficulty(self) -> Optional[Difficulty]:
        """
        최근 5문제 정답률을 기반으로 난이도를 자동 조절한다.

        Returns:
            변경된 난이도 (변경 없으면 None)
        """
        session = self._session_store.load()
        if session is None or len(session.grade_results) < _RECENT_COUNT:
            return None

        # 최근 5문제 정답률 계산
        recent = session.grade_results[-_RECENT_COUNT:]
        accuracy = sum(r.is_correct for r in recent) / _RECENT_COUNT

        current = session.current_difficulty
        current_idx = _DIFFICULTY_ORDER.index(current)
        new_difficulty: Optional[Difficulty] = None

        if accuracy >= _UPGRADE_THRESHOLD:
            # 상향 조절 (Hard 경계 처리)
            if current_idx < len(_DIFFICULTY_ORDER) - 1:
                new_difficulty = _DIFFICULTY_ORDER[current_idx + 1]
        elif accuracy < _DOWNGRADE_THRESHOLD:
            # 하향 조절 (Easy 경계 처리)
            if current_idx > 0:
                new_difficulty = _DIFFICULTY_ORDER[current_idx - 1]

        if new_difficulty is not None:
            session.current_difficulty = new_difficulty
            session.updated_at = datetime.now()
            self._session_store.save(session)
            self._session = session

            # 난이도 범위 안내
            difficulty_ranges = {
                Difficulty.EASY: "0~350점",
                Difficulty.MEDIUM: "351~450점",
                Difficulty.HARD: "451~600점",
            }
            print(
                f"\n🔄 난이도가 조정되었습니다: {current.value} → {new_difficulty.value} "
                f"(예상 점수 범위: {difficulty_ranges[new_difficulty]})"
            )

        return new_difficulty

    def show_menu(self) -> MenuChoice:
        """
        채점 후 다음 행동 메뉴를 출력하고 사용자 선택을 받는다.

        Returns:
            선택된 MenuChoice
        """
        print("\n" + "-" * 40)
        print("다음 행동을 선택하세요:")
        print("  1. 다음 문제 풀기")
        print("  2. 오답 분석 보기")
        print("  3. 학습 리포트 보기")
        print("  4. 종료")
        print("-" * 40)

        menu_map = {
            "1": MenuChoice.NEXT_QUESTION,
            "2": MenuChoice.ANALYZE,
            "3": MenuChoice.REPORT,
            "4": MenuChoice.QUIT,
        }

        while True:
            choice = input("선택 (1~4): ").strip()
            if choice in menu_map:
                return menu_map[choice]
            print("⚠️  1~4 중에서 선택해 주세요.")

    def run(self) -> None:
        """
        전체 학습 루프를 실행한다.

        세션 초기화 → 문제 생성 → 채점 → 분석 → 추천 → 반복
        """
        print("\n" + "=" * 60)
        print("🎓 FLEX AI 학습 에이전트에 오신 것을 환영합니다!")
        print("=" * 60)

        # 기존 세션 복원 또는 새 세션 초기화
        session = self._session_store.load()
        if session is not None:
            print(f"\n📂 기존 세션을 불러왔습니다.")
            print(f"   목표 점수: {session.target_score}점")
            print(f"   현재 난이도: {session.current_difficulty.value}")
            print(f"   풀이한 문제 수: {len(session.grade_results)}개")
            self._session = session
        else:
            # 새 세션 초기화
            self._session = self._init_new_session()

        # 학습 루프
        current_question: Optional[Question] = None

        while True:
            # 문제가 없으면 새 문제 생성
            if current_question is None:
                current_question = self._generate_next_question()
                if current_question is None:
                    continue

            # 사용자 답안 입력
            user_answer = self._get_user_answer(current_question)
            if user_answer is None:
                continue

            # 채점
            result = self._grader.grade(current_question, user_answer)
            self._grader.display_result(result, current_question)
            current_question = None

            # 난이도 자동 조절
            self.adjust_difficulty()

            # 다음 행동 메뉴
            choice = self.show_menu()

            if choice == MenuChoice.NEXT_QUESTION:
                continue

            elif choice == MenuChoice.ANALYZE:
                self._show_analysis()

            elif choice == MenuChoice.REPORT:
                self._show_report()

            elif choice == MenuChoice.QUIT:
                # 종료 시 최종 리포트 출력
                print("\n📊 최종 학습 리포트를 생성합니다...")
                self._show_report()
                print("\n👋 학습을 종료합니다. 수고하셨습니다!")
                break

    def _init_new_session(self) -> Session:
        """새 세션을 초기화하고 반환한다."""
        print("\n새 학습 세션을 시작합니다.")

        # 목표 점수 입력
        while True:
            try:
                target_score = int(input("목표 점수를 입력하세요 (0~600): ").strip())
                validate_score(target_score)
                break
            except (ValueError, InvalidScoreError) as e:
                print(f"⚠️  {e}")

        # 현재 예상 점수 입력
        while True:
            try:
                current_score = int(input("현재 예상 점수를 입력하세요 (0~600): ").strip())
                validate_score(current_score)
                break
            except (ValueError, InvalidScoreError) as e:
                print(f"⚠️  {e}")

        return self.initialize_session(target_score, current_score)

    def _generate_next_question(self) -> Optional[Question]:
        """다음 문제를 생성하고 출력한다."""
        session = self._session_store.load()
        if session is None:
            return None

        # 분석 결과 기반 추천
        analysis = self._analyzer.analyze(session.grade_results)
        subtype = self._recommender.recommend_subtype(analysis, session.current_difficulty)
        reason = self._recommender.get_recommendation_reason(subtype, analysis)

        print(f"\n{reason}")
        print(f"🔄 문제를 생성 중입니다... (유형: {subtype.value}, 난이도: {session.current_difficulty.value})")

        try:
            question = self._question_generator.generate(subtype, session.current_difficulty)
        except QuestionGenerationError as e:
            print(f"\n❌ 문제 생성에 실패했습니다: {e}")
            retry = input("다시 시도하시겠습니까? (y/n): ").strip().lower()
            if retry == "y":
                return None
            return None

        # 문제 출력
        self._display_question(question)
        return question

    def _display_question(self, question: Question) -> None:
        """문제를 CLI에 출력한다."""
        print("\n" + "=" * 60)
        print(f"📝 [{question.subtype.value} / {question.difficulty.value}]")
        print("\n[지문]")
        print(question.passage)
        print(f"\n[질문] {question.question_text}")
        print()
        for i, choice in enumerate(question.choices, start=1):
            print(f"  {i}. {choice}")
        print("=" * 60)

    def _get_user_answer(self, question: Question) -> Optional[int]:
        """사용자 답안을 입력받는다."""
        while True:
            try:
                answer = int(input("답안을 입력하세요 (1~4): ").strip())
                if 1 <= answer <= 4:
                    return answer
                print("⚠️  1~4 사이의 숫자를 입력해 주세요.")
            except ValueError:
                print("⚠️  숫자를 입력해 주세요.")

    def _show_analysis(self) -> None:
        """오답 분석 결과를 출력한다."""
        session = self._session_store.load()
        if session is None or not session.grade_results:
            print("\n⚠️  분석할 데이터가 없습니다. 문제를 먼저 풀어주세요.")
            return

        analysis = self._analyzer.analyze(session.grade_results)

        print("\n" + "=" * 50)
        print("📊 오답 분석 결과")
        print("=" * 50)

        if analysis.warning_message:
            print(f"\n⚠️  {analysis.warning_message}")

        print(f"\n전체 정답률: {analysis.total_accuracy:.0%}")
        print("\n세부 유형별 정답률:")

        subtype_names = {
            "Topic": "주제 찾기",
            "Detail": "세부 내용 파악",
            "TrueFalse": "진위 판단",
            "Letter": "편지글",
            "Advertisement": "광고문",
            "Academic": "학술 지문",
        }

        for subtype, acc in sorted(analysis.subtype_accuracies.items(), key=lambda x: x[1]):
            name = subtype_names.get(subtype.value, subtype.value)
            status = "⚠️ 취약" if subtype in analysis.weak_subtypes else "✅"
            print(f"  {name:12s}: {acc:.0%} {status}")

        print("=" * 50)

    def _show_report(self) -> None:
        """학습 리포트를 생성하고 출력한다."""
        session = self._session_store.load()
        if session is None:
            print("\n⚠️  세션 데이터를 불러올 수 없습니다.")
            return

        report = self._report_generator.generate(session)
        self._report_generator.display(report, session.target_score)
