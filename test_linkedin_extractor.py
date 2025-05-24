import unittest
from unittest.mock import patch, MagicMock
import json
import os
from linkedin_decision_maker_extractor import LinkedInDecisionMakerExtractor, logger
import requests # Added for requests.exceptions
import logging # Added for logger manipulation in tests
import sys # For mocking sys.exit and checking CLI behavior
import argparse # For creating mock args Namespace

class TestLinkedInDecisionMakerExtractor(unittest.TestCase):
    
    def setUp(self):
        """Set up test fixtures before each test method."""
        self.api_key = "test_api_key"
        self.extractor = LinkedInDecisionMakerExtractor(self.api_key)
        
        # Sample test data
        self.sample_company_data = {
            "id": "12345",
            "name": "Test Company",
            "website": "https://www.testcompany.com"
        }
        
        self.sample_employees = [
            {"id": "e1", "firstName": "John", "lastName": "Doe", "title": "CEO"},
            {"id": "e2", "firstName": "Jane", "lastName": "Smith", "title": "CTO"},
            {"id": "e3", "firstName": "Bob", "lastName": "Johnson", "title": "Software Engineer"},
            {"id": "e4", "firstName": "Alice", "lastName": "Williams", "title": "Director of Marketing"},
            {"id": "e5", "firstName": "Charlie", "lastName": "Brown", "title": "Sales Representative"}
        ]
    
    @patch('requests.get')
    def test_get_company_data(self, mock_get):
        """Test fetching company data."""
        # Configure the mock
        mock_response = MagicMock()
        mock_response.json.return_value = self.sample_company_data
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        # Call the method
        result = self.extractor.get_company_data("https://www.linkedin.com/company/test-company/")
        
        # Assertions
        self.assertEqual(result, self.sample_company_data)
        mock_get.assert_called_once()
    
    @patch('requests.get')
    def test_get_company_employees(self, mock_get):
        """Test fetching company employees."""
        # Configure the mock
        mock_response = MagicMock()
        mock_response.json.return_value = {"results": self.sample_employees}
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        # Call the method
        result = self.extractor.get_company_employees("12345")
        
        # Assertions
        self.assertEqual(result, self.sample_employees)
        mock_get.assert_called_once()
    
    def test_filter_decision_makers(self):
        """Test filtering decision makers based on job titles."""
        # Call the method
        result = self.extractor.filter_decision_makers(self.sample_employees)
        
        # Expected decision makers (CEO, CTO, Director)
        expected = [
            {"id": "e1", "firstName": "John", "lastName": "Doe", "title": "CEO"},
            {"id": "e2", "firstName": "Jane", "lastName": "Smith", "title": "CTO"},
            {"id": "e4", "firstName": "Alice", "lastName": "Williams", "title": "Director of Marketing"}
        ]
        
        # Assertions
        self.assertEqual(len(result), 3)
        self.assertEqual(result, expected)
    
    @patch.object(LinkedInDecisionMakerExtractor, 'get_company_data')
    @patch.object(LinkedInDecisionMakerExtractor, 'get_all_company_employees')
    def test_extract_decision_makers(self, mock_get_all_employees, mock_get_company_data):
        """Test the full extraction process."""
        # Configure the mocks
        mock_get_company_data.return_value = self.sample_company_data
        mock_get_all_employees.return_value = self.sample_employees
        
        # Call the method
        result = self.extractor.extract_decision_makers("https://www.linkedin.com/company/test-company/")
        
        # Expected decision makers
        expected = [
            {"id": "e1", "firstName": "John", "lastName": "Doe", "title": "CEO"},
            {"id": "e2", "firstName": "Jane", "lastName": "Smith", "title": "CTO"},
            {"id": "e4", "firstName": "Alice", "lastName": "Williams", "title": "Director of Marketing"}
        ]
        
        # Assertions
        self.assertEqual(len(result), 3)
        self.assertEqual(result, expected)
        mock_get_company_data.assert_called_once()
        mock_get_all_employees.assert_called_once()

    @patch('time.sleep') # Mock time.sleep for retry delays
    @patch('requests.get')
    def test_make_request_http_error_retry_and_fail(self, mock_get, mock_sleep):
        """Test _make_request handles HTTP errors, retries, and eventually fails."""
        # Configure mock_get to raise HTTPError
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
            response=MagicMock(status_code=500, text="Server Error")
        )
        mock_get.return_value = mock_response

        with self.assertLogs(logger, level='ERROR') as cm_error,
             self.assertLogs(logger, level='WARNING') as cm_warning:
            with self.assertRaises(requests.exceptions.HTTPError):
                self.extractor._make_request("test_endpoint")
        
        self.assertEqual(mock_get.call_count, self.extractor.retry_attempts)
        self.assertEqual(mock_sleep.call_count, self.extractor.retry_attempts - 1)
        # Check for specific log messages
        self.assertTrue(any(f"HTTP error 500. URL: {self.extractor.base_url}/test_endpoint" in msg for msg in cm_warning.output))
        self.assertTrue(any(f"Failed after {self.extractor.retry_attempts} attempts" in msg for msg in cm_error.output))

    @patch('time.sleep')
    @patch('requests.get')
    def test_make_request_rate_limit_retry_and_fail(self, mock_get, mock_sleep):
        """Test _make_request handles 429 rate limit errors, retries, and eventually fails."""
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
            response=MagicMock(status_code=429, text="Rate Limit Exceeded")
        )
        mock_get.return_value = mock_response

        with self.assertLogs(logger, level='ERROR') as cm_error,
             self.assertLogs(logger, level='WARNING') as cm_warning:
            with self.assertRaises(requests.exceptions.HTTPError):
                self.extractor._make_request("test_rate_limit_endpoint")

        self.assertEqual(mock_get.call_count, self.extractor.retry_attempts)
        self.assertEqual(mock_sleep.call_count, self.extractor.retry_attempts - 1)
        self.assertTrue(any(f"Rate limit hit (429). URL: {self.extractor.base_url}/test_rate_limit_endpoint" in msg for msg in cm_warning.output))
        self.assertTrue(any(f"Failed after {self.extractor.retry_attempts} attempts" in msg for msg in cm_error.output))

    @patch('time.sleep')
    @patch('requests.get')
    def test_make_request_request_exception_retry_and_fail(self, mock_get, mock_sleep):
        """Test _make_request handles general RequestExceptions, retries, and eventually fails."""
        mock_get.side_effect = requests.exceptions.ConnectionError("Connection failed")

        with self.assertLogs(logger, level='ERROR') as cm_error,
             self.assertLogs(logger, level='WARNING') as cm_warning:
            with self.assertRaises(requests.exceptions.ConnectionError):
                self.extractor._make_request("test_conn_error_endpoint")

        self.assertEqual(mock_get.call_count, self.extractor.retry_attempts)
        self.assertEqual(mock_sleep.call_count, self.extractor.retry_attempts - 1)
        self.assertTrue(any(f"Request exception for URL: {self.extractor.base_url}/test_conn_error_endpoint" in msg for msg in cm_warning.output))
        self.assertTrue(any(f"Failed after {self.extractor.retry_attempts} attempts" in msg for msg in cm_error.output))

    @patch('requests.get')
    def test_make_request_success_first_attempt(self, mock_get):
        """Test _make_request succeeds on the first attempt."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"data": "success"}
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        result = self.extractor._make_request("test_success_endpoint")
        self.assertEqual(result, {"data": "success"})
        mock_get.assert_called_once()

    def test_initialization(self):
        """Test that the extractor initializes correctly."""
        self.assertEqual(self.extractor.api_key, self.api_key)
        self.assertEqual(self.extractor.base_url, "https://api.linkedin.com/v2")
        self.assertEqual(self.extractor.retry_attempts, 3)
        # Test default retry_delay, though not strictly required by prompt, it's good practice
        self.assertEqual(self.extractor.retry_delay, 2)

    def test_save_to_csv(self):
        """Test saving data to CSV."""
        # Test data
        decision_makers = [
            {"id": "e1", "firstName": "John", "lastName": "Doe", "title": "CEO"},
            {"id": "e2", "firstName": "Jane", "lastName": "Smith", "title": "CTO"}
        ]
        test_file = "test_output.csv"
        
        try:
            # Call the method
            self.extractor.save_to_csv(decision_makers, test_file)
            
            # Assert file exists
            self.assertTrue(os.path.exists(test_file))
            
        finally:
            # Clean up
            if os.path.exists(test_file):
                os.remove(test_file)
    
    def test_save_to_json(self):
        """Test saving data to JSON."""
        # Test data
        decision_makers = [
            {"id": "e1", "firstName": "John", "lastName": "Doe", "title": "CEO"},
            {"id": "e2", "firstName": "Jane", "lastName": "Smith", "title": "CTO"}
        ]
        test_file = "test_output.json"
        
        try:
            # Call the method
            self.extractor.save_to_json(decision_makers, test_file)
            
            # Assert file exists
            self.assertTrue(os.path.exists(test_file))
            
            # Verify content
            with open(test_file, 'r') as f:
                loaded_data = json.load(f)
                self.assertEqual(loaded_data, decision_makers)
            
        finally:
            # Clean up
            if os.path.exists(test_file):
                os.remove(test_file)


# Now, we define the TestCLI class with all its methods
class TestCLI(unittest.TestCase):
    @patch('cli.argparse.ArgumentParser')
    @patch('cli.LinkedInDecisionMakerExtractor')
    @patch('cli.os.getenv')
    @patch('cli.datetime')
    @patch('builtins.print')
    @patch('cli.sys.exit') # Patch sys.exit in the context of cli.py
    def setUp(self, mock_sys_exit, mock_print, mock_datetime, mock_getenv, MockExtractor, MockArgumentParser):
        self.mock_sys_exit = mock_sys_exit
        self.mock_print = mock_print
        self.mock_datetime = mock_datetime
        self.mock_getenv = mock_getenv
        self.MockExtractor = MockExtractor
        self.mock_arg_parser = MockArgumentParser.return_value
        self.mock_extractor_instance = self.MockExtractor.return_value

        # Default behavior for mocks
        self.mock_getenv.return_value = "env_api_key" # Default API key from environment
        self.mock_extractor_instance.extract_decision_makers.return_value = [{"name": "Test User"}]
        
        # Mock datetime
        mock_now = MagicMock()
        mock_now.strftime.return_value = "20230101_120000"
        self.mock_datetime.now.return_value = mock_now
        
        # Default parsed args
        self.default_args = argparse.Namespace(
            company="http://linkedin.com/company/test",
            output="decision_makers",
            format="both",
            api_key=None # Default, rely on env var
        )
        self.mock_arg_parser.parse_args.return_value = self.default_args

        # Import cli.main here, after mocks are set up, to ensure it uses mocked components
        # We need to reload it if it was imported before, or ensure it's imported for the first time here.
        # For simplicity, we assume it's being imported effectively for tests here.
        # If cli.py was already imported, we might need importlib.reload
        global main_cli
        import cli as main_cli_module
        main_cli = main_cli_module.main


    def test_cli_success_csv_output(self):
        """Test CLI successful run with CSV output."""
        self.default_args.format = "csv"
        self.mock_arg_parser.parse_args.return_value = self.default_args
        
        main_cli()
        
        self.MockExtractor.assert_called_once_with(api_key="env_api_key")
        self.mock_extractor_instance.extract_decision_makers.assert_called_once_with("http://linkedin.com/company/test")
        self.mock_extractor_instance.save_to_csv.assert_called_once_with(
            [{"name": "Test User"}], "decision_makers_20230101_120000.csv"
        )
        self.mock_extractor_instance.save_to_json.assert_not_called()
        self.mock_print.assert_any_call("Processing complete. Results saved.")

    def test_cli_success_json_output(self):
        """Test CLI successful run with JSON output."""
        self.default_args.format = "json"
        self.mock_arg_parser.parse_args.return_value = self.default_args

        main_cli()

        self.MockExtractor.assert_called_once_with(api_key="env_api_key")
        self.mock_extractor_instance.extract_decision_makers.assert_called_once_with("http://linkedin.com/company/test")
        self.mock_extractor_instance.save_to_json.assert_called_once_with(
            [{"name": "Test User"}], "decision_makers_20230101_120000.json"
        )
        self.mock_extractor_instance.save_to_csv.assert_not_called()
        self.mock_print.assert_any_call("Processing complete. Results saved.")

    def test_cli_success_both_outputs(self):
        """Test CLI successful run with both CSV and JSON outputs."""
        # Default args already set to 'both'
        main_cli()

        self.MockExtractor.assert_called_once_with(api_key="env_api_key")
        self.mock_extractor_instance.extract_decision_makers.assert_called_once_with("http://linkedin.com/company/test")
        self.mock_extractor_instance.save_to_csv.assert_called_once_with(
            [{"name": "Test User"}], "decision_makers_20230101_120000.csv"
        )
        self.mock_extractor_instance.save_to_json.assert_called_once_with(
            [{"name": "Test User"}], "decision_makers_20230101_120000.json"
        )
        self.mock_print.assert_any_call("Processing complete. Results saved.")

    def test_cli_api_key_from_command_line(self):
        """Test API key provided via command line argument."""
        self.default_args.api_key = "cli_api_key"
        self.mock_arg_parser.parse_args.return_value = self.default_args
        
        main_cli()
        
        self.MockExtractor.assert_called_once_with(api_key="cli_api_key")
        self.mock_getenv.assert_not_called() # Should not try to get from env if provided in CLI

    def test_cli_api_key_from_environment(self):
        """Test API key fetched from environment variable."""
        # self.default_args.api_key is None by default in setUp
        self.mock_getenv.return_value = "env_api_key_specific_test" # Use a distinct value for this test
        
        main_cli()
        
        self.MockExtractor.assert_called_once_with(api_key="env_api_key_specific_test")
        self.mock_getenv.assert_called_once_with("LINKEDIN_API_KEY")

    def test_cli_no_api_key_provided(self):
        """Test scenario where no API key is available (CLI or environment)."""
        self.default_args.api_key = None
        self.mock_arg_parser.parse_args.return_value = self.default_args
        self.mock_getenv.return_value = None # No environment API key

        main_cli()
        
        self.mock_print.assert_any_call("Error: LinkedIn API key not provided. Set LINKEDIN_API_KEY or use --api-key.")
        self.mock_sys_exit.assert_called_once_with(1)

    def test_cli_no_decision_makers_found(self):
        """Test scenario where no decision makers are found."""
        self.mock_extractor_instance.extract_decision_makers.return_value = [] # Simulate no decision makers

        main_cli()
        
        self.mock_print.assert_any_call("No decision makers found or an error occurred during extraction.")
        self.mock_extractor_instance.save_to_csv.assert_not_called()
        self.mock_extractor_instance.save_to_json.assert_not_called()
        # Depending on desired behavior, sys.exit might be called or not.
        # If it should exit gracefully (e.g. sys.exit(0)), then:
        # self.mock_sys_exit.assert_called_once_with(0) 
        # If it just prints and finishes, no sys.exit call is expected beyond what might be at the very end of main.
        # For this test, let's assume it prints and exits normally (implicitly exit 0 if no error).

    def test_cli_missing_company_argument(self):
        """Test CLI behavior when --company argument is missing."""
        # We need to simulate argparse raising an error.
        # This usually happens if parse_args is called with arguments that cause it to exit.
        # We can mock parse_args to raise SystemExit like argparse does,
        # or check if parser.error (which prints message and exits) is called.
        
        # Scenario 1: Mocking parse_args to simulate its error behavior (e.g., SystemExit)
        # This requires careful handling if cli.py catches SystemExit.
        # For this test, we'll assume that if required args are missing,
        # ArgumentParser.error is called, which in turn calls sys.exit.
        # We've already patched sys.exit. Let's patch parser.error.
        self.mock_arg_parser.error = MagicMock()
        
        # To trigger the error, cli.main() would normally call parser.parse_args().
        # If parse_args itself is the one raising an error for missing arguments BEFORE cli.py's main logic,
        # we'd need to test that.
        # However, cli.py structure is:
        #   parser = create_parser()
        #   args = parser.parse_args() <-- Error happens here
        #   main_logic(args)
        # Our current mock setup for parse_args returns default_args.
        # To test missing --company, we need to simulate it *before* main_cli() is called with parsed args.
        # This test is more about the ArgumentParser configuration itself.
        
        # Let's adjust the approach:
        # We will test the parser creation and then simulate calling parse_args with missing company.
        # This means we need to get the actual parser from cli.py or reconstruct its behavior.
        
        # For simplicity in this context, let's assume the `main_cli` function
        # is called and *then* it tries to access a non-existent company attribute,
        # or that the `parse_args` mock is configured to simulate this.
        # A more direct way would be to test `create_parser` from `cli.py` if it exists,
        # or to invoke `cli.py` as a subprocess.
        
        # Given the current patching, we'll simulate parse_args raising an error.
        # This means the call to main_cli() might not even happen or complete.
        self.mock_arg_parser.parse_args.side_effect = SystemExit(2) # Typical exit code for argparse errors

        with self.assertRaises(SystemExit):
             main_cli() # This call will lead to parse_args being called

        # We expect sys.exit to be called by argparse's error handling.
        # The main_cli function itself might not reach the point of calling sys.exit.
        # This assertion depends on how ArgumentParser internally calls sys.exit.
        # Our @patch('cli.sys.exit') should catch this.
        self.mock_sys_exit.assert_called_with(2)
        # We could also check if print was called with an error message by argparse,
        # but that's usually to stderr, and our mock_print is for stdout.
        # A more robust test would involve capturing stderr.


if __name__ == '__main__':
    unittest.main()