from decimal import Decimal
from unittest.mock import patch, Mock
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
from rest_framework.test import APIClient
from rest_framework import status
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken
import requests

from admin_api.models import ExchangeRate

User = get_user_model()


class ExchangeRateViewTests(TestCase):
    """Test cases for ExchangeRateView"""
    
    def setUp(self):
        """Set up test data and client"""
        self.client = APIClient()
        self.url = reverse('admin_api:exchange-rates')
        
        # Create test user and authenticate
        self.user = User.objects.create_user(
            username='testuser',
            email='testuser@example.com',
            password='testpass123',
            first_name='Test',
            last_name='User',
            role='admin',
            user_access=['admin']
        )
        
        # Authenticate with JWT token
        self.token = RefreshToken.for_user(self.user).access_token
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token}')
        
        # Clear any existing exchange rates
        ExchangeRate.objects.all().delete()
    
    @patch('admin_api.views.requests.get')
    def test_get_fresh_rates_success(self, mock_get):
        """Test successful fetching of fresh exchange rates from API"""
        # Set up mock responses
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.raise_for_status = Mock()
        mock_response.json.return_value = {
            'rates': {
                'PHP': '60.123456',
                'USD': '1.234567',
                'CNY': '7.654321'
            }
        }
        mock_get.return_value = mock_response
        
        response = self.client.get(self.url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        
        self.assertTrue(data['success'])
        self.assertEqual(data['data']['base_currency'], 'PHP')
        self.assertTrue(data['data']['api_called'])
        
        # Check that all currencies are present
        rates = data['data']['rates']
        self.assertIn('USD', rates)
        self.assertIn('EUR', rates)
        self.assertIn('CNY', rates)
        
        # All should be from API
        for currency in ['USD', 'EUR', 'CNY']:
            self.assertEqual(rates[currency]['source'], 'api')
        
        # Verify rates were saved to database
        self.assertEqual(ExchangeRate.objects.count(), 3)
    
    def test_get_cached_rates_not_stale(self):
        """Test using cached rates when they are not stale (less than 6 hours old)"""
        # Create recent cached rates (explicitly set updated_at to be recent)
        recent_time = timezone.now() - timedelta(hours=2)  # 2 hours ago, definitely not stale
        
        for currency, rate in [('USD', '55.123456'), ('EUR', '62.789012'), ('CNY', '8.456789')]:
            rate_obj = ExchangeRate.objects.create(
                currency=currency,
                rate=Decimal(rate)
            )
            # Manually update the updated_at field to bypass auto_now
            ExchangeRate.objects.filter(id=rate_obj.id).update(updated_at=recent_time)
        
        response = self.client.get(self.url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        
        self.assertTrue(data['success'])
        self.assertFalse(data['data']['api_called'])  # Should not call API
        
        # Verify cached rates are returned
        rates = data['data']['rates']
        self.assertEqual(rates['USD']['rate'], 55.123456)
        self.assertEqual(rates['USD']['source'], 'cached')
        self.assertEqual(rates['EUR']['rate'], 62.789012)
        self.assertEqual(rates['EUR']['source'], 'cached')
        self.assertEqual(rates['CNY']['rate'], 8.456789)
        self.assertEqual(rates['CNY']['source'], 'cached')
    
    @patch('admin_api.views.requests.get')
    def test_get_stale_rates_refresh_from_api(self, mock_get):
        """Test refreshing stale rates (older than 6 hours) from API"""
        # Create stale cached rates (more than 6 hours old)
        stale_time = timezone.now() - timedelta(hours=8)  # 8 hours ago, definitely stale
        
        for currency in ['USD', 'EUR', 'CNY']:
            rate_obj = ExchangeRate.objects.create(
                currency=currency,
                rate=Decimal('50.000000')
            )
            # Manually update the updated_at field to make it stale
            ExchangeRate.objects.filter(id=rate_obj.id).update(updated_at=stale_time)
        
        # Mock successful API response with different rates
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.raise_for_status = Mock()
        mock_response.json.return_value = {
            'rates': {
                'PHP': '65.123456',
                'USD': '1.5',
                'CNY': '8.0'
            }
        }
        mock_get.return_value = mock_response
        
        response = self.client.get(self.url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        
        self.assertTrue(data['success'])
        self.assertTrue(data['data']['api_called'])
        
        # Verify fresh rates were fetched
        rates = data['data']['rates']
        for currency in ['USD', 'EUR', 'CNY']:
            self.assertEqual(rates[currency]['source'], 'api')
            self.assertNotEqual(rates[currency]['rate'], 50.0)
    
    @patch('admin_api.views.requests.get')
    def test_api_failure_with_cached_fallback(self, mock_get):
        """Test using cached data as fallback when API fails"""
        # Create stale cached rates (will trigger API call)
        stale_time = timezone.now() - timedelta(hours=8)
        
        for currency, rate in [('USD', '55.123456'), ('EUR', '60.123456'), ('CNY', '8.456789')]:
            rate_obj = ExchangeRate.objects.create(
                currency=currency,
                rate=Decimal(rate)
            )
            # Make them stale so API will be called
            ExchangeRate.objects.filter(id=rate_obj.id).update(updated_at=stale_time)
        
        # Mock API failure
        mock_get.side_effect = requests.exceptions.RequestException("API connection failed")
        
        response = self.client.get(self.url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        
        self.assertTrue(data['success'])
        
        # Should use cached fallback for all currencies
        rates = data['data']['rates']
        self.assertEqual(rates['USD']['source'], 'cached_fallback')
        self.assertEqual(rates['EUR']['source'], 'cached_fallback')
        self.assertEqual(rates['CNY']['source'], 'cached_fallback')
    
    @patch('admin_api.views.requests.get')
    def test_api_failure_no_cached_data(self, mock_get):
        """Test error response when API fails and no cached data exists"""
        # Mock API failure
        mock_get.side_effect = requests.exceptions.RequestException("API connection failed")
        
        response = self.client.get(self.url)
        
        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        data = response.json()
        
        self.assertFalse(data['success'])
        self.assertIn('errors', data)
        self.assertIn('Failed to fetch USD rate and no cached data available', data['errors']['detail'])
    
    @patch('admin_api.views.requests.get')
    def test_invalid_api_response_structure(self, mock_get):
        """Test handling of invalid API response structure"""
        # Create stale cached rates (will trigger API call)
        stale_time = timezone.now() - timedelta(hours=8)
        
        for currency, rate in [('USD', '55.123456'), ('EUR', '60.123456'), ('CNY', '8.456789')]:
            rate_obj = ExchangeRate.objects.create(
                currency=currency,
                rate=Decimal(rate)
            )
            ExchangeRate.objects.filter(id=rate_obj.id).update(updated_at=stale_time)
        
        # Mock invalid API response (missing 'rates' key)
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.raise_for_status = Mock()
        mock_response.json.return_value = {'invalid': 'structure'}
        mock_get.return_value = mock_response
        
        response = self.client.get(self.url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        
        # Should fallback to cached data
        rates = data['data']['rates']
        self.assertEqual(rates['USD']['source'], 'cached_fallback')
        self.assertEqual(rates['EUR']['source'], 'cached_fallback')
        self.assertEqual(rates['CNY']['source'], 'cached_fallback')
    
    @patch('admin_api.views.requests.get')
    def test_mixed_cached_and_fresh_rates(self, mock_get):
        """Test scenario with mix of cached and fresh rates"""
        # Create fresh cached rate for USD only
        fresh_time = timezone.now() - timedelta(hours=2)
        usd_obj = ExchangeRate.objects.create(currency='USD', rate=Decimal('55.123456'))
        ExchangeRate.objects.filter(id=usd_obj.id).update(updated_at=fresh_time)
        
        # Create stale rates for EUR and CNY
        stale_time = timezone.now() - timedelta(hours=8)
        for currency, rate in [('EUR', '60.123456'), ('CNY', '8.456789')]:
            rate_obj = ExchangeRate.objects.create(currency=currency, rate=Decimal(rate))
            ExchangeRate.objects.filter(id=rate_obj.id).update(updated_at=stale_time)
        
        # Mock API responses for stale currencies
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.raise_for_status = Mock()
        mock_response.json.return_value = {
            'rates': {
                'PHP': '65.123456',
                'EUR': '1.1',
                'CNY': '7.5'
            }
        }
        mock_get.return_value = mock_response
        
        response = self.client.get(self.url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        
        self.assertTrue(data['success'])
        self.assertTrue(data['data']['api_called'])  # API was called for EUR/CNY
        
        rates = data['data']['rates']
        
        # USD should be from cache (fresh)
        self.assertEqual(rates['USD']['source'], 'cached')
        self.assertEqual(rates['USD']['rate'], 55.123456)
        
        # EUR and CNY should be from API (were stale)
        self.assertEqual(rates['EUR']['source'], 'api')
        self.assertEqual(rates['CNY']['source'], 'api')
    
    def test_response_structure_completeness(self):
        """Test that response contains all required fields"""
        # Create fresh cached rates to avoid API calls
        fresh_time = timezone.now() - timedelta(hours=1)
        
        for currency in ['USD', 'EUR', 'CNY']:
            rate_obj = ExchangeRate.objects.create(
                currency=currency,
                rate=Decimal('50.123456')
            )
            ExchangeRate.objects.filter(id=rate_obj.id).update(updated_at=fresh_time)
        
        response = self.client.get(self.url)
        data = response.json()
        
        # Verify top-level structure
        self.assertIn('success', data)
        self.assertIn('data', data)
        
        # Verify data structure
        response_data = data['data']
        self.assertIn('base_currency', response_data)
        self.assertIn('rates', response_data)
        self.assertIn('api_called', response_data)
        self.assertIn('timestamp', response_data)
        
        # Verify rates structure for each currency
        for currency in ['USD', 'EUR', 'CNY']:
            self.assertIn(currency, response_data['rates'])
            currency_data = response_data['rates'][currency]
            self.assertIn('rate', currency_data)
            self.assertIn('last_updated', currency_data)
            self.assertIn('source', currency_data)
    
    def test_decimal_precision_maintained(self):
        """Test that decimal precision is maintained in calculations"""
        # Create test rate with high precision
        test_rate = Decimal('55.123456')
        fresh_time = timezone.now() - timedelta(hours=1)
        
        for currency, rate in [('USD', test_rate), ('EUR', '60.123456'), ('CNY', '8.456789')]:
            rate_obj = ExchangeRate.objects.create(currency=currency, rate=rate)
            ExchangeRate.objects.filter(id=rate_obj.id).update(updated_at=fresh_time)
        
        response = self.client.get(self.url)
        data = response.json()
        
        # Verify precision is maintained
        returned_rate = data['data']['rates']['USD']['rate']
        self.assertEqual(returned_rate, float(test_rate))
    
    def test_url_accessibility(self):
        """Test that the URL endpoint is accessible"""
        # Create minimal fresh cached data
        fresh_time = timezone.now() - timedelta(hours=1)
        
        for currency in ['USD', 'EUR', 'CNY']:
            rate_obj = ExchangeRate.objects.create(currency=currency, rate=Decimal('50.123456'))
            ExchangeRate.objects.filter(id=rate_obj.id).update(updated_at=fresh_time)
        
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_unauthenticated_access_denied(self):
        """Test that unauthenticated requests are denied"""
        # Remove authentication
        self.client.credentials()
        
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)