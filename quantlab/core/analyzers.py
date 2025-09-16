
from __future__ import annotations
import backtrader as bt

DEFAULT_ANALYZERS = [
    (bt.analyzers.TradeAnalyzer, "ta", None),
    (bt.analyzers.SharpeRatio_A, "sharpe", {"riskfreerate": 0.0}),
    (bt.analyzers.DrawDown, "dd", None),
]
