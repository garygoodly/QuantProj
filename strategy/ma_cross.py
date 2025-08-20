import backtrader as bt
class MaCrossStrategy(bt.Strategy):
    params = (
        ('ma_period', 20),
    )
    
    def __init__(self):
        # Initialize moving average
        self.sma = bt.indicators.SimpleMovingAverage(
            self.data.close, period=self.params.ma_period
        )
        
        # Initialize trade statistics variables
        self.trade_count = 0
        self.win_count = 0
        self.loss_count = 0
        self.total_profit = 0.0
        self.trade_results = []  # Store each trade details
        
        # Track current trade
        self.current_trade = None
        self.entry_price = 0.0
        self.entry_time = None

    def next(self):
        # If no position and close price crosses above moving average
        if not self.position and self.data.close[0] > self.sma[0]:
            # Buy
            self.buy()
            
        # If has position and close price crosses below moving average
        elif self.position and self.data.close[0] < self.sma[0]:
            # Sell
            self.sell()

    def notify_order(self, order):
        if order.status in [order.Completed]:
            if order.isbuy():
                # Record buy information
                self.entry_price = order.executed.price
                self.entry_time = self.datas[0].datetime.datetime()
                self.current_trade = {
                    'entry_time': self.entry_time,
                    'entry_price': self.entry_price,
                    'size': order.executed.size
                }
            else:  # Sell
                if self.current_trade:
                    # Calculate trade result
                    exit_price = order.executed.price
                    profit = (exit_price - self.entry_price) * order.executed.size
                    
                    self.current_trade.update({
                        'exit_time': self.datas[0].datetime.datetime(),
                        'exit_price': exit_price,
                        'profit': profit,
                        'status': 'win' if profit > 0 else 'loss'
                    })
                    
                    # Update statistics
                    self.trade_count += 1
                    self.total_profit += profit
                    
                    if profit > 0:
                        self.win_count += 1
                    else:
                        self.loss_count += 1
                    
                    # Save trade record
                    self.trade_results.append(self.current_trade)
                    self.current_trade = None
