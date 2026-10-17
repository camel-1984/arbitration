import numpy as np
import pandas as pd

from src.models import ensemble
from src.models.evaluate import cross_validate, set_display
from src.models.first_sale import read_first

WIDTH_K = 1.07


def target_lots(first: pd.DataFrame) -> pd.DataFrame:
    return first.assign(sale_price=first["first_price"], log_price=np.log(first["first_price"]))


def predict(train: pd.DataFrame, valid: pd.DataFrame) -> pd.DataFrame:
    return ensemble.predict(train, valid, width_k=WIDTH_K)


def main() -> None:
    lots = target_lots(read_first())
    set_display()
    folds, _ = cross_validate(predict, lots)
    print(folds)


if __name__ == "__main__":
    main()
