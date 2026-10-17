from datetime import datetime
from pathlib import Path

import joblib
import pandas as pd

from src.models import comparables, ensemble, explain, first_sale, typical_start
from src.models.evaluate import read_lots

MODELS_DIR = Path("models")
BUNDLE_PATH = MODELS_DIR / "bundle.joblib"
HISTORY_PATH = MODELS_DIR / "history.parquet"
HISTORY_COLUMNS = comparables.COLUMNS + ["winnerTime", "auctionTimeBegin", "salesContractTime"]


def main() -> None:
    sold = read_lots(ensemble.LOTS_PATH)
    first = first_sale.read_first(until=None)
    print(f"проданных лотов {len(sold)}, первых торгов {len(first)}", flush=True)
    market = ensemble.fit(sold)
    print("модель 1 без старта", flush=True)
    market_start = ensemble.fit(sold, with_start=True)
    print("модель 1 со стартом", flush=True)
    typical = ensemble.fit(typical_start.target_lots(first), width_k=typical_start.WIDTH_K)
    print("модель 2", flush=True)
    first_models = first_sale.fit(first_sale.oof_market_ratio(first, sold))
    print("модель 3", flush=True)
    bundle = {
        "trained_at": datetime.now().isoformat(timespec="seconds"),
        "data_until": str(sold["requestTimeBegin"].max().date()),
        "market": market,
        "market_start": market_start,
        "typical": typical,
        "first_sale": first_models,
        "factor_base": explain.contributions(market["linear"][1], sold).mean(),
    }
    MODELS_DIR.mkdir(exist_ok=True)
    joblib.dump(bundle, BUNDLE_PATH, compress=3)
    sold[HISTORY_COLUMNS].to_parquet(HISTORY_PATH, index=False)
    print(f"сохранено: {BUNDLE_PATH} ({BUNDLE_PATH.stat().st_size / 1e6:.1f} МБ), {HISTORY_PATH}")


if __name__ == "__main__":
    main()
