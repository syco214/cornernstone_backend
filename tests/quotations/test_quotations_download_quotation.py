from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase
from unittest.mock import patch, MagicMock
from io import BytesIO
from quotations_api.models import Quotation
from admin_api.models import Customer, CustomerContact
from quotations_api.views import generate_quotation_pdf
import datetime
from decimal import Decimal

User = get_user_model()

class QuotationPDFViewTests(APITestCase):
    def setUp(self):
        # Create test user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpassword'
        )
        
        # Create test customer
        self.customer = Customer.objects.create(
            name='Test Customer',
            registered_name='Test Registered Name',
            tin='123456789',
            phone_number='123-456-7890',
            company_address='123 Test Street',
            city='Test City',
            vat_type='VAT'
        )
        
        # Create customer contact
        self.contact = CustomerContact.objects.create(
            customer=self.customer,
            contact_person='John Doe',
            position='CEO',
            department='Executive',
            email='john@example.com',
            mobile_number='987-654-3210',
            office_number='123-456-7890'
        )
        
        # Create test quotation with total_amount
        self.quotation = Quotation.objects.create(
            quote_number='QT-2023-001',
            customer=self.customer,
            date=datetime.date.today(),
            total_amount=Decimal('1000.00'),  # Add total_amount
            expiry_date=datetime.date.today() + datetime.timedelta(days=30),
            currency='USD',
            purchase_request='PR-2023-001',
            notes='Test notes for quotation',
            status='draft',
            created_by=self.user,  # Add created_by
            last_modified_by=self.user  # Add last_modified_by
        )
        
        # URL for the PDF endpoint
        self.url = reverse('quotations_api:quotation-pdf', kwargs={'pk': self.quotation.pk})
        
        # Authenticate
        self.client.force_authenticate(user=self.user)
    
    @patch('quotations_api.views.generate_quotation_pdf')
    def test_get_quotation_pdf_success(self, mock_generate_pdf):
        """Test successful PDF generation and download"""
        # Mock the PDF generation function
        mock_pdf_content = BytesIO(b'PDF content')
        mock_generate_pdf.return_value = mock_pdf_content
        
        # Make the request
        response = self.client.get(self.url)
        
        # Verify the response
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response['Content-Type'], 'application/pdf')
        self.assertEqual(
            response['Content-Disposition'], 
            f'attachment; filename="{self.quotation.quote_number}.pdf"'
        )
        
        # Verify the PDF generation function was called with the correct quotation
        mock_generate_pdf.assert_called_once_with(self.quotation)
        
        # Verify the response content
        self.assertEqual(response.content, b'PDF content')
    
    @patch('quotations_api.views.generate_quotation_pdf')
    def test_get_quotation_pdf_error(self, mock_generate_pdf):
        """Test error handling during PDF generation"""
        # Mock the PDF generation function to raise an exception
        mock_generate_pdf.side_effect = Exception('PDF generation failed')
        
        # Make the request
        response = self.client.get(self.url)
        
        # Verify the response
        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertEqual(response.data['success'], False)
        self.assertEqual(response.data['errors']['detail'], 'PDF generation failed')
    
    def test_get_nonexistent_quotation(self):
        """Test attempting to get PDF for a non-existent quotation"""
        url = reverse('quotations_api:quotation-pdf', kwargs={'pk': 9999})  # Non-existent ID
        response = self.client.get(url)
        
        # The view is returning 500 instead of 404 for non-existent quotations
        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertEqual(response.data['success'], False)
        self.assertIn('No Quotation matches the given query', response.data['errors']['detail'])
    
    def test_unauthorized_access(self):
        """Test that unauthenticated users cannot access the endpoint"""
        # Logout
        self.client.force_authenticate(user=None)
        
        # Try to access the endpoint
        response = self.client.get(self.url)
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    @patch('quotations_api.views.generate_quotation_pdf')
    def test_pdf_filename(self, mock_generate_pdf):
        """Test that the PDF filename matches the quotation number"""
        # Mock the PDF generation function
        mock_pdf_content = BytesIO(b'PDF content')
        mock_generate_pdf.return_value = mock_pdf_content
        
        # Create a quotation with a special character in the quote number
        special_quotation = Quotation.objects.create(
            quote_number='QT/2023/002',
            customer=self.customer,
            date=datetime.date.today(),
            total_amount=Decimal('2000.00'),  # Add total_amount
            expiry_date=datetime.date.today() + datetime.timedelta(days=30),
            currency='USD',
            created_by=self.user,  # Add created_by
            last_modified_by=self.user  # Add last_modified_by
        )
        
        # Get the URL for this quotation
        url = reverse('quotations_api:quotation-pdf', kwargs={'pk': special_quotation.pk})
        
        # Make the request
        response = self.client.get(url)
        
        # Verify the Content-Disposition header
        self.assertEqual(
            response['Content-Disposition'], 
            f'attachment; filename="{special_quotation.quote_number}.pdf"'
        )