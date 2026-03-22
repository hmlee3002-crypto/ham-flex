"""
FLEX AI 학습 에이전트 - 커스텀 예외 클래스

에이전트 전반에서 사용하는 예외 계층 구조를 정의한다.
"""


class FlexAgentError(Exception):
    """FLEX 에이전트 기본 예외 클래스"""


class InvalidScoreError(FlexAgentError):
    """0~600 범위를 벗어난 점수 입력 시 발생"""


class InvalidAnswerError(FlexAgentError):
    """1~4 범위를 벗어난 답안 입력 시 발생"""


class QuestionGenerationError(FlexAgentError):
    """문제 생성 실패 시 발생 (LLM 호출 오류 포함)"""


class LLMResponseParseError(QuestionGenerationError):
    """LLM 응답 JSON 파싱 실패 시 발생"""


class SessionLoadError(FlexAgentError):
    """세션 데이터 로드 실패 시 발생"""
