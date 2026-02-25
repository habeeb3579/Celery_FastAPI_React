#!/usr/bin/env python3
"""
run_experiment.py — Full stack experiment runner.

Tests the complete pipeline:
  Your script → FastAPI → Celery → Redis → Worker → Results

Usage:
  # Single experiment
  python run_experiment.py

  # Custom dataset and model
  python run_experiment.py --dataset wine --model gradient_boosting

  # Run all combinations
  python run_experiment.py --all

  # Compare multiple models on same dataset
  python run_experiment.py --compare --dataset breast_cancer

Requirements:
  pip install httpx rich typer
  (API + Celery workers must be running)
"""

import time
import json
import typer
import httpx
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.panel import Panel
from rich import print as rprint

# ── Config ─────────────────────────────────────────────────────────────────────

API_BASE      = "http://localhost:8090"
POLL_INTERVAL = 2      # seconds between status polls
POLL_TIMEOUT  = 300    # max seconds to wait for training

DATASETS = ["iris", "wine", "breast_cancer", "digits"]
MODELS   = ["random_forest", "gradient_boosting", "logistic_regression", "svm"]

console = Console()
app     = typer.Typer(help="ML Experiment Runner — tests the full Celery stack")


# ══════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════

def _check_api_health(client: httpx.Client):
    """Fail fast if the API isn't running."""
    try:
        res = client.get(f"{API_BASE}/health")
        res.raise_for_status()
    except Exception:
        rprint("\n[bold red]✗ API is not running.[/bold red]")
        rprint("  Start it with: [cyan]uvicorn api.routes:app --reload[/cyan]\n")
        raise typer.Exit(1)


def _submit_training(client: httpx.Client, dataset: str, model: str, **kwargs) -> str:
    """Submit a training job, return job_id."""
    payload = {
        "dataset":    dataset,
        "model_type": model,
        "test_size":  kwargs.get("test_size", 0.2),
        "cv_folds":   kwargs.get("cv_folds", 5),
        "scale":      kwargs.get("scale", True),
    }
    res = client.post(f"{API_BASE}/train", json=payload)
    res.raise_for_status()
    data = res.json()
    return data["job_id"]


def _poll_until_done(client: httpx.Client, job_id: str) -> dict:
    """
    Poll /train/{job_id}/status until SUCCESS or FAILURE.
    Returns the final status dict.
    """
    deadline = time.time() + POLL_TIMEOUT

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("{task.fields[info]}"),
        console=console,
    ) as progress:
        task = progress.add_task("Training...", total=100, info="waiting")

        while time.time() < deadline:
            res    = client.get(f"{API_BASE}/train/{job_id}/status")
            status = res.json()
            state  = status.get("state")

            if state == "running":
                pct   = status.get("progress", 0)
                stage = status.get("stage", "")
                epoch = status.get("epoch", "")
                info  = f"{stage}" + (f" | epoch {epoch}" if epoch else "")
                progress.update(task, completed=pct, info=info)

            elif state == "success":
                progress.update(task, completed=100, info="done ✓")
                return status

            elif state == "failed":
                progress.stop()
                rprint(f"\n[bold red]✗ Training failed:[/bold red] {status.get('error')}")
                raise typer.Exit(1)

            time.sleep(POLL_INTERVAL)

    rprint("\n[bold red]✗ Timed out waiting for training.[/bold red]")
    raise typer.Exit(1)


def _run_prediction(client: httpx.Client, model_id: str, dataset: str) -> dict:
    """Run a sample prediction against the trained model."""
    # Sample inputs per dataset
    sample_inputs = {
        "iris":          {"features": [5.1, 3.5, 1.4, 0.2]},
        "wine":          {"features": [13.2, 1.78, 2.14, 11.2, 100.0, 2.65, 2.76, 0.26, 1.28, 4.38, 1.05, 3.4, 1050.0]},
        "breast_cancer": {"features": [17.99, 10.38, 122.8, 1001.0, 0.1184, 0.2776, 0.3001, 0.1471, 0.2419, 0.07871,
                                        1.095, 0.9053, 8.589, 153.4, 0.006399, 0.04904, 0.05373, 0.01587, 0.03003,
                                        0.006193, 25.38, 17.33, 184.6, 2019.0, 0.1622, 0.6656, 0.7119, 0.2654, 0.4601, 0.1189]},
        "digits":        {"features": [0.0] * 64},
    }

    input_data = sample_inputs.get(dataset, {"features": [0.5] * 4})
    res        = client.post(f"{API_BASE}/predict/{model_id}", json={"input_data": input_data})
    res.raise_for_status()
    return res.json()


