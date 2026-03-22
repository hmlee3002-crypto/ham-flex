"""
FLEX AI 학습 에이전트 - Streamlit 웹 앱
"""

import os
import streamlit as st
from datetime import datetime

from flex_agent.components.analyzer import Analyzer
from flex_agent.components.grader import Grader
from flex_agent.components.question_generator import QuestionGenerator
from flex_agent.components.recommender import Recommender
from flex_agent.components.report_generator import ReportGenerator
from flex_agent.components.score_predictor import ScorePredictor
from flex_agent.exceptions import InvalidScoreError, QuestionGenerationError
from flex_agent.llm.llm_client import LLMClient
from flex_agent.models.data_models import Difficulty, MenuChoice, ReadingSubtype, Session
from flex_agent.storage.session_store import SessionStore
from flex_agent.utils import determine_difficulty, validate_score

# ─────────────────────────────────────────────
# 페이지 설정
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="FLEX AI 학습 에이전트",
    page_icon="🎓",
    layout="wide",
)

# ─────────────────────────────────────────────
# 세부 유형 한국어 이름
# ─────────────────────────────────────────────
SUBTYPE_NAMES = {
    ReadingSubtype.TOPIC: "주제 찾기",
    ReadingSubtype.DETAIL: "세부 내용 파악",
    ReadingSubtype.TRUE_FALSE: "진위 판단",
    ReadingSubtype.LETTER: "편지글",
    ReadingSubtype.ADVERTISEMENT: "광고문",
    ReadingSubtype.ACADEMIC: "학술 지문",
}

DIFFICULTY_RANGES = {
    Difficulty.EASY: "0~350점",
    Difficulty.MEDIUM: "351~450점",
    Difficulty.HARD: "451~600점",
}

# ─────────────────────────────────────────────
# 컴포넌트 초기화 (캐시)
# ─────────────────────────────────────────────
@st.cache_resource
def get_components(api_key: str):
    """API 키를 받아 stateless 컴포넌트를 초기화한다. (Recommender 제외)"""
    session_store = SessionStore()
    llm_client = LLMClient(api_key=api_key)
    analyzer = Analyzer()
    score_predictor = ScorePredictor(session_store)
    grader = Grader(session_store)
    question_generator = QuestionGenerator(llm_client, session_store)
    report_generator = ReportGenerator(score_predictor, analyzer, session_store)
    return {
        "session_store": session_store,
        "llm_client": llm_client,
        "analyzer": analyzer,
        "score_predictor": score_predictor,
        "grader": grader,
        "question_generator": question_generator,
        "report_generator": report_generator,
    }


def get_recommender() -> Recommender:
    """Recommender는 session_state에서 관리한다 (상태 보존)."""
    if "recommender" not in st.session_state:
        st.session_state.recommender = Recommender()
    return st.session_state.recommender


# ─────────────────────────────────────────────
# 사이드바: API 키 및 세션 설정
# ─────────────────────────────────────────────
def render_sidebar():
    with st.sidebar:
        st.title("🎓 FLEX AI 학습 에이전트")
        st.markdown("---")

        # Secrets에서 API 키 자동 로드
        try:
            api_key = st.secrets["GROQ_API_KEY"]
        except (KeyError, FileNotFoundError):
            api_key = ""
            st.error("⚠️ GROQ_API_KEY가 설정되지 않았습니다. Streamlit Cloud Secrets를 확인해 주세요.")
            st.stop()

        st.markdown("---")
        st.subheader("📋 세션 설정")

        target_score = st.number_input(
            "목표 점수 (0~600)",
            min_value=0, max_value=600, value=450, step=10,
        )
        current_score = st.number_input(
            "현재 예상 점수 (0~600)",
            min_value=0, max_value=600, value=300, step=10,
        )

        if st.button("🚀 새 세션 시작", use_container_width=True):
            if not api_key:
                st.error("API 키를 입력해 주세요.")
            else:
                _start_new_session(api_key, target_score, current_score)

        # 기존 세션 불러오기
        if st.button("📂 기존 세션 불러오기", use_container_width=True):
            if not api_key:
                st.error("API 키를 입력해 주세요.")
            else:
                _load_existing_session(api_key)

        # 세션 초기화
        if st.button("🗑️ 세션 초기화", use_container_width=True):
            _clear_session()

        # 현재 세션 상태 표시
        if "session" in st.session_state and st.session_state.session:
            session: Session = st.session_state.session
            st.markdown("---")
            st.subheader("📊 현재 세션")
            st.metric("목표 점수", f"{session.target_score}점")
            st.metric("현재 난이도", session.current_difficulty.value)
            st.metric("풀이한 문제", f"{len(session.grade_results)}개")
            if session.grade_results:
                correct = sum(r.is_correct for r in session.grade_results)
                st.metric("정답률", f"{correct / len(session.grade_results):.0%}")

        return api_key


