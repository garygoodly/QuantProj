# -*- coding: utf-8 -*-
"""
MaCrossStrategy: Price-SMA crossover strategy using Backtrader.

- Buy when close crosses above SMA(period).
- Sell when close crosses below SMA(period).
- Record closed trades via notify_trade to capture net PnL after commissions.
"""

import backtrader as bt


class MaCrossStrategy(bt.Strategy):
    params = (
        ("ma_period", 20),  # SMA lookback period
    )

    def __init__(self):
        # --- Indicators ---
        # Simple Moving Average on close
        self.sma = bt.indicators.SimpleMovingAverage(
            self.data.close, period=self.p.ma_period
        )
        # CrossOver indicator: >0 up-cross, <0 down-cross, 0 no cross
        self.crossover = bt.ind.CrossOver(self.data.close, self.sma)

        # --- Storage for closed trades ---
        # We record closed trades in notify_trade to ensure PnL includes commissions
        self.trades = []

    def next(self):
        """Strategy logic executed on each bar."""
        # Enter long on upward cross
        if not self.position and self.crossover[0] > 0:
            self.buy()

        # Exit long on downward cross
        elif self.position and self.crossover[0] < 0:
            self.sell()

    def notify_trade(self, trade):
        """Called by Backtrader when a trade is updated. We record results when closed."""
        if trade.isclosed:
            # Convert bt numeric datetimes to Python datetime (tz-naive)
            dt_open = bt.num2date(trade.dtopen).replace(tzinfo=None)
            dt_close = bt.num2date(trade.dtclose).replace(tzinfo=None)

            # Derive implied exit price if size != 0 (for documentation)
            exit_price = (
                trade.price + (trade.pnl / abs(trade.size))
                if trade.size != 0
                else None
            )

            self.trades.append(
                {
                    "entry_time": dt_open,
                    "exit_time": dt_close,
                    "size": trade.size,
                    "entry_price": trade.price,     # average entry price
                    "exit_price": exit_price,       # implied average exit price
                    "gross_pnl": trade.pnl,         # before commissions
                    "net_pnl": trade.pnlcomm,       # after commissions
                    "commission": trade.commission, # total commissions
                }
            )

    # Optional: monitor orders for debugging (kept minimal and safe)
    def notify_order(self, order):
        """Keep this minimal; we rely on notify_trade for PnL.
        Useful hooks for debugging order states.
        """
        if order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log(
                f"Order {order.ref} not completed: status={order.getstatusname()}"
            )

    def log(self, txt):
        """Simple logger for debugging."""
        dt = self.datas[0].datetime.datetime(0)
        print(f"[{dt}] {txt}")
