from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from django.contrib.auth import get_user_model

User = get_user_model()

class LoginViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.login_url = reverse('admin_api:login')
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpassword123'
        )

    def test_login_success(self):
        """Test successful login with valid credentials"""
        data = {
            'username': 'testuser',
            'password': 'testpassword123'
        }
        response = self.client.post(self.login_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertIn('token', response.data['data'])
        self.assertIn('refresh', response.data['data'])
        self.assertEqual(response.data['data']['user']['username'], 'testuser')
        self.assertEqual(response.data['data']['user']['id'], self.user.id)

    def test_login_invalid_credentials(self):
        """Test login with invalid credentials"""
        data = {
            'username': 'testuser',
            'password': 'wrongpassword'
        }
        response = self.client.post(self.login_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertFalse(response.data['success'])
        self.assertEqual(response.data['error'], 'Invalid credentials')

    def test_login_missing_fields(self):
        """Test login with missing fields"""
        data = {
            'username': 'testuser'
            # Missing password
        }
        response = self.client.post(self.login_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertFalse(response.data['success'])