"""
FLEX AI 학습 에이전트 - CLI 진입점

환경변수에서 OpenAI API 키를 읽어 에이전트를 초기화하고 실행한다.
"""

import logging
import os
import sys

logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)


def main() -> None:
    """
    FLEX AI 학습 에이전트 메인 진입점.

    환경변수 OPENAI_API_KEY를 읽어 에이전트를 초기화하고 실행한다.
    """
    # OpenAI API 키 확인
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("❌ 오류: OPENAI_API_KEY 환경변수가 설정되어 있지 않습니다.")
        print("   export OPENAI_API_KEY='your-api-key' 명령으로 설정해 주세요.")
        sys.exit(1)

    # 컴포넌트 초기화 (의존성 주입)
    from flex_agent.agent import Agent
    from flex_agent.components.analyzer import Analyzer
    from flex_agent.components.grader import Grader
    from flex_agent.components.question_generator import QuestionGenerator
    from flex_agent.components.recommender import Recommender
    from flex_agent.components.report_generator import ReportGenerator
    from flex_agent.components.score_predictor import ScorePredictor
    from flex_agent.llm.llm_client import LLMClient
    from flex_agent.storage.session_store import SessionStore

    session_store = SessionStore()
    llm_client = LLMClient(api_key=api_key)
    question_generator = QuestionGenerator(llm_client=llm_client, session_store=session_store)
    grader = Grader(session_store=session_store)
    analyzer = Analyzer()
    recommender = Recommender()
    score_predictor = ScorePredictor(session_store=session_store)
    report_generator = ReportGenerator(
        score_predictor=score_predictor,
        analyzer=analyzer,
        session_store=session_store,
    )

    agent = Agent(
        session_store=session_store,
        question_generator=question_generator,
        grader=grader,
        analyzer=analyzer,
        recommender=recommender,
        score_predictor=score_predictor,
        report_generator=report_generator,
    )

    agent.run()


if __name__ == "__main__":
    main()
