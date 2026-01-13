# API Diff

A Python script to compare API responses between two endpoints based on configurable parameters. It fetches data from old and new APIs, computes differences using DeepDiff, and saves the results to the specified Excel file (default: output/api_diff.xlsx).

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/jola16/api_diff.git
   cd api_diff
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

**Note:** This script currently only supports APIs that return JSON responses.

Run the script with a configuration file:

```bash
python api_diff.py --config config/api_diff_config_SAMPLE.yaml
```

Use `--debug` for detailed logging:

```bash
python api_diff.py --config config/api_diff_config_SAMPLE.yaml --debug
```

Specify a custom output file (default: output/api_diff.xlsx):

```bash
python api_diff.py --config config/api_diff_config_SAMPLE.yaml --output my_results.xlsx
```

## Configuration

1. Copy the sample config file as a template:
   ```bash
   cp config/api_diff_config_SAMPLE.yaml config/api_diff_config.yaml
   ```

2. Edit `config/api_diff_config.yaml` with your actual:
    - API endpoints (old and new)
    - Request method (optional, default GET) for old_api and new_api
    - Authentication headers (optional)
    - Rate limiting settings
    - Parameter configurations (from files, values, or single values)

**Note:** Config files in `config/` are gitignored (except the SAMPLE file) to protect sensitive data.

**Note:** Source file paths in the config are relative to the config file's directory.

**Note:** Output files in `output/` are gitignored to protect potentially sensitive data.

## Dependencies

- deepdiff
- ratelimit
- openpyxl
- pyyaml

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.