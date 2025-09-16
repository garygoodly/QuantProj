
from .ma_cross import MaCrossStrategy

STRATEGY_REGISTRY = {
    "ma_cross": MaCrossStrategy,
}


def get_strategy_class(name: str):
    try:
        return STRATEGY_REGISTRY[name]
    except KeyError:
        raise ValueError(f"Unknown strategy: {name}. Available: {list(STRATEGY_REGISTRY.keys())}")
