# -*- coding: utf-8 -*-
"""
Backtest runner for MaCrossStrategy on AAPL using yfinance daily data.

Improvements:
- Uses column-name mapping for PandasData to avoid positional mistakes.
- Normalizes timezone to tz-naive.
- Adds a FixedSize sizer (stake=100) so capital is actually utilized.
- Adds analyzers (TradeAnalyzer, SharpeRatio_A, DrawDown).
- Saves Backtrader's figure correctly from the object returned by cerebro.plot(...).
- Exports closed trades (net PnL after commissions) and a summary report.

PEP 8 style and English comments as requested.
"""

import os
from datetime import datetime

import backtrader as bt
import matplotlib.pyplot as plt
import pandas as pd
import yfinance as yf

from strategy.ma_cross import MaCrossStrategy


def ensure_results_dir(path: str = "backtest_results") -> str:
    """Create results directory if it does not exist."""
    if not os.path.exists(path):
        os.makedirs(path)
    return path


def download_data(
    ticker: str = "AAPL",
    start: str = "2021-01-01",
    end: str = "2023-01-01",
) -> pd.DataFrame:
    """Download OHLCV data via yfinance and return a cleaned DataFrame."""
    df = yf.download(ticker, start=start, end=end, progress=False)

    # Normalize timezone to tz-naive to avoid potential issues in Backtrader
    if getattr(df.index, "tz", None) is not None:
        df.index = df.index.tz_localize(None)

    # If MultiIndex like ('Close','AAPL'), take the first level
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    # Lower-case all column names as strings
    df.columns = [str(c).lower() for c in df.columns]

    # Rename to lower snake case for clarity and robust PandasData mapping by name
    df = df.rename(
        columns={
            "open": "open",
            "high": "high",
            "low": "low",
            "close": "close",
            "adj close": "adj_close",
            "volume": "volume",
        }
    )

    # Ensure pure string column names
    df.columns = [str(c) for c in df.columns]
    return df


def add_analyzers(cerebro: bt.Cerebro) -> None:
    """Attach commonly used analyzers."""
    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name="ta")
    # Annualized Sharpe (use with care for daily data; assumes trading-year convention)
    cerebro.addanalyzer(bt.analyzers.SharpeRatio_A, riskfreerate=0.0, _name="sharpe")
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name="dd")


def save_plot(cerebro: bt.Cerebro, outpath: str) -> None:
    """
    Save the Backtrader-generated figure properly.
    cerebro.plot(...) returns nested list(s) of figures.
    """
    figs = cerebro.plot(style="candle", volume=True, iplot=False)
    # Handle nested return ([[fig,...], ...]) safely:
    fig0 = figs[0][0] if isinstance(figs[0], (list, tuple)) else figs[0]
    fig0.savefig(outpath, dpi=300, bbox_inches="tight")
    plt.close(fig0)