def _run_explain(client: httpx.Client, model_id: str, dataset: str) -> dict:
    """Run an explanation against the trained model."""
    sample_inputs = {
        "iris":          {"features": [5.1, 3.5, 1.4, 0.2]},
        "wine":          {"features": [13.2, 1.78, 2.14, 11.2, 100.0, 2.65, 2.76, 0.26, 1.28, 4.38, 1.05, 3.4, 1050.0]},
        "breast_cancer": {"features": [17.99] * 30},
        "digits":        {"features": [0.0] * 64},
    }

    input_data = sample_inputs.get(dataset, {"features": [0.5] * 4})
    res        = client.post(f"{API_BASE}/predict/{model_id}/explain", json={"input_data": input_data})
    res.raise_for_status()
    return res.json()


def _print_metrics(metrics: dict, dataset: str, model: str, job_id: str):
    """Pretty print experiment results."""
    console.print(Panel(
        f"[bold cyan]Dataset:[/bold cyan]  {dataset}\n"
        f"[bold cyan]Model:[/bold cyan]    {model}\n"
        f"[bold cyan]Job ID:[/bold cyan]   {job_id}",
        title="Experiment",
        border_style="cyan",
    ))

    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Metric",    style="dim")
    table.add_column("Value",     justify="right")

    table.add_row("Test Accuracy",  f"[green]{metrics['test_accuracy']:.4f}[/green]")
    table.add_row("F1 (weighted)",  f"{metrics['f1_score_weighted']:.4f}")
    table.add_row("CV Mean",        f"{metrics['cv_mean']:.4f}")
    table.add_row("CV Std",         f"± {metrics['cv_std']:.4f}")

    console.print(table)


def _print_prediction(prediction: dict):
    """Pretty print a prediction result."""
    label      = prediction.get("label", "unknown")
    confidence = prediction.get("confidence", 0)
    probas     = prediction.get("probabilities") or {}

    console.print(f"\n[bold]Sample Prediction:[/bold]")
    console.print(f"  Label      : [green]{label}[/green]")
    console.print(f"  Confidence : [yellow]{confidence:.2%}[/yellow]")

    if probas:
        console.print("  Probabilities:")
        for cls, prob in sorted(probas.items(), key=lambda x: x[1], reverse=True):
            bar   = "█" * int(prob * 20)
            color = "green" if cls == label else "dim"
            console.print(f"    [{color}]{cls:<20} {bar:<20} {prob:.4f}[/{color}]")


def _print_explanation(explanation: dict):
    """Pretty print feature importances."""
    importances = explanation.get("feature_importances")
    if not importances:
        console.print("\n[dim]Feature importances not available for this model type.[/dim]")
        return

    console.print("\n[bold]Top Feature Importances:[/bold]")
    top5 = list(importances.items())[:5]
    for feat, imp in top5:
        bar = "█" * int(imp * 40)
        console.print(f"  {feat:<40} [cyan]{bar:<20}[/cyan] {imp:.4f}")


def _print_summary_table(results: list[dict]):
    """Print a comparison table across multiple experiments."""
    table = Table(title="Experiment Summary", show_header=True, header_style="bold magenta")
    table.add_column("Dataset",        style="cyan")
    table.add_column("Model",          style="cyan")
    table.add_column("Test Accuracy",  justify="right")
    table.add_column("CV Mean",        justify="right")
    table.add_column("CV Std",         justify="right")
    table.add_column("Job ID",         style="dim")

    for r in sorted(results, key=lambda x: x["test_accuracy"], reverse=True):
        acc   = r["test_accuracy"]
        color = "green" if acc >= 0.95 else "yellow" if acc >= 0.85 else "red"
        table.add_row(
            r["dataset"],
            r["model"],
            f"[{color}]{acc:.4f}[/{color}]",
            f"{r['cv_mean']:.4f}",
            f"± {r['cv_std']:.4f}",
            r["job_id"],
        )

    console.print(table)


