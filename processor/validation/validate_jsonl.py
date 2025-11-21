"""
Validate raw_smc_export.jsonl against a lightweight schema.
Usage:
    python -m processor.validation.validate_jsonl --input raw_smc_export.jsonl
"""

import argparse
import json
from typing import List, Tuple

from .schema import validate_record


def validate_file(path: str) -> int:
    errors: List[Tuple[int, List[Tuple[str, List[str]]]]] = []
    with open(path, "r", encoding="utf-8") as f:
        for idx, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                errors.append((idx, [("json", [f"decode_error: {exc}"])]))
                continue

            problems = validate_record(record)
            if problems:
                errors.append((idx, problems))

    if errors:
        print(f"Found {len(errors)} problematic lines:")
        for line_no, issues in errors[:50]:
            print(f"- Line {line_no}:")
            for section, fields in issues:
                print(f"    [{section}] missing: {', '.join(fields)}")
        if len(errors) > 50:
            print(f"... truncated, total errors: {len(errors)}")
        return 1

    print("Validation passed: no missing required fields.")
    return 0


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="Path to raw_smc_export.jsonl")
    args = parser.parse_args()
    exit_code = validate_file(args.input)
    raise SystemExit(exit_code)


if __name__ == "__main__":
    main()
