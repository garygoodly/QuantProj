
# CLI to run backtests without touching core/library code
import argparse
from pathlib import Path
import pandas as pd

from quantlab.strategies import get_strategy_class
from quantlab.core.data import download_ohlcv, bt_feed_from_df
from quantlab.core.engine import run_backtest
from quantlab.core.analyzers import DEFAULT_ANALYZERS
from quantlab.utils.io import ensure_dir, save_cerebro_plot


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--strategy", default="ma_cross")
    p.add_argument("--symbol", default="AAPL")
    p.add_argument("--start", default="2021-01-01")
    p.add_argument("--end", default="2023-01-01")
    p.add_argument("--cash", type=float, default=100_000)
    p.add_argument("--commission", type=float, default=0.001)
    p.add_argument("--stake", type=int, default=100)
    p.add_argument("--ma_period", type=int, default=20)
    p.add_argument("--outdir", default="results")
    return p.parse_args()


def main():
    args = parse_args()
    ensure_dir(args.outdir)

    df = download_ohlcv(args.symbol, args.start, args.end)
    feed = bt_feed_from_df(df)

    strat_cls = get_strategy_class(args.strategy)
    strat_kwargs = {"ma_period": args.ma_period} if args.strategy == "ma_cross" else {}

    cerebro, strat = run_backtest(
        strategy_cls=strat_cls,
        data_feed=feed,
        initial_cash=args.cash,
        commission=args.commission,
        sizer_stake=args.stake,
        analyzers=DEFAULT_ANALYZERS,
        strategy_kwargs=strat_kwargs,
    )

    png_path = str(Path(args.outdir) / f"{args.strategy}_{args.symbol}.png")
    save_cerebro_plot(cerebro, png_path)

    trades = getattr(strat, "trades", [])
    if trades:
        pd.DataFrame(trades).to_csv(Path(args.outdir) /
                                    f"{args.strategy}_{args.symbol}_trades.csv",
                                    index=False)

    print("Done:", png_path)


if __name__ == "__main__":
    main()
