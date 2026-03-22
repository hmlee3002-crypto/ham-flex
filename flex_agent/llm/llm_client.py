"""
FLEX AI 학습 에이전트 - LLM 클라이언트

Google Gemini API 호출 래퍼. 지수 백오프 재시도 로직을 포함한다.
"""

import logging
import time
from typing import Optional

from flex_agent.exceptions import QuestionGenerationError

logger = logging.getLogger(__name__)

_MAX_RETRIES = 3
_RETRY_DELAYS = [1, 2, 4]


class LLMClient:
    """
    Google Gemini API 호출 래퍼.

    API 오류 발생 시 지수 백오프 방식으로 최대 3회 재시도하며,
    모두 실패하면 QuestionGenerationError를 발생시킨다.
    """

    def __init__(self, api_key: str, model: str = "gemini-2.0-flash") -> None:
        """
        Args:
            api_key: Google AI Studio API 키
            model: 사용할 모델명 (기본값: gemini-1.5-flash)
        """
        try:
            import google.generativeai as genai
        except ImportError as e:
            raise ImportError(
                "google-generativeai 패키지가 설치되어 있지 않습니다. "
                "pip install google-generativeai"
            ) from e

        import google.generativeai as genai
        genai.configure(api_key=api_key)
        self._model = genai.GenerativeModel(model)

    def complete(self, prompt: str) -> str:
        """
        Gemini에 프롬프트를 전송하고 응답 텍스트를 반환한다.

        Args:
            prompt: 전달할 프롬프트 텍스트

        Returns:
            응답 텍스트

        Raises:
            QuestionGenerationError: 최대 재시도 횟수 초과 시
        """
        last_error: Optional[Exception] = None

        for attempt in range(_MAX_RETRIES):
            try:
                response = self._model.generate_content(prompt)
                return response.text or ""
            except Exception as e:
                last_error = e
                logger.warning(
                    "Gemini 호출 실패 (시도 %d/%d): %s. %d초 후 재시도...",
                    attempt + 1, _MAX_RETRIES, e, _RETRY_DELAYS[attempt],
                )
                if attempt + 1 < _MAX_RETRIES:
                    time.sleep(_RETRY_DELAYS[attempt])

        raise QuestionGenerationError(
            f"LLM 호출이 {_MAX_RETRIES}회 모두 실패했습니다: {last_error}"
        ) from last_error
