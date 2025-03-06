from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()

class UserViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.users_url = reverse('users')
        
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
        
        # Create regular users
        self.user1 = User.objects.create_user(
            username='user1',
            email='user1@example.com',
            password='password123',
            first_name='User',
            last_name='One',
            role='user',
            user_access=['inventory']
        )
        
        self.user2 = User.objects.create_user(
            username='user2',
            email='user2@example.com',
            password='password123',
            first_name='User',
            last_name='Two',
            role='user',
            user_access=['warehouse']
        )
        
        # Authenticate as admin
        self.admin_token = RefreshToken.for_user(self.admin_user).access_token
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.admin_token}')
        
        # User detail URL
        self.user_detail_url = reverse('user-detail', args=[self.user1.id])
        
        # New user data for creation tests
        self.new_user_data = {
            'username': 'newuser',
            'email': 'new@example.com',
            'password': 'newpassword123',
            'first_name': 'New',
            'last_name': 'User',
            'role': 'user',
            'user_access': ['inventory', 'warehouse'],
            'is_active': True
        }
        
        # Update data for PUT tests
        self.update_data = {
            'first_name': 'Updated',
            'last_name': 'Name',
            'user_access': ['finance']
        }

    def test_get_users_list(self):
        """Test retrieving list of users"""
        response = self.client.get(self.users_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertEqual(len(response.data['data']), 3)  # 3 users total
        self.assertIn('meta', response.data)
        self.assertIn('user_access_options', response.data['meta'])
        self.assertIn('user_role_options', response.data['meta'])

    def test_get_users_with_search(self):
        """Test retrieving users with search parameter"""
        response = self.client.get(f"{self.users_url}?search=One")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertEqual(len(response.data['data']), 1)
        self.assertEqual(response.data['data'][0]['username'], 'user1')

    def test_get_users_with_sorting(self):
        """Test retrieving users with sorting parameters"""
        response = self.client.get(f"{self.users_url}?sort_by=username&sort_direction=desc")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        # First user should be 'user2' when sorted by username in descending order
        self.assertEqual(response.data['data'][0]['username'], 'user2')

    def test_get_single_user(self):
        """Test retrieving a single user by ID"""
        response = self.client.get(self.user_detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertEqual(response.data['data']['username'], 'user1')
        self.assertEqual(response.data['data']['first_name'], 'User')
        self.assertEqual(response.data['data']['last_name'], 'One')

    def test_create_user(self):
        """Test creating a new user"""
        response = self.client.post(self.users_url, self.new_user_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data['success'])
        self.assertEqual(response.data['data']['username'], 'newuser')
        self.assertEqual(response.data['data']['email'], 'new@example.com')
        self.assertEqual(response.data['data']['first_name'], 'New')
        self.assertEqual(response.data['data']['last_name'], 'User')
        self.assertEqual(response.data['data']['role'], 'user')
        self.assertEqual(response.data['data']['user_access'], ['inventory', 'warehouse'])

    def test_create_user_invalid_data(self):
        """Test creating a user with invalid data"""
        invalid_data = {
            'username': '',  # Empty username
            'email': 'invalid-email',  # Invalid email
            'password': 'short',  # Short password
        }
        response = self.client.post(self.users_url, invalid_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data['success'])
        self.assertIn('errors', response.data)

    def test_update_user(self):
        """Test updating a user"""
        update_data = {
            'first_name': 'Updated',
            'last_name': 'Name',
            'user_access': ['delivery']
        }
        
        response = self.client.put(self.user_detail_url, update_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertEqual(response.data['data']['first_name'], 'Updated')
        self.assertEqual(response.data['data']['last_name'], 'Name')
        self.assertEqual(response.data['data']['user_access'], ['delivery'])

    def test_update_user_invalid_data(self):
        """Test updating a user with invalid data"""
        invalid_data = {
            'email': 'invalid-email',  # Invalid email
        }
        response = self.client.put(self.user_detail_url, invalid_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data['success'])
        self.assertIn('errors', response.data)

    def test_delete_user(self):
        """Test deleting a user"""
        response = self.client.delete(self.user_detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertIsNone(response.data['data'])
        
        # Verify user is deleted
        with self.assertRaises(User.DoesNotExist):
            User.objects.get(id=self.user1.id)

    def test_unauthenticated_access(self):
        """Test accessing user endpoints without authentication"""
        self.client.credentials()  # Remove authentication
        response = self.client.get(self.users_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)