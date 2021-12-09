import os
import pickle
import sys

from pathlib import Path
import numpy as np
import pandas as pd
import xgboost as xgb
from rich.console import Console
from rich.table import Table
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.metrics import (
    mean_absolute_error,
    mean_absolute_percentage_error,
    mean_squared_error,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import PolynomialFeatures, StandardScaler

sys.path.append(str(Path(__file__).parent.parent.absolute()))
from tools.utils import (
    Encoding,
    custom_mape,
    encode_all_structures,
)

# Set Up
DATA_DIR = os.path.join(
    str(Path(__file__).parent.parent.parent.absolute()), "data/"
)

MODELS_DIR = os.path.join(
    str(Path(__file__).parent.parent.parent.absolute()), "models/delta_E/"
)

encoding = Encoding.COLUMN_MASS

console = Console()

# Loading Data
with console.status("") as status:
    status.update("[bold blue]Loading data...")
    df = pd.read_csv(
        os.path.join(DATA_DIR, "data.csv"), index_col=0, na_filter=False
    )

    status.update(f"[bold blue]Encoding structures ({encoding})...")
    df = encode_all_structures(df, encoding)

    status.update(f"[bold blue]Splitting data...")
    cols_raw = list(df.columns)
    cols_trash = [
        "structure",
        "converged",
        "n_iterations",
        "delta_E",
        "fermi",
        "total_energy",
    ]
    cols_independent = ["time"]
    cols_drop = cols_trash + cols_independent

    cols_dependent = cols_raw.copy()
    for element in cols_drop:
        cols_dependent.remove(element)

    X_raw = df[cols_dependent][df["converged"]]
    y_raw = np.abs(df[cols_independent][df["converged"]]).squeeze()

    # Train-test-split
    X_train, X_test, y_train, y_test = train_test_split(
        X_raw, y_raw, test_size=0.2, random_state=42
    )
console.log("Data loaded")

# Model definition
linear_augmented_model = Pipeline(
    [
        ("scaler_init", StandardScaler()),
        ("poly_features", PolynomialFeatures(degree=2)),
        ("scaler_final", StandardScaler()),
        ("regressor", LinearRegression()),
    ]
)

rf_model = RandomForestRegressor(random_state=0)

gb_model = GradientBoostingRegressor(
    n_estimators=5000, learning_rate=0.05, random_state=0
)

xgb_model = xgb.XGBRegressor(
    n_estimators=5000, learning_rate=0.05, random_state=0
)

# detect if gpu is usable with xgboost by training on toy data
try:
    xgb_model.set_params(tree_method="gpu_hist")
    xgb_model.fit(np.array([[1, 2, 3]]), np.array([[1]]))
    console.print("[italic bright_black]Using GPU for XGBoost")
except:
    xgb_model.set_params(tree_method="hist")
    console.print("[italic bright_black]Using CPU for XGBoost")

models = {
    "Augmented Linear Regression": linear_augmented_model,
    "Random Forest": rf_model,
    # "Gradient Boosting": gb_model,
    "XGBoost": xgb_model,
}

# Model training
with console.status("") as status:
    for model_name, model in models.items():
        status.update(f"[bold blue]Training {model_name}...")
        model.fit(X_train, y_train)
        console.log(f"[blue]Finished training {model_name}[/blue]")


# Model evaluation
with console.status("") as status:
    for model_name, model in models.items():
        status.update(f"[bold blue]Evaluating {model_name}...")

        table = Table(title=model_name)
        table.add_column("Loss name", justify="center", style="cyan")
        table.add_column("Train", justify="center", style="green")
        table.add_column("Test", justify="center", style="green")

        y_pred_train = model.predict(X_train)
        y_pred_test = model.predict(X_test)

        for loss_name, loss_fn in [
            ("MSE", mean_squared_error),
            ("MAE", mean_absolute_error),
            ("MAPE", mean_absolute_percentage_error),
            # ("Custom MAPE", custom_mape),
        ]:
            train_loss = loss_fn(y_train, y_pred_train)
            test_loss = loss_fn(y_test, y_pred_test)
            table.add_row(loss_name, f"{train_loss:.4E}", f"{test_loss:.4E}")

        console.print(table)

if input("Save models? (y/[n]) ") == "y":
    save_models = {
        "Random Forest": rf_model,
        "Gradient Boosting": gb_model,
        "XGBoost": xgb_model,
    }

    models_filenames = [
        "random_forest_model.pkl",
        "gb_model.pkl",
        "xgb_model.pkl",
    ]

    with console.status("[bold green] Saving models...") as status:
        for filename, (model_name, model) in zip(
            models_filenames, save_models.items()
        ):
            modelpath = MODELS_DIR + filename
            with open(modelpath, "wb") as file:
                pickle.dump(model, file)
            console.log(f"[green]Saved {model_name} to {modelpath}[/green]")
