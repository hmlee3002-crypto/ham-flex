# 🎓 FLEX AI 학습 에이전트

FLEX 중국어 시험 독해 영역을 AI로 대비하는 학습 에이전트입니다.

## 주요 기능

- 🤖 AI 기반 FLEX 스타일 4지선다 독해 문제 자동 생성
- 📊 세부 유형별 오답 분석 (주제 찾기, 세부 내용 파악, 진위 판단, 편지글, 광고문, 학술 지문)
- 📈 예상 점수 예측 및 종합 학습 리포트
- 🔄 정답률 기반 난이도 자동 조절 (Easy / Medium / Hard)

## 난이도 기준

| 난이도 | 예상 독해 점수 범위 |
|--------|-------------------|
| Easy   | 0 ~ 350점         |
| Medium | 351 ~ 450점       |
| Hard   | 451 ~ 600점       |

## 로컬 실행

```bash
# 1. 의존성 설치
pip install -r requirements.txt

# 2. Streamlit 앱 실행
streamlit run app.py
```

앱 실행 후 사이드바에 OpenAI API 키를 입력하세요.

## Streamlit Cloud 배포

1. 이 레포지토리를 GitHub에 push합니다.
2. [Streamlit Cloud](https://streamlit.io/cloud)에서 레포를 연결합니다.
3. **Settings → Secrets**에 아래 내용을 추가합니다:

```toml
OPENAI_API_KEY = "sk-..."
```

4. Deploy 버튼을 누르면 자동 배포됩니다.

## 테스트 실행

```bash
pytest tests/ -v
```

## 기술 스택

- Python 3.9+
- OpenAI API (gpt-4o-mini)
- Streamlit
- Hypothesis (속성 기반 테스트)
