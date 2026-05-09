import io
from typing import List, Optional, Tuple

import pandas as pd

from model import APPResult


class ComparisonTable:
    """LP/IP 결과를 나란히 비교하는 표 생성기."""

    VARIABLES: List[Tuple[str, str, str]] = [
        ("작업자 W",  "W", "인"),
        ("고용 H",    "H", "인"),
        ("해고 L",    "L", "인"),
        ("생산 P",    "P", "개"),
        ("재고 I",    "I", "개"),
        ("부재고 S",  "S", "개"),
        ("외주 C",    "C", "개"),
        ("잔업 O",    "O", "시간"),
    ]

    METHODS = ("LP", "LP반올림", "IP")

    def __init__(self, result_lp: APPResult, result_ip: Optional[APPResult]):
        if not result_lp.is_optimal:
            raise ValueError(f"LP result is not optimal: {result_lp.status}")
        self.result_lp = result_lp
        self.result_ip = result_ip if (result_ip is not None and result_ip.is_optimal) else None
        self.TH = result_lp.horizon
        self.months = [f"{i}월" for i in range(1, self.TH + 1)]

    def _values_for_method(self, method: str, var_attr: str) -> List:
        if method == "LP":
            raw = getattr(self.result_lp, var_attr)
            return [round(raw[t], 4) for t in range(1, self.TH + 1)]

        if method == "LP반올림":
            raw = getattr(self.result_lp, var_attr)
            return [int(round(raw[t])) for t in range(1, self.TH + 1)]

        if method == "IP":
            if self.result_ip is None:
                return ["—"] * self.TH
            raw = getattr(self.result_ip, var_attr)
            return [int(round(raw[t])) for t in range(1, self.TH + 1)]

        raise ValueError(f"Unknown method: {method}")

    def as_dataframe(self) -> pd.DataFrame:
        index_tuples = []
        rows = []
        for label, attr, unit in self.VARIABLES:
            full_label = f"{label} ({unit})"
            for method in self.METHODS:
                index_tuples.append((full_label, method))
                rows.append(self._values_for_method(method, attr))

        index = pd.MultiIndex.from_tuples(index_tuples, names=["변수", "풀이"])
        df = pd.DataFrame(rows, index=index, columns=self.months)
        return df

    def as_csv(self) -> bytes:
        df = self.as_dataframe()
        buf = io.StringIO()
        df.to_csv(buf, encoding="utf-8-sig")
        return buf.getvalue().encode("utf-8-sig")

    def summary_row(self) -> pd.DataFrame:
        data = {
            "총비용 (천원)": [
                round(self.result_lp.total_cost, 2),
                round(self.result_lp.total_cost),
                round(self.result_ip.total_cost) if self.result_ip else "—",
            ],
        }
        df = pd.DataFrame(data, index=list(self.METHODS))
        df.index.name = "풀이"
        return df