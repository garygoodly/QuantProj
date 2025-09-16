
from __future__ import annotations
import backtrader as bt


def run_backtest(strategy_cls,
                 data_feed: bt.feeds.PandasData,
                 initial_cash: float = 100_000.0,
                 commission: float = 0.001,
                 sizer_stake: int = 100,
                 analyzers=None,
                 strategy_kwargs=None):
    analyzers = analyzers or []
    strategy_kwargs = strategy_kwargs or {}

    cerebro = bt.Cerebro()
    cerebro.adddata(data_feed)
    cerebro.addstrategy(strategy_cls, **strategy_kwargs)
    cerebro.broker.setcash(initial_cash)
    cerebro.broker.setcommission(commission=commission)
    cerebro.addsizer(bt.sizers.FixedSize, stake=sizer_stake)

    for an, name, kwargs in analyzers:
        cerebro.addanalyzer(an, _name=name, **(kwargs or {}))

    strat = cerebro.run()[0]
    return cerebro, strat
