"""API Diff Script.

This script compares API responses between two endpoints based on configurable parameters.
It fetches JSON data from old and new APIs, computes differences using DeepDiff, and saves the
results to the specified Excel file.

Helper functions are in api_diff_helpers.py.
"""

import argparse
import csv
import itertools
import logging
from pathlib import Path
from typing import Any
import yaml

from deepdiff import DeepDiff
from ratelimit import limits, sleep_and_retry

import api_diff_helpers

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


def is_empty_json(data: Any) -> bool:
    """Check if data is empty JSON-like value."""
    if data is None:
        return True
    if isinstance(data, dict) and not data:
        return True
    if isinstance(data, list) and not data:
        return True
    if isinstance(data, str) and not data:
        return True
    if isinstance(data, (int, float)) and data == 0:
        return True
    if isinstance(data, bool) and not data:
        return True
    return False


class ArgumentParserWithHelp(argparse.ArgumentParser):
    """Argument parser that prints help on error."""

    def error(self, _message: str) -> None:
        """Override to print help on error."""
        self.print_help()
        self.exit(2)


def build_param_lists(config: dict[str, Any], config_path: Path) -> list[list[str]]:
    """Build parameter lists from config."""
    param_lists: list[list[str]] = []
    for p in config["param_mapping"]:
        if "source" in p:
            source_path = config_path.parent / p["source"]
            lines = source_path.read_text(encoding="utf-8").splitlines()
            param_lists.append(list(dict.fromkeys([line.strip() for line in lines if line.strip()])))
        elif "values" in p:
            param_lists.append(p["values"])
        elif "value" in p:
            param_lists.append([str(p["value"])])
        else:
            msg = f"Parameter {p.get('csv_column', 'unknown')} must have 'source', 'values', or 'value'"
            raise ValueError(msg)
    return param_lists


def main() -> None:
    """Compare API responses."""
    parser = ArgumentParserWithHelp(description="Compare API responses for different model IDs.")
    parser.add_argument(
        "--config",
        required=True,
        help="Path to the YAML config file (e.g., config/api_diff_config.yaml). "
        "See config/api_diff_config_SAMPLE.yaml for a template.",
    )
    parser.add_argument("--debug", action="store_true", help="Enable debug logging.")
    parser.add_argument(
        "--output", "-o", default="output/api_diff.xlsx",
        help="Path to the output Excel file. Default: output/api_diff.xlsx"
    )
    args = parser.parse_args()

    Path(args.output).parent.mkdir(parents=True, exist_ok=True)

    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)

    config: dict[str, Any] = yaml.safe_load(
        Path(args.config).read_text(encoding="utf-8")
    )

    @sleep_and_retry
    @limits(calls=config["rate_limit_calls"], period=config["rate_limit_period"])
    def fetch(base_url: str, *, method: str = "GET", params: dict[str, Any] | None = None, headers: dict[str, str] | None = None) -> dict[str, Any]:
        return api_diff_helpers.fetch(base_url, method=method, params=params, headers=headers)

    results: list[dict[str, Any]] = []

    if "csv_file" in config:
        # New CSV-based mode
        csv_path = Path(args.config).parent / config["csv_file"]
        with open(csv_path, 'r', encoding='utf-8') as f:
            sample = f.read(1024)
            f.seek(0)
            sniffer = csv.Sniffer()
            try:
                delimiter = sniffer.sniff(sample, delimiters=',;\t').delimiter
            except csv.Error:
                delimiter = ','
            reader = csv.DictReader(f, delimiter=delimiter)
            test_cases = list(reader)
        total_diffs_to_run = len(test_cases)
        logger.info("Total test cases: %d", total_diffs_to_run)

        diff_count = 0
        for row in test_cases:
            api_params: dict[str, Any] = {
                p["request_param"]: row[p["csv_column"]]
                for p in config["param_mapping"]
            }
            old_method = config["old_api"].get("request_method", "GET")
            new_method = config["new_api"].get("request_method", "GET")
            old: dict[str, Any] = fetch(
                config["old_api"]["url"],
                method=old_method,
                params=api_params,
                headers=config["old_api"]["headers"]
            )
            new: dict[str, Any] = fetch(
                config["new_api"]["url"],
                method=new_method,
                params=api_params,
                headers=config["new_api"]["headers"]
            )
            logger.debug("Old: %s", old)
            logger.debug("New: %s", new)
            diff = DeepDiff(old, new, ignore_order=True)
            result: dict[str, Any] = {
                p["csv_column"]: row[p["csv_column"]] for p in config["param_mapping"]
            }
            result["has_diff"] = bool(diff)
            result["has_data"] = not is_empty_json(old) or not is_empty_json(new)
            result["diff"] = str(diff) if diff else ""
            results.append(result)
            if diff:
                diff_count += 1
                if diff_count % 1000 == 0:
                    api_diff_helpers.save_to_excel(results, args.output)
                    logger.info("Saved intermediate results after %d diffs of %d", diff_count, total_diffs_to_run)
            if diff:
                logger.info("%s: %s", "-".join(str(row[p["csv_column"]]) for p in config["param_mapping"]), diff)
            else:
                logger.info("%s: No diff, has_data=%s", "-".join(str(row[p["csv_column"]]) for p in config["param_mapping"]), result["has_data"])
    else:
        # Legacy permutation mode
        param_lists = build_param_lists(config, Path(args.config))

        total_diffs_to_run = 1
        for lst in param_lists:
            total_diffs_to_run *= len(lst)
        logger.info("Total number of diffs to run: %d", total_diffs_to_run)

        diff_count = 0
        for combo in itertools.product(*param_lists):
            api_params: dict[str, Any] = {
                p["request_param"]: v
                for p, v in zip(config["param_mapping"], combo, strict=True)
            }
            old_method = config["old_api"].get("request_method", "GET")
            new_method = config["new_api"].get("request_method", "GET")
            old: dict[str, Any] = fetch(
                config["old_api"]["url"],
                method=old_method,
                params=api_params,
                headers=config["old_api"]["headers"]
            )
            new: dict[str, Any] = fetch(
                config["new_api"]["url"],
                method=new_method,
                params=api_params,
                headers=config["new_api"]["headers"]
            )
            logger.debug("Old: %s", old)
            logger.debug("New: %s", new)
            diff = DeepDiff(old, new, ignore_order=True)
            result: dict[str, Any] = {
                p["csv_column"]: v for p, v in zip(config["param_mapping"], combo, strict=True)
            }
            result["has_diff"] = bool(diff)
            result["has_data"] = not is_empty_json(old) or not is_empty_json(new)
            result["diff"] = str(diff) if diff else ""
            results.append(result)
            if diff:
                diff_count += 1
                if diff_count % 1000 == 0:
                    api_diff_helpers.save_to_excel(results, args.output)
                    logger.info("Saved intermediate results after %d diffs of %d", diff_count, total_diffs_to_run)
            if diff:
                logger.info("%s: %s", "-".join(str(v) for v in combo), diff)
            else:
                logger.info("%s: No diff, has_data=%s", "-".join(str(v) for v in combo), result["has_data"])

    api_diff_helpers.save_to_excel(results, args.output)


if __name__ == "__main__":
    main()
