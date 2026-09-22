import pytest

from flembench import cache, runner
from flembench.adapters.base import Completion
from flembench.registry import ModelSpec


class FakeAdapter:
    def __init__(self, answer="A"):
        self.answer, self.calls = answer, 0

    def complete(self, model_id, system, user, max_tokens, params):
        self.calls += 1
        return Completion(
            text=self.answer, input_tokens=100, output_tokens=1, model_reported=model_id
        )


@pytest.fixture
def spec():
    return ModelSpec(
        key="fake",
        provider="fake",
        model_id="fake-1",
        params={"t": 0},
        reasoning="none",
        price={"input": 1.0, "output": 2.0},
    )


@pytest.fixture(autouse=True)
def tmp_cache(tmp_path, monkeypatch):
    monkeypatch.setattr(cache, "CACHE_DIR", tmp_path / "cache")


def test_execute_caches_and_never_requeries(pair_items, spec):
    fake = FakeAdapter()
    jobs = runner.plan(pair_items, [spec], repeats=2)
    assert len(jobs) == 4 and len({j.key for j in jobs}) == 4
    spent = runner.execute(jobs, budget_usd=1.0, adapter_factory=lambda p: fake)
    assert fake.calls == 4 and spent == pytest.approx(4 * (100 * 1 + 1 * 2) / 1e6)
    runner.execute(runner.plan(pair_items, [spec], repeats=2), 1.0, adapter_factory=lambda p: fake)
    assert fake.calls == 4  # all cached


def test_estimate_skips_cached(pair_items, spec):
    jobs = runner.plan(pair_items, [spec])
    [e] = runner.estimate(jobs)
    assert e.calls == 2 and e.cached == 0 and e.worst_case_usd > e.expected_usd > 0
    runner.execute(jobs, 1.0, adapter_factory=lambda p: FakeAdapter())
    [e] = runner.estimate(runner.plan(pair_items, [spec]))
    assert e.calls == 0 and e.cached == 2


def test_budget_stops_run(pair_items, spec):
    with pytest.raises(runner.BudgetExceeded):
        runner.execute(
            runner.plan(pair_items, [spec], repeats=3),
            budget_usd=1e-9,
            adapter_factory=lambda p: FakeAdapter(),
        )


def test_score_rows_from_cache(pair_items, spec):
    be, _ = pair_items
    jobs = runner.plan(pair_items, [spec])
    runner.execute(jobs, 1.0, adapter_factory=lambda p: FakeAdapter(answer=be.gold))
    rows = runner.score_rows(jobs)
    assert [r["correct"] for r in rows] == [True, True]
    assert {r["variety"] for r in rows} == {"be", "nl"}


def test_prompt_change_changes_key(pair_items, spec):
    be, _ = pair_items
    [j1] = runner.plan([be], [spec])
    [j2] = runner.plan([be.model_copy(update={"prompt": be.prompt + "!"})], [spec])
    assert j1.key != j2.key


def test_heldout_needs_private_dir(pair_items, spec):
    held = [i.model_copy(update={"split": "heldout"}) for i in pair_items]
    with pytest.raises(RuntimeError, match="FLEMBENCH_HELDOUT_DIR"):
        runner.plan(held, [spec])


def test_retry_on_transient_then_success_and_permanent_raises():
    calls = {"n": 0}

    def flaky():
        calls["n"] += 1
        if calls["n"] < 3:
            raise RuntimeError("503 UNAVAILABLE: high demand")
        return Completion(text="A", input_tokens=1, output_tokens=1)

    waits = []
    assert runner.call_with_retry(flaky, sleep=waits.append).text == "A"
    assert waits == [10, 30]

    def broke():
        raise RuntimeError("429 insufficient_quota: no credits")

    with pytest.raises(RuntimeError, match="insufficient_quota"):
        runner.call_with_retry(broke, sleep=waits.append)
    assert waits == [10, 30]  # no waiting on permanent errors
    assert not runner.is_transient(RuntimeError("400 INVALID_ARGUMENT thinking level"))
