
from __future__ import annotations
from pathlib import Path
import matplotlib.pyplot as plt


def ensure_dir(path: str):
    Path(path).mkdir(parents=True, exist_ok=True)


def save_cerebro_plot(cerebro, out_png: str):
    figs = cerebro.plot(style="candle", volume=True, iplot=False)
    fig0 = figs[0][0] if isinstance(figs[0], (list, tuple)) else figs[0]
    fig0.savefig(out_png, dpi=300, bbox_inches="tight")
    plt.close(fig0)
