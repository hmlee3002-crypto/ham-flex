"""
FLEX AI 학습 에이전트 - 문제 생성기

LLM을 호출하여 FLEX 스타일 4지선다 독해 문제를 생성한다.
"""

import json
import logging
import re
import uuid
from datetime import datetime
from typing import Any, Dict

from flex_agent.exceptions import LLMResponseParseError
from flex_agent.llm.llm_client import LLMClient
from flex_agent.models.data_models import Difficulty, Question, ReadingSubtype
from flex_agent.storage.session_store import SessionStore

logger = logging.getLogger(__name__)

# 세부 유형별 한국어 설명 및 예시 질문 패턴
_SUBTYPE_DESCRIPTIONS: Dict[ReadingSubtype, Dict[str, Any]] = {
    ReadingSubtype.TOPIC: {
        "name": "주제 찾기",
        "description": "글의 주제, 목적, 제목을 묻는 유형",
        "example_questions": [
            "上文主要谈的是什么？",
            "这篇文章的主题是什么？",
            "上文的标题最合适的是哪一个？",
        ],
    },
    ReadingSubtype.DETAIL: {
        "name": "세부 내용 파악",
        "description": "다양한 의문사로 세부 정보를 묻는 유형",
        "example_questions": [
            "根据上文，可以得知的信息是什么？",
            "根据上文，下列哪项是正确的？",
            "根据上文，作者认为什么？",
        ],
    },
    ReadingSubtype.TRUE_FALSE: {
        "name": "진위 판단",
        "description": "지문 내용과 일치/불일치 보기를 고르는 유형",
        "example_questions": [
            "根据上文，下列哪项与文章内容不符？",
            "根据上文，下列哪项是正确的？",
            "下列哪项与上文内容相符？",
        ],
    },
    ReadingSubtype.LETTER: {
        "name": "편지글",
        "description": "비즈니스 편지 또는 개인 편지 형식의 지문",
        "example_questions": [
            "根据上文，这封信的目的是什么？",
            "根据上文，写信人想表达什么？",
            "根据上文，收信人应该做什么？",
        ],
    },
    ReadingSubtype.ADVERTISEMENT: {
        "name": "광고문",
        "description": "구인·제품·부동산 광고 형식의 지문",
        "example_questions": [
            "根据上文，这则广告的目的是什么？",
            "根据上文，下列哪项符合广告内容？",
            "根据上文，应聘者需要具备什么条件？",
        ],
    },
    ReadingSubtype.ACADEMIC: {
        "name": "학술 지문",
        "description": "학술적 내용의 세부 사항 파악 또는 진위 판단",
        "example_questions": [
            "根据上文，下列哪项是正确的？",
            "根据上文，研究结果表明什么？",
            "根据上文，下列哪项与文章内容不符？",
        ],
    },
}

# 난이도별 지문 길이 및 복잡도 지침
_DIFFICULTY_GUIDELINES: Dict[Difficulty, Dict[str, str]] = {
    Difficulty.EASY: {
        "length": "100~150자 내외의 짧은 지문",
        "complexity": "일상적인 어휘와 간단한 문장 구조 사용",
        "hsk_level": "HSK 3~4급 수준",
    },
    Difficulty.MEDIUM: {
        "length": "150~250자 내외의 중간 길이 지문",
        "complexity": "다양한 어휘와 복합 문장 구조 사용",
        "hsk_level": "HSK 4~5급 수준",
    },
    Difficulty.HARD: {
        "length": "250~350자 내외의 긴 지문",
        "complexity": "전문 어휘와 복잡한 문장 구조, 함축적 표현 사용",
        "hsk_level": "HSK 5~6급 수준",
    },
}


