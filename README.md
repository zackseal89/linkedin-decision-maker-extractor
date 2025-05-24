# LinkedIn Decision Maker Extraction Tool

A Python-based tool for extracting decision makers from LinkedIn company profiles. This tool helps identify key personnel within organizations for sales prospecting, recruitment, or market research purposes.

## Features

- Extract company data from LinkedIn
- Identify decision makers based on job titles
- Robust error handling and retry logic
- Rate limiting to respect LinkedIn API constraints
- Data export to CSV and JSON formats
- Comprehensive logging

## Installation

### Prerequisites

- Python 3.7+
- LinkedIn API Key (set as an environment variable)

### Setup

1.  **Clone the repository:**
    ```bash
    git clone <repository_url>
    cd linkedin-decision-maker-extractor
    ```

2.  **Create and activate a virtual environment (recommended):**
    ```bash
    python -m venv venv
    # On Windows
    venv\Scripts\activate
    # On macOS/Linux
    source venv/bin/activate
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
    If `requirements.txt` is not present, you might need to install them manually:
    ```bash
    pip install requests pandas python-dotenv
    ```

4.  **Set up the LinkedIn API Key:**
    The tool requires your LinkedIn API key to be set as an environment variable named `LINKEDIN_API_KEY`.
    You can set this in your system's environment variables, or create a `.env` file in the project root with the following content:
    ```
    LINKEDIN_API_KEY="your_actual_api_key_here"
    ```
    The script will automatically load this `.env` file if `python-dotenv` is installed and the file exists.
    Alternatively, the API key can be provided directly via the `--api-key` or `-k` command-line option in `cli.py`, which will take precedence over the environment variable.

## Usage

### Command Line Interface (Recommended)

The primary way to use the tool is via its command-line interface.

```bash
python cli.py --company <company_linkedin_url> [options]
```

**Arguments:**

-   `--company <url>` or `-c <url>`: (Required) The full LinkedIn URL of the target company.
    Example: `--company "https://www.linkedin.com/company/google/"`

**Options:**

-   `--output <prefix>` or `-o <prefix>`: (Optional) Prefix for the output CSV and JSON files. A timestamp will be appended. Defaults to `decision_makers`.
    Example: `--output my_company_decision_makers` will result in files like `my_company_decision_makers_YYYYMMDD_HHMMSS.csv`.
-   `--format <format>` or `-f <format>`: (Optional) Output format. Choices: `csv`, `json`, `both`. Default: `both`.
    Example: `--format csv`
-   `--api-key <key>` or `-k <key>`: (Optional) LinkedIn API key. If provided, this will override the `LINKEDIN_API_KEY` environment variable.
    Example: `--api-key your_actual_api_key_here`

**Example CLI Usage:**

```bash
# Ensure LINKEDIN_API_KEY is set in your environment or .env file,
# or provide it with the --api-key option.
python cli.py --company "https://www.linkedin.com/company/microsoft/" --output microsoft_contacts --format both
```
This will fetch decision makers for Microsoft and save the results to `microsoft_contacts_YYYYMMDD_HHMMSS.csv` and `microsoft_contacts_YYYYMMDD_HHMMSS.json`.

### As a Python Module (Advanced Usage)

You can import and use the `LinkedInDecisionMakerExtractor` class in your own Python scripts. The `linkedin_decision_maker_extractor.py` file itself is no longer runnable as a standalone script after the removal of its `main` function.

```python
import os
from linkedin_decision_maker_extractor import LinkedInDecisionMakerExtractor
from datetime import datetime

# Ensure LINKEDIN_API_KEY is set as an environment variable or pass the key directly.
# Example using environment variable:
api_key = os.getenv("LINKEDIN_API_KEY")

# Or, provide the API key directly:
# api_key = "your_actual_api_key_here"

if not api_key:
    print("Error: LinkedIn API key not provided. Set the LINKEDIN_API_KEY environment variable or pass the key to the extractor.")
    exit()

# Initialize the extractor with the API key
extractor = LinkedInDecisionMakerExtractor(api_key=api_key)

# Define the target company URL
company_url = "https://www.linkedin.com/company/linkedin/" # Replace with a valid LinkedIn company URL

print(f"Attempting to extract decision makers for: {company_url}")

try:
    # Extract decision makers
    decision_makers = extractor.extract_decision_makers(company_url)

    if decision_makers:
        print(f"Found {len(decision_makers)} potential decision makers.")
        
        # Create a timestamp for unique filenames
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Define output filenames
        csv_output_file = f"decision_makers_{timestamp}.csv"
        json_output_file = f"decision_makers_{timestamp}.json"
        
        # Save to CSV
        extractor.save_to_csv(decision_makers, csv_output_file)
        print(f"Decision makers data saved to {csv_output_file}")
        
        # Save to JSON
        extractor.save_to_json(decision_makers, json_output_file)
        print(f"Decision makers data saved to {json_output_file}")
        
    else:
        print("No decision makers found or an error occurred during extraction.")

except Exception as e:
    print(f"An error occurred during the process: {e}")

```

## Deployment

### Docker Deployment

1. Build the Docker image
   ```bash
   docker build -t linkedin-extractor .
   ```

2. Run the container
   ```bash
   docker run -e LINKEDIN_API_KEY=your_api_key_here linkedin-extractor
   ```

### Cloud Deployment

This tool can be deployed to various cloud platforms:

- **AWS Lambda**: For serverless execution
- **Google Cloud Functions**: For event-driven processing
- **Azure Functions**: For scheduled extraction tasks

## Legal and Compliance

Before using this tool, ensure you comply with:

- LinkedIn's Terms of Service
- Data protection regulations (GDPR, CCPA, etc.)
- Your organization's data usage policies

## Maintenance

- Regularly check for LinkedIn API changes
- Update dependencies to address security vulnerabilities
- Monitor rate limits and adjust as needed

## License

MIT

## Disclaimer

This tool is provided for educational purposes only. Users are responsible for ensuring their use of the tool complies with LinkedIn's Terms of Service and applicable laws.