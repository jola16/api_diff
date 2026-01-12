# API Diff

A Python script to compare API responses between two endpoints based on configurable parameters. It fetches data from old and new APIs, computes differences using DeepDiff, and saves the results to an Excel file.

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

Run the script with a configuration file:

```bash
python api_diff.py --config config/api_diff_config_SAMPLE.yaml
```

Use `--debug` for detailed logging:

```bash
python api_diff.py --config config/api_diff_config_SAMPLE.yaml --debug
```

## Configuration

Create a YAML config file based on `config/api_diff_config_SAMPLE.yaml`. It should include:

- API endpoints (old and new)
- Headers
- Rate limiting
- Parameter configurations (from files, values, or single values)

## Dependencies

- deepdiff
- ratelimit
- openpyxl
- pyyaml

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.