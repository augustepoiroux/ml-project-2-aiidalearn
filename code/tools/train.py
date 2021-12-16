import os
import sys
from pathlib import Path

import numpy as np
from rich.console import Console
from rich.table import Table
from sklearn.metrics import (
    mean_absolute_error,
    mean_absolute_percentage_error,
    mean_squared_error,
    accuracy_score
)

ROOT_DIR = os.path.dirname(
    os.path.dirname(os.path.dirname(str(Path(__file__).absolute())))
)

sys.path.append(os.path.join(ROOT_DIR, "code"))
from tools.utils import custom_mape, percentile_absolute_percentage_error
from tools.transform import magnitude_transform



def train_models(models, X_train, y_train, console: Console):
    with console.status("") as status:
        for model_name, model in models.items():
            status.update(f"[bold blue]Training {model_name}...")
            model.fit(X_train, y_train)
            console.log(f"[blue]Finished training {model_name}[/blue]")


def evaluate_models(models, X_train, y_train, test_sets, console: Console):
    with console.status("") as status:
        for model_name, model in models.items():
            status.update(f"[bold blue]Evaluating {model_name}...")

            table = Table(title=model_name)
            table.add_column("Loss name", justify="center", style="cyan")
            table.add_column("Train", justify="center", style="green")
            for name, _, _ in test_sets:
                table.add_column(
                    f"Test - {name}", justify="center", style="green"
                )

            y_pred_train = model.predict(X_train)
            y_pred_tests = [
                model.predict(X_test) for _, X_test, _ in test_sets
            ]

            for loss_name, loss_fn in [
                ("MSE", mean_squared_error),
                ("MAE", mean_absolute_error),
                ("MAPE", mean_absolute_percentage_error),
                ("Custom MAPE", lambda a, b: custom_mape(a, b, True)),
                (
                    "50%-APE",
                    lambda a, b: percentile_absolute_percentage_error(
                        a, b, 50
                    ),
                ),
                (
                    "90%-APE",
                    lambda a, b: percentile_absolute_percentage_error(
                        a, b, 90
                    ),
                ),
            ]:
                train_loss = loss_fn(y_train, y_pred_train)
                test_losses = [
                    loss_fn(y_test, y_pred_test)
                    for (_, _, y_test), y_pred_test in zip(
                        test_sets, y_pred_tests
                    )
                ]
                table.add_row(
                    loss_name,
                    f"{train_loss:.4E}",
                    *[f"{test_loss:.4E}" for test_loss in test_losses],
                )

            console.print(table)

def train_classifiers(models, X_train, y_train, console: Console):
    with console.status("") as status:
        for model_name, model in models.items():
            status.update(f"[bold blue]Training {model_name}...")
            magnitude_y_train = magnitude_transform(y_train)
            model.fit(X_train, magnitude_y_train)
            console.log(f"[blue]Finished training {model_name}[/blue]")


def evaluate_classifiers(models, X_train, y_train, test_sets, console: Console):
    with console.status("") as status:
        for model_name, model in models.items():
            status.update(f"[bold blue]Evaluating {model_name}...")

            table = Table(title=model_name)
            table.add_column("Loss name", justify="center", style="cyan")
            table.add_column("Train", justify="center", style="green")
            for name, _, _ in test_sets:
                table.add_column(
                    f"Test - {name}", justify="center", style="green"
                )

            y_pred_train = model.predict(X_train)
            y_pred_tests = [
                model.predict(X_test) for _, X_test, _ in test_sets
            ]


            for loss_name, loss_fn in [
                ("Accuracy", accuracy_score),
            ]:
                train_loss = loss_fn(magnitude_transform(y_train), y_pred_train)
                test_losses = [
                    loss_fn(magnitude_transform(y_test), y_pred_test)
                    for (_, _, y_test), y_pred_test in zip(
                        test_sets, y_pred_tests
                    )
                ]

                if loss_name == "Accuracy":
                    table.add_row(
                        loss_name,
                        f"{100*train_loss:.2f}%",
                        *[f"{100*test_loss:.2f}%" for test_loss in test_losses],
                    )
                else:
                    table.add_row(
                        loss_name,
                        f"{train_loss:.4E}",
                        *[f"{test_loss:.4E}" for test_loss in test_losses],
                    )

            console.print(table)


def print_test_samples(models, test_sets, console: Console, n_sample=10):
    for test_name, X_test, y_test in test_sets:
        table = Table(title=f"Test samples - {test_name}")
        table.add_column("Real", justify="center", style="green")
        for model_name, _ in models.items():
            table.add_column(model_name, justify="center", style="yellow")

        idx_sample = np.random.choice(
            X_test.index, size=n_sample, replace=False
        )
        results = [
            np.array(y_test[y_test.index.intersection(idx_sample)].squeeze())
        ]
        for model_name, model in models.items():
            results.append(
                np.array(
                    model.predict(
                        X_test.loc[X_test.index.intersection(idx_sample)]
                    ).squeeze()
                )
            )

        for i in range(n_sample):
            table.add_row(*[f"{r[i]:.3E}" for r in results],)
        console.print(table)

def print_problematic_samples(models, test_sets, console: Console, elts, n_sample=10):
    for elt in elts:
        for test_name, X_test, y_test in test_sets:
            table = Table(title=f"Test samples - {test_name}")
            table.add_column("Real", justify="center", style="green")
            for model_name, _ in models.items():
                table.add_column(model_name, justify="center", style="yellow")

            elt_mask = X_test[elt].to_numpy().nonzero()[0]
            idx_sample = np.random.choice(
                X_test.iloc[elt_mask].index, size=n_sample, replace=False
            )
            results = [
                np.array(y_test[y_test.index.intersection(idx_sample)].squeeze())
            ]
            for model_name, model in models.items():
                results.append(
                    np.array(
                        model.predict(
                            X_test.loc[X_test.index.intersection(idx_sample)]
                        ).squeeze()
                    )
                )

            for i in range(n_sample):
                table.add_row(*[f"{r[i]:.3E}" for r in results],)
            console.print(table)