def _start_new_session(api_key: str, target_score: int, current_score: int):
    """새 세션을 초기화한다."""
    try:
        validate_score(target_score)
        validate_score(current_score)
    except InvalidScoreError as e:
        st.sidebar.error(str(e))
        return

    comps = get_components(api_key)
    session_store: SessionStore = comps["session_store"]
    session_store.clear()

    difficulty = determine_difficulty(current_score)
    now = datetime.now()
    session = Session(
        target_score=target_score,
        current_difficulty=difficulty,
        created_at=now,
        updated_at=now,
    )
    session_store.save(session)

    # st.session_state 초기화
    st.session_state.session = session
    st.session_state.api_key = api_key
    st.session_state.current_question = None
    st.session_state.grade_result = None
    st.session_state.page = "quiz"
    st.session_state.recommender = Recommender()  # 새 세션마다 초기화
    st.sidebar.success(
        f"세션 시작! 초기 난이도: {difficulty.value} ({DIFFICULTY_RANGES[difficulty]})"
    )
    st.rerun()


def _load_existing_session(api_key: str):
    """기존 세션을 불러온다."""
    comps = get_components(api_key)
    session_store: SessionStore = comps["session_store"]
    session = session_store.load()
    if session:
        st.session_state.session = session
        st.session_state.api_key = api_key
        st.session_state.current_question = None
        st.session_state.grade_result = None
        st.session_state.page = "quiz"
        st.sidebar.success(
            f"세션 불러오기 완료! (풀이한 문제: {len(session.grade_results)}개)"
        )
        st.rerun()
    else:
        st.sidebar.warning("저장된 세션이 없습니다. 새 세션을 시작해 주세요.")


def _clear_session():
    """세션을 초기화한다."""
    if "api_key" in st.session_state:
        comps = get_components(st.session_state.api_key)
        comps["session_store"].clear()
    for key in ["session", "current_question", "grade_result", "page", "active_tab", "recommender"]:
        st.session_state.pop(key, None)
    st.sidebar.success("세션이 초기화되었습니다.")
    st.rerun()


