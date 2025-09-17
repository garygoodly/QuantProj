# CLI to run backtests without touching core/library code
import argparse
from pathlib import Path
from datetime import datetime
import pandas as pd

from quantlab.strategies import get_strategy_class
from quantlab.core.data import download_ohlcv, bt_feed_from_df
from quantlab.core.engine import run_backtest
from quantlab.core.analyzers import DEFAULT_ANALYZERS
from quantlab.utils.io import ensure_dir, save_cerebro_plot


def parse_args():
    """Parse command-line arguments."""
    p = argparse.ArgumentParser()
    p.add_argument("--strategy", default="ma_cross",
                   help="Strategy name registered in quantlab.strategies")
    p.add_argument("--symbol", default="AAPL", help="Ticker symbol")
    p.add_argument("--start", default="2021-01-01", help="Backtest start date (YYYY-MM-DD)")
    p.add_argument("--end", default="2023-01-01", help="Backtest end date (YYYY-MM-DD)")
    p.add_argument("--cash", type=float, default=100_000, help="Initial cash")
    p.add_argument("--commission", type=float, default=0.001,
                   help="Commission per side as a fraction (e.g., 0.001 = 10 bps)")
    p.add_argument("--stake", type=int, default=100, help="Number of shares per trade")
    p.add_argument("--ma_period", type=int, default=20, help="SMA period for ma_cross")
    p.add_argument("--export-fills", action="store_true", default=True,
                   help="Export per-fill executions if strategy supports it")
    p.add_argument("--no-export-fills", dest="export_fills", action="store_false",
                   help="Disable per-fill export")
    p.add_argument("--outdir", default="results", help="Output directory")
    return p.parse_args()


def main():
    args = parse_args()
    outdir = Path(args.outdir)
    ensure_dir(str(outdir))

    # --- Load data ---
    df = download_ohlcv(args.symbol, args.start, args.end)
    feed = bt_feed_from_df(df)

    # --- Strategy class & kwargs ---
    strat_cls = get_strategy_class(args.strategy)
    strat_kwargs = {}
    if args.strategy == "ma_cross":
        # Pass in both ma_period and export_fills if the strategy supports them
        strat_kwargs = {
            "ma_period": args.ma_period,
            "export_fills": args.export_fills,
        }

    # --- Run backtest ---
    cerebro, strat = run_backtest(
        strategy_cls=strat_cls,
        data_feed=feed,
        initial_cash=args.cash,
        commission=args.commission,
        sizer_stake=args.stake,
        analyzers=DEFAULT_ANALYZERS,
        strategy_kwargs=strat_kwargs,
    )

    # --- Save plot ---
    png_path = outdir / f"{args.strategy}_{args.symbol}.png"
    save_cerebro_plot(cerebro, str(png_path))

    # --- Export trades (per-trade summaries) ---
    trades = getattr(strat, "trades", [])
    trades_csv_path = None
    if trades:
        trades_df = pd.DataFrame(trades)

        # Round numeric columns for readability if present
        round_2 = ["size_peak", "avg_entry_cost", "gross_pnl", "net_pnl", "commission"]
        for col in round_2:
            if col in trades_df.columns:
                trades_df[col] = trades_df[col].astype(float).round(2)

        trades_csv_path = outdir / f"{args.strategy}_{args.symbol}_trades.csv"
        trades_df.to_csv(trades_csv_path, index=False)

    # --- Optional: export per-fill executions (scaling in/out details) ---
    fills = getattr(strat, "fills_log", [])
    fills_csv_path = None
    if args.export_fills and fills:
        fills_df = pd.DataFrame(fills)
        for col in ["size", "price", "commission"]:
            if col in fills_df.columns:
                fills_df[col] = fills_df[col].astype(float).round(4)
        fills_csv_path = outdir / f"{args.strategy}_{args.symbol}_fills.csv"
        fills_df.to_csv(fills_csv_path, index=False)

    # --- Collect summary stats ---
    final_value = cerebro.broker.getvalue()
    net_pl = final_value - args.cash
    ret_pct = (final_value / args.cash - 1.0) * 100.0

    ta = strat.analyzers.ta.get_analysis()
    sharpe = strat.analyzers.sharpe.get_analysis()
    dd = strat.analyzers.dd.get_analysis()

    total_trades = ta.get("total", {}).get("closed", 0)
    wins = ta.get("won", {}).get("total", 0)
    losses = ta.get("lost", {}).get("total", 0)
    win_rate = wins / total_trades * 100 if total_trades > 0 else None
    sharpe_a = sharpe.get("sharperatio", None)
    max_drawdown = dd.get("max", {}).get("drawdown", None)
    max_dd_len = dd.get("max", {}).get("len", None)

    # --- Print summary to console ---
    print("\n=== Backtest Results ===")
    print(f"Strategy: {args.strategy} | Symbol: {args.symbol}")
    print(f"Period: {args.start} → {args.end}")
    print(f"Final Portfolio Value: ${final_value:,.2f}")
    print(f"Initial Capital:       ${args.cash:,.2f}")
    print(f"Net Profit/Loss:       ${net_pl:,.2f}")
    print(f"Return:                {ret_pct:.2f}%")
    print(f"Total Closed Trades:   {total_trades}")
    print(f"Wins: {wins} | Losses: {losses}")
    print(f"Win Rate:              {win_rate:.2f}%"
          if win_rate is not None else "Win Rate: N/A")
    print(f"Sharpe (annualized):   {sharpe_a}")
    print(f"Max Drawdown (%):      {max_drawdown} | Length (bars): {max_dd_len}")
    print(f"Plot saved to:         {png_path}")
    if trades_csv_path:
        print(f"Trades CSV:            {trades_csv_path}")
    if fills_csv_path:
        print(f"Fills  CSV:            {fills_csv_path}")

    # --- Save summary to file ---
    summary_file = outdir / f"{args.strategy}_{args.symbol}_summary.txt"
    with open(summary_file, "w", encoding="utf-8") as f:
        f.write("=== Backtest Results Summary ===\n")
        f.write(f"Generated at: {datetime.now():%Y-%m-%d %H:%M:%S}\n")
        f.write(f"Strategy: {args.strategy}\n")
        f.write(f"Symbol: {args.symbol}\n")
        f.write(f"Period: {args.start} to {args.end}\n")
        f.write("\n--- Portfolio ---\n")
        f.write(f"Initial Cash: ${args.cash:,.2f}\n")
        f.write(f"Final Value:  ${final_value:,.2f}\n")
        f.write(f"Net P/L:      ${net_pl:,.2f}\n")
        f.write(f"Return:       {ret_pct:.2f}%\n")
        f.write("\n--- Trades ---\n")
        f.write(f"Total Closed Trades: {total_trades}\n")
        f.write(f"Wins: {wins}\n")
        f.write(f"Losses: {losses}\n")
        f.write(f"Win Rate: {win_rate:.2f}%\n" if win_rate is not None else "Win Rate: N/A\n")
        f.write("\n--- Risk Metrics ---\n")
        f.write(f"Sharpe (annualized): {sharpe_a}\n")
        f.write(f"Max Drawdown (%): {max_drawdown}\n")
        f.write(f"Max Drawdown Length (bars): {max_dd_len}\n")
        f.write("\n--- Files ---\n")
        f.write(f"- Plot:       {png_path}\n")
        if trades_csv_path:
            f.write(f"- Trades CSV: {trades_csv_path}\n")
        if fills_csv_path:
            f.write(f"- Fills CSV:  {fills_csv_path}\n")

    print(f"\nSummary saved to {summary_file}")


if __name__ == "__main__":
    main()
