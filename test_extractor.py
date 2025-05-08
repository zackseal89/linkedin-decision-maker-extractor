import unittest
from unittest.mock import patch, MagicMock
from linkedin_decision_maker_extractor import LinkedInDecisionMakerExtractor

class TestLinkedInDecisionMakerExtractor(unittest.TestCase):
    def setUp(self):
        self.api_key = "test_api_key"
        self.extractor = LinkedInDecisionMakerExtractor(self.api_key)
        
    def test_initialization(self):
        """Test that the extractor initializes correctly."""
        self.assertEqual(self.extractor.api_key, self.api_key)
        self.assertEqual(self.extractor.base_url, "https://api.linkedin.com/v2")
        self.assertEqual(self.extractor.retry_attempts, 3)
        
    @patch('requests.get')
    def test_get_company_data(self, mock_get):
        """Test fetching company data."""
        # Mock response
        mock_response = MagicMock()
        mock_response.json.return_value = {"id": "123456", "name": "Test Company"}
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        # Call the method
        company_url = "https://www.linkedin.com/company/test-company/"
        result = self.extractor.get_company_data(company_url)
        
        # Assertions
        mock_get.assert_called_once()
        self.assertEqual(result, {"id": "123456", "name": "Test Company"})
        
    @patch('requests.get')
    def test_get_company_employees(self, mock_get):
        """Test fetching company employees."""
        # Mock response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "results": [
                {"id": "emp1", "name": "John Doe", "title": "CEO"},
                {"id": "emp2", "name": "Jane Smith", "title": "CTO"}
            ]
        }
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        # Call the method
        company_id = "123456"
        result = self.extractor.get_company_employees(company_id)
        
        # Assertions
        mock_get.assert_called_once()
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["name"], "John Doe")
        
    def test_filter_decision_makers(self):
        """Test filtering decision makers based on job titles."""
        employees = [
            {"id": "emp1", "name": "John Doe", "title": "CEO"},
            {"id": "emp2", "name": "Jane Smith", "title": "CTO"},
            {"id": "emp3", "name": "Bob Johnson", "title": "Software Engineer"},
            {"id": "emp4", "name": "Alice Brown", "title": "Head of Marketing"},
            {"id": "emp5", "name": "Charlie Wilson", "title": "Intern"}
        ]
        
        result = self.extractor.filter_decision_makers(employees)
        
        # Should find 3 decision makers: CEO, CTO, and Head of Marketing
        self.assertEqual(len(result), 3)
        titles = [emp["title"] for emp in result]
        self.assertIn("CEO", titles)
        self.assertIn("CTO", titles)
        self.assertIn("Head of Marketing", titles)
        
    @patch.object(LinkedInDecisionMakerExtractor, 'get_company_data')
    @patch.object(LinkedInDecisionMakerExtractor, 'get_all_company_employees')
    @patch.object(LinkedInDecisionMakerExtractor, 'filter_decision_makers')
    def test_extract_decision_makers(self, mock_filter, mock_get_employees, mock_get_company):
        """Test the full extraction process."""
        # Mock responses
        mock_get_company.return_value = {"id": "123456", "name": "Test Company"}
        
        employees = [
            {"id": "emp1", "name": "John Doe", "title": "CEO"},
            {"id": "emp2", "name": "Jane Smith", "title": "CTO"},
            {"id": "emp3", "name": "Bob Johnson", "title": "Software Engineer"}
        ]
        mock_get_employees.return_value = employees
        
        decision_makers = [
            {"id": "emp1", "name": "John Doe", "title": "CEO"},
            {"id": "emp2", "name": "Jane Smith", "title": "CTO"}
        ]
        mock_filter.return_value = decision_makers
        
        # Call the method
        company_url = "https://www.linkedin.com/company/test-company/"
        result = self.extractor.extract_decision_makers(company_url)
        
        # Assertions
        mock_get_company.assert_called_once_with(company_url)
        mock_get_employees.assert_called_once_with("123456")
        mock_filter.assert_called_once_with(employees)
        self.assertEqual(result, decision_makers)

if __name__ == '__main__':
    unittest.main()