# ─────────────────────────────────────────────
# 퀴즈 페이지
# ─────────────────────────────────────────────
def render_quiz_page():
    session: Session = st.session_state.session
    api_key: str = st.session_state.api_key
    comps = get_components(api_key)

    st.title("📝 문제 풀기")

    # 난이도 자동 조절 체크
    _maybe_adjust_difficulty(session, comps)

    # 채점 결과가 있으면 먼저 표시
    if st.session_state.get("grade_result") and st.session_state.get("current_question"):
        _render_grade_result()
        return

    # 문제 생성 또는 기존 문제 표시
    question = st.session_state.get("current_question")

    if question is None:
        if st.button("🔄 문제 생성하기", use_container_width=True):
            _generate_question(session, comps)
        else:
            st.info("'문제 생성하기' 버튼을 눌러 문제를 시작하세요.")
        return

    # 문제 표시
    st.markdown(f"**유형:** {SUBTYPE_NAMES.get(question.subtype, str(question.subtype))} | **난이도:** {question.difficulty.value if hasattr(question.difficulty, 'value') else question.difficulty}")
    st.markdown("---")
    st.subheader("📖 지문")
    st.markdown(f"> {question.passage}")
    st.markdown("---")
    st.subheader(f"❓ {question.question_text}")

    # 선택지 라디오
    choice_labels = [f"{i+1}. {c}" for i, c in enumerate(question.choices)]
    selected = st.radio("답안을 선택하세요:", choice_labels, index=None, key="answer_radio")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("✅ 제출", use_container_width=True, disabled=(selected is None)):
            if selected:
                answer_num = int(selected[0])  # "1. ..." → 1
                grader = comps["grader"]
                result = grader.grade(question, answer_num)
                # 세션 갱신
                st.session_state.session = comps["session_store"].load()
                st.session_state.grade_result = result
                st.rerun()
    with col2:
        if st.button("⏭️ 문제 건너뛰기", use_container_width=True):
            st.session_state.current_question = None
            st.session_state.grade_result = None
            st.rerun()


def _generate_question(session: Session, comps: dict):
    """다음 문제를 생성한다."""
    analyzer = comps["analyzer"]
    recommender = get_recommender()
    question_generator = comps["question_generator"]

    analysis = analyzer.analyze(session.grade_results)
    subtype = recommender.recommend_subtype(analysis, session.current_difficulty)

    subtype_label = SUBTYPE_NAMES.get(subtype, subtype.value)

    with st.spinner(f"문제 생성 중... (유형: {subtype_label}, 난이도: {session.current_difficulty.value})"):
        try:
            question = question_generator.generate(subtype, session.current_difficulty)
            st.session_state.current_question = question
            st.session_state.grade_result = None
            st.rerun()
        except QuestionGenerationError as e:
            st.error(f"문제 생성 실패: {e}")


def _render_grade_result():
    """채점 결과를 표시하고 다음 행동을 선택한다."""
    result = st.session_state.grade_result
    question = st.session_state.current_question

    if result.is_correct:
        st.success("✅ 정답입니다!")
    else:
        st.error(f"❌ 오답입니다. 정답은 **{result.correct_answer}번** 입니다. (입력: {result.user_answer}번)")

    # 문제 + 해설 함께 표시
    with st.expander("📖 문제 및 해설 보기", expanded=True):
        st.markdown("**[지문]**")
        st.markdown(f"> {question.passage}")
        st.markdown(f"**[질문]** {question.question_text}")
        for i, choice in enumerate(question.choices, start=1):
            prefix = "✅ " if i == result.correct_answer else ("❌ " if i == result.user_answer else "　 ")
            st.markdown(f"{prefix}{i}. {choice}")
        st.markdown("---")
        st.markdown(f"**해설:** {question.explanation}")

    st.markdown("---")
    st.subheader("다음 행동을 선택하세요")
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("➡️ 다음 문제", use_container_width=True, key="grade_next"):
            st.session_state.current_question = None
            st.session_state.grade_result = None
            st.rerun()
    with col2:
        if st.button("📊 오답 분석", use_container_width=True, key="grade_analysis"):
            st.session_state.current_question = None
            st.session_state.grade_result = None
            st.session_state.active_tab = "analysis"
            st.rerun()
    with col3:
        if st.button("📋 학습 리포트", use_container_width=True, key="grade_report"):
            st.session_state.current_question = None
            st.session_state.grade_result = None
            st.session_state.active_tab = "report"
            st.rerun()


