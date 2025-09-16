
# quant-backtest

Modular Backtrader project for experimenting with multiple strategies safely.

## Quick Start

```bash
python -m venv .venv && source .venv/bin/activate  # (Windows: .venv\Scripts\activate)
pip install -r requirements.txt
python scripts/run_backtest.py --strategy ma_cross --symbol AAPL --start 2021-01-01 --end 2023-01-01
```

Results (plot and CSV) will be saved under `results/`.
