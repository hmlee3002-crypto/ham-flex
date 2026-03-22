"""
FLEX AI 학습 에이전트 - 채점기

사용자 답안을 채점하고 정오 여부 및 해설을 출력한다.
"""

from datetime import datetime

from flex_agent.exceptions import InvalidAnswerError
from flex_agent.models.data_models import GradeResult, Question
from flex_agent.storage.session_store import SessionStore


class Grader:
    """
    사용자 답안 채점 및 해설 출력 컴포넌트.

    채점 결과를 SessionStore에 저장한다.
    """

    def __init__(self, session_store: SessionStore) -> None:
        """
        Args:
            session_store: 세션 저장소
        """
        self._session_store = session_store

    def grade(self, question: Question, user_answer: int) -> GradeResult:
        """
        사용자 답안을 채점한다.

        Args:
            question: 채점할 문제
            user_answer: 사용자 답안 (1~4)

        Returns:
            채점 결과 GradeResult 객체

        Raises:
            InvalidAnswerError: 1~4 범위를 벗어난 답안 입력 시
        """
        if not (1 <= user_answer <= 4):
            raise InvalidAnswerError(
                f"답안은 1~4 사이의 정수여야 합니다. 입력값: {user_answer}"
            )

        result = GradeResult(
            question_id=question.id,
            subtype=question.subtype,
            difficulty=question.difficulty,
            user_answer=user_answer,
            correct_answer=question.correct_answer,
            is_correct=(user_answer == question.correct_answer),
            graded_at=datetime.now(),
        )

        # 채점 결과를 세션에 저장
        session = self._session_store.load()
        if session is not None:
            session.grade_results.append(result)
            session.updated_at = datetime.now()
            self._session_store.save(session)

        return result

    def display_result(self, result: GradeResult, question: Question) -> None:
        """
        채점 결과(정오 여부 + 해설)를 CLI에 출력한다.

        Args:
            result: 채점 결과
            question: 채점된 문제 (해설 출력용)
        """
        print("\n" + "=" * 50)
        if result.is_correct:
            print("✅ 정답입니다!")
        else:
            print(f"❌ 오답입니다. 정답은 {result.correct_answer}번입니다.")
            print(f"   (입력한 답: {result.user_answer}번)")

        print(f"\n📖 해설:\n{question.explanation}")
        print("=" * 50)
