"""
FLEX AI 학습 에이전트 - 데이터 모델 정의

모든 핵심 데이터 구조(열거형, dataclass)를 정의하며,
JSON 직렬화/역직렬화 메서드를 포함한다.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional


# ─────────────────────────────────────────────
# 열거형 (Enum)
# ─────────────────────────────────────────────

class Difficulty(Enum):
    """문제 난이도 (예상 점수 범위에 따라 결정)"""
    EASY = "Easy"      # 0 ~ 350점
    MEDIUM = "Medium"  # 351 ~ 450점
    HARD = "Hard"      # 451 ~ 600점


class ReadingSubtype(Enum):
    """독해 세부 유형"""
    TOPIC = "Topic"                      # 주제 찾기
    DETAIL = "Detail"                    # 세부 내용 파악
    TRUE_FALSE = "TrueFalse"             # 진위 판단
    LETTER = "Letter"                    # 편지글
    ADVERTISEMENT = "Advertisement"      # 광고문
    ACADEMIC = "Academic"                # 학술 지문


class MenuChoice(Enum):
    """채점 후 다음 행동 메뉴 선택지"""
    NEXT_QUESTION = "next"    # 다음 문제 풀기
    ANALYZE = "analyze"       # 오답 분석
    REPORT = "report"         # 리포트 보기
    QUIT = "quit"             # 종료


# ─────────────────────────────────────────────
# 핵심 데이터 모델 (dataclass)
# ─────────────────────────────────────────────

@dataclass
class Question:
    """FLEX 스타일 4지선다 문제"""
    id: str                        # UUID
    subtype: ReadingSubtype        # 독해 세부 유형
    difficulty: Difficulty         # 난이도
    passage: str                   # 중국어 지문
    question_text: str             # 질문 텍스트
    choices: List[str]             # 4개 선택지 (인덱스 0~3 → 번호 1~4)
    correct_answer: int            # 정답 번호 (1~4)
    explanation: str               # 해설
    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict:
        """JSON 직렬화용 딕셔너리 변환"""
        return {
            "id": self.id,
            "subtype": self.subtype.value,
            "difficulty": self.difficulty.value,
            "passage": self.passage,
            "question_text": self.question_text,
            "choices": self.choices,
            "correct_answer": self.correct_answer,
            "explanation": self.explanation,
            "created_at": self.created_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Question":
        """딕셔너리에서 Question 객체 복원"""
        return cls(
            id=data["id"],
            subtype=ReadingSubtype(data["subtype"]),
            difficulty=Difficulty(data["difficulty"]),
            passage=data["passage"],
            question_text=data["question_text"],
            choices=data["choices"],
            correct_answer=data["correct_answer"],
            explanation=data["explanation"],
            created_at=datetime.fromisoformat(data["created_at"]),
        )


@dataclass
class GradeResult:
    """채점 결과"""
    question_id: str               # 문제 UUID
    subtype: ReadingSubtype        # 독해 세부 유형
    difficulty: Difficulty         # 난이도
    user_answer: int               # 사용자 답안 (1~4)
    correct_answer: int            # 정답 번호 (1~4)
    is_correct: bool               # 정오 여부
    graded_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict:
        """JSON 직렬화용 딕셔너리 변환"""
        return {
            "question_id": self.question_id,
            "subtype": self.subtype.value,
            "difficulty": self.difficulty.value,
            "user_answer": self.user_answer,
            "correct_answer": self.correct_answer,
            "is_correct": self.is_correct,
            "graded_at": self.graded_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "GradeResult":
        """딕셔너리에서 GradeResult 객체 복원"""
        return cls(
            question_id=data["question_id"],
            subtype=ReadingSubtype(data["subtype"]),
            difficulty=Difficulty(data["difficulty"]),
            user_answer=data["user_answer"],
            correct_answer=data["correct_answer"],
            is_correct=data["is_correct"],
            graded_at=datetime.fromisoformat(data["graded_at"]),
        )


@dataclass
class AnalysisResult:
    """오답 분석 결과"""
    subtype_accuracies: Dict[ReadingSubtype, float]   # 세부 유형별 정답률
    weak_subtypes: List[ReadingSubtype]               # 취약 유형 (정답률 < 0.6)
    total_accuracy: float                             # 전체 정답률
    warning_message: Optional[str] = None            # 데이터 부족 경고 메시지

    def to_dict(self) -> dict:
        """JSON 직렬화용 딕셔너리 변환"""
        return {
            "subtype_accuracies": {k.value: v for k, v in self.subtype_accuracies.items()},
            "weak_subtypes": [s.value for s in self.weak_subtypes],
            "total_accuracy": self.total_accuracy,
            "warning_message": self.warning_message,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "AnalysisResult":
        """딕셔너리에서 AnalysisResult 객체 복원"""
        return cls(
            subtype_accuracies={ReadingSubtype(k): v for k, v in data["subtype_accuracies"].items()},
            weak_subtypes=[ReadingSubtype(s) for s in data["weak_subtypes"]],
            total_accuracy=data["total_accuracy"],
            warning_message=data.get("warning_message"),
        )


@dataclass
class ScorePrediction:
    """예상 점수 예측 결과"""
    basic_score: float             # 정답률 × 600
    weighted_score: float          # 가중치 적용 점수
    data_count: int                # 계산에 사용된 데이터 수
    is_reliable: bool              # 데이터 10개 이상 여부

    def to_dict(self) -> dict:
        """JSON 직렬화용 딕셔너리 변환"""
        return {
            "basic_score": self.basic_score,
            "weighted_score": self.weighted_score,
            "data_count": self.data_count,
            "is_reliable": self.is_reliable,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ScorePrediction":
        """딕셔너리에서 ScorePrediction 객체 복원"""
        return cls(
            basic_score=data["basic_score"],
            weighted_score=data["weighted_score"],
            data_count=data["data_count"],
            is_reliable=data["is_reliable"],
        )


@dataclass
class Report:
    """종합 학습 리포트"""
    predicted_score: float                           # 예상 점수
    target_score: int                                # 목표 점수
    achievement_rate: float                          # 예상 점수 / 목표 점수 × 100
    subtype_accuracies: Dict[ReadingSubtype, float]  # 세부 유형별 정답률
    strong_subtypes: List[ReadingSubtype]            # 강점 영역 (정답률 ≥ 0.7)
    weak_subtypes: List[ReadingSubtype]              # 취약 영역 (정답률 < 0.6)
    study_directions: List[str]                      # 학습 방향 텍스트
    generated_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict:
        """JSON 직렬화용 딕셔너리 변환"""
        return {
            "predicted_score": self.predicted_score,
            "target_score": self.target_score,
            "achievement_rate": self.achievement_rate,
            "subtype_accuracies": {k.value: v for k, v in self.subtype_accuracies.items()},
            "strong_subtypes": [s.value for s in self.strong_subtypes],
            "weak_subtypes": [s.value for s in self.weak_subtypes],
            "study_directions": self.study_directions,
            "generated_at": self.generated_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Report":
        """딕셔너리에서 Report 객체 복원"""
        return cls(
            predicted_score=data["predicted_score"],
            target_score=data["target_score"],
            achievement_rate=data["achievement_rate"],
            subtype_accuracies={ReadingSubtype(k): v for k, v in data["subtype_accuracies"].items()},
            strong_subtypes=[ReadingSubtype(s) for s in data["strong_subtypes"]],
            weak_subtypes=[ReadingSubtype(s) for s in data["weak_subtypes"]],
            study_directions=data["study_directions"],
            generated_at=datetime.fromisoformat(data["generated_at"]),
        )


@dataclass
class Session:
    """학습 세션 전체 데이터"""
    target_score: int                              # 목표 점수
    current_difficulty: Difficulty                 # 현재 난이도
    questions: List[Question] = field(default_factory=list)          # 생성된 문제 목록
    grade_results: List[GradeResult] = field(default_factory=list)   # 채점 결과 목록
    predicted_score: Optional[float] = None                          # 최근 예상 점수
    reports: List[Report] = field(default_factory=list)              # 생성된 리포트 목록
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict:
        """JSON 직렬화용 딕셔너리 변환"""
        return {
            "target_score": self.target_score,
            "current_difficulty": self.current_difficulty.value,
            "questions": [q.to_dict() for q in self.questions],
            "grade_results": [r.to_dict() for r in self.grade_results],
            "predicted_score": self.predicted_score,
            "reports": [r.to_dict() for r in self.reports],
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Session":
        """딕셔너리에서 Session 객체 복원"""
        return cls(
            target_score=data["target_score"],
            current_difficulty=Difficulty(data["current_difficulty"]),
            questions=[Question.from_dict(q) for q in data.get("questions", [])],
            grade_results=[GradeResult.from_dict(r) for r in data.get("grade_results", [])],
            predicted_score=data.get("predicted_score"),
            reports=[Report.from_dict(r) for r in data.get("reports", [])],
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
        )