def _maybe_adjust_difficulty(session: Session, comps: dict):
    """최근 5문제 기준으로 난이도를 자동 조절한다."""
    RECENT_COUNT = 5
    UPGRADE_THRESHOLD = 0.8
    DOWNGRADE_THRESHOLD = 0.4
    DIFFICULTY_ORDER = [Difficulty.EASY, Difficulty.MEDIUM, Difficulty.HARD]

    results = session.grade_results
    if len(results) < RECENT_COUNT:
        return

    # 마지막 문제가 방금 채점된 경우에만 체크 (5의 배수)
    if len(results) % RECENT_COUNT != 0:
        return

    recent = results[-RECENT_COUNT:]
    accuracy = sum(r.is_correct for r in recent) / RECENT_COUNT
    current = session.current_difficulty
    current_idx = DIFFICULTY_ORDER.index(current)
    new_difficulty = None

    if accuracy >= UPGRADE_THRESHOLD and current_idx < len(DIFFICULTY_ORDER) - 1:
        new_difficulty = DIFFICULTY_ORDER[current_idx + 1]
    elif accuracy < DOWNGRADE_THRESHOLD and current_idx > 0:
        new_difficulty = DIFFICULTY_ORDER[current_idx - 1]

    if new_difficulty:
        session.current_difficulty = new_difficulty
        session.updated_at = datetime.now()
        comps["session_store"].save(session)
        st.session_state.session = session
        st.toast(
            f"🔄 난이도 조정: {current.value} → {new_difficulty.value} "
            f"({DIFFICULTY_RANGES[new_difficulty]})",
            icon="🔄",
        )


# ─────────────────────────────────────────────
# 오답 분석 페이지
# ─────────────────────────────────────────────
def render_analysis_page():
    session: Session = st.session_state.session
    api_key: str = st.session_state.api_key
    comps = get_components(api_key)

    st.title("📊 오답 분석")

    if not session.grade_results:
        st.warning("분석할 데이터가 없습니다. 문제를 먼저 풀어주세요.")
        if st.button("문제 풀러 가기", key="analysis_to_quiz"):
            st.session_state.active_tab = "quiz"
            st.rerun()
        return

    analyzer = comps["analyzer"]
    analysis = analyzer.analyze(session.grade_results)

    if analysis.warning_message:
        st.warning(analysis.warning_message)

    # 전체 정답률
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("전체 정답률", f"{analysis.total_accuracy:.0%}")
    with col2:
        st.metric("풀이한 문제", f"{len(session.grade_results)}개")
    with col3:
        correct = sum(r.is_correct for r in session.grade_results)
        st.metric("정답 수", f"{correct}개")

    st.markdown("---")
    st.subheader("세부 유형별 정답률")

    # 정답률 바 차트
    subtype_data = {
        SUBTYPE_NAMES.get(subtype, str(subtype)): round(acc * 100, 1)
        for subtype, acc in sorted(analysis.subtype_accuracies.items(), key=lambda x: x[1])
    }
    if subtype_data:
        st.bar_chart(subtype_data)

    # 취약 영역 강조
    if analysis.weak_subtypes:
        st.subheader("⚠️ 취약 영역")
        for subtype in analysis.weak_subtypes:
            acc = analysis.subtype_accuracies.get(subtype, 0)
            st.error(f"**{SUBTYPE_NAMES.get(subtype, str(subtype))}**: 정답률 {acc:.0%}")

    if st.button("➡️ 문제 풀러 가기", use_container_width=True, key="analysis_go_quiz"):
        st.session_state.active_tab = "quiz"
        st.rerun()


