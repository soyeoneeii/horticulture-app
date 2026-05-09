# 원예장비 제조업체 총괄생산계획
- 총괄생산계획(Aggregate Production Planning)
- 2026-1 스마트제조 과제
- Pyomo 기반 최적화 + Streamlit 대시보드

## 주요 기능
- 8개 결정변수(W, H, L, P, I, S, C, O)의 월별 최적값 도출
- LP, IP 풀이 모두 지원
- IP 기반 시각화 차트 제공하여, 현재 계획의 적절성 판단 가능
- 5개 시각화 차트 (인력 / 생산 / 재고 / 비용 / 수요충족 검증)
- 사용자 임계값 기반 진단

## 모델
- 결정변수 8개(NonNegative)
- 목적함수(Z): 총비용 최소화
- 제약조건 5종: 노동력 균형, 생산능력, 재고 균형, 초과근무 한도, 초기/최종값
- Solver: GLPK

## 배포
https://horticulture-app.streamlit.app/

## 모듈 구조
```
horticulture-app/
├── config.py        # 상수 (기본 파라미터, 색상, 슬라이더 범위)
├── model.py         # Pyomo 최적화 모델
├── analytics.py     # 결과 분석 (KPI, 비용 분해, 진단)
├── charts.py        # Plotly 차트 5개
├── tables.py        # LP/IP 비교 표 (UI 미노출, 라이브러리로만 보존)
├── app.py           # Streamlit UI 진입점
│
├── requirements.txt # Python 패키지
├── packages.txt     # 시스템 패키지 (GLPK)
└── README.md
```

- `tables.py`는 LP/IP 결정변수 비교 표 + CSV 다운로드 기능을 제공하지만, 차트 5개로 시각화가 충분하다고 판단해 현재 UI에 노출하지 않음
- 라이러리로 보존되어있어 표 기능이 필요할 때 import만 하여 즉시 복원 가능

**의존성 흐름**: `config` → `model` → `analytics` → `charts` / `tables` → `app`