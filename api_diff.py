"""API Diff Script.

This script compares API responses between two endpoints based on configurable parameters.
It fetches data from old and new APIs, computes differences using DeepDiff,
and saves the results to an Excel file.

Helper functions are in api_diff_helpers.py.
"""

import argparse
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


class ArgumentParserWithHelp(argparse.ArgumentParser):
    def error(self, message):
        self.print_help()
        self.exit(2)


def main() -> None:
    """Compare API responses."""
    parser = ArgumentParserWithHelp(description="Compare API responses for different model IDs.")
    parser.add_argument("--config", required=True, help="Path to the YAML config file.")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging.")
    args = parser.parse_args()

    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)

    config: dict[str, Any] = yaml.safe_load(Path(args.config).read_text())

    @sleep_and_retry
    @limits(calls=config['rate_limit_calls'], period=config['rate_limit_period'])
    def fetch(base_url: str, headers: dict[str, str], **params: Any) -> dict[str, Any]:
        return api_diff_helpers.fetch(base_url, headers, **params)

    results: list[dict[str, Any]] = []

    param_lists: list[list[str]] = []
    for p in config['param_config']:
        if "source" in p:
            with Path(p["source"]).open(encoding="utf-8") as f:
                param_lists.append([line.strip() for line in f if line.strip()])
        elif "values" in p:
            param_lists.append(p["values"])
        elif "value" in p:
            param_lists.append([str(p["value"])])
        else:
            raise ValueError(f"Parameter {p.get('name', 'unknown')} must have 'source', 'values', or 'value'")

    for combo in itertools.product(*param_lists):
        api_params: dict[str, Any] = {
            p.get("api_name", p["name"]): v
            for p, v in zip(config['param_config'], combo)
        }
        old: dict[str, Any] = fetch(config['old_api']['url'], config['old_api']['headers'], **api_params)
        new: dict[str, Any] = fetch(config['new_api']['url'], config['new_api']['headers'], **api_params)
        diff = DeepDiff(old, new, ignore_order=True)
        result: dict[str, Any] = {p["name"]: v for p, v in zip(config['param_config'], combo)}
        result["has_diff"] = bool(diff)
        result["diff"] = str(diff) if diff else ""
        results.append(result)
        if diff:
            logger.info("%s: %s", "-".join(str(v) for v in combo), diff)
        else:
            logger.info("%s: No diff", "-".join(str(v) for v in combo))

    api_diff_helpers.save_to_excel(results)


if __name__ == "__main__":
    main()
