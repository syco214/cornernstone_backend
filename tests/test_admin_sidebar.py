from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()

class SidebarViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.sidebar_url = reverse('sidebar')
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpassword123',
            first_name='Test',
            last_name='User',
            role='user',
            user_access=['inventory', 'warehouse']
        )
        self.token = RefreshToken.for_user(self.user).access_token
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token}')

    def test_sidebar_authenticated(self):
        """Test sidebar data retrieval for authenticated user"""
        response = self.client.get(self.sidebar_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertEqual(response.data['data']['id'], self.user.id)
        self.assertEqual(response.data['data']['first_name'], 'Test')
        self.assertEqual(response.data['data']['last_name'], 'User')
        self.assertEqual(response.data['data']['role'], 'user')
        self.assertEqual(response.data['data']['user_access'], ['inventory', 'warehouse'])

    def test_sidebar_unauthenticated(self):
        """Test sidebar data retrieval for unauthenticated user"""
        self.client.credentials()  # Remove authentication
        response = self.client.get(self.sidebar_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)