from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase
from admin_api.models import Customer, ParentCompany
from quotations_api.serializers import CustomerListSerializer

User = get_user_model()

class CustomerListViewTests(APITestCase):
    def setUp(self):
        # Create test user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpassword'
        )
        
        # Create parent company for testing
        self.parent_company = ParentCompany.objects.create(
            name='Parent Corp',
            consolidate_payment_terms=True
        )
        
        # Create test customers with different statuses
        self.active_customer1 = Customer.objects.create(
            name='Active Customer 1',
            registered_name='Active Registered 1',
            tin='12345',
            phone_number='111-222-3333',
            status='active',
            company_address='123 Main St',
            city='City 1',
            vat_type='VAT'
        )
        
        self.active_customer2 = Customer.objects.create(
            name='Active Customer 2',
            registered_name='Active Registered 2',
            tin='67890',
            phone_number='444-555-6666',
            status='active',
            company_address='456 Oak St',
            city='City 2',
            vat_type='Non-VAT'
        )
        
        self.active_customer_with_parent = Customer.objects.create(
            name='Active Customer with Parent',
            registered_name='Active Registered with Parent',
            tin='54321',
            phone_number='777-888-9999',
            status='active',
            has_parent=True,
            parent_company=self.parent_company,
            company_address='789 Pine St',
            city='City 3',
            vat_type='VAT'
        )
        
        self.inactive_customer = Customer.objects.create(
            name='Inactive Customer',
            registered_name='Inactive Registered',
            tin='09876',
            phone_number='000-999-8888',
            status='inactive',
            company_address='321 Elm St',
            city='City 4',
            vat_type='VAT'
        )
        
        # URL for the customer list endpoint
        self.url = reverse('customer-list')
        
        # Authenticate
        self.client.force_authenticate(user=self.user)
    
    def test_get_active_customers_only(self):
        """Test that only active customers are returned"""
        response = self.client.get(self.url)
        
        # Get all active customers from the database
        active_customers = Customer.objects.filter(status='active')
        serializer = CustomerListSerializer(active_customers, many=True)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['success'], True)
        self.assertEqual(len(response.data['data']), 3)  # Only active customers
        
        # Check that inactive customers are not included
        customer_ids = [customer['id'] for customer in response.data['data']]
        self.assertIn(self.active_customer1.id, customer_ids)
        self.assertIn(self.active_customer2.id, customer_ids)
        self.assertIn(self.active_customer_with_parent.id, customer_ids)
        self.assertNotIn(self.inactive_customer.id, customer_ids)
        
        # Verify the data structure matches the serializer output
        self.assertEqual(response.data['data'], serializer.data)
    
    def test_customer_list_fields(self):
        """Test that only the specified fields are included in the response"""
        response = self.client.get(self.url)
        
        # Check the first customer in the response
        customer_data = response.data['data'][0]
        
        # Verify only the fields specified in the serializer are included
        self.assertIn('id', customer_data)
        self.assertIn('name', customer_data)
        self.assertIn('registered_name', customer_data)
        
        # Verify other fields are not included
        self.assertNotIn('tin', customer_data)
        self.assertNotIn('phone_number', customer_data)
        self.assertNotIn('status', customer_data)
        self.assertNotIn('company_address', customer_data)
        self.assertNotIn('city', customer_data)
        self.assertNotIn('vat_type', customer_data)
    
    def test_unauthorized_access(self):
        """Test that unauthenticated users cannot access the endpoint"""
        # Logout
        self.client.force_authenticate(user=None)
        
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_customer_ordering(self):
        """Test that customers are returned in the correct order (by name)"""
        response = self.client.get(self.url)
        
        # Get the names from the response
        customer_names = [customer['name'] for customer in response.data['data']]
        
        # Check that they're in alphabetical order
        expected_order = sorted([
            self.active_customer1.name,
            self.active_customer2.name,
            self.active_customer_with_parent.name
        ])
        
        self.assertEqual(customer_names, expected_order)