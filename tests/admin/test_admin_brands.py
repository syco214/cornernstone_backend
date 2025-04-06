from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken
from admin_api.models import Brand

User = get_user_model()

class BrandViewTests(TestCase):
    """Tests for the Brand API endpoints"""
    
    def setUp(self):
        """Set up test data and authentication"""
        self.client = APIClient()
        self.brands_url = reverse('brands')
        
        # Create admin user
        self.admin_user = User.objects.create_user(
            username='adminuser',
            email='admin@example.com',
            password='adminpassword123',
            first_name='Admin',
            last_name='User',
            role='admin',
            user_access=['admin']
        )
        
        # Create regular user (for testing permissions)
        self.regular_user = User.objects.create_user(
            username='regularuser',
            email='regular@example.com',
            password='regularpassword123',
            first_name='Regular',
            last_name='User',
            role='user',
            user_access=['inventory']
        )
        
        # Create test brands
        self.brand1 = Brand.objects.create(
            name='Test Brand 1',
            made_in='Country 1',
            show_made_in=True,
            remarks='Test remarks 1'
        )
        
        self.brand2 = Brand.objects.create(
            name='Test Brand 2',
            made_in='Country 2',
            show_made_in=False,
            remarks='Test remarks 2'
        )
        
        # Authenticate as admin
        self.admin_token = RefreshToken.for_user(self.admin_user).access_token
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.admin_token}')
        
        # Brand detail URL
        self.brand_detail_url = reverse('brand-detail', args=[self.brand1.id])
        
        # New brand data for creation tests
        self.new_brand_data = {
            'name': 'New Brand',
            'made_in': 'New Country',
            'show_made_in': True,
            'remarks': 'New brand remarks'
        }
        
        # Update data for PUT tests
        self.update_data = {
            'name': 'Updated Brand',
            'made_in': 'Updated Country',
            'show_made_in': False
        }

    def test_get_brands_list(self):
        """Test retrieving list of brands"""
        response = self.client.get(self.brands_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertEqual(len(response.data['data']), 2)  # 2 brands total
        
        # Check pagination metadata
        self.assertIn('meta', response.data)
        self.assertIn('pagination', response.data['meta'])
        self.assertEqual(response.data['meta']['pagination']['count'], 2)

    def test_get_brands_with_search(self):
        """Test retrieving brands with search parameter"""
        response = self.client.get(f"{self.brands_url}?search=Brand 1")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertEqual(len(response.data['data']), 1)
        self.assertEqual(response.data['data'][0]['name'], 'Test Brand 1')

    def test_get_brands_with_sorting(self):
        """Test retrieving brands with sorting parameters"""
        response = self.client.get(f"{self.brands_url}?sort_by=name&sort_direction=desc")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        # First brand should be 'Test Brand 2' when sorted by name in descending order
        self.assertEqual(response.data['data'][0]['name'], 'Test Brand 2')

    def test_get_single_brand(self):
        """Test retrieving a single brand by ID"""
        response = self.client.get(self.brand_detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertEqual(response.data['data']['name'], 'Test Brand 1')
        self.assertEqual(response.data['data']['made_in'], 'Country 1')
        self.assertTrue(response.data['data']['show_made_in'])
        self.assertEqual(response.data['data']['remarks'], 'Test remarks 1')

    def test_create_brand(self):
        """Test creating a new brand"""
        response = self.client.post(self.brands_url, self.new_brand_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data['success'])
        self.assertEqual(response.data['data']['name'], 'New Brand')
        self.assertEqual(response.data['data']['made_in'], 'New Country')
        self.assertTrue(response.data['data']['show_made_in'])
        self.assertEqual(response.data['data']['remarks'], 'New brand remarks')
        
        # Verify brand was created in database
        self.assertTrue(Brand.objects.filter(name='New Brand').exists())

    def test_create_brand_invalid_data(self):
        """Test creating a brand with invalid data"""
        invalid_data = {
            'name': '',  # Empty name
            'made_in': 'Country',
            'show_made_in': True
        }
        response = self.client.post(self.brands_url, invalid_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data['success'])
        self.assertIn('errors', response.data)
        self.assertIn('name', response.data['errors'])

    def test_create_duplicate_brand(self):
        """Test creating a brand with a name that already exists"""
        duplicate_data = {
            'name': 'Test Brand 1',  # Already exists
            'made_in': 'New Country',
            'show_made_in': True
        }
        response = self.client.post(self.brands_url, duplicate_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data['success'])

    def test_update_brand(self):
        """Test updating a brand"""
        response = self.client.put(self.brand_detail_url, self.update_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertEqual(response.data['data']['name'], 'Updated Brand')
        self.assertEqual(response.data['data']['made_in'], 'Updated Country')
        self.assertFalse(response.data['data']['show_made_in'])
        
        # Verify brand was updated in database
        updated_brand = Brand.objects.get(id=self.brand1.id)
        self.assertEqual(updated_brand.name, 'Updated Brand')
        self.assertEqual(updated_brand.made_in, 'Updated Country')
        self.assertFalse(updated_brand.show_made_in)

    def test_update_brand_invalid_data(self):
        """Test updating a brand with invalid data"""
        invalid_data = {
            'name': '',  # Empty name
        }
        response = self.client.put(self.brand_detail_url, invalid_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data['success'])
        self.assertIn('errors', response.data)
        self.assertIn('name', response.data['errors'])

    def test_delete_brand(self):
        """Test deleting a brand"""
        response = self.client.delete(self.brand_detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        
        # Verify brand is deleted
        with self.assertRaises(Brand.DoesNotExist):
            Brand.objects.get(id=self.brand1.id)

    def test_unauthenticated_access(self):
        """Test accessing brand endpoints without authentication"""
        self.client.credentials()  # Remove authentication
        response = self.client.get(self.brands_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)