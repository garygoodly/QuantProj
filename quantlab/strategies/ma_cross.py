
# -*- coding: utf-8 -*-
"""
MaCrossStrategy: Price-SMA crossover strategy using Backtrader.
"""

import backtrader as bt


class MaCrossStrategy(bt.Strategy):
    params = (("ma_period", 20),)

    def __init__(self):
        self.sma = bt.indicators.SimpleMovingAverage(self.data.close,
                                                     period=self.p.ma_period)
        self.crossover = bt.ind.CrossOver(self.data.close, self.sma)
        self.trades = []

    def next(self):
        if not self.position and self.crossover[0] > 0:
            self.buy()
        elif self.position and self.crossover[0] < 0:
            self.sell()

    def notify_trade(self, trade):
        if trade.isclosed:
            dt_open = bt.num2date(trade.dtopen).replace(tzinfo=None)
            dt_close = bt.num2date(trade.dtclose).replace(tzinfo=None)
            exit_price = (trade.price + (trade.pnl / abs(trade.size))
                          if trade.size != 0 else None)
            self.trades.append({
                "entry_time": dt_open,
                "exit_time": dt_close,
                "size": trade.size,
                "entry_price": trade.price,
                "exit_price": exit_price,
                "gross_pnl": trade.pnl,
                "net_pnl": trade.pnlcomm,
                "commission": trade.commission,
            })
