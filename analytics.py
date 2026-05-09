from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional

from model import APPResult


class Diagnosis(Enum):
    GREEN = "green"
    YELLOW = "yellow"
    RED = "red"


# 사용자 입력 판단 기준
@dataclass(frozen=True)
class Thresholds:
    max_backlog_months: int
    max_workforce_adjustment: int
    target_profit_margin: float

    def diagnose_backlog(self, observed_months: int) -> Diagnosis:
        if observed_months <= self.max_backlog_months:
            return Diagnosis.GREEN
        if observed_months == self.max_backlog_months + 1:
            return Diagnosis.YELLOW
        return Diagnosis.RED

    def diagnose_workforce(self, observed_adjustment: int) -> Diagnosis:
        if observed_adjustment <= self.max_workforce_adjustment:
            return Diagnosis.GREEN
        if observed_adjustment <= self.max_workforce_adjustment * 2:
            return Diagnosis.YELLOW
        return Diagnosis.RED

    def diagnose_profit_margin(self, observed_margin: float) -> Diagnosis:
        if observed_margin >= self.target_profit_margin:
            return Diagnosis.GREEN
        if observed_margin >= self.target_profit_margin * 0.5:
            return Diagnosis.YELLOW
        return Diagnosis.RED


@dataclass(frozen=True)
class CostBreakdown:
    monthly: Dict[str, List[float]]
    total: Dict[str, float]

    @property
    def grand_total(self) -> float:
        return sum(self.total.values())


@dataclass(frozen=True)
class KPIReport:

    total_cost_lp: float
    total_cost_ip: Optional[float]
    ip_lp_gap_pct: Optional[float]

    revenue: float
    profit: float
    profit_margin: float

    backlog_months: int
    max_backlog: float
    max_workforce_adjustment: int
    avg_inventory: float
    final_inventory: float
    total_overtime: float
    total_outsourcing: float

    diagnosis_backlog: Diagnosis
    diagnosis_workforce: Diagnosis
    diagnosis_profit: Diagnosis


