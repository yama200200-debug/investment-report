#!/usr/bin/env python3
"""Compare the main-branch validator and the candidate using one frozen FRED snapshot."""
import contextlib
import importlib.util
import io
import json
import os
import shutil
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path.cwd()
ARTIFACTS = ROOT / "artifacts"
RECORDS_SOURCE = ROOT / "research-data/fortune/fortune_records.json"
JSON_SOURCE = ROOT / "research-data/validation/fortune_validation.json"
OLD_SCRIPT = Path(os.environ["OLD_VALIDATE_SCRIPT_PATH"])
NEW_SCRIPT = ROOT / "scripts/validate_fortune.py"
KEY = os.environ.get("FRED_API_KEY", "").strip()
RETURN_FIELDS = ("ret_1d_pct", "ret_5d_pct", "ret_20d_pct")
METADATA_FIELDS = (
    "schema_version", "record_id", "event", "event_date_utc",
    "series_id", "series_name", "rule_version", "base_date",
)
REQUIRED_FIELDS = METADATA_FIELDS + ("computed_at",) + RETURN_FIELDS


def load_module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError("validator module could not be loaded")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def run_validator(module, name, snapshots, fixed_utc, run_root):
    run_root.mkdir(parents=True, exist_ok=True)
    records_copy = run_root / "fortune_records.json"
    output_copy = run_root / "fortune_validation.json"
    shutil.copyfile(RECORDS_SOURCE, records_copy)
    shutil.copyfile(JSON_SOURCE, output_copy)
    module.RECORDS = records_copy
    module.OUT = output_copy

    class FrozenDateTime:
        @classmethod
        def now(cls, tz=None):
            return fixed_utc.astimezone(tz) if tz is not None else fixed_utc.replace(tzinfo=None)

    module.datetime = FrozenDateTime
    module.fetch_series = lambda series_id, _key: list(snapshots[series_id])
    module.time.sleep = lambda _seconds: None
    capture = io.StringIO()
    with contextlib.redirect_stdout(capture):
        module.main()
    (run_root / "stdout.log").write_text(capture.getvalue(), encoding="utf-8")
    return output_copy, capture.getvalue()


def key_for(row):
    return (row.get("record_id"), row.get("series_id"))


def main():
    if not KEY:
        print("ERROR: FRED_API_KEY secret is unavailable; key value was not printed.")
        return 2
    if not OLD_SCRIPT.is_file():
        print("ERROR: old validator source is unavailable.")
        return 2
    if not RECORDS_SOURCE.is_file() or not JSON_SOURCE.is_file():
        print("ERROR: required input JSON is unavailable.")
        return 2

    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    initial_rows = json.loads(JSON_SOURCE.read_text(encoding="utf-8"))
    old_module = load_module(OLD_SCRIPT, "old_validate_fortune")
    new_module = load_module(NEW_SCRIPT, "new_validate_fortune")

    # Fetch each FRED series once. Both validator runs then receive this exact snapshot.
    snapshots = {}
    try:
        for series_id, _label in old_module.SERIES:
            snapshots[series_id] = old_module.fetch_series(series_id, KEY)
    except Exception as exc:
        print(f"ERROR: FRED snapshot acquisition failed ({type(exc).__name__}); details suppressed.")
        return 2
    (ARTIFACTS / "fred_snapshot.json").write_text(
        json.dumps(snapshots, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    # One instant is shared by both executions; no script arguments or environment overrides are added.
    fixed_utc = datetime.now(timezone.utc).replace(microsecond=0)
    with tempfile.TemporaryDirectory(prefix="fortune-validator-test-") as temp:
        temp_root = Path(temp)
        old_path, old_log = run_validator(
            old_module, "old", snapshots, fixed_utc, temp_root / "old"
        )
        new_path, new_log = run_validator(
            new_module, "new", snapshots, fixed_utc, temp_root / "new"
        )
        old_rows = json.loads(old_path.read_text(encoding="utf-8"))
        new_rows = json.loads(new_path.read_text(encoding="utf-8"))
        shutil.copyfile(old_path, ARTIFACTS / "fortune_validation_old.json")
        shutil.copyfile(new_path, ARTIFACTS / "fortune_validation_new.json")

    initial_by_key = {key_for(row): row for row in initial_rows if isinstance(row, dict)}
    errors = []
    allowed_differences = []
    if len(old_rows) != len(new_rows):
        errors.append(f"row count differs: old={len(old_rows)} new={len(new_rows)}")

    if len(old_rows) == len(new_rows):
        for index, (old, new) in enumerate(zip(old_rows, new_rows)):
            if not isinstance(old, dict) or not isinstance(new, dict):
                if old != new:
                    errors.append(f"row[{index}] non-object value differs")
                continue
            if list(old.keys()) != list(new.keys()):
                errors.append(f"row[{index}] field names/order differ")
                continue
            baseline = initial_by_key.get(key_for(new))
            filled_in_new = []
            if baseline is not None:
                for field in RETURN_FIELDS:
                    if baseline.get(field) is None and new.get(field) is not None:
                        filled_in_new.append(field)
                    elif baseline.get(field) is not None and new.get(field) != baseline.get(field):
                        errors.append(
                            f"existing non-null changed in candidate: row[{index}].{field}"
                        )
                for field in METADATA_FIELDS:
                    if field in baseline and new.get(field) != baseline.get(field):
                        errors.append(
                            f"existing metadata changed in candidate: row[{index}].{field}"
                        )
            for field in old:
                if old[field] == new[field]:
                    continue
                old_value, new_value = old[field], new[field]
                if field in RETURN_FIELDS and old_value is None and new_value is not None:
                    if baseline is not None and baseline.get(field) is None:
                        allowed_differences.append(
                            {"row": index, "field": field, "old": old_value, "new": new_value}
                        )
                        continue
                if field == "computed_at" and filled_in_new:
                    allowed_differences.append(
                        {"row": index, "field": field, "old": old_value, "new": new_value}
                    )
                    continue
                errors.append(
                    f"disallowed difference row[{index}].{field}: "
                    f"old={old_value!r} new={new_value!r}"
                )

    # Verify field structure against the initial JSON for every pre-existing row.
    new_by_key = {key_for(row): row for row in new_rows if isinstance(row, dict)}
    for key, baseline in initial_by_key.items():
        candidate = new_by_key.get(key)
        if candidate is None:
            errors.append(f"pre-existing row disappeared: {key}")
            continue
        if list(baseline.keys()) != list(candidate.keys()):
            errors.append(f"pre-existing field structure/order changed: {key}")

    (ARTIFACTS / "run_logs.txt").write_text(
        "=== OLD VALIDATOR LOG ===\n" + old_log
        + "\n=== CANDIDATE VALIDATOR LOG ===\n" + new_log,
        encoding="utf-8",
    )
    report = {
        "passed": not errors,
        "fixed_computed_at_utc": fixed_utc.isoformat(),
        "initial_rows": len(initial_rows),
        "old_output_rows": len(old_rows),
        "candidate_output_rows": len(new_rows),
        "allowed_differences": allowed_differences,
        "errors": errors,
        "rules": {
            "same_initial_json": True,
            "same_fred_snapshot": True,
            "same_fixed_time": True,
            "allowed_output_differences": "null-to-value return fill; computed_at only on rows filled by candidate",
            "existing_non_null_values_preserved": True,
            "row_order_and_field_structure_checked": True,
        },
    }
    (ARTIFACTS / "comparison_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print("=== OLD VALIDATOR LOG ===")
    print(old_log, end="")
    print("=== CANDIDATE VALIDATOR LOG ===")
    print(new_log, end="")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
