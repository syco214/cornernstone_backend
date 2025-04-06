from django.urls import reverse
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from django.contrib.auth import get_user_model
from admin_api.models import Forwarder, ForwarderContact

User = get_user_model()

class ForwarderViewTests(TestCase):
    """Tests for the Forwarder API views."""

    def setUp(self):
        """Set up test data."""
        # Create a test user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpassword'
        )
        
        # Create test forwarders
        self.forwarder1 = Forwarder.objects.create(
            company_name='Test Forwarder 1',
            address='123 Forwarder St',
            email='forwarder1@example.com',
            phone_number='123-456-7890',
            payment_type='cod'
        )
        
        self.forwarder2 = Forwarder.objects.create(
            company_name='Test Forwarder 2',
            address='456 Forwarder Ave',
            email='forwarder2@example.com',
            phone_number='987-654-3210',
            payment_type='terms',
            payment_terms_days=30
        )
        
        # Create related data for forwarder1
        self.contact1 = ForwarderContact.objects.create(
            forwarder=self.forwarder1,
            contact_person='John Smith',
            position='Agent',
            department='Logistics',
            email='john@example.com',
            office_number='111-222-3333',
            personal_number='444-555-6666'
        )
        
        # Set up API client
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        
        # URLs
        self.list_url = reverse('forwarders')
        self.detail_url = reverse('forwarder-detail', args=[self.forwarder1.id])
    
    def test_get_forwarder_list(self):
        """Test retrieving a list of forwarders."""
        response = self.client.get(self.list_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertEqual(len(response.data['data']), 2)
    
    def test_get_forwarder_detail(self):
        """Test retrieving a single forwarder with all related data."""
        response = self.client.get(self.detail_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        
        data = response.data['data']
        self.assertEqual(data['company_name'], 'Test Forwarder 1')
        self.assertEqual(len(data['contacts']), 1)
        self.assertEqual(data['payment_type'], 'cod')
    
    def test_search_forwarders(self):
        """Test searching for forwarders."""
        response = self.client.get(f"{self.list_url}?search=Test Forwarder 1")
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertEqual(len(response.data['data']), 1)
        self.assertEqual(response.data['data'][0]['company_name'], 'Test Forwarder 1')
    
    def test_filter_by_payment_type(self):
        """Test filtering forwarders by payment type."""
        response = self.client.get(f"{self.list_url}?payment_type=terms")
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertEqual(len(response.data['data']), 1)
        self.assertEqual(response.data['data'][0]['company_name'], 'Test Forwarder 2')
    
    def test_sort_forwarders(self):
        """Test sorting forwarders."""
        # Sort by company_name descending
        response = self.client.get(f"{self.list_url}?sort_by=company_name&sort_direction=desc")
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertEqual(response.data['data'][0]['company_name'], 'Test Forwarder 2')
        self.assertEqual(response.data['data'][1]['company_name'], 'Test Forwarder 1')
    
    def test_create_forwarder_minimal(self):
        """Test creating a forwarder with minimal data."""
        data = {
            'company_name': 'New Forwarder',
            'address': 'New Address',
            'email': 'new@example.com',
            'phone_number': '123-123-1234',
            'payment_type': 'cod'
        }
        
        response = self.client.post(self.list_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data['success'])
        self.assertEqual(response.data['data']['company_name'], 'New Forwarder')
        
        # Check that the forwarder was created in the database
        self.assertEqual(Forwarder.objects.count(), 3)
    
    def test_create_forwarder_with_payment_terms(self):
        """Test creating a forwarder with payment terms."""
        data = {
            'company_name': 'Terms Forwarder',
            'address': 'Terms Address',
            'email': 'terms@example.com',
            'phone_number': '123-123-1234',
            'payment_type': 'terms',
            'payment_terms_days': 45
        }
        
        response = self.client.post(self.list_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data['success'])
        self.assertEqual(response.data['data']['payment_type'], 'terms')
        self.assertEqual(response.data['data']['payment_terms_days'], 45)
    
    def test_create_forwarder_payment_terms_validation(self):
        """Test validation error when payment_type is 'terms' but no payment_terms_days is provided."""
        data = {
            'company_name': 'Invalid Forwarder',
            'address': 'Invalid Address',
            'email': 'invalid@example.com',
            'phone_number': '123-123-1234',
            'payment_type': 'terms'  # Missing payment_terms_days
        }
        
        response = self.client.post(self.list_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data['success'])
        self.assertIn('payment_terms_days', response.data['errors'])
    
    def test_create_forwarder_validation_error(self):
        """Test validation error when creating a forwarder."""
        # Missing required fields
        data = {
            'company_name': 'Incomplete Forwarder'
            # Missing address, email, phone_number
        }
        
        response = self.client.post(self.list_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data['success'])
    
    def test_create_forwarder_with_contacts(self):
        """Test creating a forwarder with contacts."""
        data = {
            'company_name': 'Complete Forwarder',
            'address': 'Complete Address',
            'email': 'complete@example.com',
            'phone_number': '123-123-1234',
            'payment_type': 'cod',
            'contacts': [
                {
                    'contact_person': 'Jane Doe',
                    'position': 'Manager',
                    'department': 'Operations',
                    'email': 'jane@example.com',
                    'office_number': '111-222-3333',
                    'personal_number': '444-555-6666'
                },
                {
                    'contact_person': 'Bob Smith',
                    'position': 'Assistant',
                    'department': 'Operations',
                    'email': 'bob@example.com',
                    'office_number': '777-888-9999',
                    'personal_number': '000-111-2222'
                }
            ]
        }
        
        response = self.client.post(self.list_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data['success'])
        
        # Check that related data was created
        forwarder_id = response.data['data']['id']
        forwarder = Forwarder.objects.get(id=forwarder_id)
        
        self.assertEqual(forwarder.contacts.count(), 2)
    
    def test_update_forwarder(self):
        """Test updating a forwarder."""
        data = {
            'company_name': 'Updated Forwarder 1',
            'email': 'updated@example.com'
        }
        
        response = self.client.put(self.detail_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        
        # Check that the forwarder was updated
        self.forwarder1.refresh_from_db()
        self.assertEqual(self.forwarder1.company_name, 'Updated Forwarder 1')
        self.assertEqual(self.forwarder1.email, 'updated@example.com')
    
    def test_update_forwarder_payment_type(self):
        """Test updating a forwarder's payment type."""
        data = {
            'payment_type': 'terms',
            'payment_terms_days': 60
        }
        
        response = self.client.put(self.detail_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        
        # Check that the payment type was updated
        self.forwarder1.refresh_from_db()
        self.assertEqual(self.forwarder1.payment_type, 'terms')
        self.assertEqual(self.forwarder1.payment_terms_days, 60)
    
    def test_update_forwarder_with_contacts(self):
        """Test updating a forwarder with contacts."""
        data = {
            'company_name': 'Fully Updated Forwarder',
            'contacts': [
                {
                    'id': self.contact1.id,
                    'contact_person': 'Updated John',
                    'position': 'Senior Agent',
                    'department': 'Logistics',
                    'email': 'updated@example.com',
                    'office_number': self.contact1.office_number,
                    'personal_number': self.contact1.personal_number
                },
                {
                    'contact_person': 'New Contact',
                    'position': 'New Position',
                    'department': 'New Department',
                    'email': 'new@example.com',
                    'office_number': '123-456-7890',
                    'personal_number': '098-765-4321'
                }
            ]
        }
        
        response = self.client.put(self.detail_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        
        # Check that the related data was updated
        self.forwarder1.refresh_from_db()
        
        # Should have 2 contacts now (1 updated, 1 new)
        self.assertEqual(self.forwarder1.contacts.count(), 2)
        updated_contact = self.forwarder1.contacts.get(id=self.contact1.id)
        self.assertEqual(updated_contact.contact_person, 'Updated John')
        self.assertEqual(updated_contact.email, 'updated@example.com')
    
    def test_delete_forwarder(self):
        """Test deleting a forwarder."""
        response = self.client.delete(self.detail_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        
        # Check that the forwarder was deleted
        self.assertEqual(Forwarder.objects.count(), 1)
        with self.assertRaises(Forwarder.DoesNotExist):
            Forwarder.objects.get(id=self.forwarder1.id)
        
        # Related data should also be deleted (cascade)
        self.assertEqual(ForwarderContact.objects.filter(forwarder_id=self.forwarder1.id).count(), 0)
    
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