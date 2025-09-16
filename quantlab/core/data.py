
from __future__ import annotations
import pandas as pd
import yfinance as yf
import backtrader as bt


def download_ohlcv(symbol: str, start: str, end: str) -> pd.DataFrame:
    df = yf.download(symbol, start=start, end=end, progress=False)
    if getattr(df.index, "tz", None) is not None:
        df.index = df.index.tz_localize(None)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df.columns = [str(c).lower() for c in df.columns]
    df = df.rename(columns={"adj close": "adj_close"})
    return df


def bt_feed_from_df(df: pd.DataFrame) -> bt.feeds.PandasData:
    return bt.feeds.PandasData(
        dataname=df,
        datetime=None,
        open="open",
        high="high",
        low="low",
        close="close",
        volume="volume",
        openinterest=None,
    )
