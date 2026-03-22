"""
FLEX AI 학습 에이전트 - LLM 클라이언트

OpenAI API 호출 래퍼. 지수 백오프 재시도 로직을 포함한다.
"""

import logging
import time
from typing import Optional

from flex_agent.exceptions import QuestionGenerationError

logger = logging.getLogger(__name__)

# 재시도 설정
_MAX_RETRIES = 3
_RETRY_DELAYS = [1, 2, 4]  # 초 단위 (지수 백오프)


class LLMClient:
    """
    OpenAI API 호출 래퍼.

    API 오류 발생 시 지수 백오프 방식으로 최대 3회 재시도하며,
    모두 실패하면 QuestionGenerationError를 발생시킨다.
    """

    def __init__(self, api_key: str, model: str = "gpt-4o-mini") -> None:
        """
        Args:
            api_key: OpenAI API 키
            model: 사용할 모델명 (기본값: gpt-4o-mini)
        """
        try:
            from openai import OpenAI
        except ImportError as e:
            raise ImportError("openai 패키지가 설치되어 있지 않습니다. pip install openai") from e

        self._client = OpenAI(api_key=api_key)
        self._model = model

    def complete(self, prompt: str) -> str:
        """
        LLM에 프롬프트를 전송하고 응답 텍스트를 반환한다.

        지수 백오프 방식으로 최대 3회 재시도한다.

        Args:
            prompt: LLM에 전달할 프롬프트 텍스트

        Returns:
            LLM 응답 텍스트

        Raises:
            QuestionGenerationError: 최대 재시도 횟수 초과 시
        """
        last_error: Optional[Exception] = None

        for attempt, delay in enumerate(zip(range(_MAX_RETRIES), _RETRY_DELAYS), start=1):
            attempt_num, wait_sec = delay
            try:
                response = self._client.chat.completions.create(
                    model=self._model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.7,
                )
                return response.choices[0].message.content or ""

            except Exception as e:
                last_error = e
                logger.warning(
                    "LLM 호출 실패 (시도 %d/%d): %s. %d초 후 재시도...",
                    attempt_num + 1, _MAX_RETRIES, e, wait_sec
                )
                if attempt_num + 1 < _MAX_RETRIES:
                    time.sleep(wait_sec)

        raise QuestionGenerationError(
            f"LLM 호출이 {_MAX_RETRIES}회 모두 실패했습니다: {last_error}"
        ) from last_error
