import requests
import time
import pandas as pd
import logging
import requests
import time
import pandas as pd
import logging
import json
from typing import Dict, List, Optional
from datetime import datetime
import os
import argparse

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("linkedin_extractor.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

class LinkedInDecisionMakerExtractor:
    def __init__(self, api_key: str):
        """
        Initialize the LinkedIn Decision Maker Extractor.
        
        Args:
            api_key (str): API key for LinkedIn API authentication
        """
        self.api_key = api_key
        self.base_url = "https://api.linkedin.com/v2"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        self.retry_attempts = 3
        self.retry_delay = 2  # seconds
        logger.info("LinkedIn Decision Maker Extractor initialized")

    def _make_request(self, endpoint: str, params: Dict = None, method: str = "GET") -> Dict:
        """
        Make a request to the LinkedIn API with retry logic and rate limiting.
        
        Args:
            endpoint (str): API endpoint to call
            params (Dict, optional): Query parameters for the request
            method (str, optional): HTTP method (GET, POST, etc.)
            
        Returns:
            Dict: JSON response from the API
            
        Raises:
            requests.exceptions.RequestException: If the request fails after retries
        """
        url = f"{self.base_url}/{endpoint}"
        
        for attempt in range(self.retry_attempts):
            try:
                # Add delay for rate limiting
                if attempt > 0:
                    delay = self.retry_delay * (2 ** attempt)  # Exponential backoff
                    logger.info(f"Retrying in {delay} seconds (attempt {attempt+1}/{self.retry_attempts})")
                    time.sleep(delay)
                
                if method.upper() == "GET":
                    response = requests.get(url, headers=self.headers, params=params)
                elif method.upper() == "POST":
                    response = requests.post(url, headers=self.headers, json=params)
                else:
                    raise ValueError(f"Unsupported HTTP method: {method}")
                
                response.raise_for_status()  # This will raise HTTPError for 4xx/5xx
                return response.json()
            
            except requests.exceptions.HTTPError as e_http:
                # Log the response text for more details, especially for 429
                response_text = ""
                try:
                    response_text = e_http.response.text
                except AttributeError:
                    pass # No response text available

                if e_http.response.status_code == 429:
                    logger.warning(
                        f"Rate limit hit (429). URL: {url}. Params: {params}. Response: {response_text}. "
                        f"Retrying as per policy (attempt {attempt + 1}/{self.retry_attempts})."
                    )
                else:
                    logger.warning(
                        f"HTTP error {e_http.response.status_code}. URL: {url}. Params: {params}. Response: {response_text}. "
                        f"Retrying (attempt {attempt + 1}/{self.retry_attempts})."
                    )
                
                if attempt == self.retry_attempts - 1:
                    logger.error(f"Failed after {self.retry_attempts} attempts for URL {url} with params {params} due to HTTPError: {e_http}")
                    raise
            except requests.exceptions.RequestException as e_req:  # For non-HTTP errors like connection errors, timeouts
                logger.warning(
                    f"Request exception for URL {url} with params {params}: {e_req}. "
                    f"Retrying (attempt {attempt + 1}/{self.retry_attempts})."
                )
                if attempt == self.retry_attempts - 1:
                    logger.error(f"Failed after {self.retry_attempts} attempts for URL {url} with params {params} due to RequestException: {e_req}")
                    raise
        
        # This should not be reached due to the raise in the loop
        raise RuntimeError("Request failed after retries")

    def get_company_data(self, company_url: str) -> Dict:
        """
        Fetch company data from LinkedIn API.
        
        Args:
            company_url (str): LinkedIn URL of the company
            
        Returns:
            Dict: Company data
        """
        logger.info(f"Fetching company data for {company_url}")
        endpoint = "company"
        params = {"link": company_url}
        
        try:
            return self._make_request(endpoint, params)
        except Exception as e:
            logger.error(f"Error fetching company data: {e}")
            raise

    def get_company_employees(self, company_id: str, page: int = 1, page_size: int = 100) -> List[Dict]:
        """
        Fetch employees of a company from LinkedIn API.
        
        Args:
            company_id (str): LinkedIn company ID
            page (int, optional): Page number for pagination
            page_size (int, optional): Number of results per page
            
        Returns:
            List[Dict]: List of employee data
        """
        logger.info(f"Fetching employees for company ID {company_id} (page {page})")
        endpoint = "company_employee"
        params = {
            "companyId": company_id,
            "page": page,
            "pageSize": page_size
        }
        
        try:
            response = self._make_request(endpoint, params)
            return response.get("results", [])
        except Exception as e:
            logger.error(f"Error fetching company employees: {e}")
            return []

    def get_all_company_employees(self, company_id: str) -> List[Dict]:
        """
        Fetch all employees of a company using pagination.
        
        Args:
            company_id (str): LinkedIn company ID
            
        Returns:
            List[Dict]: List of all employee data
        """
        logger.info(f"Fetching all employees for company ID {company_id}")
        all_employees = []
        page = 1
        page_size = 100
        
        while True:
            employees = self.get_company_employees(company_id, page, page_size)
            if not employees:
                break
                
            all_employees.extend(employees)
            logger.info(f"Fetched {len(employees)} employees (total: {len(all_employees)})")
            
            if len(employees) < page_size:
                break
                
            page += 1
            # Add delay to respect rate limits
            time.sleep(1)
        
        return all_employees

    def filter_decision_makers(self, employees: List[Dict]) -> List[Dict]:
        """
        Filter employees to identify decision makers based on job titles.
        
        Args:
            employees (List[Dict]): List of employee data
            
        Returns:
            List[Dict]: List of decision makers
        """
        logger.info(f"Filtering decision makers from {len(employees)} employees")
        decision_maker_titles = [
            "CEO", "Chief", "President", "Director", "VP", "Vice President",
            "Head of", "Manager", "Founder", "Owner", "Partner", "Executive"
        ]
        
        decision_makers = []
        for employee in employees:
            title = employee.get("title", "").lower()
            for decision_title in decision_maker_titles:
                if decision_title.lower() in title:
                    decision_makers.append(employee)
                    break
        
        logger.info(f"Found {len(decision_makers)} decision makers")
        return decision_makers

    def extract_decision_makers(self, company_url: str) -> List[Dict]:
        """
        Extract decision makers from a company.
        
        Args:
            company_url (str): LinkedIn URL of the company
            
        Returns:
            List[Dict]: List of decision makers
        """
        logger.info(f"Extracting decision makers for {company_url}")
        try:
            # Get company data
            company_data = self.get_company_data(company_url)
            company_id = company_data.get("id")
            
            if not company_id:
                logger.error("Company ID not found in company data")
                return []
            
            # Get all employees
            employees = self.get_all_company_employees(company_id)
            
            # Filter decision makers
            decision_makers = self.filter_decision_makers(employees)
            
            return decision_makers
        except Exception as e:
            logger.error(f"Error extracting decision makers: {e}")
            return []

    def save_to_csv(self, decision_makers: List[Dict], output_file: str) -> None:
        """
        Save decision makers to a CSV file.
        
        Args:
            decision_makers (List[Dict]): List of decision makers
            output_file (str): Path to output CSV file
        """
        logger.info(f"Saving {len(decision_makers)} decision makers to {output_file}")
        try:
            df = pd.DataFrame(decision_makers)
            df.to_csv(output_file, index=False)
            logger.info(f"Successfully saved to {output_file}")
        except Exception as e:
            logger.error(f"Error saving to CSV: {e}")
            raise

    def save_to_json(self, decision_makers: List[Dict], output_file: str) -> None:
        """
        Save decision makers to a JSON file.
        
        Args:
            decision_makers (List[Dict]): List of decision makers
            output_file (str): Path to output JSON file
        """
        logger.info(f"Saving {len(decision_makers)} decision makers to {output_file}")
        try:
            with open(output_file, 'w') as f:
                json.dump(decision_makers, f, indent=4)
            logger.info(f"Successfully saved to {output_file}")
        except Exception as e:
            logger.error(f"Error saving to JSON: {e}")
            raise

# Example usage
def main():
    parser = argparse.ArgumentParser(description="Extract decision makers from a LinkedIn company URL.")
    parser.add_argument("company_url", type=str, help="The LinkedIn URL of the company.")
    parser.add_argument(
        "--output_prefix", 
        type=str, 
        default="decision_makers", 
        help="Prefix for the output CSV and JSON files. Timestamp will be appended. (default: decision_makers)"
    )
    
    args = parser.parse_args()
    
    api_key = os.getenv("LINKEDIN_API_KEY")
    if not api_key:
        logger.error("LINKEDIN_API_KEY environment variable not set.")
        # Also print to console for immediate user feedback if logs are not monitored
        print("Error: LINKEDIN_API_KEY environment variable not set. Please set it before running the script.")
        return

    extractor = LinkedInDecisionMakerExtractor(api_key)
    
    logger.info(f"Processing company URL: {args.company_url}")
    decision_makers = extractor.extract_decision_makers(args.company_url)
    
    if decision_makers:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        csv_file = f"{args.output_prefix}_{timestamp}.csv"
        json_file = f"{args.output_prefix}_{timestamp}.json"
        
        extractor.save_to_csv(decision_makers, csv_file)
        extractor.save_to_json(decision_makers, json_file)
        logger.info(f"Processing complete. Results saved to {csv_file} and {json_file}")
    else:
        logger.info("No decision makers found or an error occurred during extraction.")

if __name__ == "__main__":
    main()