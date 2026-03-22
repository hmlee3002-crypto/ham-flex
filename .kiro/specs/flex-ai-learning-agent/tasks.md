# 구현 계획: FLEX AI 학습 에이전트

## 개요

설계 문서의 컴포넌트 구조를 기반으로, 데이터 모델 → 저장소 → LLM 클라이언트 → 핵심 컴포넌트 → 에이전트 조율 → CLI 진입점 순서로 점진적으로 구현한다. 각 단계는 이전 단계 위에 쌓이며, 고아 코드 없이 최종적으로 완전히 연결된다.

## 태스크

- [x] 1. 프로젝트 구조 및 데이터 모델 설정
  - [x] 1.1 프로젝트 디렉토리 구조 및 패키지 초기화
    - `flex_agent/`, `flex_agent/components/`, `flex_agent/storage/`, `flex_agent/models/`, `flex_agent/llm/`, `tests/` 디렉토리 생성
    - 각 디렉토리에 `__init__.py` 파일 생성
    - `requirements.txt` 작성 (`openai`, `hypothesis`)
    - _요구사항: 전체_

  - [x] 1.2 데이터 모델 구현 (`flex_agent/models/data_models.py`)
    - `Difficulty`, `ReadingSubtype`, `MenuChoice` 열거형 구현
    - `Question`, `GradeResult`, `AnalysisResult`, `ScorePrediction`, `Report`, `Session` dataclass 구현
    - JSON 직렬화/역직렬화를 위한 `to_dict()` / `from_dict()` 메서드 구현 (datetime, Enum 처리 포함)
    - _요구사항: 1.1, 1.2, 2.2, 3.4, 9.1_

  - [ ]* 1.3 세션 직렬화 라운드트립 속성 테스트 작성 (`tests/test_session_store.py`)
    - **속성 3: 세션 직렬화 라운드트립**
    - **검증 대상: 요구사항 1.5, 2.5, 3.4, 9.1, 9.2**

- [x] 2. 오류 클래스 및 유틸리티 구현
  - [x] 2.1 커스텀 예외 클래스 구현 (`flex_agent/exceptions.py`)
    - `FlexAgentError`, `InvalidScoreError`, `InvalidAnswerError`, `QuestionGenerationError`, `LLMResponseParseError`, `SessionLoadError` 구현
    - _요구사항: 1.3, 2.4, 3.3, 9.3_

  - [x] 2.2 점수 유효성 검사 및 난이도 결정 유틸리티 구현 (`flex_agent/utils.py`)
    - `validate_score(score: int) -> None` 구현 (범위 외 입력 시 `InvalidScoreError` 발생)
    - `determine_difficulty(score: int) -> Difficulty` 구현 (0~350→Easy, 351~450→Medium, 451~600→Hard)
    - _요구사항: 1.2, 1.3_

  - [ ]* 2.3 점수 → 난이도 매핑 속성 테스트 작성 (`tests/test_utils.py`)
    - **속성 1: 점수 범위 → 난이도 매핑**
    - **검증 대상: 요구사항 1.2**

  - [ ]* 2.4 유효하지 않은 점수 입력 거부 속성 테스트 작성 (`tests/test_utils.py`)
    - **속성 2: 유효하지 않은 점수 입력 거부**
    - **검증 대상: 요구사항 1.3**

- [x] 3. 체크포인트 - 모든 테스트 통과 확인
  - 모든 테스트가 통과하는지 확인하고, 문제가 있으면 사용자에게 질문한다.

- [x] 4. SessionStore 구현
  - [x] 4.1 JSON 파일 기반 세션 저장소 구현 (`flex_agent/storage/session_store.py`)
    - `save(session: Session) -> None` 구현 (임시 파일 → 원자적 교체 방식)
    - `load() -> Optional[Session]` 구현 (파싱 실패 시 `None` 반환)
    - `clear() -> None` 구현
    - _요구사항: 1.5, 9.1, 9.2, 9.3, 9.4_

  - [ ]* 4.2 SessionStore 단위 테스트 작성 (`tests/test_session_store.py`)
    - 손상된 JSON 파일 로드 시 `None` 반환 검증 (요구사항 9.3)
    - 임시 파일 교체 방식 저장 검증 (요구사항 9.4)
    - _요구사항: 9.3, 9.4_

- [x] 5. LLM 클라이언트 구현
  - [x] 5.1 OpenAI API 래퍼 구현 (`flex_agent/llm/llm_client.py`)
    - `LLMClient` 클래스 구현 (`complete(prompt, model)` 메서드)
    - 지수 백오프 재시도 로직 구현 (최대 3회, 1초/2초/4초 간격)
    - API 오류 시 `QuestionGenerationError` 발생
    - _요구사항: 2.4_

