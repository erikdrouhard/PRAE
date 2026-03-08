"""Tests for metric parsing and execution."""

from prae.executor import parse_metric, run_target
from pathlib import Path
import tempfile
import os


def test_parse_metric_basic():
    output = "epoch 10\nfinal_loss: 0.4523\naccuracy: 0.87"
    result = parse_metric(output, r"final_loss:\s*([\d.]+)")
    assert result is not None
    assert abs(result - 0.4523) < 1e-6


def test_parse_metric_no_match():
    output = "no metric here"
    result = parse_metric(output, r"final_loss:\s*([\d.]+)")
    assert result is None


def test_parse_metric_integer():
    output = "score: 42"
    result = parse_metric(output, r"score:\s*(\d+)")
    assert result == 42.0


def test_parse_metric_scientific():
    output = "loss: 1.5e-3"
    result = parse_metric(output, r"loss:\s*([0-9.e-]+)")
    assert result is not None
    assert abs(result - 0.0015) < 1e-6


def test_run_target_success():
    with tempfile.TemporaryDirectory() as d:
        result = run_target("echo 'final_loss: 0.5'", Path(d), budget_seconds=10)
        assert not result.timed_out
        assert result.returncode == 0
        assert "final_loss" in result.stdout


def test_run_target_timeout():
    with tempfile.TemporaryDirectory() as d:
        result = run_target("sleep 10", Path(d), budget_seconds=1)
        assert result.timed_out


def test_run_target_error():
    with tempfile.TemporaryDirectory() as d:
        result = run_target("exit 1", Path(d), budget_seconds=10)
        assert result.returncode == 1
        assert not result.timed_out
