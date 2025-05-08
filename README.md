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

## Usage

### Command Line Interface (Recommended)

The primary way to use the tool is via its command-line interface.

```bash
python linkedin_decision_maker_extractor.py <company_linkedin_url> [options]
```

**Arguments:**

-   `company_linkedin_url`: (Required) The full LinkedIn URL of the target company.
    Example: `https://www.linkedin.com/company/google/`

**Options:**

-   `--output_prefix <prefix>`: (Optional) Prefix for the output CSV and JSON files. A timestamp will be appended. Defaults to `decision_makers`.
    Example: `--output_prefix my_company_decision_makers` will result in files like `my_company_decision_makers_YYYYMMDD_HHMMSS.csv`.

**Example CLI Usage:**

```bash
# Ensure LINKEDIN_API_KEY is set in your environment or .env file
python linkedin_decision_maker_extractor.py "https://www.linkedin.com/company/microsoft/" --output_prefix microsoft_contacts
```
This will fetch decision makers for Microsoft and save the results to `microsoft_contacts_YYYYMMDD_HHMMSS.csv` and `microsoft_contacts_YYYYMMDD_HHMMSS.json`.

### As a Python Module (Advanced Usage)

You can also import and use the `LinkedInDecisionMakerExtractor` class in your own Python scripts.

```python
import os
from linkedin_decision_maker_extractor import LinkedInDecisionMakerExtractor
from datetime import datetime

# Ensure LINKEDIN_API_KEY is set as an environment variable
api_key = os.getenv("LINKEDIN_API_KEY")
if not api_key:
    print("Error: LINKEDIN_API_KEY environment variable not set.")
    exit()

extractor = LinkedInDecisionMakerExtractor(api_key)

company_url = "https://www.linkedin.com/company/example-inc/"

print(f"Extracting decision makers for {company_url}...")
decision_makers = extractor.extract_decision_makers(company_url)

if decision_makers:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_file = f"module_usage_decision_makers_{timestamp}.csv"
    json_file = f"module_usage_decision_makers_{timestamp}.json"
    
    extractor.save_to_csv(decision_makers, csv_file)
    extractor.save_to_json(decision_makers, json_file)
    print(f"Results saved to {csv_file} and {json_file}")
else:
    print("No decision makers found or an error occurred.")

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