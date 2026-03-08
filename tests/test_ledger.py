"""Tests for ledger write/read roundtrip."""

import tempfile
from pathlib import Path

from prae.ledger import LedgerEntry, append_entry, read_entries


def test_roundtrip():
    with tempfile.TemporaryDirectory() as d:
        path = Path(d) / "ledger.jsonl"

        entry = LedgerEntry(
            iteration=1,
            mode="prae",
            timestamp="2025-01-01T00:00:00Z",
            baseline_ref="abc1234",
            proposal_summary="adjust learning rate",
            verdict="keep",
            parsed_metric=0.45,
            execution_status="success",
            baseline_advanced=True,
        )
        append_entry(path, entry)

        entries = read_entries(path)
        assert len(entries) == 1
        assert entries[0].iteration == 1
        assert entries[0].mode == "prae"
        assert entries[0].verdict == "keep"
        assert entries[0].parsed_metric == 0.45
        assert entries[0].baseline_advanced is True


def test_multiple_entries():
    with tempfile.TemporaryDirectory() as d:
        path = Path(d) / "ledger.jsonl"

        for i in range(5):
            entry = LedgerEntry(
                iteration=i + 1,
                mode="baseline",
                timestamp=f"2025-01-0{i+1}T00:00:00Z",
                baseline_ref=f"ref{i}",
                verdict="keep" if i % 2 == 0 else "discard",
            )
            append_entry(path, entry)

        entries = read_entries(path)
        assert len(entries) == 5
        assert entries[0].iteration == 1
        assert entries[4].iteration == 5


def test_read_nonexistent():
    entries = read_entries("/tmp/nonexistent_ledger_abc123.jsonl")
    assert entries == []