class QuestionGenerator:
    """
    FLEX 스타일 4지선다 독해 문제 생성기.

    LLM을 호출하여 지정된 세부 유형과 난이도에 맞는 문제를 생성하고
    SessionStore에 저장한다.
    """

    def __init__(self, llm_client: LLMClient, session_store: SessionStore) -> None:
        """
        Args:
            llm_client: LLM API 클라이언트
            session_store: 세션 저장소
        """
        self._llm_client = llm_client
        self._session_store = session_store

    def generate(self, subtype: ReadingSubtype, difficulty: Difficulty) -> Question:
        """
        지정된 세부 유형과 난이도의 FLEX 스타일 문제를 생성한다.

        Args:
            subtype: 독해 세부 유형
            difficulty: 문제 난이도

        Returns:
            생성된 Question 객체

        Raises:
            LLMResponseParseError: LLM 응답 파싱 실패 시
            QuestionGenerationError: LLM 호출 실패 시
        """
        # 잘못된 타입이 들어온 경우 fallback
        if not isinstance(subtype, ReadingSubtype):
            subtype = ReadingSubtype.TOPIC
        if not isinstance(difficulty, Difficulty):
            difficulty = Difficulty.MEDIUM

        prompt = self._build_prompt(subtype, difficulty)
        raw_response = self._llm_client.complete(prompt)
        question = self._parse_llm_response(raw_response, subtype, difficulty)

        # 생성된 문제를 세션에 저장
        session = self._session_store.load()
        if session is not None:
            session.questions.append(question)
            session.updated_at = datetime.now()
            self._session_store.save(session)

        return question

    def _build_prompt(self, subtype: ReadingSubtype, difficulty: Difficulty) -> str:
        """
        세부 유형과 난이도에 맞는 LLM 프롬프트를 구성한다.

        Args:
            subtype: 독해 세부 유형
            difficulty: 문제 난이도

        Returns:
            LLM에 전달할 프롬프트 문자열
        """
        subtype_info = _SUBTYPE_DESCRIPTIONS.get(subtype)
        if subtype_info is None:
            # fallback: TOPIC으로 대체
            subtype = ReadingSubtype.TOPIC
            subtype_info = _SUBTYPE_DESCRIPTIONS[subtype]
        difficulty_info = _DIFFICULTY_GUIDELINES.get(difficulty, _DIFFICULTY_GUIDELINES[Difficulty.MEDIUM])
        example_q = subtype_info["example_questions"][0]

        prompt = f"""당신은 FLEX 중국어 시험 문제 출제 전문가입니다.
아래 조건에 맞는 FLEX 읽기(독해) 영역 4지선다 문제 1개를 생성해 주세요.

## 문제 유형
- 세부 유형: {subtype_info['name']} ({subtype_info['description']})
- 예시 질문 패턴: {example_q}

## 난이도 조건
- 난이도: {difficulty.value} ({difficulty_info['hsk_level']})
- 지문 길이: {difficulty_info['length']}
- 복잡도: {difficulty_info['complexity']}

## 생성 규칙
1. 지문(passage)은 반드시 중국어로 작성하세요.
2. 질문(question)은 중국어로 작성하세요.
3. 선택지(choices)는 4개이며 중국어로 작성하세요.
4. 정답 번호(correct_answer)는 1~4 사이의 정수입니다.
5. 해설(explanation)은 한국어로 작성하세요.
6. 반드시 아래 JSON 형식으로만 응답하세요. 다른 텍스트는 포함하지 마세요.

## 응답 형식 (JSON)
{{
  "passage": "중국어 지문 텍스트",
  "question": "중국어 질문 텍스트",
  "choices": ["선택지1", "선택지2", "선택지3", "선택지4"],
  "correct_answer": 2,
  "explanation": "한국어 해설 텍스트"
}}"""

        return prompt

    def _parse_llm_response(
        self,
        raw: str,
        subtype: ReadingSubtype,
        difficulty: Difficulty,
    ) -> Question:
        """
        LLM 응답 JSON을 파싱하여 Question 객체를 생성한다.

        Args:
            raw: LLM 원본 응답 텍스트
            subtype: 독해 세부 유형
            difficulty: 문제 난이도

        Returns:
            파싱된 Question 객체

        Raises:
            LLMResponseParseError: JSON 파싱 실패 또는 구조 검증 실패 시
        """
        # JSON 블록 추출 (마크다운 코드 블록 처리)
        json_text = raw.strip()
        json_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", json_text)
        if json_match:
            json_text = json_match.group(1).strip()

        try:
            data = json.loads(json_text)
        except json.JSONDecodeError as e:
            raise LLMResponseParseError(
                f"LLM 응답 JSON 파싱 실패: {e}\n원본 응답: {raw[:200]}"
            ) from e

        # 필수 필드 검증
        self._validate_question_data(data)

        return Question(
            id=str(uuid.uuid4()),
            subtype=subtype,
            difficulty=difficulty,
            passage=data["passage"],
            question_text=data["question"],
            choices=data["choices"],
            correct_answer=data["correct_answer"],
            explanation=data["explanation"],
            created_at=datetime.now(),
        )

    def _validate_question_data(self, data: dict) -> None:
        """
        파싱된 문제 데이터의 구조를 검증한다.

        Args:
            data: 파싱된 딕셔너리

        Raises:
            LLMResponseParseError: 구조 검증 실패 시
        """
        required_fields = ["passage", "question", "choices", "correct_answer", "explanation"]
        for field_name in required_fields:
            if field_name not in data:
                raise LLMResponseParseError(f"필수 필드 누락: '{field_name}'")

        if not data["passage"] or not isinstance(data["passage"], str):
            raise LLMResponseParseError("passage가 비어있거나 문자열이 아닙니다.")

        if not data["question"] or not isinstance(data["question"], str):
            raise LLMResponseParseError("question이 비어있거나 문자열이 아닙니다.")

        if not isinstance(data["choices"], list) or len(data["choices"]) != 4:
            raise LLMResponseParseError(
                f"choices는 정확히 4개여야 합니다. 현재: {len(data.get('choices', []))}개"
            )

        for i, choice in enumerate(data["choices"]):
            if not choice or not isinstance(choice, str):
                raise LLMResponseParseError(f"choices[{i}]가 비어있거나 문자열이 아닙니다.")

        correct = data["correct_answer"]
        if not isinstance(correct, int) or not (1 <= correct <= 4):
            raise LLMResponseParseError(
                f"correct_answer는 1~4 사이의 정수여야 합니다. 현재: {correct}"
            )

        if not data["explanation"] or not isinstance(data["explanation"], str):
            raise LLMResponseParseError("explanation이 비어있거나 문자열이 아닙니다.")
