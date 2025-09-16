
# Minimal tests to ensure strategies load and run a few bars
import pandas as pd
from quantlab.strategies import get_strategy_class
from quantlab.core.data import bt_feed_from_df
from quantlab.core.engine import run_backtest


def tiny_df():
    idx = pd.date_range("2021-01-01", periods=50, freq="D")
    df = pd.DataFrame({
        "open": range(50),
        "high": [x+1 for x in range(50)],
        "low":  [x-1 for x in range(50)],
        "close": range(50),
        "volume": [1000]*50,
    }, index=idx)
    return df


def test_ma_cross_runs():
    strat_cls = get_strategy_class("ma_cross")
    feed = bt_feed_from_df(tiny_df())
    cerebro, strat = run_backtest(strat_cls, feed, sizer_stake=1)
    assert hasattr(strat, "trades")