# ─────────────────────────────────────────────
# 학습 리포트 페이지
# ─────────────────────────────────────────────
def render_report_page():
    session: Session = st.session_state.session
    api_key: str = st.session_state.api_key
    comps = get_components(api_key)

    st.title("📋 학습 리포트")

    if not session.grade_results:
        st.warning("리포트를 생성할 데이터가 없습니다. 문제를 먼저 풀어주세요.")
        if st.button("문제 풀러 가기", key="report_to_quiz"):
            st.session_state.active_tab = "quiz"
            st.rerun()
        return

    report_generator = comps["report_generator"]
    report = report_generator.generate(session)
    # 세션 갱신 (리포트 저장됨)
    st.session_state.session = comps["session_store"].load()

    if report is None:
        st.warning("리포트 생성에 실패했습니다.")
        return

    # 핵심 지표
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("예상 점수", f"{report.predicted_score:.1f}점")
    with col2:
        st.metric("목표 점수", f"{report.target_score}점")
    with col3:
        delta_color = "normal" if report.achievement_rate >= 80 else "inverse"
        st.metric("달성률", f"{report.achievement_rate:.1f}%")

    st.markdown("---")

    # 세부 유형별 정답률
    st.subheader("📈 세부 유형별 정답률")
    subtype_data = {
        SUBTYPE_NAMES.get(subtype, str(subtype)): round(acc * 100, 1)
        for subtype, acc in sorted(report.subtype_accuracies.items(), key=lambda x: x[1], reverse=True)
    }
    if subtype_data:
        st.bar_chart(subtype_data)

    col_strong, col_weak = st.columns(2)
    with col_strong:
        if report.strong_subtypes:
            st.subheader("💪 강점 영역")
            for subtype in report.strong_subtypes:
                acc = report.subtype_accuracies.get(subtype, 0)
                st.success(f"**{SUBTYPE_NAMES.get(subtype, str(subtype))}**: {acc:.0%}")
        else:
            st.subheader("💪 강점 영역")
            st.info("아직 강점 영역이 없습니다.")

    with col_weak:
        if report.weak_subtypes:
            st.subheader("⚠️ 취약 영역")
            for subtype in report.weak_subtypes:
                acc = report.subtype_accuracies.get(subtype, 0)
                st.error(f"**{SUBTYPE_NAMES.get(subtype, str(subtype))}**: {acc:.0%}")
        else:
            st.subheader("⚠️ 취약 영역")
            st.success("취약 영역이 없습니다. 훌륭해요!")

    # 학습 방향
    if report.study_directions:
        st.markdown("---")
        st.subheader("📚 학습 방향")
        for direction in report.study_directions:
            st.info(direction)

    if st.button("➡️ 계속 학습하기", use_container_width=True, key="report_go_quiz"):
        st.session_state.active_tab = "quiz"
        st.rerun()


# ─────────────────────────────────────────────
# 메인 라우터
# ─────────────────────────────────────────────
def main():
    api_key = render_sidebar()

    # 세션이 없으면 시작 화면
    if "session" not in st.session_state or not st.session_state.session:
        st.title("🎓 FLEX AI 학습 에이전트")
        st.markdown("""
        FLEX 중국어 시험 독해 영역을 AI로 대비하세요.

        **시작 방법:**
        1. 왼쪽 사이드바에 OpenAI API 키를 입력하세요.
        2. 목표 점수와 현재 예상 점수를 설정하세요.
        3. '새 세션 시작' 버튼을 누르세요.

        **주요 기능:**
        - 🤖 AI 기반 FLEX 스타일 문제 자동 생성
        - 📊 세부 유형별 오답 분석
        - 📈 예상 점수 예측 및 학습 리포트
        - 🔄 정답률 기반 난이도 자동 조절
        """)
        return

    # 페이지 라우팅
    page = st.session_state.get("active_tab", "quiz")

    # 상단 네비게이션 버튼
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("📝 문제 풀기", use_container_width=True, key="nav_quiz",
                     type="primary" if page == "quiz" else "secondary"):
            st.session_state.active_tab = "quiz"
            st.rerun()
    with col2:
        if st.button("📊 오답 분석", use_container_width=True, key="nav_analysis",
                     type="primary" if page == "analysis" else "secondary"):
            st.session_state.active_tab = "analysis"
            st.rerun()
    with col3:
        if st.button("📋 학습 리포트", use_container_width=True, key="nav_report",
                     type="primary" if page == "report" else "secondary"):
            st.session_state.active_tab = "report"
            st.rerun()

    st.markdown("---")

    if page == "quiz":
        render_quiz_page()
    elif page == "analysis":
        render_analysis_page()
    elif page == "report":
        render_report_page()
    else:
        render_quiz_page()


if __name__ == "__main__":
    main()
