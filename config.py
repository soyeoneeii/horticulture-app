DEFAULT_PARAMS = {
    "demand": (1600, 3000, 3200, 3800, 2200, 2200),

    "regular_wage": 4,
    "overtime_wage": 6,
    "hiring_cost": 300,
    "firing_cost": 500,
    "holding_cost": 2,
    "backlog_cost": 5,
    "material_cost": 10,
    "outsourcing_cost": 30,
    "sale_price": 40,

    "work_days": 20,
    "work_hours": 8,
    "standard_time": 4,
    "max_overtime_per_person": 10,

    "initial_workers": 80,
    "initial_inventory": 1000,
    "initial_shortage": 0,
    "final_inventory_min": 500,
    "final_shortage": 0,
}


DEFAULT_THRESHOLDS = {
    "max_backlog_months": 0,
    "max_workforce_adjustment": 5,
    "target_profit_margin": 10.0,
}


COLORS = {
    "workers":       "#2E86AB",
    "hire":          "#06A77D",
    "fire":          "#D62246",
    "regular_prod":  "#4A90E2",
    "overtime_prod": "#F39C12",
    "outsource":     "#9B59B6",
    "demand":        "#2C3E50",
    "supply":        "#16A085",
    "inventory":     "#3498DB",
    "shortage":      "#E74C3C",
    "capacity":      "#7F8C8D",
    "safety":        "#E67E22",
}

COST_COLORS = {
    "정규임금":   "#3498DB",
    "초과임금":   "#F39C12",
    "고용비용":   "#06A77D",
    "해고비용":   "#D62246",
    "재고유지비": "#9B59B6",
    "부재고비용": "#E67E22",
    "재료비":     "#1ABC9C",
    "하청비용":   "#34495E",
}

STATUS_COLORS = {
    "green":  "#27AE60",
    "yellow": "#F39C12",
    "red":    "#E74C3C",
}

STATUS_EMOJI = {
    "green":  "🟢",
    "yellow": "🟡",
    "red":    "🔴",
}


MIN_PLANNING_HORIZON = 1
MAX_PLANNING_HORIZON = 12
DEFAULT_PLANNING_HORIZON = 6

SLIDER_RANGES = {
    "regular_wage":     (1, 20, 1),
    "overtime_wage":    (1, 30, 1),
    "hiring_cost":      (50, 1000, 50),
    "firing_cost":      (50, 1000, 50),
    "holding_cost":     (0, 20, 1),
    "backlog_cost":     (0, 30, 1),
    "material_cost":    (1, 50, 1),
    "outsourcing_cost": (10, 100, 5),
    "sale_price":       (10, 100, 5),
}

DEMAND_MIN = 0
DEMAND_MAX = 20000
DEMAND_STEP = 100