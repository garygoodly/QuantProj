import backtrader as bt
import yfinance as yf

# 定義策略
class MaCrossStrategy(bt.Strategy):
    def __init__(self):
        self.sma1 = bt.indicators.SimpleMovingAverage(self.data.close, period=20)
        self.sma2 = bt.indicators.SimpleMovingAverage(self.data.close, period=50)

    def next(self):
        if not self.position:  # 沒有持倉
            if self.sma1 > self.sma2:
                self.buy()
        elif self.sma1 < self.sma2:
            self.close()

# Cerebro 引擎
cerebro = bt.Cerebro()
cerebro.addstrategy(MaCrossStrategy)

# 下載資料
df = yf.download('AAPL', start='2021-01-01', end='2023-01-01')

# 確保欄位名稱正確
dataframe = df.rename(columns={
    'Open': 'open',
    'High': 'high',
    'Low': 'low',
    'Close': 'close',
    'Adj Close': 'adj_close',
    'Volume': 'volume'
})

# 在添加數據之前處理欄位名稱
if hasattr(dataframe.columns, 'levels'):  # 如果是 MultiIndex
    dataframe.columns = ['_'.join(map(str, col)).strip() for col in dataframe.columns.values]
else:
    dataframe.columns = [str(col) for col in dataframe.columns]

# 然後創建 data feed
data = bt.feeds.PandasData(
    dataname=dataframe,
    datetime=None,  # 如果 DataFrame 索引是日期時間
    open=0,         # 根據你的欄位順序調整
    high=1,
    low=2,
    close=3,
    volume=4,
    openinterest=-1
)

cerebro.adddata(data)

# 起始資金與手續費
cerebro.broker.setcash(100000)
cerebro.broker.setcommission(commission=0.001)

# 執行回測
cerebro.run()
cerebro.plot()