- [x] 6. QuestionGenerator 구현
  - [x] 6.1 FLEX 스타일 문제 생성기 구현 (`flex_agent/components/question_generator.py`)
    - `_build_prompt(subtype, difficulty) -> str` 구현 (세부 유형별 프롬프트 템플릿 포함)
    - `_parse_llm_response(raw: str) -> Question` 구현 (JSON 파싱 및 구조 검증)
    - `generate(subtype, difficulty) -> Question` 구현 (LLM 호출 → 파싱 → SessionStore 저장)
    - LLM 응답 파싱 실패 시 `LLMResponseParseError` 발생
    - _요구사항: 2.1, 2.2, 2.3, 2.4, 2.5_

  - [ ]* 6.2 생성된 문제 구조적 완전성 속성 테스트 작성 (`tests/test_question_generator.py`)
    - **속성 4: 생성된 문제의 구조적 완전성**
    - **검증 대상: 요구사항 2.2**

  - [ ]* 6.3 QuestionGenerator 단위 테스트 작성 (`tests/test_question_generator.py`)
    - LLM 호출 실패 시 `QuestionGenerationError` 발생 검증 (요구사항 2.4)
    - _요구사항: 2.4_

- [x] 7. Grader 구현
  - [x] 7.1 답안 채점기 구현 (`flex_agent/components/grader.py`)
    - `grade(question, user_answer) -> GradeResult` 구현 (1~4 범위 외 입력 시 `InvalidAnswerError` 발생)
    - `display_result(result: GradeResult) -> None` 구현 (정오 여부 + 해설 CLI 출력)
    - 채점 결과를 SessionStore에 저장
    - _요구사항: 3.1, 3.2, 3.3, 3.4_

  - [ ]* 7.2 채점 정확성 속성 테스트 작성 (`tests/test_grader.py`)
    - **속성 5: 채점 정확성**
    - **검증 대상: 요구사항 3.1**

  - [ ]* 7.3 유효하지 않은 답안 입력 거부 속성 테스트 작성 (`tests/test_grader.py`)
    - **속성 6: 유효하지 않은 답안 입력 거부**
    - **검증 대상: 요구사항 3.3**

- [x] 8. 체크포인트 - 모든 테스트 통과 확인
  - 모든 테스트가 통과하는지 확인하고, 문제가 있으면 사용자에게 질문한다.

- [x] 9. Analyzer 구현
  - [x] 9.1 오답 분석기 구현 (`flex_agent/components/analyzer.py`)
    - `analyze(results: List[GradeResult]) -> AnalysisResult` 구현 (세부 유형별 정답률 계산, 취약 영역 분류)
    - `get_weakness_subtypes(results) -> List[ReadingSubtype]` 구현 (정답률 오름차순 정렬)
    - 채점 데이터 5개 미만 시 경고 메시지 반환 처리
    - _요구사항: 4.1, 4.2, 4.3, 4.4, 4.5_

  - [ ]* 9.2 유형별 정답률 계산 정확성 속성 테스트 작성 (`tests/test_analyzer.py`)
    - **속성 7: 유형별 정답률 계산 정확성**
    - **검증 대상: 요구사항 4.1, 4.2**

  - [ ]* 9.3 취약 영역 분류 정확성 속성 테스트 작성 (`tests/test_analyzer.py`)
    - **속성 8: 취약 영역 분류 정확성**
    - **검증 대상: 요구사항 4.3**

  - [ ]* 9.4 Analyzer 단위 테스트 작성 (`tests/test_analyzer.py`)
    - 채점 데이터 5개 미만 시 경고 반환 검증 (요구사항 4.5)
    - _요구사항: 4.5_

- [x] 10. Recommender 구현
  - [x] 10.1 맞춤 문제 추천기 구현 (`flex_agent/components/recommender.py`)
    - `recommend_subtype(analysis, current_difficulty) -> ReadingSubtype` 구현 (취약 영역 우선 순환 추천)
    - `get_recommendation_reason(subtype, analysis) -> str` 구현 (추천 근거 텍스트 반환)
    - 취약 영역 없을 때 현재보다 한 단계 높은 난이도 균등 추천 처리
    - _요구사항: 5.1, 5.2, 5.3, 5.4_

  - [ ]* 10.2 취약 영역 우선 추천 속성 테스트 작성 (`tests/test_recommender.py`)
    - **속성 9: 취약 영역 우선 추천**
    - **검증 대상: 요구사항 5.1**

  - [ ]* 10.3 취약 영역 순환 추천 속성 테스트 작성 (`tests/test_recommender.py`)
    - **속성 10: 취약 영역 순환 추천**
    - **검증 대상: 요구사항 5.2**

  - [ ]* 10.4 Recommender 단위 테스트 작성 (`tests/test_recommender.py`)
    - 취약 영역 없을 때 상위 난이도 균등 추천 검증 (요구사항 5.3)
    - _요구사항: 5.3_

