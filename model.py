from dataclasses import dataclass, field
from typing import Tuple, Literal

from pyomo.environ import (
    ConcreteModel, Var, Objective, Constraint,
    NonNegativeReals, NonNegativeIntegers,
    SolverFactory, minimize, value,
)


# 입력 파라미터 클래스
@dataclass(frozen=True)
class APPParameters:
    demand: Tuple[float, ...]

    regular_wage: float
    overtime_wage: float
    hiring_cost: float
    firing_cost: float
    holding_cost: float
    backlog_cost: float
    material_cost: float
    outsourcing_cost: float
    sale_price: float

    work_days: int
    work_hours: int
    standard_time: float
    max_overtime_per_person: int

    initial_workers: int
    initial_inventory: int
    initial_shortage: int
    final_inventory_min: int
    final_shortage: int

    @property
    def horizon(self) -> int:
        return len(self.demand)

    @property
    def regular_labor_cost_per_worker(self) -> float:
        return self.regular_wage * self.work_hours * self.work_days

    @property
    def regular_capacity_per_worker(self) -> float:
        return self.work_days * self.work_hours / self.standard_time

    @property
    def overtime_capacity_per_hour(self) -> float:
        return 1.0 / self.standard_time


# 최적화 결과 클래스
@dataclass(frozen=True)
class APPResult:
    status: str
    total_cost: float
    horizon: int
    params: APPParameters
    model_type: Literal["LP", "IP"]

    D: Tuple[float, ...]
    W: Tuple[float, ...]
    H: Tuple[float, ...]
    L: Tuple[float, ...]
    P: Tuple[float, ...]
    I: Tuple[float, ...]
    S: Tuple[float, ...]
    C: Tuple[float, ...]
    O: Tuple[float, ...]

    @property
    def is_optimal(self) -> bool:
        return self.status == "optimal"


# 최적화 모델 클래스
class APPModel:
    def __init__(self, params: APPParameters, model_type: Literal["LP", "IP"] = "LP"):
        if model_type not in ("LP", "IP"):
            raise ValueError(f"model_type must be 'LP' or 'IP', got {model_type!r}")
        self.params = params
        self.model_type = model_type
        self._model = self._build()

    def _build(self) -> ConcreteModel:
        p = self.params
        TH = p.horizon
        TIME = list(range(0, TH + 1))
        T = list(range(1, TH + 1))
        D = p.demand

        var_domain = NonNegativeIntegers if self.model_type == "IP" else NonNegativeReals

        m = ConcreteModel()

        m.W = Var(TIME, domain=var_domain, bounds=(0, None))
        m.H = Var(TIME, domain=var_domain, bounds=(0, None))
        m.L = Var(TIME, domain=var_domain, bounds=(0, None))
        m.P = Var(TIME, domain=var_domain, bounds=(0, None))
        m.I = Var(TIME, domain=var_domain, bounds=(0, None))
        m.S = Var(TIME, domain=var_domain, bounds=(0, None))
        m.C = Var(TIME, domain=var_domain, bounds=(0, None))
        m.O = Var(TIME, domain=NonNegativeReals, bounds=(0, None))

        wage_unit = p.regular_labor_cost_per_worker

        m.Cost = Objective(
            rule=lambda m: sum(
                wage_unit * m.W[t]
                + p.overtime_wage * m.O[t]
                + p.hiring_cost * m.H[t]
                + p.firing_cost * m.L[t]
                + p.holding_cost * m.I[t]
                + p.backlog_cost * m.S[t]
                + p.material_cost * m.P[t]
                + p.outsourcing_cost * m.C[t]
                for t in T
            ),
            sense=minimize,
        )

        m.labor = Constraint(
            T, rule=lambda m, t: m.W[t] == m.W[t-1] + m.H[t] - m.L[t]
        )

        reg_cap = p.regular_capacity_per_worker
        ot_cap = p.overtime_capacity_per_hour
        m.capacity = Constraint(
            T, rule=lambda m, t: m.P[t] <= reg_cap * m.W[t] + ot_cap * m.O[t]
        )

        m.inventory = Constraint(
            T,
            rule=lambda m, t: m.I[t] == m.I[t-1] + m.P[t] + m.C[t]
                                       - D[t-1] - m.S[t-1] + m.S[t],
        )

        m.overtime = Constraint(
            T, rule=lambda m, t: m.O[t] <= p.max_overtime_per_person * m.W[t]
        )

        m.W_0 = Constraint(rule=lambda m: m.W[0] == p.initial_workers)
        m.I_0 = Constraint(rule=lambda m: m.I[0] == p.initial_inventory)
        m.S_0 = Constraint(rule=lambda m: m.S[0] == p.initial_shortage)
        m.last_inventory = Constraint(rule=lambda m: m.I[TH] >= p.final_inventory_min)
        m.last_shortage = Constraint(rule=lambda m: m.S[TH] == p.final_shortage)

        for var in (m.H, m.L, m.P, m.C, m.O):
            var[0].fix(0)

        return m

    def solve(self, solver_name: str = "glpk") -> APPResult:
        results = SolverFactory(solver_name).solve(self._model)
        status = str(results.solver.termination_condition)

        if status != "optimal":
            return APPResult(
                status=status,
                total_cost=float("nan"),
                horizon=self.params.horizon,
                params=self.params,
                model_type=self.model_type,
                D=tuple(self.params.demand),
                W=(), H=(), L=(), P=(), I=(), S=(), C=(), O=(),
            )

        m = self._model
        TH = self.params.horizon
        time_range = range(0, TH + 1)

        return APPResult(
            status="optimal",
            total_cost=float(value(m.Cost)),
            horizon=TH,
            params=self.params,
            model_type=self.model_type,
            D=tuple(self.params.demand),
            W=tuple(float(value(m.W[t])) for t in time_range),
            H=tuple(float(value(m.H[t])) for t in time_range),
            L=tuple(float(value(m.L[t])) for t in time_range),
            P=tuple(float(value(m.P[t])) for t in time_range),
            I=tuple(float(value(m.I[t])) for t in time_range),
            S=tuple(float(value(m.S[t])) for t in time_range),
            C=tuple(float(value(m.C[t])) for t in time_range),
            O=tuple(float(value(m.O[t])) for t in time_range),
        )