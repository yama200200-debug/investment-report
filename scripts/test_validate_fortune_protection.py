#!/usr/bin/env python3
"""Isolated regression tests for candidate-only Fortune validator protections.

Uses temporary JSON files and mocked observations only. Never calls FRED or
writes to repository validation data.
"""
import contextlib
import importlib.util
import io
import json
import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent
CANDIDATE = ROOT / "validate_fortune.py"
JST = timezone(timedelta(hours=9))
FIXED_UTC = datetime(2026, 10, 27, 12, 0, 0, tzinfo=timezone.utc)
RETURN_FIELDS = ("ret_1d_pct", "ret_5d_pct", "ret_20d_pct")
METADATA_FIELDS = (
    "schema_version", "record_id", "event", "event_date_utc",
    "series_id", "series_name", "rule_version", "base_date",
)
REQUIRED_FIELDS = METADATA_FIELDS + ("computed_at",) + RETURN_FIELDS


def observations(count=31):
    return [
        (f"2024-01-{day:02d}", float(100 + day))
        for day in range(1, count + 1)
    ]


def computed_returns(obs):
    dates = [date for date, _value in obs]
    values = [value for _date, value in obs]
    base_idx = next(i for i, date in enumerate(dates) if date >= "2024-01-10") - 1
    base = values[base_idx]
    result = {}
    for horizon in (1, 5, 20):
        idx = base_idx + horizon
        result[f"ret_{horizon}d_pct"] = (
            round((values[idx] / base - 1.0) * 100.0, 4)
            if idx < len(values) else None
        )
    return result


def record_fixture():
    return {
        "record_id": "EVT-TEST-001",
        "record_type": "event",
        "event": "isolated protection test",
        "tolerance_trading_days": 0,
        "target_date_start": "2024-01-10",
        "target_date_end": "2024-01-10",
    }


def row_fixture(obs=None):
    obs = obs or observations()
    return {
        "schema_version": 1,
        "record_id": "EVT-TEST-001",
        "event": "isolated protection test",
        "event_date_utc": "2024-01-10",
        "series_id": "SP500",
        "series_name": "S&P500",
        "rule_version": "base_prev_close_v1",
        "computed_at": "2020-01-01T00:00:00+09:00",
        "base_date": "2024-01-09",
        **computed_returns(obs),
    }