- [x] 11. ScorePredictor 구현
  - [x] 11.1 예상 점수 예측기 구현 (`flex_agent/components/score_predictor.py`)
    - `_weighted_score(subtype_accuracies) -> float` 구현 (균등 가중치 1/6 적용)
    - `predict(results: List[GradeResult]) -> ScorePrediction` 구현 (기본 점수 + 가중 점수 계산, SessionStore 저장)
    - 데이터 10개 미만 시 `is_reliable=False` 및 경고 메시지 처리
    - _요구사항: 7.1, 7.2, 7.3, 7.4, 7.5_

  - [ ]* 11.2 기본 예상 점수 계산 속성 테스트 작성 (`tests/test_score_predictor.py`)
    - **속성 12: 기본 예상 점수 계산**
    - **검증 대상: 요구사항 7.1**

  - [ ]* 11.3 가중 예상 점수 계산 속성 테스트 작성 (`tests/test_score_predictor.py`)
    - **속성 13: 가중 예상 점수 계산**
    - **검증 대상: 요구사항 7.2**

  - [ ]* 11.4 ScorePredictor 단위 테스트 작성 (`tests/test_score_predictor.py`)
    - 데이터 10개 미만 시 신뢰도 경고 포함 검증 (요구사항 7.4)
    - _요구사항: 7.4_

- [x] 12. 체크포인트 - 모든 테스트 통과 확인
  - 모든 테스트가 통과하는지 확인하고, 문제가 있으면 사용자에게 질문한다.

- [x] 13. ReportGenerator 구현
  - [x] 13.1 학습 리포트 생성기 구현 (`flex_agent/components/report_generator.py`)
    - `generate(session: Session) -> Report` 구현 (ScorePredictor + Analyzer 결과 종합, 학습 방향 텍스트 생성)
    - `display(report: Report) -> None` 구현 (리포트 CLI 출력)
    - 채점 데이터 없을 때 안내 메시지 처리
    - 생성된 리포트를 SessionStore에 저장
    - _요구사항: 8.1, 8.2, 8.3, 8.4, 8.5, 8.6_

  - [ ]* 13.2 리포트 내용 정확성 속성 테스트 작성 (`tests/test_report_generator.py`)
    - **속성 14: 리포트 내용 정확성**
    - **검증 대상: 요구사항 8.2, 8.3, 8.4**

  - [ ]* 13.3 ReportGenerator 단위 테스트 작성 (`tests/test_report_generator.py`)
    - 채점 데이터 없을 때 안내 메시지 반환 검증 (요구사항 8.6)
    - _요구사항: 8.6_

- [x] 14. Agent 및 난이도 자동 조절 구현
  - [x] 14.1 난이도 자동 조절 로직 구현 (`flex_agent/agent.py`)
    - `adjust_difficulty() -> Optional[Difficulty]` 구현 (최근 5문제 정답률 기반, Hard/Easy 경계 처리)
    - 난이도 변경 시 CLI 알림 및 SessionStore 저장
    - _요구사항: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 6.7_

  - [ ]* 14.2 난이도 자동 조절 방향성 속성 테스트 작성 (`tests/test_difficulty_adjuster.py`)
    - **속성 11: 난이도 자동 조절 방향성**
    - **검증 대상: 요구사항 6.1, 6.2, 6.3, 6.4, 6.5**

  - [ ]* 14.3 난이도 조절 경계 단위 테스트 작성 (`tests/test_difficulty_adjuster.py`)
    - Hard 난이도에서 상향 조절 시도 시 변경 없음 검증 (요구사항 6.4)
    - Easy 난이도에서 하향 조절 시도 시 변경 없음 검증 (요구사항 6.5)
    - _요구사항: 6.4, 6.5_

  - [x] 14.4 Agent 전체 흐름 조율 구현 (`flex_agent/agent.py`)
    - `initialize_session(target_score, current_score) -> Session` 구현 (입력 유효성 검사, 초기 난이도 결정, SessionStore 저장)
    - `show_menu() -> MenuChoice` 구현 (채점 후 다음 행동 메뉴 출력 및 선택 수신)
    - `run() -> None` 구현 (전체 학습 루프: 세션 초기화 → 문제 생성 → 채점 → 분석 → 추천 → 반복)
    - 종료 시 최종 리포트 출력
    - _요구사항: 1.1, 1.2, 1.3, 1.4, 10.1, 10.2, 10.3, 10.4_

- [x] 15. CLI 진입점 구현 및 전체 연결
  - [x] 15.1 CLI 진입점 구현 (`flex_agent/main.py`)
    - `main()` 함수 구현 (SessionStore 로드 → Agent 초기화 → `agent.run()` 호출)
    - 기존 세션 데이터 복원 처리 (요구사항 9.2)
    - `if __name__ == "__main__": main()` 진입점 설정
    - _요구사항: 9.2, 10.1, 10.2, 10.3, 10.4_

- [x] 16. 최종 체크포인트 - 모든 테스트 통과 확인
  - 모든 테스트가 통과하는지 확인하고, 문제가 있으면 사용자에게 질문한다.

## 참고

- `*` 표시된 태스크는 선택 사항으로, MVP 구현 시 건너뛸 수 있다.
- 각 태스크는 특정 요구사항과 연결되어 추적 가능하다.
- 속성 기반 테스트는 Hypothesis 라이브러리를 사용하며, 각 테스트는 최소 100회 반복 실행된다.
- 체크포인트에서 점진적으로 기능을 검증하여 오류를 조기에 발견한다.