def main():
    # --- Configs ---
    symbol = "AAPL"
    start_date = "2021-01-01"
    end_date = "2023-01-01"
    initial_cash = 100_000.0
    commission_rate = 0.001  # 10 bps per trade side (example)
    ma_period = 20
    stake = 100  # shares per trade

    # --- Prepare output dir ---
    results_dir = ensure_results_dir("backtest_results")

    # --- Download and prepare data ---
    data_df = download_data(symbol, start=start_date, end=end_date)

    # --- Build Backtrader feed using column names (safer than positional) ---
    data_feed = bt.feeds.PandasData(
        dataname=data_df,
        datetime=None,        # index is already datetime
        open="open",
        high="high",
        low="low",
        close="close",
        volume="volume",
        openinterest=None,    # no open interest field
    )

    # --- Cerebro engine ---
    cerebro = bt.Cerebro()
    cerebro.addstrategy(MaCrossStrategy, ma_period=ma_period)
    cerebro.adddata(data_feed)

    # --- Broker settings ---
    cerebro.broker.setcash(initial_cash)
    cerebro.broker.setcommission(commission=commission_rate)

    # --- Sizer to actually utilize capital ---
    cerebro.addsizer(bt.sizers.FixedSize, stake=stake)

    # --- Analyzers ---
    add_analyzers(cerebro)

    # --- Run backtest ---
    strat = cerebro.run()[0]

    # --- Save plot correctly from Backtrader ---
    chart_path = os.path.join(results_dir, "backtest_chart.png")
    save_plot(cerebro, chart_path)

    # --- Extract results ---
    final_value = cerebro.broker.getvalue()
    net_pl = final_value - initial_cash
    ret_pct = (final_value / initial_cash - 1.0) * 100.0

    # Closed trades (recorded via notify_trade in strategy)
    trades_df = pd.DataFrame(strat.trades)

    # Analyzers
    ta = strat.analyzers.ta.get_analysis()
    sharpe = strat.analyzers.sharpe.get_analysis()
    dd = strat.analyzers.dd.get_analysis()

    # Derive trade stats safely
    total_trades = 0
    wins = 0
    losses = 0
    win_rate = None

    if "total" in ta and "closed" in ta["total"]:
        total_trades = ta["total"]["closed"]

    if "won" in ta and "total" in ta["won"]:
        wins = ta["won"]["total"]

    if "lost" in ta and "total" in ta["lost"]:
        losses = ta["lost"]["total"]

    if total_trades > 0:
        win_rate = wins / total_trades * 100.0

    # Sharpe (annualized)
    sharpe_a = sharpe.get("sharperatio", None)

    # Drawdown
    max_drawdown = dd.get("max", {}).get("drawdown", None)
    max_dd_len = dd.get("max", {}).get("len", None)

    # --- Save CSV of trades ---
    trades_csv = os.path.join(results_dir, "trade_history.csv")
    if not trades_df.empty:
        trades_df.to_csv(trades_csv, index=False)

    # --- Save summary to text file ---
    summary_path = os.path.join(results_dir, "summary.txt")
    with open(summary_path, "w", encoding="utf-8") as f:
        f.write("=== Backtest Results Summary ===\n")
        f.write(f"Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Symbol: {symbol}\n")
        f.write(f"Period: {start_date} to {end_date}\n")
        f.write(f"Strategy: Price-SMA Cross (SMA period = {ma_period})\n")
        f.write("\n--- Portfolio ---\n")
        f.write(f"Initial Cash: ${initial_cash:,.2f}\n")
        f.write(f"Final Value: ${final_value:,.2f}\n")
        f.write(f"Net P/L: ${net_pl:,.2f}\n")
        f.write(f"Return: {ret_pct:.2f}%\n")
        f.write("\n--- Trades ---\n")
        f.write(f"Total Closed Trades: {total_trades}\n")
        f.write(f"Wins: {wins}\n")
        f.write(f"Losses: {losses}\n")
        if win_rate is not None:
            f.write(f"Win Rate: {win_rate:.2f}%\n")
        else:
            f.write("Win Rate: N/A (no closed trades)\n")
        f.write("\n--- Risk/Quality ---\n")
        f.write(f"Sharpe (annualized): {sharpe_a}\n")
        f.write(f"Max Drawdown (%): {max_drawdown}\n")
        f.write(f"Max Drawdown Length (bars): {max_dd_len}\n")
        f.write("\n--- Files ---\n")
        f.write(f"- Chart: {chart_path}\n")
        if not trades_df.empty:
            f.write(f"- Trades CSV: {trades_csv}\n")
        f.write(f"- Summary: {summary_path}\n")

    # --- Print to console ---
    print("\n=== Backtest Results ===")
    print(f"Final Portfolio Value: ${final_value:,.2f}")
    print(f"Initial Capital: ${initial_cash:,.2f}")
    print(f"Net Profit/Loss: ${net_pl:,.2f}")
    print(f"Return: {ret_pct:.2f}%")
    print(f"Total Closed Trades: {total_trades}")
    print(f"Wins: {wins} | Losses: {losses}")
    if win_rate is not None:
        print(f"Win Rate: {win_rate:.2f}%")
    else:
        print("Win Rate: N/A (no closed trades)")
    print(f"Sharpe (annualized): {sharpe_a}")
    print(f"Max Drawdown (%): {max_drawdown} | Length (bars): {max_dd_len}")

    if not trades_df.empty:
        print("\n=== Trade History (first 5) ===")
        print(trades_df.head())

    print("\nBacktest completed successfully!")
    print("Results saved in 'backtest_results/' folder:")
    print("- backtest_chart.png (chart plot)")
    print("- trade_history.csv (detailed trades, if any)")
    print("- summary.txt (performance summary)")


if __name__ == "__main__":
    main()
