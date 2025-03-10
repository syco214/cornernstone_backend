from django.urls import reverse
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from django.contrib.auth import get_user_model
from admin_api.models import (
    Customer, 
    CustomerAddress, 
    CustomerContact, 
    CustomerPaymentTerm,
    ParentCompany
)
import json
from decimal import Decimal

User = get_user_model()

class CustomerViewTests(TestCase):
    """Tests for the Customer API views."""

    def setUp(self):
        """Set up test data."""
        # Create a test user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpassword'
        )
        
        # Create a parent company with only the fields it actually has
        self.parent_company = ParentCompany.objects.create(
            name='Test Parent Company',
            consolidate_payment_terms=True
        )
        
        # Create test customers
        self.customer1 = Customer.objects.create(
            name='Test Customer 1',
            registered_name='Test Registered 1',
            tin='987654321',
            phone_number='987-654-3210',
            status='active',
            has_parent=False,
            company_address='123 Test St',
            city='Test City',
            vat_type='VAT'
        )
        
        self.customer2 = Customer.objects.create(
            name='Test Customer 2',
            registered_name='Test Registered 2',
            phone_number='555-555-5555',
            status='inactive',
            has_parent=True,
            parent_company=self.parent_company,
            company_address='456 Test Ave',
            city='Another City'
        )
        
        # Create related data for customer1
        self.address1 = CustomerAddress.objects.create(
            customer=self.customer1,
            delivery_address='123 Delivery St',
            delivery_schedule='Monday-Friday 9-5'
        )
        
        self.contact1 = CustomerContact.objects.create(
            customer=self.customer1,
            contact_person='John Doe',
            position='Manager',
            department='Sales'
        )
        
        self.payment_term1 = CustomerPaymentTerm.objects.create(
            customer=self.customer1,
            name='Standard Terms',
            credit_limit=Decimal('50000.00'),
            stock_payment_terms='30 days',
            stock_dp_percentage=Decimal('20.00'),
            stock_terms_days=30,
            import_payment_terms='45 days',
            import_dp_percentage=Decimal('30.00'),
            import_terms_days=45
        )
        
        # Set up API client
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        
        # URLs
        self.list_url = reverse('customers')
        self.detail_url = reverse('customer-detail', args=[self.customer1.id])
    
    def test_get_customer_list(self):
        """Test retrieving a list of customers."""
        response = self.client.get(self.list_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertEqual(len(response.data['data']), 2)
    
    def test_get_customer_detail(self):
        """Test retrieving a single customer with all related data."""
        response = self.client.get(self.detail_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        
        data = response.data['data']
        self.assertEqual(data['name'], 'Test Customer 1')
        self.assertEqual(len(data['addresses']), 1)
        self.assertEqual(len(data['contacts']), 1)
        self.assertIsNotNone(data['payment_term'])
    
    def test_search_customers(self):
        """Test searching for customers."""
        response = self.client.get(f"{self.list_url}?search=Test Customer 1")
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertEqual(len(response.data['data']), 1)
        self.assertEqual(response.data['data'][0]['name'], 'Test Customer 1')
    
    def test_filter_by_status(self):
        """Test filtering customers by status."""
        response = self.client.get(f"{self.list_url}?status=inactive")
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertEqual(len(response.data['data']), 1)
        self.assertEqual(response.data['data'][0]['name'], 'Test Customer 2')
    
    def test_filter_by_parent_company(self):
        """Test filtering customers by parent company."""
        response = self.client.get(f"{self.list_url}?parent_company_id={self.parent_company.id}")
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertEqual(len(response.data['data']), 1)
        self.assertEqual(response.data['data'][0]['name'], 'Test Customer 2')
    
    def test_sort_customers(self):
        """Test sorting customers."""
        # Sort by name descending
        response = self.client.get(f"{self.list_url}?sort_by=name&sort_direction=desc")
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertEqual(response.data['data'][0]['name'], 'Test Customer 2')
        self.assertEqual(response.data['data'][1]['name'], 'Test Customer 1')
    
    def test_create_customer_minimal(self):
        """Test creating a customer with minimal data."""
        data = {
            'name': 'New Customer',
            'registered_name': 'New Registered Name',
            'phone_number': '123-123-1234',
            'company_address': 'New Address',
            'city': 'New City'
        }
        
        response = self.client.post(self.list_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data['success'])
        self.assertEqual(response.data['data']['name'], 'New Customer')
        
        # Check that the customer was created in the database
        self.assertEqual(Customer.objects.count(), 3)
    
    def test_create_customer_with_parent_company(self):
        """Test creating a customer with a parent company."""
        data = {
            'name': 'Child Customer',
            'registered_name': 'Child Registered',
            'phone_number': '123-123-1234',
            'company_address': 'Child Address',
            'city': 'Child City',
            'has_parent': True,
            'parent_company': self.parent_company.id
        }
        
        response = self.client.post(self.list_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data['success'])
        self.assertEqual(response.data['data']['parent_company'], self.parent_company.id)
    
    def test_create_customer_parent_validation_error(self):
        """Test validation error when has_parent is True but no parent_company is provided."""
        data = {
            'name': 'Invalid Customer',
            'registered_name': 'Invalid Registered',
            'phone_number': '123-123-1234',
            'company_address': 'Invalid Address',
            'city': 'Invalid City',
            'has_parent': True  # Missing parent_company
        }
        
        response = self.client.post(self.list_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data['success'])
        self.assertIn('parent_company', response.data['errors'])
    
    def test_create_customer_validation_error(self):
        """Test validation error when creating a customer."""
        # Missing required fields
        data = {
            'name': 'Incomplete Customer'
            # Missing registered_name, phone_number, etc.
        }
        
        response = self.client.post(self.list_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data['success'])
    
    def test_create_customer_with_related_data(self):
        """Test creating a customer with addresses, contacts, and payment terms."""
        data = {
            'name': 'Complete Customer',
            'registered_name': 'Complete Registered',
            'phone_number': '123-123-1234',
            'company_address': 'Complete Address',
            'city': 'Complete City',
            'addresses': [
                {
                    'delivery_address': 'Delivery Address 1',
                    'delivery_schedule': 'Monday-Wednesday'
                },
                {
                    'delivery_address': 'Delivery Address 2',
                    'delivery_schedule': 'Thursday-Friday'
                }
            ],
            'contacts': [
                {
                    'contact_person': 'Jane Smith',
                    'position': 'CEO',
                    'department': 'Executive'
                }
            ],
            'payment_term': {
                'name': 'Premium Terms',
                'credit_limit': 100000,
                'stock_payment_terms': '60 days',
                'stock_dp_percentage': 10,
                'stock_terms_days': 60,
                'import_payment_terms': '90 days',
                'import_dp_percentage': 15,
                'import_terms_days': 90
            }
        }
        
        response = self.client.post(self.list_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data['success'])
        
        # Check that related data was created
        customer_id = response.data['data']['id']
        customer = Customer.objects.get(id=customer_id)
        
        self.assertEqual(customer.addresses.count(), 2)
        self.assertEqual(customer.contacts.count(), 1)
        self.assertIsNotNone(hasattr(customer, 'payment_term'))
    
    def test_update_customer(self):
        """Test updating a customer."""
        data = {
            'name': 'Updated Customer 1',
            'status': 'inactive'
        }
        
        response = self.client.put(self.detail_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        
        # Check that the customer was updated
        self.customer1.refresh_from_db()
        self.assertEqual(self.customer1.name, 'Updated Customer 1')
        self.assertEqual(self.customer1.status, 'inactive')
    
    def test_update_customer_with_related_data(self):
        """Test updating a customer with related data."""
        data = {
            'name': 'Fully Updated Customer',
            'addresses': [
                {
                    'id': self.address1.id,
                    'delivery_address': 'Updated Delivery St',
                    'delivery_schedule': 'Updated Schedule'
                },
                {
                    'delivery_address': 'New Delivery Address',
                    'delivery_schedule': 'New Schedule'
                }
            ],
            'contacts': [
                {
                    'contact_person': 'New Contact',
                    'position': 'New Position',
                    'department': 'New Department'
                }
            ],
            'payment_term': {
                'name': 'Updated Terms',
                'credit_limit': 75000,
                'stock_payment_terms': 'Updated stock terms',
                'stock_dp_percentage': 25,
                'stock_terms_days': 45,
                'import_payment_terms': 'Updated import terms',
                'import_dp_percentage': 35,
                'import_terms_days': 60
            }
        }
        
        response = self.client.put(self.detail_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        
        # Check that the related data was updated
        self.customer1.refresh_from_db()
        
        # Should have 2 addresses now (1 updated, 1 new)
        self.assertEqual(self.customer1.addresses.count(), 2)
        updated_address = self.customer1.addresses.get(id=self.address1.id)
        self.assertEqual(updated_address.delivery_address, 'Updated Delivery St')
        
        # Should have 1 contact (old one deleted, new one added)
        self.assertEqual(self.customer1.contacts.count(), 1)
        new_contact = self.customer1.contacts.first()
        self.assertEqual(new_contact.contact_person, 'New Contact')
        
        # Payment term should be updated
        self.customer1.payment_term.refresh_from_db()
        self.assertEqual(self.customer1.payment_term.name, 'Updated Terms')
        self.assertEqual(self.customer1.payment_term.credit_limit, Decimal('75000.00'))
    
    def test_delete_customer(self):
        """Test deleting a customer."""
        response = self.client.delete(self.detail_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        
        # Check that the customer was deleted
        self.assertEqual(Customer.objects.count(), 1)
        with self.assertRaises(Customer.DoesNotExist):
            Customer.objects.get(id=self.customer1.id)
        
        # Related data should also be deleted (cascade)
        self.assertEqual(CustomerAddress.objects.filter(customer_id=self.customer1.id).count(), 0)
        self.assertEqual(CustomerContact.objects.filter(customer_id=self.customer1.id).count(), 0)
        self.assertEqual(CustomerPaymentTerm.objects.filter(customer_id=self.customer1.id).count(), 0)
    
    def test_unauthorized_access(self):
        """Test that unauthenticated users cannot access the API."""
        # Create a client without authentication
        client = APIClient()
        
        response = client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        
        response = client.get(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        
        response = client.post(self.list_url, {})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        
        response = client.put(self.detail_url, {})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        
        response = client.delete(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)