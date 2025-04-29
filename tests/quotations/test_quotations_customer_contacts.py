from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase
from admin_api.models import Customer, CustomerContact
from quotations_api.serializers import CustomerContactSerializer

User = get_user_model()

class CustomerContactListViewTests(APITestCase):
    def setUp(self):
        # Create test user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpassword'
        )
        
        # Create test customers
        self.customer1 = Customer.objects.create(
            name='Test Customer 1',
            registered_name='Test Registered 1',
            phone_number='111-222-3333',
            company_address='123 Main St',
            city='City 1'
        )
        
        self.customer2 = Customer.objects.create(
            name='Test Customer 2',
            registered_name='Test Registered 2',
            phone_number='444-555-6666',
            company_address='456 Oak St',
            city='City 2'
        )
        
        # Create test contacts for customer1
        self.contact1 = CustomerContact.objects.create(
            customer=self.customer1,
            contact_person='John Doe',
            position='CEO',
            department='Executive',
            email='john@example.com',
            mobile_number='123-456-7890',
            office_number='098-765-4321'
        )
        
        self.contact2 = CustomerContact.objects.create(
            customer=self.customer1,
            contact_person='Jane Smith',
            position='CFO',
            department='Finance',
            email='jane@example.com',
            mobile_number='234-567-8901',
            office_number='987-654-3210'
        )
        
        # Create test contact for customer2
        self.contact3 = CustomerContact.objects.create(
            customer=self.customer2,
            contact_person='Bob Johnson',
            position='CTO',
            department='Technology',
            email='bob@example.com',
            mobile_number='345-678-9012',
            office_number='876-543-2109'
        )
        
        # URL for the customer contact list endpoint
        self.url = reverse('customer-contact-list')
        
        # Authenticate
        self.client.force_authenticate(user=self.user)
    
    def test_get_contacts_without_customer_id(self):
        """Test that an error is returned when no customer_id is provided"""
        response = self.client.get(self.url)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['success'], False)
        self.assertIn('detail', response.data['errors'])
        self.assertEqual(response.data['errors']['detail'], 'Customer ID is required')
    
    def test_get_contacts_for_customer(self):
        """Test getting contacts for a specific customer"""
        response = self.client.get(f"{self.url}?customer_id={self.customer1.id}")
        
        contacts = CustomerContact.objects.filter(customer_id=self.customer1.id)
        serializer = CustomerContactSerializer(contacts, many=True)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['success'], True)
        self.assertEqual(len(response.data['data']), 2)  # Two contacts for customer1
        self.assertEqual(response.data['data'], serializer.data)
        
        # Verify the correct contacts are returned
        contact_ids = [contact['id'] for contact in response.data['data']]
        self.assertIn(self.contact1.id, contact_ids)
        self.assertIn(self.contact2.id, contact_ids)
        self.assertNotIn(self.contact3.id, contact_ids)  # This is for customer2
    
    def test_search_contacts(self):
        """Test searching for contacts by name"""
        # Search for "John" in customer1's contacts
        response = self.client.get(f"{self.url}?customer_id={self.customer1.id}&search=John")
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['success'], True)
        self.assertEqual(len(response.data['data']), 1)
        self.assertEqual(response.data['data'][0]['contact_person'], 'John Doe')
        
        # Search for "Jane" in customer1's contacts
        response = self.client.get(f"{self.url}?customer_id={self.customer1.id}&search=Jane")
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['data']), 1)
        self.assertEqual(response.data['data'][0]['contact_person'], 'Jane Smith')
        
        # Search for non-existent name
        response = self.client.get(f"{self.url}?customer_id={self.customer1.id}&search=nonexistent")
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['data']), 0)
    
    def test_create_contact(self):
        """Test creating a new contact"""
        data = {
            'customer': self.customer1.id,
            'contact_person': 'Alice Brown',
            'position': 'COO',
            'department': 'Operations',
            'email': 'alice@example.com',
            'mobile_number': '456-789-0123',
            'office_number': '765-432-1098'
        }
        
        response = self.client.post(self.url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['success'], True)
        self.assertEqual(response.data['data']['contact_person'], data['contact_person'])
        
        # Verify the contact was created in the database
        self.assertTrue(CustomerContact.objects.filter(contact_person='Alice Brown').exists())
        
        # Verify customer1 now has 3 contacts
        self.assertEqual(CustomerContact.objects.filter(customer=self.customer1).count(), 3)
    
    def test_create_contact_invalid_data(self):
        """Test creating a contact with invalid data"""
        # Missing required field (contact_person)
        data = {
            'customer': self.customer1.id,
            'position': 'COO',
            'department': 'Operations',
            'email': 'alice@example.com',
            'mobile_number': '456-789-0123',
            'office_number': '765-432-1098'
        }
        
        response = self.client.post(self.url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['success'], False)
        self.assertIn('contact_person', response.data['errors'])
        
        # Missing customer
        data = {
            'contact_person': 'Alice Brown',
            'position': 'COO',
            'department': 'Operations',
            'email': 'alice@example.com',
            'mobile_number': '456-789-0123',
            'office_number': '765-432-1098'
        }
        
        response = self.client.post(self.url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['success'], False)
        self.assertIn('customer', response.data['errors'])
    
    def test_pagination(self):
        """Test pagination of contacts"""
        # Create more contacts to test pagination
        for i in range(10):
            CustomerContact.objects.create(
                customer=self.customer1,
                contact_person=f'Test Contact {i}',
                position=f'Position {i}',
                department=f'Department {i}',
                email=f'test{i}@example.com',
                mobile_number=f'123-456-{i}',
                office_number=f'987-654-{i}'
            )
        
        # Get contacts with pagination
        response = self.client.get(f"{self.url}?customer_id={self.customer1.id}")
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['success'], True)
        self.assertIn('meta', response.data)
        self.assertIn('pagination', response.data['meta'])
        self.assertIn('count', response.data['meta']['pagination'])
        self.assertEqual(response.data['meta']['pagination']['count'], 12)  # 2 original + 10 new
        
        # Test second page if available
        if response.data['meta']['pagination']['next']:
            next_url = response.data['meta']['pagination']['next']
            # Extract the page parameter
            page_param = next_url.split('page=')[1].split('&')[0]
            response = self.client.get(f"{self.url}?customer_id={self.customer1.id}&page={page_param}")
            
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(response.data['success'], True)
            self.assertGreater(len(response.data['data']), 0)
    
    def test_unauthorized_access(self):
        """Test that unauthenticated users cannot access the endpoint"""
        # Logout
        self.client.force_authenticate(user=None)
        
        # Try to access endpoints
        get_response = self.client.get(f"{self.url}?customer_id={self.customer1.id}")
        post_response = self.client.post(self.url, {
            'customer': self.customer1.id,
            'contact_person': 'Test Person',
            'position': 'Test Position',
            'department': 'Test Department',
            'email': 'test@example.com',
            'mobile_number': '123-456-7890',
            'office_number': '987-654-3210'
        }, format='json')
        
        self.assertEqual(get_response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(post_response.status_code, status.HTTP_401_UNAUTHORIZED)