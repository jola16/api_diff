"""Create Test Data CSV Script.

This script generates a CSV file with all parameter combinations from a YAML config,
matching the logic used in api_diff.py for permutation-based testing.
"""

import argparse
import csv
import itertools
import logging
from pathlib import Path
from typing import Any
import yaml

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


class ArgumentParserWithHelp(argparse.ArgumentParser):
    """Argument parser that prints help on error."""

    def error(self, _message: str) -> None:
        """Override to print help on error."""
        self.print_help()
        self.exit(2)


def build_param_lists(config: dict[str, Any], config_path: Path) -> list[list[str]]:
    """Build parameter lists from config."""
    param_lists: list[list[str]] = []
    for p in config["param_config"]:
        if "source" in p:
            source_path = config_path.parent / p["source"]
            lines = source_path.read_text(encoding="utf-8").splitlines()
            param_lists.append(list(dict.fromkeys([line.strip() for line in lines if line.strip()])))
        elif "values" in p:
            param_lists.append(p["values"])
        elif "value" in p:
            param_lists.append([str(p["value"])])
        else:
            msg = f"Parameter {p.get('name', 'unknown')} must have 'source', 'values', or 'value'"
            raise ValueError(msg)
    return param_lists


def main() -> None:
    """Generate CSV with all parameter combinations."""
    parser = ArgumentParserWithHelp(description="Generate CSV with all parameter combinations from config.")
    parser.add_argument(
        "--config",
        required=True,
        help="Path to the YAML config file (e.g., config/api_diff_config_SAMPLE.yaml).",
    )
    parser.add_argument(
        "--output", "-o", default="config/test_data.csv",
        help="Path to the output CSV file. Default: config/test_data.csv"
    )
    args = parser.parse_args()

    Path(args.output).parent.mkdir(parents=True, exist_ok=True)

    config: dict[str, Any] = yaml.safe_load(
        Path(args.config).read_text(encoding="utf-8")
    )

    param_lists = build_param_lists(config, Path(args.config))

    total_combos = 1
    for lst in param_lists:
        total_combos *= len(lst)
    logger.info("Total combinations to generate: %d", total_combos)

    with open(args.output, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        # Write header
        writer.writerow([p["name"] for p in config["param_config"]])
        # Write rows
        for combo in itertools.product(*param_lists):
            writer.writerow(combo)

    logger.info("CSV generated: %s", args.output)


if __name__ == "__main__":
    main()