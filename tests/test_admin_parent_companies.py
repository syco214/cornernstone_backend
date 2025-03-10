from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from decimal import Decimal
from django.contrib.auth import get_user_model
from admin_api.models import ParentCompany, ParentCompanyPaymentTerm, Customer

User = get_user_model()

class ParentCompanyTests(TestCase):
    """Test suite for ParentCompany API views"""

    def setUp(self):
        """Set up test data and authenticate client"""
        self.client = APIClient()
        
        # Create test user and authenticate
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpassword123'
        )
        self.client.force_authenticate(user=self.user)
        
        # Create test parent companies
        self.parent_company1 = ParentCompany.objects.create(
            name='Test Parent Company 1',
            consolidate_payment_terms=True
        )
        
        self.parent_company2 = ParentCompany.objects.create(
            name='Test Parent Company 2',
            consolidate_payment_terms=False
        )
        
        # Create payment terms for parent company 1
        self.payment_term1 = ParentCompanyPaymentTerm.objects.create(
            parent_company=self.parent_company1,
            name='Standard Terms',
            credit_limit=Decimal('100000.00'),
            stock_payment_terms='Net 30',
            stock_dp_percentage=Decimal('0.00'),
            stock_terms_days=30,
            import_payment_terms='LC 60',
            import_dp_percentage=Decimal('30.00'),
            import_terms_days=60
        )
        
        # Create customers associated with parent companies
        self.customer1 = Customer.objects.create(
            name='Customer 1',
            parent_company=self.parent_company1
        )
        
        self.customer2 = Customer.objects.create(
            name='Customer 2',
            parent_company=self.parent_company1
        )
        
        self.customer3 = Customer.objects.create(
            name='Customer 3',
            parent_company=self.parent_company2
        )
        
        # URLs
        self.list_url = reverse('parent-companies')
        self.detail_url = reverse('parent-company-detail', args=[self.parent_company1.id])
        
        # Valid data for creating/updating
        self.valid_parent_company_data = {
            'name': 'New Parent Company',
            'consolidate_payment_terms': True,
            'payment_term': {
                'name': 'Premium Terms',
                'credit_limit': '150000.00',
                'stock_payment_terms': 'Net 45',
                'stock_dp_percentage': '10.00',
                'stock_terms_days': 45,
                'import_payment_terms': 'LC 90',
                'import_dp_percentage': '20.00',
                'import_terms_days': 90
            }
        }
        
        self.valid_update_data = {
            'name': 'Updated Parent Company',
            'consolidate_payment_terms': False
        }
        
        self.invalid_data = {
            'name': '',  # Empty name should be invalid
            'consolidate_payment_terms': True
        }

    def test_get_parent_companies_list(self):
        """Test retrieving a list of parent companies"""
        response = self.client.get(self.list_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertEqual(len(response.data['data']), 2)
        self.assertIn('meta', response.data)
        self.assertIn('pagination', response.data['meta'])

    def test_get_parent_company_detail(self):
        """Test retrieving a single parent company with its payment terms and customers"""
        response = self.client.get(self.detail_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertEqual(response.data['data']['name'], 'Test Parent Company 1')
        self.assertTrue(response.data['data']['consolidate_payment_terms'])
        
        # Check payment term data
        self.assertIsNotNone(response.data['data']['payment_term'])
        self.assertEqual(response.data['data']['payment_term']['name'], 'Standard Terms')
        self.assertEqual(Decimal(response.data['data']['payment_term']['credit_limit']), Decimal('100000.00'))
        
        # Check customers data
        self.assertEqual(len(response.data['data']['customers']), 2)
        customer_names = [c['name'] for c in response.data['data']['customers']]
        self.assertIn('Customer 1', customer_names)
        self.assertIn('Customer 2', customer_names)

    def test_create_parent_company_with_payment_term(self):
        """Test creating a new parent company with payment terms"""
        response = self.client.post(
            self.list_url,
            self.valid_parent_company_data,
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data['success'])
        
        # Verify parent company was created
        parent_company = ParentCompany.objects.get(name='New Parent Company')
        self.assertTrue(parent_company.consolidate_payment_terms)
        
        # Verify payment term was created
        payment_term = ParentCompanyPaymentTerm.objects.get(parent_company=parent_company)
        self.assertEqual(payment_term.name, 'Premium Terms')
        self.assertEqual(payment_term.credit_limit, Decimal('150000.00'))
        self.assertEqual(payment_term.stock_terms_days, 45)

    def test_create_parent_company_without_payment_term(self):
        """Test creating a parent company without payment terms"""
        data = {
            'name': 'Parent Company No Terms',
            'consolidate_payment_terms': False
        }
        
        response = self.client.post(
            self.list_url,
            data,
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data['success'])
        
        # Verify parent company was created
        parent_company = ParentCompany.objects.get(name='Parent Company No Terms')
        self.assertFalse(parent_company.consolidate_payment_terms)
        
        # Verify no payment term was created
        with self.assertRaises(ParentCompanyPaymentTerm.DoesNotExist):
            ParentCompanyPaymentTerm.objects.get(parent_company=parent_company)

    def test_create_parent_company_invalid_data(self):
        """Test creating a parent company with invalid data"""
        response = self.client.post(
            self.list_url,
            self.invalid_data,
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data['success'])
        self.assertIn('errors', response.data)
        self.assertIn('name', response.data['errors'])

    def test_update_parent_company(self):
        """Test updating a parent company"""
        response = self.client.put(
            self.detail_url,
            self.valid_update_data,
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        
        # Verify parent company was updated
        self.parent_company1.refresh_from_db()
        self.assertEqual(self.parent_company1.name, 'Updated Parent Company')
        self.assertFalse(self.parent_company1.consolidate_payment_terms)

    def test_update_parent_company_with_payment_term(self):
        """Test updating a parent company and its payment terms"""
        update_data = {
            'name': 'Updated With Terms',
            'payment_term': {
                'name': 'Updated Terms',
                'credit_limit': '200000.00',
                'stock_payment_terms': 'Net 60',
                'stock_dp_percentage': '15.00',
                'stock_terms_days': 60,
                'import_payment_terms': 'LC 120',
                'import_dp_percentage': '25.00',
                'import_terms_days': 120
            }
        }
        
        response = self.client.put(
            self.detail_url,
            update_data,
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        
        # Verify parent company was updated
        self.parent_company1.refresh_from_db()
        self.assertEqual(self.parent_company1.name, 'Updated With Terms')
        
        # Verify payment term was updated
        self.payment_term1.refresh_from_db()
        self.assertEqual(self.payment_term1.name, 'Updated Terms')
        self.assertEqual(self.payment_term1.credit_limit, Decimal('200000.00'))
        self.assertEqual(self.payment_term1.stock_terms_days, 60)
        self.assertEqual(self.payment_term1.import_terms_days, 120)

    def test_add_payment_term_to_existing_parent_company(self):
        """Test adding payment terms to a parent company that didn't have them"""
        # First, delete existing payment term
        self.payment_term1.delete()
        
        update_data = {
            'payment_term': {
                'name': 'New Terms',
                'credit_limit': '50000.00',
                'stock_payment_terms': 'Net 15',
                'stock_dp_percentage': '5.00',
                'stock_terms_days': 15,
                'import_payment_terms': 'LC 30',
                'import_dp_percentage': '10.00',
                'import_terms_days': 30
            }
        }
        
        response = self.client.put(
            self.detail_url,
            update_data,
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        
        # Verify new payment term was created
        payment_term = ParentCompanyPaymentTerm.objects.get(parent_company=self.parent_company1)
        self.assertEqual(payment_term.name, 'New Terms')
        self.assertEqual(payment_term.credit_limit, Decimal('50000.00'))

    def test_delete_parent_company(self):
        """Test deleting a parent company"""
        response = self.client.delete(self.detail_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        
        # Verify parent company was deleted
        with self.assertRaises(ParentCompany.DoesNotExist):
            ParentCompany.objects.get(id=self.parent_company1.id)
        
        # Verify payment term was deleted (cascade)
        with self.assertRaises(ParentCompanyPaymentTerm.DoesNotExist):
            ParentCompanyPaymentTerm.objects.get(id=self.payment_term1.id)

    def test_search_parent_companies(self):
        """Test searching parent companies by name"""
        response = self.client.get(f"{self.list_url}?search=Company 1")
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertEqual(len(response.data['data']), 1)
        self.assertEqual(response.data['data'][0]['name'], 'Test Parent Company 1')

    def test_sort_parent_companies(self):
        """Test sorting parent companies"""
        # Test ascending sort (default)
        response = self.client.get(f"{self.list_url}?sort_by=name&sort_direction=asc")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['data'][0]['name'], 'Test Parent Company 1')
        self.assertEqual(response.data['data'][1]['name'], 'Test Parent Company 2')
        
        # Test descending sort
        response = self.client.get(f"{self.list_url}?sort_by=name&sort_direction=desc")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['data'][0]['name'], 'Test Parent Company 2')
        self.assertEqual(response.data['data'][1]['name'], 'Test Parent Company 1')

    def test_unauthorized_access(self):
        """Test that unauthenticated users cannot access the API"""
        # Create a new client without authentication
        unauthenticated_client = APIClient()
        
        # Try to access the list endpoint
        response = unauthenticated_client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        
        # Try to access the detail endpoint
        response = unauthenticated_client.get(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        
        # Try to create a parent company
        response = unauthenticated_client.post(
            self.list_url,
            self.valid_parent_company_data,
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED) 