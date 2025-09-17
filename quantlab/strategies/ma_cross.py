
# -*- coding: utf-8 -*-
"""
MaCrossStrategy: Price-SMA crossover strategy using Backtrader.
"""
import backtrader as bt


class MaCrossStrategy(bt.Strategy):
    params = (
        ("ma_period", 20),
        ("export_fills", True),  # set True to export per-fill details
    )

    def __init__(self):
        # --- Indicators ---
        self.sma = bt.indicators.SimpleMovingAverage(
            self.data.close, period=self.p.ma_period
        )
        self.crossover = bt.ind.CrossOver(self.data.close, self.sma)

        # --- Per-position ledger (for scaling in/out) ---
        self._pos_size = 0.0           # current total size (>0 for long)
        self._avg_cost = 0.0           # VWAP of the open position
        self._realized_pnl = 0.0       # realized PnL from partial exits (pre-commission)
        self._comm_total = 0.0         # accumulated commissions for this position
        self._first_entry_time = None  # timestamp of the first entry of this position
        self._fills = []               # list of all fills for this position
        self._size_peak = 0.0          # max size reached during this position

        # --- Closed-trade summaries ---
        self.trades = []               # per-trade summary (one row per complete round trip)
        self.fills_log = []            # optional: all fills across all trades

    def next(self):
        # Simple SMA cross logic
        if not self.position and self.crossover[0] > 0:
            self.buy()
        elif self.position and self.crossover[0] < 0:
            self.sell()

    def notify_order(self, order):
        """Record each fill to support scaling and peak size."""
        if order.status != order.Completed:
            return

        dt = self.datas[0].datetime.datetime(0)
        fill_size = order.executed.size       # buy: +, sell: -
        fill_price = order.executed.price
        fill_comm = order.executed.comm or 0.0

        # Global fills log (across all trades), useful for exporting
        if self.p.export_fills:
            self.fills_log.append(
                {
                    "time": dt,
                    "side": "BUY" if order.isbuy() else "SELL",
                    "size": float(fill_size),
                    "price": float(fill_price),
                    "commission": float(fill_comm),
                }
            )

        # Commission accumulate for current position
        self._comm_total += fill_comm

        if order.isbuy():
            # If entering from flat, initialize per-position ledger
            if self._pos_size == 0:
                self._first_entry_time = dt
                self._realized_pnl = 0.0
                self._comm_total = fill_comm
                self._fills = []
                self._size_peak = 0.0

            # Track this fill inside current position scope
            self._fills.append(
                {"time": dt, "side": "BUY", "size": float(fill_size),
                 "price": float(fill_price), "commission": float(fill_comm)}
            )

            # Update VWAP average cost
            new_size = self._pos_size + abs(fill_size)
            if new_size > 0:
                self._avg_cost = (
                    (self._avg_cost * self._pos_size) + (fill_price * abs(fill_size))
                ) / new_size
            self._pos_size = new_size

            # Update peak size
            if self._pos_size > self._size_peak:
                self._size_peak = self._pos_size

        else:  # SELL
            sell_qty = abs(fill_size)
            # Cap to current size for safety
            sell_qty = min(sell_qty, self._pos_size)

            # Realize PnL for the sold portion (pre-commission)
            realized = (fill_price - self._avg_cost) * sell_qty
            self._realized_pnl += realized

            # Track this fill
            self._fills.append(
                {"time": dt, "side": "SELL", "size": float(-sell_qty),  # negative for clarity
                 "price": float(fill_price), "commission": float(fill_comm)}
            )

            # Reduce position size
            self._pos_size -= sell_qty
            # avg cost unchanged while position remains > 0

    def notify_trade(self, trade):
        """When the position fully closes, record the per-trade summary."""
        if not trade.isclosed:
            return

        dt_open = (
            self._first_entry_time
            if self._first_entry_time is not None
            else bt.num2date(trade.dtopen).replace(tzinfo=None)
        )
        dt_close = bt.num2date(trade.dtclose).replace(tzinfo=None)

        net_pnl = trade.pnlcomm if trade.pnlcomm is not None else trade.pnl

        self.trades.append(
            {
                "entry_time": dt_open,
                "exit_time": dt_close,
                "size_peak": float(self._size_peak),         # <-- now filled
                "avg_entry_cost": float(self._avg_cost),
                "gross_pnl": float(trade.pnl),
                "net_pnl": float(net_pnl),
                "commission": float(trade.commission),
                "fills_count": int(len(self._fills)),
            }
        )

        # Reset per-position ledger
        self._pos_size = 0.0
        self._avg_cost = 0.0
        self._realized_pnl = 0.0
        self._comm_total = 0.0
        self._first_entry_time = None
        self._fills = []
        self._size_peak = 0.0
