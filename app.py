from typing import List, Optional, Tuple

import streamlit as st

from model import APPParameters, APPModel, APPResult
from analytics import Thresholds, ResultAnalyzer, KPIReport, Diagnosis
from charts import ChartBuilder
from config import (
    DEFAULT_PARAMS, DEFAULT_THRESHOLDS,
    SLIDER_RANGES, STATUS_EMOJI,
    MIN_PLANNING_HORIZON, MAX_PLANNING_HORIZON, DEFAULT_PLANNING_HORIZON,
    DEMAND_MIN, DEMAND_MAX, DEMAND_STEP,
)


class DashboardApp:
    PAGE_TITLE = "원예장비 총괄생산계획"

    def __init__(self):
        self._configure_page()
        self._init_session_state()

    def _configure_page(self) -> None:
        st.set_page_config(
            page_title="총괄생산계획 대시보드",
            page_icon="🌳",
            layout="wide",
            initial_sidebar_state="expanded",
        )

    def _init_session_state(self) -> None:
        if "demand_count" not in st.session_state:
            st.session_state.demand_count = DEFAULT_PLANNING_HORIZON
        if "last_result_lp" not in st.session_state:
            st.session_state.last_result_lp = None
        if "last_result_ip" not in st.session_state:
            st.session_state.last_result_ip = None
        if "last_thresholds" not in st.session_state:
            st.session_state.last_thresholds = None

    def _render_demand_section(self) -> Tuple[float, ...]:
        st.sidebar.subheader("수요 (개/월)")

        count = st.session_state.demand_count
        demand_values: List[float] = []
        defaults = DEFAULT_PARAMS["demand"]

        for i in range(count):
            default_val = defaults[i] if i < len(defaults) else 2000
            val = st.sidebar.number_input(
                f"{i+1}월",
                min_value=DEMAND_MIN, max_value=DEMAND_MAX,
                value=int(default_val), step=DEMAND_STEP,
                key=f"demand_{i}",
            )
            demand_values.append(float(val))

        col_a, col_b = st.sidebar.columns(2)
        with col_a:
            if st.button("➕ 월 추가", use_container_width=True,
                         disabled=count >= MAX_PLANNING_HORIZON):
                st.session_state.demand_count += 1
                st.rerun()
        with col_b:
            if st.button("➖ 월 삭제", use_container_width=True,
                         disabled=count <= MIN_PLANNING_HORIZON):
                st.session_state.demand_count -= 1
                st.rerun()

        return tuple(demand_values)

    def _render_cost_section(self) -> dict:
        st.sidebar.subheader("비용 파라미터 (천원)")
        labels = {
            "regular_wage":     "정규임금 (시간)",
            "overtime_wage":    "초과임금 (시간)",
            "hiring_cost":      "고용비용 (인)",
            "firing_cost":      "해고비용 (인)",
            "holding_cost":     "재고유지비 (개·월)",
            "backlog_cost":     "부재고비용 (개·월)",
            "material_cost":    "재료비 (개)",
            "outsourcing_cost": "하청비용 (개)",
            "sale_price":       "판매단가 (개)",
        }
        values = {}
        for key, label in labels.items():
            lo, hi, step = SLIDER_RANGES[key]
            values[key] = st.sidebar.slider(
                label, min_value=lo, max_value=hi,
                value=DEFAULT_PARAMS[key], step=step,
                key=f"cost_{key}",
            )
        return values

    def _render_work_section(self) -> dict:
        st.sidebar.subheader("작업 조건")
        return {
            "work_days": st.sidebar.number_input(
                "작업일수 (일/월)", 1, 31, DEFAULT_PARAMS["work_days"], 1,
                key="work_days"),
            "work_hours": st.sidebar.number_input(
                "작업시간 (시간/일)", 1, 24, DEFAULT_PARAMS["work_hours"], 1,
                key="work_hours"),
            "standard_time": st.sidebar.number_input(
                "표준 작업시간 (시간/개)", 0.1, 100.0, float(DEFAULT_PARAMS["standard_time"]), 0.5,
                key="standard_time"),
            "max_overtime_per_person": st.sidebar.number_input(
                "1인 잔업 한도 (시간/월)", 0, 100, DEFAULT_PARAMS["max_overtime_per_person"], 1,
                key="max_overtime_per_person"),
        }

    def _render_initial_section(self) -> dict:
        st.sidebar.subheader("초기/최종 조건")
        return {
            "initial_workers": st.sidebar.number_input(
                "초기 작업자 수 (명)", 0, 1000, DEFAULT_PARAMS["initial_workers"], 1,
                key="initial_workers"),
            "initial_inventory": st.sidebar.number_input(
                "초기 재고 (개)", 0, 100000, DEFAULT_PARAMS["initial_inventory"], 50,
                key="initial_inventory"),
            "initial_shortage": st.sidebar.number_input(
                "초기 부재고 (개)", 0, 100000, DEFAULT_PARAMS["initial_shortage"], 50,
                key="initial_shortage"),
            "final_inventory_min": st.sidebar.number_input(
                "최종 재고 하한 = 안전재고 (개)", 0, 100000, DEFAULT_PARAMS["final_inventory_min"], 50,
                key="final_inventory_min"),
            "final_shortage": st.sidebar.number_input(
                "최종 부재고 (개)", 0, 100000, DEFAULT_PARAMS["final_shortage"], 50,
                key="final_shortage"),
        }

    def _render_thresholds_section(self) -> Thresholds:
        st.sidebar.subheader("판단 기준")
        st.sidebar.caption("계획의 적절성을 평가할 임계값")

        max_backlog = st.sidebar.number_input(
            "허용 부재고 발생 월 수", 0, 12, DEFAULT_THRESHOLDS["max_backlog_months"], 1,
            key="th_backlog")
        max_adjust = st.sidebar.number_input(
            "월별 인력 조정 허용폭 (명)", 0, 100, DEFAULT_THRESHOLDS["max_workforce_adjustment"], 1,
            key="th_workforce")
        target_margin = st.sidebar.number_input(
            "목표 영업이익률 (%)", 0.0, 100.0, DEFAULT_THRESHOLDS["target_profit_margin"], 1.0,
            key="th_margin")

        return Thresholds(
            max_backlog_months=max_backlog,
            max_workforce_adjustment=max_adjust,
            target_profit_margin=target_margin,
        )

    def _render_sidebar(self) -> Tuple[APPParameters, Thresholds, bool, bool]:
        st.sidebar.title("입력")

        demand = self._render_demand_section()
        st.sidebar.divider()
        cost = self._render_cost_section()
        st.sidebar.divider()
        work = self._render_work_section()
        st.sidebar.divider()
        initial = self._render_initial_section()
        st.sidebar.divider()
        thresholds = self._render_thresholds_section()
        st.sidebar.divider()

        params = APPParameters(demand=demand, **cost, **work, **initial)

        col_run, col_reset = st.sidebar.columns(2)
        with col_run:
            run_clicked = st.button("최적화 실행", type="primary", use_container_width=True)
        with col_reset:
            reset_clicked = st.button("↺ 기본값 리셋", use_container_width=True)

        return params, thresholds, run_clicked, reset_clicked

    def _solve(self, params: APPParameters) -> Tuple[APPResult, Optional[APPResult]]:
        with st.spinner("LP 모델 풀이 중..."):
            result_lp = APPModel(params, "LP").solve()
        with st.spinner("IP 모델 풀이 중..."):
            result_ip = APPModel(params, "IP").solve()
        return result_lp, result_ip

    def _render_kpis(self, kpi: KPIReport) -> None:
        cols = st.columns(5)

        with cols[0]:
            st.metric(
                label="LP 총비용 (천원)",
                value=f"{kpi.total_cost_lp:,.0f}",
            )

        with cols[1]:
            ip_label = "IP 총비용 (천원)"
            ip_value = f"{kpi.total_cost_ip:,.0f}" if kpi.total_cost_ip is not None else "—"
            ip_delta = (f"{kpi.ip_lp_gap_pct:+.3f}% vs LP"
                        if kpi.ip_lp_gap_pct is not None else None)
            st.metric(label=ip_label, value=ip_value, delta=ip_delta,
                      delta_color="inverse",
                      )

        with cols[2]:
            emoji = STATUS_EMOJI[kpi.diagnosis_profit.value]
            st.metric(
                label=f"{emoji} 영업이익률 (보조)",
                value=f"{kpi.profit_margin:.1f}%",
                help=f"매출 {kpi.revenue:,.0f} − 비용 {kpi.total_cost_ip or kpi.total_cost_lp:,.0f}",
            )

        with cols[3]:
            emoji = STATUS_EMOJI[kpi.diagnosis_backlog.value]
            st.metric(
                label=f"{emoji} 부재고 발생",
                value=f"{kpi.backlog_months}개월",
                delta=f"최대 {kpi.max_backlog:.0f}개" if kpi.max_backlog > 0 else None,
                delta_color="inverse",
                help="계획기간 중 수요를 다 채우지 못해 부재고가 발생한 달의 수",
            )

        with cols[4]:
            emoji = STATUS_EMOJI[kpi.diagnosis_workforce.value]
            st.metric(
                label=f"{emoji} 최대 인력조정",
                value=f"{kpi.max_workforce_adjustment}명",
                help="한 달에 발생한 (고용+해고) 최댓값",
            )

    def _render_supplementary_kpis(self, kpi: KPIReport) -> None:
        cols = st.columns(4)
        with cols[0]:
            st.metric("평균 재고", f"{kpi.avg_inventory:,.0f}개")
        with cols[1]:
            st.metric("최종 재고", f"{kpi.final_inventory:,.0f}개")
        with cols[2]:
            st.metric("총 잔업시간", f"{kpi.total_overtime:,.0f}시간")
        with cols[3]:
            st.metric("총 외주량", f"{kpi.total_outsourcing:,.0f}개")

    def _render_charts(self, builder: ChartBuilder) -> None:
        config = {"displayModeBar": False}
        st.plotly_chart(builder.workforce(), use_container_width=True, config=config)
        st.plotly_chart(builder.production(), use_container_width=True, config=config)
        st.plotly_chart(builder.inventory(), use_container_width=True, config=config)
        st.plotly_chart(builder.cost_breakdown(), use_container_width=True, config=config)
        st.plotly_chart(builder.demand_fulfillment(), use_container_width=True, config=config)

    def _render_results(
        self,
        result_lp: APPResult,
        result_ip: Optional[APPResult],
        thresholds: Thresholds,
    ) -> None:
        if not result_lp.is_optimal:
            st.error(
                f"LP 풀이 실패: `{result_lp.status}`\n\n"
                "가능한 원인:\n"
                "- 수요가 생산능력을 크게 초과\n"
                "- 안전재고가 너무 높음\n"
                "- 잔업/외주 한도가 너무 낮음\n\n"
                "사이드바에서 파라미터를 조정한 뒤 다시 시도해 주세요."
            )
            return

        analyzer = ResultAnalyzer(result_lp, result_ip, thresholds)
        kpi = analyzer.kpis()
        builder = ChartBuilder(analyzer)

        st.caption(f"차트 기준: **{analyzer.chart_basis}** "
                   f"({'정수 실행계획' if analyzer.chart_basis == 'IP' else '연속 풀이 (IP infeasible)'})")

        if result_ip is not None and not result_ip.is_optimal:
            st.warning(f"IP는 풀리지 않았습니다 (`{result_ip.status}`). LP 결과로 표시합니다.")

        self._render_kpis(kpi)
        st.divider()
        self._render_supplementary_kpis(kpi)
        st.divider()

        self._render_charts(builder)

    def _render_welcome(self) -> None:
        st.info(
            "사이드바에서 **파라미터를 입력**하고 **최적화 실행** 버튼을 누르세요.\n\n"
            "기본값은 6개월입니다."
        )
        with st.expander("모델 설명"):
            st.markdown("""
**총괄생산계획**은 중장기 계획기간 동안 다음 8개를 매월 결정하는 최적화 문제입니다:

| 변수 | 의미 |
|:---:|:---:|
| **W** | 작업자 수 (인/월)|
| **H** | 고용 (인/월)|
| **L** | 해고 (인/월)|
| **P** | 생산량 (개/월)|
| **I** | 재고 (개/월)|
| **S** | 부족재고 (개/월)|
| **C** | 외주 (개/월)|
| **O** | 초과시간 (시간/월)|

**목적함수**: 8개 비용 항목 합계의 최소화
                        
**풀이방식**: LP / IP 두 가지 모두 수행하여 비교

**수요, 비용, 작업조건이 바뀌면 새 최적계획이 다시 수립됩니다.**
            """)

    def run(self) -> None:
        st.title(self.PAGE_TITLE)

        params, thresholds, run_clicked, reset_clicked = self._render_sidebar()

        if reset_clicked:
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()

        if run_clicked:
            result_lp, result_ip = self._solve(params)
            st.session_state.last_result_lp = result_lp
            st.session_state.last_result_ip = result_ip
            st.session_state.last_thresholds = thresholds

        if st.session_state.last_result_lp is not None:
            self._render_results(
                st.session_state.last_result_lp,
                st.session_state.last_result_ip,
                st.session_state.last_thresholds,
            )
        else:
            self._render_welcome()


if __name__ == "__main__":
    DashboardApp().run()