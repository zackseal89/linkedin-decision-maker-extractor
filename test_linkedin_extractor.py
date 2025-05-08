import unittest
from unittest.mock import patch, MagicMock
import json
import os
from linkedin_decision_maker_extractor import LinkedInDecisionMakerExtractor, logger
import requests # Added for requests.exceptions
import logging # Added for logger manipulation in tests

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


    @patch('linkedin_decision_maker_extractor.LinkedInDecisionMakerExtractor')
    @patch('linkedin_decision_maker_extractor.argparse.ArgumentParser.parse_args')
    @patch('linkedin_decision_maker_extractor.os.getenv')
    @patch('linkedin_decision_maker_extractor.datetime')
    def test_main_success(self, mock_datetime, mock_getenv, mock_parse_args, MockExtractor):
        """Test main function successful execution."""
        # Mock args
        mock_args = MagicMock()
        mock_args.company_url = "http://linkedin.com/company/test"
        mock_args.output_prefix = "test_output"
        mock_parse_args.return_value = mock_args
        
        # Mock API key
        mock_getenv.return_value = "fake_api_key"
        
        # Mock datetime
        mock_now = MagicMock()
        mock_now.strftime.return_value = "20230101_120000"
        mock_datetime.now.return_value = mock_now
        
        # Mock extractor instance and its methods
        mock_extractor_instance = MockExtractor.return_value
        mock_extractor_instance.extract_decision_makers.return_value = [{"name": "Test User"}]
        
        # Capture print calls
        with patch('builtins.print') as mock_print:
            # Suppress logger output to console for this test to avoid clutter
            # and focus on what main() itself prints or logs to file.
            # We are primarily testing the flow and file operations here.
            original_handlers = logger.handlers
            logger.handlers = [h for h in original_handlers if not isinstance(h, logging.StreamHandler)]
            try:
                from linkedin_decision_maker_extractor import main as extractor_main
                extractor_main()
            finally:
                logger.handlers = original_handlers # Restore original handlers

        mock_getenv.assert_called_once_with("LINKEDIN_API_KEY")
        MockExtractor.assert_called_once_with("fake_api_key")
        mock_extractor_instance.extract_decision_makers.assert_called_once_with("http://linkedin.com/company/test")
        mock_extractor_instance.save_to_csv.assert_called_once_with([{"name": "Test User"}], "test_output_20230101_120000.csv")
        mock_extractor_instance.save_to_json.assert_called_once_with([{"name": "Test User"}], "test_output_20230101_120000.json")

    @patch('linkedin_decision_maker_extractor.argparse.ArgumentParser.parse_args')
    @patch('linkedin_decision_maker_extractor.os.getenv')
    @patch('builtins.print') # To capture print output
    def test_main_no_api_key(self, mock_print, mock_getenv, mock_parse_args):
        """Test main function when LINKEDIN_API_KEY is not set."""
        mock_args = MagicMock()
        mock_args.company_url = "http://linkedin.com/company/test"
        mock_parse_args.return_value = mock_args
        
        mock_getenv.return_value = None # Simulate missing API key
        
        from linkedin_decision_maker_extractor import main as extractor_main
        with self.assertLogs(logger, level='ERROR') as cm:
            extractor_main()
        
        mock_getenv.assert_called_once_with("LINKEDIN_API_KEY")
        mock_print.assert_called_with("Error: LINKEDIN_API_KEY environment variable not set. Please set it before running the script.")
        self.assertTrue(any("LINKEDIN_API_KEY environment variable not set" in msg for msg in cm.output))

if __name__ == '__main__':
    unittest.main()