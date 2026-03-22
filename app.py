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
    layout="centered",
)

# 전역 CSS
st.markdown("""
<style>
/* 전체 배경 그라데이션 */
.stApp {
    background: linear-gradient(160deg, #e8faf9 0%, #d0f0ee 40%, #eef4ff 100%);
    min-height: 100vh;
}

/* 기본 텍스트 */
body, .stMarkdown, p, div { font-family: 'Inter', 'Apple SD Gothic Neo', sans-serif; }

/* 흰색 둥근 카드 */
.card {
    background: #ffffff;
    border-radius: 20px;
    padding: 24px 28px;
    margin-bottom: 16px;
    box-shadow: 0 2px 16px rgba(83,207,202,0.10);
}
.card-title {
    font-size: 16px;
    font-weight: 700;
    color: #1a1a1a;
    margin-bottom: 4px;
}
.card-subtitle {
    font-size: 13px;
    color: #888;
    margin-bottom: 18px;
}

/* 민트 그라데이션 카드 */
.card-mint {
    background: linear-gradient(135deg, #53cfca 0%, #38b2ac 100%);
    border-radius: 20px;
    padding: 24px 28px;
    margin-bottom: 16px;
    color: #fff;
}

/* 통계 박스 */
.stat-box {
    background: #ffffff;
    border-radius: 16px;
    padding: 16px;
    text-align: center;
    box-shadow: 0 2px 12px rgba(83,207,202,0.10);
}
.stat-value {
    font-size: 26px;
    font-weight: 800;
    color: #53cfca;
}
.stat-label {
    font-size: 12px;
    color: #999;
    margin-top: 2px;
}

/* 유형별 정답률 행 */
.subtype-row { margin-bottom: 18px; }
.subtype-label { font-size: 14px; color: #444; margin-bottom: 4px; font-weight: 500; }
.subtype-score { font-size: 15px; font-weight: 700; margin-bottom: 6px; }

/* 진행 바 */
.bar-bg {
    background-color: #e8f8f7;
    border-radius: 99px;
    height: 8px;
    width: 100%;
}
.bar-fill {
    background: linear-gradient(90deg, #53cfca, #38b2ac);
    border-radius: 99px;
    height: 8px;
}
.bar-fill-weak {
    background: linear-gradient(90deg, #ff8a80, #ff5252);
    border-radius: 99px;
    height: 8px;
}

/* 버튼 스타일 오버라이드 */
.stButton > button {
    border-radius: 12px !important;
    font-weight: 600 !important;
}
.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #53cfca, #38b2ac) !important;
    border: none !important;
    color: white !important;
}

/* 입력 필드 */
.stNumberInput > div > div > input,
.stRadio { border-radius: 12px !important; }

/* 상단 상태 바 */
.status-bar {
    background: #ffffff;
    border-radius: 16px;
    padding: 12px 20px;
    display: flex;
    gap: 24px;
    align-items: center;
    margin-bottom: 16px;
    box-shadow: 0 2px 12px rgba(83,207,202,0.10);
    flex-wrap: wrap;
}
.status-item-label { font-size: 11px; color: #999; }
.status-item-value { font-size: 15px; font-weight: 700; color: #1a1a1a; }
.status-item-value.mint { color: #53cfca; }
</style>
""", unsafe_allow_html=True)

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