# 분석 메서드 제공
class ResultAnalyzer:
    EPSILON = 1e-6

    def __init__(
        self,
        result_lp: APPResult,
        result_ip: Optional[APPResult],
        thresholds: Thresholds,
    ):
        if not result_lp.is_optimal:
            raise ValueError(f"LP result is not optimal: {result_lp.status}")

        self.result_lp = result_lp
        self.result_ip = result_ip
        self.thresholds = thresholds

        if result_ip is not None and result_ip.is_optimal:
            self.result_main = result_ip
            self.chart_basis = "IP"
        else:
            self.result_main = result_lp
            self.chart_basis = "LP"

        self.params = self.result_main.params
        self.TH = self.result_main.horizon

    def _safe_pct(self, numerator: float, denominator: float) -> float:
        return (numerator / denominator * 100.0) if denominator > self.EPSILON else 0.0

    def cost_breakdown(self) -> CostBreakdown:
        r = self.result_main
        p = self.params
        T = range(1, self.TH + 1)
        wage_unit = p.regular_labor_cost_per_worker

        monthly = {
            "정규임금":   [wage_unit * r.W[t] for t in T],
            "초과임금":   [p.overtime_wage * r.O[t] for t in T],
            "고용비용":   [p.hiring_cost * r.H[t] for t in T],
            "해고비용":   [p.firing_cost * r.L[t] for t in T],
            "재고유지비": [p.holding_cost * r.I[t] for t in T],
            "부재고비용": [p.backlog_cost * r.S[t] for t in T],
            "재료비":     [p.material_cost * r.P[t] for t in T],
            "하청비용":   [p.outsourcing_cost * r.C[t] for t in T],
        }
        total = {k: sum(v) for k, v in monthly.items()}
        return CostBreakdown(monthly=monthly, total=total)

    def production_plan(self) -> Dict[str, List[float]]:
        r = self.result_main
        T = range(1, self.TH + 1)
        return {
            "demand":      list(r.D),
            "production":  [r.P[t] for t in T],
            "outsourcing": [r.C[t] for t in T],
        }

    def capacity_usage(self) -> Dict[str, List[float]]:
        """강의록 생산능력 제약식 P_t ≤ 40W_t + O_t/4 의 좌변/우변 및 활용률.

        'capacity'는 정규+잔업 총 능력 (제약식 우변).
        'regular_capacity'는 정규시간만의 능력 (40W_t) — 시각화 분리용.
        """
        r = self.result_main
        p = self.params
        T = range(1, self.TH + 1)

        regular_capacity = [p.regular_capacity_per_worker * r.W[t] for t in T]
        capacity = [
            reg + p.overtime_capacity_per_hour * r.O[t]
            for reg, t in zip(regular_capacity, T)
        ]
        production = [r.P[t] for t in T]
        utilization = [self._safe_pct(p_t, cap) for p_t, cap in zip(production, capacity)]

        return {
            "production":       production,
            "regular_capacity": regular_capacity,
            "capacity":         capacity,
            "utilization":      utilization,
        }

    def overtime_usage(self) -> Dict[str, List[float]]:
        r = self.result_main
        p = self.params
        T = range(1, self.TH + 1)

        overtime_limit = [p.max_overtime_per_person * r.W[t] for t in T]
        overtime_used = [r.O[t] for t in T]
        utilization = [self._safe_pct(o, lim) for o, lim in zip(overtime_used, overtime_limit)]

        return {
            "overtime":       overtime_used,
            "overtime_limit": overtime_limit,
            "utilization":    utilization,
        }

    def demand_fulfillment(self) -> List[float]:
        r = self.result_main
        T = range(1, self.TH + 1)

        return [
            r.P[t] + r.C[t] - (r.I[t] - r.I[t-1]) + (r.S[t] - r.S[t-1])
            for t in T
        ]

    def kpis(self) -> KPIReport:
        r_main = self.result_main
        p = self.params
        T = range(1, self.TH + 1)

        revenue = p.sale_price * sum(r_main.D)

        total_cost_lp = self.result_lp.total_cost
        total_cost_ip = None
        ip_lp_gap_pct = None
        if self.result_ip is not None and self.result_ip.is_optimal:
            total_cost_ip = self.result_ip.total_cost
            if total_cost_lp > self.EPSILON:
                ip_lp_gap_pct = (total_cost_ip - total_cost_lp) / total_cost_lp * 100.0

        chart_total_cost = r_main.total_cost
        profit = revenue - chart_total_cost
        profit_margin = self._safe_pct(profit, revenue)

        shortages = list(r_main.S[1:self.TH + 1])
        backlog_months = sum(1 for s in shortages if s > self.EPSILON)
        max_backlog = max(shortages, default=0.0)

        max_workforce_adjustment = max(
            (int(round(r_main.H[t] + r_main.L[t])) for t in T),
            default=0,
        )

        inventories = list(r_main.I[1:self.TH + 1])
        avg_inventory = sum(inventories) / self.TH if self.TH > 0 else 0.0
        final_inventory = inventories[-1] if inventories else 0.0

        total_overtime = sum(r_main.O[t] for t in T)
        total_outsourcing = sum(r_main.C[t] for t in T)

        th = self.thresholds
        return KPIReport(
            total_cost_lp=total_cost_lp,
            total_cost_ip=total_cost_ip,
            ip_lp_gap_pct=ip_lp_gap_pct,
            revenue=revenue,
            profit=profit,
            profit_margin=profit_margin,
            backlog_months=backlog_months,
            max_backlog=max_backlog,
            max_workforce_adjustment=max_workforce_adjustment,
            avg_inventory=avg_inventory,
            final_inventory=final_inventory,
            total_overtime=total_overtime,
            total_outsourcing=total_outsourcing,
            diagnosis_backlog=th.diagnose_backlog(backlog_months),
            diagnosis_workforce=th.diagnose_workforce(max_workforce_adjustment),
            diagnosis_profit=th.diagnose_profit_margin(profit_margin),
        )