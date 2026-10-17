from functools import partial
from pathlib import Path

import pandas as pd

from src.models import baseline, ensemble, first_sale, typical_start
from src.models.evaluate import cross_validate, metrics, read_lots, set_display

TEST_QUARTERS = ["2026Q1", "2026Q2", "2026Q3"]
OUT_DIR = Path("data/final_test")


def regression_report(name: str, predict, lots: pd.DataFrame) -> pd.DataFrame:
    folds, predictions = cross_validate(predict, lots, TEST_QUARTERS)
    folds.loc["все лоты"] = pd.Series(metrics(predictions["sale_price"], predictions))
    predictions.to_parquet(OUT_DIR / f"{name}.parquet")
    print(name, "\n", folds, "\n", flush=True)
    return folds


def main() -> None:
    set_display()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    sold = read_lots(ensemble.LOTS_PATH)
    first = first_sale.read_first(until=None)
    starts = typical_start.target_lots(first)

    regression_report("model1_baseline", baseline.predict, sold)
    regression_report("model1_without_start", ensemble.predict, sold)
    regression_report("model1_with_start", partial(ensemble.predict, with_start=True), sold)
    regression_report("model2_baseline", baseline.predict, starts)
    regression_report("model2", typical_start.predict, starts)

    folds, predictions = first_sale.cross_validate(first, sold, TEST_QUARTERS)
    predictions.to_parquet(OUT_DIR / "model3.parquet")
    pd.set_option("display.float_format", "{:.4f}".format)
    print("model3\n", folds.to_string(index=False), "\n")
    pooled = pd.DataFrame({model: first_sale.metrics(predictions["sold_first"], predictions[model])
                           for model in ["base rate", "logistic", "catboost", "p_first"]}).T
    print("model3, все лоты\n", pooled, "\n")
    print("калибровка (p_first)\n", first_sale.calibration(predictions["sold_first"], predictions["p_first"]))


if __name__ == "__main__":
    main()
