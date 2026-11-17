"""Offline transport/budget checks; this suite never calls a real API."""

import importlib.util
from pathlib import Path

import pytest

from workevo.errors import BudgetExceeded, Incompatible

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "workevo_benchmark", ROOT / "scripts/live_benchmark.py"
)
benchmark = importlib.util.module_from_spec(spec)
spec.loader.exec_module(benchmark)


async def test_full_rehearsal_never_needs_a_live_key(tmp_path):
    receipt = await benchmark.benchmark(
        "not-a-real-key", live=False, output=tmp_path / "receipt.json"
    )
    assert receipt["status"] == "passed"
    assert receipt["generation_attempts"] == 3
    assert receipt["mode"] == "offline_rehearsal" and not receipt["usage_measured"]
    assert receipt["fixture_trials"] == 40
    assert receipt["optimization"]["final_quality"] == 1
    assert receipt["paired_target"]["baseline"]["correct_records"] == 2
    assert receipt["paired_target"]["evolved"]["correct_records"] == 2
    assert "not-a-real-key" not in (tmp_path / "receipt.json").read_text()


async def test_generation_limit_checked_before_count_or_dispatch():
    client = benchmark.ClaudeSession("placeholder", transport=benchmark.fake_transport)
    for _ in range(3):
        await client({"role": "optimizer"}, 256, 20)
    before = client.preflights
    with pytest.raises(BudgetExceeded):
        await client({}, 256, 20)
    assert client.preflights == before and len(client.calls) == 3


async def test_preflight_limit_prevents_paid_generation():
    called = []

    def transport(path, body, key, timeout):
        called.append(path)
        return {"input_tokens": 1201}

    client = benchmark.ClaudeSession("placeholder", transport=transport)
    with pytest.raises(BudgetExceeded):
        await client({}, 256, 20)
    assert called == ["/count_tokens"] and not client.calls


async def test_spend_forecast_refuses_before_generation():
    called = []

    def transport(path, body, key, timeout):
        called.append(path)
        return {"input_tokens": 1000}

    client = benchmark.ClaudeSession("placeholder", transport=transport)
    client.estimated_usd = 0.0009
    with pytest.raises(BudgetExceeded):
        await client({}, 256, 20)
    assert called == ["/count_tokens"] and not client.calls


async def test_failed_generation_retains_forecast_and_never_retries():
    called = []

    def transport(path, body, key, timeout):
        called.append(path)
        if path:
            return {"input_tokens": 100}
        raise Incompatible("transport failure")

    client = benchmark.ClaudeSession("placeholder", transport=transport)
    with pytest.raises(Incompatible):
        await client({}, 256, 20)
    assert client.unresolved and client.estimated_usd > 0
    with pytest.raises(BudgetExceeded):
        await client({}, 256, 20)
    assert called == ["/count_tokens", ""]


async def test_truncation_is_charged_without_continuation():
    def transport(path, body, key, timeout):
        result = benchmark.fake_transport(path, body, key, timeout)
        if not path:
            result["stop_reason"] = "max_tokens"
        return result

    client = benchmark.ClaudeSession("placeholder", transport=transport)
    with pytest.raises(Incompatible):
        await client({"role": "optimizer"}, 256, 20)
    assert len(client.calls) == 1 and client.calls[0]["usage"]["output_tokens"] == 45
    assert client.estimated_usd > 0 and not client.unresolved


def test_redirects_do_not_forward_authentication():
    assert (
        benchmark.NoRedirect().redirect_request(None, None, 302, "", {}, "https://example.com")
        is None
    )
