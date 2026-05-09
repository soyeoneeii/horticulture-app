from typing import List

import plotly.graph_objects as go
from plotly.subplots import make_subplots

from analytics import ResultAnalyzer, Diagnosis
from config import COLORS, COST_COLORS, STATUS_COLORS


class ChartBuilder:
    HEIGHT_DEFAULT = 380
    HEIGHT_TALL = 460
    MARGIN = dict(l=50, r=30, t=70, b=40)
    FONT = dict(family="Arial, 'Apple SD Gothic Neo', sans-serif", size=12)
    LEGEND_TOP = dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)

    def __init__(self, analyzer: ResultAnalyzer):
        self.analyzer = analyzer
        self.params = analyzer.params
        self.thresholds = analyzer.thresholds
        self.TH = analyzer.TH
        self.months = [f"{i}월" for i in range(1, self.TH + 1)]

    def _base_layout(self, title: str, height: int = None) -> dict:
        return dict(
            title=dict(text=title, x=0.02, xanchor="left",
                       font=dict(size=15, color="#2C3E50")),
            height=height or self.HEIGHT_DEFAULT,
            margin=self.MARGIN,
            font=self.FONT,
            legend=self.LEGEND_TOP,
            plot_bgcolor="white",
            xaxis=dict(showgrid=False, linecolor="#BDC3C7"),
            yaxis=dict(gridcolor="#ECF0F1", linecolor="#BDC3C7"),
        )

    # 인력차트
    def workforce(self) -> go.Figure:
        r = self.analyzer.result_main
        T_idx = list(range(1, self.TH + 1))
        W = [r.W[t] for t in T_idx]
        H = [r.H[t] for t in T_idx]
        L = [r.L[t] for t in T_idx]
        L_neg = [-l for l in L]

        threshold = self.thresholds.max_workforce_adjustment
        initial_workers = self.params.initial_workers

        all_w = W + [initial_workers]
        w_span = max(all_w) - min(all_w)
        w_pad = max(3.0, w_span * 0.25)
        w_y_range = [max(0, min(all_w) - w_pad), max(all_w) + w_pad]

        max_change = max(max(H, default=0), max(L, default=0), float(threshold))
        if max_change == 0:
            max_change = 1
        change_y = max_change * 1.4

        fig = make_subplots(
            rows=2, cols=1,
            row_heights=[0.62, 0.38],
            shared_xaxes=True,
            vertical_spacing=0.2,
            subplot_titles=("작업자 수 W", "월별 인력 조정 (고용 H · 해고 L)"),
        )

        fig.add_trace(
            go.Scatter(
                x=self.months, y=W,
                name="작업자 수 W",
                mode="lines+markers+text",
                line=dict(color=COLORS["workers"], width=3),
                marker=dict(size=11, line=dict(color="white", width=2)),
                text=[f"{w:.0f}" for w in W],
                textposition="top center",
                textfont=dict(size=12, color=COLORS["workers"]),
                cliponaxis=False,
                hovertemplate="<b>%{x}</b><br>작업자: %{y:.1f}명<extra></extra>",
            ),
            row=1, col=1,
        )
        fig.add_hline(
            y=initial_workers,
            line_dash="dot", line_color=COLORS["workers"], opacity=0.5,
            annotation_text=f"초기 {initial_workers}명",
            annotation_position="top left",
            annotation_font=dict(size=10, color=COLORS["workers"]),
            row=1, col=1,
        )

        fig.add_trace(
            go.Bar(
                x=self.months, y=H,
                name="고용 H",
                marker_color=COLORS["hire"],
                marker_line=dict(color="white", width=1),
                text=[f"+{int(round(h))}" if h > 0.5 else "" for h in H],
                textposition="outside",
                textfont=dict(color=COLORS["hire"], size=11),
                cliponaxis=False,
                hovertemplate="<b>%{x}</b><br>고용: +%{y:.0f}명<extra></extra>",
            ),
            row=2, col=1,
        )
        fig.add_trace(
            go.Bar(
                x=self.months, y=L_neg,
                name="해고 L",
                marker_color=COLORS["fire"],
                marker_line=dict(color="white", width=1),
                text=[f"-{int(round(l))}" if l > 0.5 else "" for l in L],
                textposition="outside",
                textfont=dict(color=COLORS["fire"], size=11),
                cliponaxis=False,
                hovertemplate="<b>%{x}</b><br>해고: %{customdata:.0f}명<extra></extra>",
                customdata=L,
            ),
            row=2, col=1,
        )

        if threshold > 0:
            fig.add_hline(
                y=threshold,
                line_dash="dash", line_color="#7F8C8D", opacity=0.7,
                annotation_text=f"임계 +{threshold}",
                annotation_position="top right",
                annotation_font=dict(size=10, color="#7F8C8D"),
                row=2, col=1,
            )
            fig.add_hline(
                y=-threshold,
                line_dash="dash", line_color="#7F8C8D", opacity=0.7,
                annotation_text=f"임계 -{threshold}",
                annotation_position="bottom right",
                annotation_font=dict(size=10, color="#7F8C8D"),
                row=2, col=1,
            )

        layout = self._base_layout("① 인력 결정", height=self.HEIGHT_TALL)
        layout["margin"] = dict(l=60, r=30, t=80, b=40)
        fig.update_layout(**layout)

        fig.update_yaxes(
            title_text="작업자 (명)", row=1, col=1,
            range=w_y_range,
            gridcolor="#ECF0F1", linecolor="#BDC3C7",
        )
        fig.update_yaxes(
            title_text="조정 (명)", row=2, col=1,
            range=[-change_y, change_y],
            gridcolor="#ECF0F1", linecolor="#BDC3C7",
            zeroline=True, zerolinecolor="#34495E", zerolinewidth=1.5,
        )
        fig.update_xaxes(showgrid=False, linecolor="#BDC3C7")

        return fig

    # 셍산차트
    def production(self) -> go.Figure:
        plan = self.analyzer.production_plan()
        cap = self.analyzer.capacity_usage()

        production = plan["production"]
        outsourcing = plan["outsourcing"]
        demand = plan["demand"]
        regular_capacity = cap["regular_capacity"]
        total_capacity = cap["capacity"]

        fig = go.Figure()

        fig.add_trace(go.Bar(
            x=self.months, y=production,
            name="생산량 P",
            marker_color=COLORS["regular_prod"],
            text=[f"{int(round(p))}" for p in production],
            textposition="inside",
            insidetextanchor="middle",
            textfont=dict(color="white", size=11),
            hovertemplate="<b>%{x}</b><br>생산: %{y:.0f}개<extra></extra>",
        ))
        fig.add_trace(go.Bar(
            x=self.months, y=outsourcing,
            name="외주 C",
            marker_color=COLORS["outsource"],
            text=[f"외주 +{int(round(c))}" if c > 0.5 else "" for c in outsourcing],
            textposition="outside",
            textfont=dict(color=COLORS["outsource"], size=10),
            cliponaxis=False,
            hovertemplate="<b>%{x}</b><br>외주: %{y:.0f}개<extra></extra>",
        ))

        fig.add_trace(go.Scatter(
            x=self.months, y=regular_capacity,
            name="정규 능력 (40·W)",
            mode="lines",
            line=dict(color=COLORS["capacity"], width=2, dash="dash"),
            hovertemplate="<b>%{x}</b><br>정규 능력: %{y:.0f}개<extra></extra>",
        ))
        fig.add_trace(go.Scatter(
            x=self.months, y=total_capacity,
            name="총 능력 (40·W + O/4)",
            mode="lines",
            line=dict(color=COLORS["overtime_prod"], width=2, dash="dash"),
            hovertemplate="<b>%{x}</b><br>총 능력: %{y:.0f}개<extra></extra>",
        ))
        fig.add_trace(go.Scatter(
            x=self.months, y=demand,
            name="수요 D",
            mode="lines+markers",
            line=dict(color=COLORS["demand"], width=2, dash="dot"),
            marker=dict(size=8, symbol="diamond"),
            hovertemplate="<b>%{x}</b><br>수요: %{y:.0f}개<extra></extra>",
        ))

        layout = self._base_layout("② 생산 결정 (생산 P · 외주 C · 능력 한계 · 수요 D)")
        layout["barmode"] = "stack"
        fig.update_layout(**layout)
        fig.update_yaxes(title_text="수량 (개)")
        return fig

    # 재고차트
    def inventory(self) -> go.Figure:
        r = self.analyzer.result_main
        T_idx = list(range(1, self.TH + 1))
        I = [r.I[t] for t in T_idx]
        S_neg = [-r.S[t] for t in T_idx]
        safety_stock = self.params.final_inventory_min

        fig = go.Figure()

        fig.add_trace(go.Scatter(
            x=self.months, y=I,
            name="재고 I",
            mode="lines+markers",
            line=dict(color=COLORS["inventory"], width=3),
            marker=dict(size=10),
            fill="tozeroy",
            fillcolor="rgba(52, 152, 219, 0.2)",
            hovertemplate="<b>%{x}</b><br>재고: %{y:.0f}개<extra></extra>",
        ))

        fig.add_trace(go.Scatter(
            x=self.months, y=S_neg,
            name="부재고 S",
            mode="lines+markers",
            line=dict(color=COLORS["shortage"], width=3),
            marker=dict(size=10),
            fill="tozeroy",
            fillcolor="rgba(231, 76, 60, 0.3)",
            hovertemplate="<b>%{x}</b><br>부재고: %{customdata:.0f}개<extra></extra>",
            customdata=[-s for s in S_neg],
        ))

        fig.add_hline(
            y=safety_stock,
            line_dash="dash", line_color=COLORS["safety"], line_width=2,
            annotation_text=f"안전재고 {safety_stock}",
            annotation_position="top right",
            annotation_font=dict(color=COLORS["safety"], size=11),
        )
        fig.add_hline(y=0, line_color="#7F8C8D", line_width=1)

        layout = self._base_layout("③ 재고 결정 (재고 I · 부재고 S · 안전재고선)")
        fig.update_layout(**layout)
        fig.update_yaxes(title_text="수량 (개)", zeroline=True,
                         zerolinecolor="#7F8C8D", zerolinewidth=1)
        return fig

    # 비용차트
    def cost_breakdown(self) -> go.Figure:
        breakdown = self.analyzer.cost_breakdown()

        fig = make_subplots(
            rows=1, cols=2,
            column_widths=[0.62, 0.38],
            specs=[[{"type": "bar"}, {"type": "domain"}]],
            subplot_titles=("월별 비용 구성 (시기별 변동)", "전체 비용 비중 (총합 점유율)"),
            horizontal_spacing=0.08,
        )

        for category, monthly_values in breakdown.monthly.items():
            fig.add_trace(
                go.Bar(
                    x=self.months, y=monthly_values,
                    name=category,
                    marker_color=COST_COLORS[category],
                    hovertemplate=f"<b>%{{x}}</b><br>{category}: %{{y:,.0f}}천원<extra></extra>",
                ),
                row=1, col=1,
            )

        sorted_items = sorted(breakdown.total.items(), key=lambda kv: kv[1], reverse=True)
        labels = [k for k, _ in sorted_items]
        values = [v for _, v in sorted_items]
        colors = [COST_COLORS[k] for k in labels]

        fig.add_trace(
            go.Pie(
                labels=labels, values=values,
                marker=dict(colors=colors, line=dict(color="white", width=2)),
                hole=0.5,
                textinfo="none",
                showlegend=False,
                sort=False,
                direction="clockwise",
                hovertemplate="<b>%{label}</b><br>%{value:,.0f}천원 (%{percent})<extra></extra>",
            ),
            row=1, col=2,
        )

        layout = self._base_layout("④ 비용 구조 분해 (8개 항목)", height=self.HEIGHT_TALL)
        layout["barmode"] = "stack"
        layout["margin"] = dict(l=60, r=30, t=70, b=90)
        layout["legend"] = dict(
            orientation="h",
            yanchor="top", y=-0.18,
            xanchor="center", x=0.5,
        )
        fig.update_layout(**layout)
        fig.update_yaxes(title_text="비용 (천원)", row=1, col=1, gridcolor="#ECF0F1")
        return fig

    def demand_fulfillment(self) -> go.Figure:
        plan = self.analyzer.production_plan()
        fulfillment = self.analyzer.demand_fulfillment()
        demand = plan["demand"]
        gaps = [f - d for f, d in zip(fulfillment, demand)]

        fig = go.Figure()

        fig.add_trace(go.Bar(
            x=self.months, y=demand,
            name="수요 D",
            marker_color="rgba(44, 62, 80, 0.25)",
            marker_line=dict(color=COLORS["demand"], width=1.5),
            hovertemplate="<b>%{x}</b><br>수요: %{y:.0f}개<extra></extra>",
        ))

        fig.add_trace(go.Scatter(
            x=self.months, y=fulfillment,
            name="충족량 (P+C-ΔI+ΔS)",
            mode="lines+markers",
            line=dict(color=COLORS["supply"], width=3),
            marker=dict(size=10, symbol="circle"),
            hovertemplate="<b>%{x}</b><br>충족: %{y:.0f}개<extra></extra>",
        ))

        for month, gap, d_val in zip(self.months, gaps, demand):
            if abs(gap) < 0.5:
                continue
            fig.add_annotation(
                x=month, y=d_val,
                text=f"갭 {gap:+.0f}",
                showarrow=False,
                yshift=20,
                font=dict(size=10, color=COLORS["shortage"] if gap < 0 else COLORS["inventory"]),
            )

        layout = self._base_layout("⑤ 수요 충족 검증 (재고균형식 좌변 vs 수요)")
        fig.update_layout(**layout)
        fig.update_yaxes(title_text="수량 (개)")
        return fig