def run_candidate(initial_row, obs=None):
    obs = obs or observations()
    with tempfile.TemporaryDirectory(prefix="fortune-protection-test-") as temp:
        root = Path(temp)
        records_path = root / "fortune_records.json"
        output_path = root / "fortune_validation.json"
        records_path.write_text(
            json.dumps([record_fixture()], ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        initial_rows = [] if initial_row is None else [initial_row]
        initial_text = json.dumps(initial_rows, ensure_ascii=False, indent=1) + "\n"
        output_path.write_text(initial_text, encoding="utf-8")

        spec = importlib.util.spec_from_file_location("fortune_validator_candidate_test", CANDIDATE)
        if spec is None or spec.loader is None:
            raise RuntimeError("Unable to load candidate validator")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        module.RECORDS = records_path
        module.OUT = output_path
        module.SERIES = [("SP500", "S&P500")]
        module.fetch_series = lambda _series_id, _key: list(obs)

        class FrozenDateTime:
            @classmethod
            def now(cls, tz=None):
                return FIXED_UTC.astimezone(tz) if tz is not None else FIXED_UTC.replace(tzinfo=None)

        module.datetime = FrozenDateTime
        capture = io.StringIO()
        prior_key = os.environ.get("FRED_API_KEY")
        os.environ["FRED_API_KEY"] = "isolated-test-placeholder"
        try:
            with mock.patch.object(module.time, "sleep", lambda _seconds: None):
                with contextlib.redirect_stdout(capture):
                    module.main()
        finally:
            if prior_key is None:
                os.environ.pop("FRED_API_KEY", None)
            else:
                os.environ["FRED_API_KEY"] = prior_key

        final_text = output_path.read_text(encoding="utf-8")
        return {
            "initial_rows": initial_rows,
            "initial_text": initial_text,
            "final_text": final_text,
            "final_rows": json.loads(final_text),
            "stdout": capture.getvalue(),
            "fixed_computed_at": FIXED_UTC.astimezone(JST).isoformat(timespec="seconds"),
        }


class ProtectionTests(unittest.TestCase):
    def test_P01_conflicting_non_null_value_is_preserved_and_warned(self):
        row = row_fixture()
        row.update({"ret_1d_pct": 999.0, "ret_5d_pct": 888.0, "ret_20d_pct": 777.0})
        result = run_candidate(row)
        self.assertEqual(result["final_rows"], [row])
        self.assertIn("既存値を保持", result["stdout"])
        self.assertIn("field=ret_1d_pct", result["stdout"])
        self.assertIn("変更なし", result["stdout"])

    def test_P02_null_values_are_filled_without_changing_other_fields(self):
        row = row_fixture()
        row.update({"ret_1d_pct": None, "ret_5d_pct": None, "ret_20d_pct": None})
        result = run_candidate(row)
        final = result["final_rows"][0]
        expected = computed_returns(observations())
        for field in RETURN_FIELDS:
            self.assertEqual(final[field], expected[field])
        for field in METADATA_FIELDS:
            self.assertEqual(final[field], row[field])
        self.assertEqual(final["computed_at"], result["fixed_computed_at"])
        self.assertIn("更新 1行", result["stdout"])

    def test_P03_existing_non_null_is_preserved_when_recomputed_value_is_null(self):
        short_obs = observations(14)
        row = row_fixture(short_obs)
        row["ret_20d_pct"] = 123.456
        result = run_candidate(row, short_obs)
        self.assertEqual(result["final_rows"], [row])
        self.assertIn("field=ret_20d_pct", result["stdout"])
        self.assertIn("既存値を保持", result["stdout"])

    def test_P04_missing_required_field_skips_row_without_modification(self):
        row = row_fixture()
        del row["base_date"]
        result = run_candidate(row)
        self.assertEqual(result["final_rows"], [row])
        self.assertIn("必須フィールド欠落", result["stdout"])
        self.assertIn("missing_fields=base_date", result["stdout"])

    def test_P05_metadata_mismatch_skips_row_without_modification(self):
        row = row_fixture()
        row["base_date"] = "2024-01-08"
        result = run_candidate(row)
        self.assertEqual(result["final_rows"], [row])
        self.assertIn("メタデータ不一致", result["stdout"])
        self.assertIn("metadata_mismatch=base_date", result["stdout"])

    def test_P06_no_fill_keeps_computed_at_and_does_not_write(self):
        row = row_fixture()
        result = run_candidate(row)
        self.assertEqual(result["final_rows"], [row])
        self.assertEqual(result["final_text"], result["initial_text"])
        self.assertIn("変更なし", result["stdout"])

    def test_P07_multiple_nulls_fill_only_null_fields_and_count_one_row(self):
        row = row_fixture()
        row["ret_1d_pct"] = None
        row["ret_5d_pct"] = 456.789
        row["ret_20d_pct"] = None
        result = run_candidate(row)
        final = result["final_rows"][0]
        expected = computed_returns(observations())
        self.assertEqual(final["ret_1d_pct"], expected["ret_1d_pct"])
        self.assertEqual(final["ret_5d_pct"], 456.789)
        self.assertEqual(final["ret_20d_pct"], expected["ret_20d_pct"])
        self.assertEqual(final["computed_at"], result["fixed_computed_at"])
        self.assertEqual(list(final.keys()), list(row.keys()))
        self.assertIn("更新 1行", result["stdout"])


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(ProtectionTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    raise SystemExit(0 if result.wasSuccessful() else 1)
