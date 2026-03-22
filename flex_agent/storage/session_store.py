"""
FLEX AI 학습 에이전트 - 세션 저장소

JSON 파일 기반으로 세션 데이터를 안전하게 저장하고 불러온다.
임시 파일 → 원자적 교체 방식으로 데이터 손실을 방지한다.
"""

import json
import logging
import os
from pathlib import Path
from typing import Optional

from flex_agent.models.data_models import Session

logger = logging.getLogger(__name__)

# 저장 파일 경로 (프로젝트 루트 기준)
_DEFAULT_PATH = Path("session_data.json")


class SessionStore:
    """
    JSON 파일 기반 세션 데이터 영속성 관리.

    저장 시 임시 파일(.tmp)에 먼저 기록한 후 원자적으로 교체하여
    저장 도중 오류가 발생해도 기존 데이터를 보존한다.
    """

    def __init__(self, file_path: Path = _DEFAULT_PATH) -> None:
        """
        Args:
            file_path: 세션 데이터 저장 경로 (기본값: session_data.json)
        """
        self._file_path = Path(file_path)
        self._tmp_path = self._file_path.with_suffix(".json.tmp")

    def save(self, session: Session) -> None:
        """
        세션 데이터를 JSON 파일에 저장한다.

        임시 파일에 먼저 기록한 후 원자적으로 교체하여 데이터 손실을 방지한다.

        Args:
            session: 저장할 Session 객체
        """
        try:
            # 1단계: 임시 파일에 기록
            with open(self._tmp_path, "w", encoding="utf-8") as f:
                json.dump(session.to_dict(), f, ensure_ascii=False, indent=2)

            # 2단계: 원자적 교체 (임시 파일 → 실제 파일)
            os.replace(self._tmp_path, self._file_path)

        except Exception as e:
            # 기록 실패 시 임시 파일 정리
            if self._tmp_path.exists():
                try:
                    self._tmp_path.unlink()
                except OSError:
                    pass
            logger.error("세션 저장 실패: %s", e)
            raise

    def load(self) -> Optional[Session]:
        """
        JSON 파일에서 세션 데이터를 불러온다.

        Returns:
            복원된 Session 객체, 파일이 없거나 파싱 실패 시 None
        """
        if not self._file_path.exists():
            return None

        try:
            with open(self._file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            session = Session.from_dict(data)
            # subtype/difficulty가 문자열로 남아있는 경우 강제 변환
            from flex_agent.models.data_models import Difficulty, ReadingSubtype
            for r in session.grade_results:
                if isinstance(r.subtype, str):
                    r.subtype = ReadingSubtype(r.subtype)
                if isinstance(r.difficulty, str):
                    r.difficulty = Difficulty(r.difficulty)
            for q in session.questions:
                if isinstance(q.subtype, str):
                    q.subtype = ReadingSubtype(q.subtype)
                if isinstance(q.difficulty, str):
                    q.difficulty = Difficulty(q.difficulty)
            return session

        except (json.JSONDecodeError, KeyError, ValueError, TypeError) as e:
            # 파싱 실패 시 오류 기록 후 None 반환
            logger.error("세션 로드 실패 (파싱 오류): %s", e)
            return None

        except Exception as e:
            logger.error("세션 로드 실패 (예상치 못한 오류): %s", e)
            return None

    def clear(self) -> None:
        """세션 데이터 파일을 삭제한다."""
        if self._file_path.exists():
            self._file_path.unlink()
        if self._tmp_path.exists():
            self._tmp_path.unlink()