# ══════════════════════════════════════════════════════════════
# COMMANDS
# ══════════════════════════════════════════════════════════════

@app.command()
def run(
    dataset: str = typer.Option("iris",         "--dataset", "-d", help=f"One of: {DATASETS}"),
    model:   str = typer.Option("random_forest","--model",   "-m", help=f"One of: {MODELS}"),
    predict: bool = typer.Option(True,  "--predict/--no-predict", help="Run a sample prediction after training"),
    explain: bool = typer.Option(True,  "--explain/--no-explain", help="Run feature explanation after training"),
    save:    bool = typer.Option(False, "--save",                 help="Save results to results.json"),
):
    """Run a single training experiment end-to-end."""
    with httpx.Client(timeout=30) as client:
        _check_api_health(client)

        console.print(f"\n[bold]Submitting training job...[/bold]")
        console.print(f"  dataset={dataset}  model={model}\n")

        job_id = _submit_training(client, dataset, model)
        status = _poll_until_done(client, job_id)
        metrics = status["metrics"]

        _print_metrics(metrics, dataset, model, job_id)

        if predict:
            pred = _run_prediction(client, job_id, dataset)
            _print_prediction(pred)

        if explain:
            expl = _run_explain(client, job_id, dataset)
            _print_explanation(expl)

        if save:
            out = {"job_id": job_id, "dataset": dataset, "model": model, "metrics": metrics}
            with open("results.json", "w") as f:
                json.dump(out, f, indent=2)
            console.print(f"\n[dim]Results saved to results.json[/dim]")

        console.print(f"\n[bold green]✓ Experiment complete.[/bold green]")
        console.print(f"  Predict URL : [cyan]{API_BASE}/predict/{job_id}[/cyan]")
        console.print(f"  Explain URL : [cyan]{API_BASE}/predict/{job_id}/explain[/cyan]\n")


@app.command()
def compare(
    dataset: str = typer.Option("iris", "--dataset", "-d", help="Dataset to compare models on"),
    save:    bool = typer.Option(False, "--save",          help="Save results to results.json"),
):
    """Train all models on the same dataset and compare results."""
    results = []

    with httpx.Client(timeout=30) as client:
        _check_api_health(client)

        console.print(f"\n[bold]Comparing all models on dataset: {dataset}[/bold]\n")

        for model in MODELS:
            console.rule(f"[cyan]{model}[/cyan]")
            job_id = _submit_training(client, dataset, model)
            status = _poll_until_done(client, job_id)
            m      = status["metrics"]

            results.append({
                "dataset":       dataset,
                "model":         model,
                "job_id":        job_id,
                "test_accuracy": m["test_accuracy"],
                "cv_mean":       m["cv_mean"],
                "cv_std":        m["cv_std"],
            })

        console.print()
        _print_summary_table(results)

        if save:
            with open("results.json", "w") as f:
                json.dump(results, f, indent=2)
            console.print(f"\n[dim]Results saved to results.json[/dim]")


@app.command(name="all")
def run_all(
    save: bool = typer.Option(False, "--save", help="Save results to results.json"),
):
    """Run every dataset × model combination — full benchmark."""
    results = []
    combos  = [(d, m) for d in DATASETS for m in MODELS]

    with httpx.Client(timeout=30) as client:
        _check_api_health(client)

        console.print(f"\n[bold]Running full benchmark: {len(combos)} experiments[/bold]\n")

        for dataset, model in combos:
            console.rule(f"[cyan]{dataset}[/cyan] × [magenta]{model}[/magenta]")
            try:
                job_id = _submit_training(client, dataset, model)
                status = _poll_until_done(client, job_id)
                m      = status["metrics"]
                results.append({
                    "dataset":       dataset,
                    "model":         model,
                    "job_id":        job_id,
                    "test_accuracy": m["test_accuracy"],
                    "cv_mean":       m["cv_mean"],
                    "cv_std":        m["cv_std"],
                })
            except Exception as e:
                console.print(f"[red]Failed: {e}[/red]")

        console.print()
        _print_summary_table(results)

        if save:
            with open("results.json", "w") as f:
                json.dump(results, f, indent=2)
            console.print(f"\n[dim]Results saved to results.json[/dim]")


if __name__ == "__main__":
    app()