DIFFICULTY_NAMES = {
    Difficulty.EASY: "쉬움",
    Difficulty.MEDIUM: "보통",
    Difficulty.HARD: "어려움",
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
# API 키 로드
# ─────────────────────────────────────────────
def get_api_key() -> str:
    try:
        return st.secrets["GROQ_API_KEY"]
    except (KeyError, FileNotFoundError):
        st.error("⚠️ GROQ_API_KEY가 설정되지 않았습니다. Streamlit Cloud Secrets를 확인해 주세요.")
        st.stop()
        return ""


# ─────────────────────────────────────────────
# 홈 화면
# ─────────────────────────────────────────────
def render_home(api_key: str):
    st.markdown("""
    <div style="padding: 40px 0 8px 0;">
        <div style="font-size:13px; color:#53cfca; font-weight:600; letter-spacing:1px; text-transform:uppercase;">FLEX AI</div>
        <div style="font-size:32px; font-weight:800; color:#1a1a1a; margin-top:4px; line-height:1.2;">학습 에이전트</div>
        <div style="font-size:15px; color:#888; margin-top:8px;">FLEX 중국어 독해 영역을 AI로 대비하세요</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    target_score = st.number_input(
        "목표 점수 (0~600)",
        min_value=0, max_value=600, value=450, step=10,
        key="home_target",
    )

    difficulty_option = st.radio(
        "시작 난이도",
        options=["쉬움 (0~350점)", "보통 (351~450점)", "어려움 (451~600점)"],
        horizontal=True,
        key="home_difficulty",
    )
    difficulty_map = {
        "쉬움 (0~350점)": (Difficulty.EASY, 300),
        "보통 (351~450점)": (Difficulty.MEDIUM, 400),
        "어려움 (451~600점)": (Difficulty.HARD, 500),
    }
    selected_difficulty, current_score = difficulty_map[difficulty_option]

    col_start, col_load = st.columns(2)
    with col_start:
        if st.button("새 세션 시작", use_container_width=True, type="primary", key="home_start"):
            _start_new_session(api_key, target_score, current_score)
    with col_load:
        if st.button("이어하기", use_container_width=True, key="home_load"):
            _load_existing_session(api_key)

    st.markdown("<br>", unsafe_allow_html=True)

    st.markdown('<div style="font-size:13px;font-weight:600;color:#888;margin:20px 0 10px;">주요 기능</div>', unsafe_allow_html=True)

    features = [
        ("1", "문제 자동 생성", "FLEX 스타일 중국어 독해 문제를 즉시 생성"),
        ("2", "오답 분석", "취약 유형을 시각적으로 파악"),
        ("3", "예상 점수", "풀이 데이터 기반 점수 예측"),
        ("4", "난이도 조절", "정답률에 따라 자동으로 조정"),
    ]
    for num, title, desc in features:
        st.markdown(f"""
        <div style="background:#fff;border-radius:12px;padding:10px 14px;margin-bottom:8px;
                    box-shadow:0 1px 6px rgba(83,207,202,0.08);display:flex;gap:12px;align-items:center;">
            <div style="min-width:22px;height:22px;background:linear-gradient(135deg,#53cfca,#38b2ac);
                        border-radius:50%;display:flex;align-items:center;justify-content:center;
                        font-size:11px;font-weight:800;color:#fff;flex-shrink:0;">{num}</div>
            <div>
                <span style="font-size:13px;font-weight:700;color:#1a1a1a;">{title}</span>
                <span style="font-size:12px;color:#bbb;margin-left:8px;">{desc}</span>
            </div>
        </div>""", unsafe_allow_html=True)


def _start_new_session(api_key: str, target_score: int, current_score: int):
    """새 세션을 초기화한다."""
    try:
        validate_score(target_score)
        validate_score(current_score)
    except InvalidScoreError as e:
        st.error(str(e))
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

    st.session_state.session = session
    st.session_state.api_key = api_key
    st.session_state.current_question = None
    st.session_state.grade_result = None
    st.session_state.active_tab = "quiz"
    st.session_state.recommender = Recommender()
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
        st.session_state.active_tab = "quiz"
        st.rerun()
    else:
        st.warning("저장된 세션이 없습니다. 새 세션을 시작해 주세요.")


def _clear_session():
    """세션을 초기화한다."""
    if "api_key" in st.session_state:
        comps = get_components(st.session_state.api_key)
        comps["session_store"].clear()
    for key in ["session", "current_question", "grade_result", "page", "active_tab", "recommender"]:
        st.session_state.pop(key, None)
    st.rerun()


# ─────────────────────────────────────────────
# 퀴즈 페이지
# ─────────────────────────────────────────────
def render_quiz_page():
    session: Session = st.session_state.session
    api_key: str = st.session_state.api_key
    comps = get_components(api_key)

    # 난이도 자동 조절 체크
    _maybe_adjust_difficulty(session, comps)

    # 채점 결과가 있으면 먼저 표시
    if st.session_state.get("grade_result") and st.session_state.get("current_question"):
        _render_grade_result()
        return

    # 문제 생성 또는 기존 문제 표시
    question = st.session_state.get("current_question")

    if question is None:
        # 자동으로 문제 생성 (버튼 없이)
        _generate_question(session, comps)
        return

    # 문제 표시
    # subtype/difficulty를 enum으로 안전하게 변환
    subtype = question.subtype
    difficulty = question.difficulty
    if isinstance(subtype, str):
        try:
            subtype = ReadingSubtype(subtype)
        except ValueError:
            pass
    if isinstance(difficulty, str):
        try:
            difficulty = Difficulty(difficulty)
        except ValueError:
            pass

    subtype_label = SUBTYPE_NAMES.get(subtype, subtype.value if hasattr(subtype, "value") else subtype)
    difficulty_label = DIFFICULTY_NAMES.get(difficulty, difficulty.value if hasattr(difficulty, "value") else difficulty)

    st.markdown(f"**유형:** {subtype_label} | **난이도:** {difficulty_label}")
    st.markdown("---")
    st.subheader("지문")
    st.markdown(f"> {question.passage}")
    st.markdown("---")
    st.subheader(question.question_text)

    # 선택지 라디오
    choice_labels = [f"{i+1}. {c}" for i, c in enumerate(question.choices)]
    selected = st.radio("답안을 선택하세요:", choice_labels, index=None, key="answer_radio")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("제출", use_container_width=True, disabled=(selected is None)):
            if selected:
                answer_num = int(selected[0])  # "1. ..." → 1
                grader = comps["grader"]
                result = grader.grade(question, answer_num)
                # 세션 갱신
                st.session_state.session = comps["session_store"].load()
                st.session_state.grade_result = result
                st.rerun()
    with col2:
        if st.button("문제 건너뛰기", use_container_width=True):
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
        st.success("정답입니다!")
    else:
        st.error(f"오답입니다. 정답은 {result.correct_answer}번 입니다. (입력: {result.user_answer}번)")

    # 문제 + 해설 함께 표시
    with st.expander("문제 및 해설 보기", expanded=True):
        st.markdown("**[지문]**")
        st.markdown(f"> {question.passage}")
        st.markdown(f"**[질문]** {question.question_text}")

        choices_html = ""
        for i, choice in enumerate(question.choices, start=1):
            is_correct = (i == result.correct_answer)
            is_wrong = (i == result.user_answer and not result.is_correct)
            if is_correct:
                choices_html += f"""
                <div style="background:#e6faf8;border:2px solid #53cfca;border-radius:10px;
                            padding:10px 16px;margin:6px 0;display:flex;align-items:center;gap:10px;">
                    <span style="color:#53cfca;font-weight:900;font-size:16px;">●</span>
                    <span style="font-weight:600;color:#1a1a1a;">{i}. {choice}</span>
                </div>"""
            elif is_wrong:
                choices_html += f"""
                <div style="background:#fff0f0;border:2px solid #ff5252;border-radius:10px;
                            padding:10px 16px;margin:6px 0;display:flex;align-items:center;gap:10px;">
                    <span style="color:#ff5252;font-weight:900;font-size:16px;">✕</span>
                    <span style="color:#ff5252;">{i}. {choice}</span>
                </div>"""
            else:
                choices_html += f"""
                <div style="background:#f9f9f9;border:1px solid #e0e0e0;border-radius:10px;
                            padding:10px 16px;margin:6px 0;display:flex;align-items:center;gap:10px;">
                    <span style="color:#ccc;font-size:16px;">○</span>
                    <span style="color:#666;">{i}. {choice}</span>
                </div>"""

        st.markdown(choices_html, unsafe_allow_html=True)
        st.markdown("---")
        st.markdown(f"**해설:** {question.explanation}")

    st.markdown("---")
    st.subheader("다음 행동을 선택하세요")
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("다음 문제", use_container_width=True, key="grade_next"):
            st.session_state.current_question = None
            st.session_state.grade_result = None
            st.rerun()
    with col2:
        if st.button("오답 분석", use_container_width=True, key="grade_analysis"):
            st.session_state.current_question = None
            st.session_state.grade_result = None
            st.session_state.active_tab = "analysis"
            st.rerun()
    with col3:
        if st.button("학습 리포트", use_container_width=True, key="grade_report"):
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
    # 문자열로 저장된 경우 enum으로 변환
    if isinstance(current, str):
        try:
            current = Difficulty(current)
            session.current_difficulty = current
        except ValueError:
            return
    if current not in DIFFICULTY_ORDER:
        return
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
            f"🔄 난이도 조정: {DIFFICULTY_NAMES.get(current, current.value)} → {DIFFICULTY_NAMES.get(new_difficulty, new_difficulty.value)} "
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

    # 상단 통계 카드
    total = len(session.grade_results)
    correct = sum(r.is_correct for r in session.grade_results)
    accuracy_pct = int(analysis.total_accuracy * 100)

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(f"""
        <div class="stat-box">
            <div class="stat-value">{accuracy_pct}%</div>
            <div class="stat-label">전체 정답률</div>
        </div>""", unsafe_allow_html=True)
    with col2:
        st.markdown(f"""
        <div class="stat-box">
            <div class="stat-value">{total}</div>
            <div class="stat-label">풀이한 문제</div>
        </div>""", unsafe_allow_html=True)
    with col3:
        st.markdown(f"""
        <div class="stat-box">
            <div class="stat-value">{correct}</div>
            <div class="stat-label">정답 수</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # 유형별 정답률 카드
    sorted_subtypes = sorted(analysis.subtype_accuracies.items(), key=lambda x: x[1])

    st.markdown("""
    <div class="card">
        <div class="card-title">유형별 정답률</div>
        <div class="card-subtitle">정답률 60% 미만은 취약 영역으로 분류됩니다</div>
    </div>""", unsafe_allow_html=True)

    for subtype, acc in sorted_subtypes:
        if isinstance(subtype, str):
            try:
                from flex_agent.models.data_models import ReadingSubtype as RS
                subtype = RS(subtype)
            except ValueError:
                pass
        name = SUBTYPE_NAMES.get(subtype, subtype if isinstance(subtype, str) else subtype.value)
        pct = int(acc * 100)
        is_weak = subtype in analysis.weak_subtypes
        bar_class = "bar-fill-weak" if is_weak else "bar-fill"
        score_color = "#ff6b6b" if is_weak else "#53cfca"
        weak_badge = "&nbsp;&nbsp;취약" if is_weak else ""
        st.markdown(f"""
        <div style="background:#fff;border-radius:12px;padding:12px 16px;margin-bottom:8px;
                    box-shadow:0 1px 6px rgba(83,207,202,0.08);">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;">
                <span style="font-size:14px;font-weight:500;color:#444;">{name}</span>
                <span style="font-size:14px;font-weight:700;color:{score_color};">{pct}%{weak_badge}</span>
            </div>
            <div style="background:#e8f8f7;border-radius:99px;height:8px;">
                <div style="background:{'linear-gradient(90deg,#ff8a80,#ff5252)' if is_weak else 'linear-gradient(90deg,#53cfca,#38b2ac)'};
                            border-radius:99px;height:8px;width:{pct}%;"></div>
            </div>
        </div>""", unsafe_allow_html=True)

    # 취약 개념 카드
    if analysis.weak_subtypes:
        st.markdown("""
        <div class="card">
            <div class="card-title">취약한 개념</div>
            <div class="card-subtitle">집중적으로 연습이 필요한 유형입니다</div>
        </div>""", unsafe_allow_html=True)

        for subtype in analysis.weak_subtypes:
            acc = analysis.subtype_accuracies.get(subtype, 0)
            if isinstance(subtype, str):
                try:
                    from flex_agent.models.data_models import ReadingSubtype as RS
                    subtype = RS(subtype)
                except ValueError:
                    pass
            name = SUBTYPE_NAMES.get(subtype, subtype if isinstance(subtype, str) else subtype.value)
            pct = int(acc * 100)
            st.markdown(f"""
            <div style="background:#fff0f0;border-radius:12px;padding:12px 16px;margin-bottom:8px;
                        border-left:4px solid #ff5252;">
                <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;">
                    <span style="font-size:14px;font-weight:500;color:#444;">{name}</span>
                    <span style="font-size:14px;font-weight:700;color:#ff6b6b;">{pct}%</span>
                </div>
                <div style="background:#ffe0e0;border-radius:99px;height:8px;">
                    <div style="background:linear-gradient(90deg,#ff8a80,#ff5252);
                                border-radius:99px;height:8px;width:{pct}%;"></div>
                </div>
            </div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("문제 풀러 가기", use_container_width=True, key="analysis_go_quiz"):
        st.session_state.active_tab = "quiz"
        st.rerun()


# ─────────────────────────────────────────────
# 학습 리포트 페이지
# ─────────────────────────────────────────────
def render_report_page():
    session: Session = st.session_state.session
    api_key: str = st.session_state.api_key
    comps = get_components(api_key)

    if not session.grade_results:
        st.warning("리포트를 생성할 데이터가 없습니다. 문제를 먼저 풀어주세요.")
        if st.button("문제 풀러 가기", key="report_to_quiz"):
            st.session_state.active_tab = "quiz"
            st.rerun()
        return

    report_generator = comps["report_generator"]
    report = report_generator.generate(session)
    st.session_state.session = comps["session_store"].load()

    if report is None:
        st.warning("리포트 생성에 실패했습니다.")
        return

    # 핵심 지표 카드
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(f"""
        <div class="stat-box">
            <div class="stat-value">{report.predicted_score:.0f}</div>
            <div class="stat-label">예상 점수</div>
        </div>""", unsafe_allow_html=True)
    with col2:
        st.markdown(f"""
        <div class="stat-box">
            <div class="stat-value">{report.target_score}</div>
            <div class="stat-label">목표 점수</div>
        </div>""", unsafe_allow_html=True)
    with col3:
        achieve_color = "#4d9fff" if report.achievement_rate >= 80 else "#ff6b6b"
        st.markdown(f"""
        <div class="stat-box">
            <div class="stat-value" style="color:{achieve_color}">{report.achievement_rate:.0f}%</div>
            <div class="stat-label">목표 달성률</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # 예상 점수 vs 목표 점수 진행 바
    progress_pct = min(int(report.predicted_score / report.target_score * 100), 100) if report.target_score > 0 else 0
    st.markdown(f"""
    <div class="card">
        <div class="card-title">목표 달성 현황</div>
        <div class="card-subtitle">예상 점수 {report.predicted_score:.0f}점 / 목표 {report.target_score}점</div>
        <div class="bar-bg"><div class="bar-fill" style="width:{progress_pct}%"></div></div>
    </div>""", unsafe_allow_html=True)

    # 유형별 정답률
    sorted_subtypes = sorted(report.subtype_accuracies.items(), key=lambda x: x[1])

    st.markdown("""
    <div class="card">
        <div class="card-title">유형별 정답률</div>
    </div>""", unsafe_allow_html=True)

    for subtype, acc in sorted_subtypes:
        if isinstance(subtype, str):
            try:
                from flex_agent.models.data_models import ReadingSubtype as RS
                subtype = RS(subtype)
            except ValueError:
                pass
        name = SUBTYPE_NAMES.get(subtype, subtype if isinstance(subtype, str) else subtype.value)
        pct = int(acc * 100)
        is_weak = subtype in report.weak_subtypes
        score_color = "#ff6b6b" if is_weak else "#53cfca"
        st.markdown(f"""
        <div style="background:#fff;border-radius:12px;padding:12px 16px;margin-bottom:8px;
                    box-shadow:0 1px 6px rgba(83,207,202,0.08);">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;">
                <span style="font-size:14px;font-weight:500;color:#444;">{name}</span>
                <span style="font-size:14px;font-weight:700;color:{score_color};">{pct}%</span>
            </div>
            <div style="background:#e8f8f7;border-radius:99px;height:8px;">
                <div style="background:{'linear-gradient(90deg,#ff8a80,#ff5252)' if is_weak else 'linear-gradient(90deg,#53cfca,#38b2ac)'};
                            border-radius:99px;height:8px;width:{pct}%;"></div>
            </div>
        </div>""", unsafe_allow_html=True)

    # 학습 방향
    if report.study_directions:
        st.markdown("""
        <div class="card">
            <div class="card-title">학습 방향</div>
            <div class="card-subtitle">취약 영역 기반 추천 학습 방향입니다</div>
        </div>""", unsafe_allow_html=True)
        for d in report.study_directions:
            st.markdown(f"""
            <div style="color:#555;font-size:14px;padding:10px 16px;margin-bottom:6px;
                        background:#fff;border-radius:10px;border-left:3px solid #53cfca;">
                {d}
            </div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("계속 학습하기", use_container_width=True, key="report_go_quiz"):
        st.session_state.active_tab = "quiz"
        st.rerun()


# ─────────────────────────────────────────────
# 메인 라우터
# ─────────────────────────────────────────────
def main():
    api_key = get_api_key()

    # 세션이 없으면 홈 화면
    if "session" not in st.session_state or not st.session_state.session:
        render_home(api_key)
        return

    session: Session = st.session_state.session
    page = st.session_state.get("active_tab", "quiz")

    # 앱 타이틀
    st.markdown("""
    <div style="padding: 24px 0 8px 0;">
        <div style="font-size:12px; color:#53cfca; font-weight:600; letter-spacing:1px; text-transform:uppercase;">FLEX AI</div>
        <div style="font-size:22px; font-weight:800; color:#1a1a1a; margin-top:2px;">학습 에이전트</div>
    </div>
    """, unsafe_allow_html=True)

    # 상단 상태 바
    total = len(session.grade_results)
    predicted = session.predicted_score or 0
    difficulty = session.current_difficulty
    if isinstance(difficulty, str):
        try:
            difficulty = Difficulty(difficulty)
        except ValueError:
            pass
    difficulty_label = DIFFICULTY_NAMES.get(difficulty, difficulty if isinstance(difficulty, str) else difficulty.value)

    predicted_html = (
        f'<div class="status-item-value mint">{predicted:.0f}점</div>'
        f'<div style="font-size:11px;color:#aaa;margin-top:1px;">예측중</div>'
        if predicted == 0 else
        f'<div class="status-item-value mint">{predicted:.0f}점</div>'
    )

    st.markdown(f"""
    <div class="status-bar">
        <div><div class="status-item-label">목표 점수</div><div class="status-item-value">{session.target_score}점</div></div>
        <div><div class="status-item-label">예상 점수</div>{predicted_html}</div>
        <div><div class="status-item-label">난이도</div><div class="status-item-value">{difficulty_label}</div></div>
        <div><div class="status-item-label">풀이 문제</div><div class="status-item-value">{total}문제</div></div>
    </div>
    """, unsafe_allow_html=True)

    # 네비게이션 버튼
    col1, col2, col3, col4 = st.columns([3, 3, 3, 2])
    with col1:
        if st.button("문제 풀기", use_container_width=True, key="nav_quiz",
                     type="primary" if page == "quiz" else "secondary"):
            st.session_state.active_tab = "quiz"
            st.rerun()
    with col2:
        if st.button("실력 분석", use_container_width=True, key="nav_analysis",
                     type="primary" if page == "analysis" else "secondary"):
            st.session_state.active_tab = "analysis"
            st.rerun()
    with col3:
        if st.button("학습 리포트", use_container_width=True, key="nav_report",
                     type="primary" if page == "report" else "secondary"):
            st.session_state.active_tab = "report"
            st.rerun()
    with col4:
        if st.button("홈", use_container_width=True, key="nav_home"):
            _clear_session()

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
