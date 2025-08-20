import backtrader as bt
class MaCrossStrategy(bt.Strategy):
    params = (
        ('fast_period', 20),
        ('slow_period', 50),
    )
    
    def __init__(self):
        self.sma1 = bt.indicators.SimpleMovingAverage(
            self.data.close, period=self.params.fast_period)
        self.sma2 = bt.indicators.SimpleMovingAverage(
            self.data.close, period=self.params.slow_period)
        
        self.order = None
        self.trade_count = 0
        self.win_count = 0
        self.loss_count = 0
        self.total_profit = 0
        self.entry_dates = []
        self.exit_dates = []
        self.trade_results = []

    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            return
        
        if order.status in [order.Completed]:
            if order.isbuy():
                self.entry_price = order.executed.price
                self.entry_date = self.data.datetime.date(0)
                self.entry_dates.append(self.entry_date)
            else:
                exit_price = order.executed.price
                exit_date = self.data.datetime.date(0)
                self.exit_dates.append(exit_date)
                
                # Calculate trade results
                profit_pct = (exit_price / self.entry_price - 1) * 100
                profit_abs = (exit_price - self.entry_price) * order.executed.size
                self.total_profit += profit_abs
                
                self.trade_results.append({
                    'entry_date': self.entry_date,
                    'exit_date': exit_date,
                    'entry_price': self.entry_price,
                    'exit_price': exit_price,
                    'profit_pct': profit_pct,
                    'profit_abs': profit_abs,
                    'hold_days': (exit_date - self.entry_date).days
                })
                
                if profit_abs > 0:
                    self.win_count += 1
                else:
                    self.loss_count += 1
                
                self.trade_count += 1
        
        self.order = None

    def next(self):
        if self.order:
            return
            
        if not self.position:
            if self.sma1[0] > self.sma2[0]:
                self.order = self.buy()
        else:
            if self.sma1[0] < self.sma2[0]:
                self.order = self.sell()