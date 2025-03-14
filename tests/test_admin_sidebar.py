from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from admin_api.models import CustomUser

class SidebarTests(TestCase):
    def setUp(self):
        # Create admin user
        self.admin_user = CustomUser.objects.create_user(
            username='admin_user',
            email='admin@example.com',
            password='password123',
            first_name='Admin',
            last_name='User',
            role='admin',
            user_access=['inventory', 'quotations'],
            admin_access=['users', 'inventory']
        )
        
        # Create regular user
        self.regular_user = CustomUser.objects.create_user(
            username='regular_user',
            email='user@example.com',
            password='password123',
            first_name='Regular',
            last_name='User',
            role='user',
            user_access=['inventory']
        )
        
        # Create supervisor user with admin access
        self.supervisor_user = CustomUser.objects.create_user(
            username='supervisor_user',
            email='supervisor@example.com',
            password='password123',
            first_name='Supervisor',
            last_name='User',
            role='supervisor',
            user_access=['inventory', 'warehouse'],
            admin_access=['inventory', 'warehouses']
        )
        
        # Create supervisor user without admin access
        self.supervisor_no_admin = CustomUser.objects.create_user(
            username='supervisor_no_admin',
            email='supervisor2@example.com',
            password='password123',
            first_name='Supervisor',
            last_name='NoAdmin',
            role='supervisor',
            user_access=['inventory', 'warehouse']
        )
        
        self.client = APIClient()
        self.url = reverse('sidebar')

    def test_sidebar_admin_user(self):
        """Test that admin users can access the sidebar data with admin_access field"""
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.get(self.url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        
        # Check user data
        user_data = response.data['data']
        self.assertEqual(user_data['id'], self.admin_user.id)
        self.assertEqual(user_data['first_name'], 'Admin')
        self.assertEqual(user_data['last_name'], 'User')
        self.assertEqual(user_data['role'], 'admin')
        self.assertEqual(set(user_data['user_access']), set(['inventory', 'quotations']))
        self.assertEqual(set(user_data['admin_access']), set(['users', 'inventory']))

    def test_sidebar_regular_user(self):
        """Test that regular users can access the sidebar data with empty admin_access"""
        self.client.force_authenticate(user=self.regular_user)
        response = self.client.get(self.url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        
        # Check user data
        user_data = response.data['data']
        self.assertEqual(user_data['id'], self.regular_user.id)
        self.assertEqual(user_data['first_name'], 'Regular')
        self.assertEqual(user_data['last_name'], 'User')
        self.assertEqual(user_data['role'], 'user')
        self.assertEqual(set(user_data['user_access']), set(['inventory']))
        self.assertEqual(set(user_data['admin_access']), set())

    def test_sidebar_supervisor_with_admin_access(self):
        """Test that supervisors with admin_access can access the sidebar data with admin_access field"""
        self.client.force_authenticate(user=self.supervisor_user)
        response = self.client.get(self.url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        
        # Check user data
        user_data = response.data['data']
        self.assertEqual(user_data['id'], self.supervisor_user.id)
        self.assertEqual(user_data['first_name'], 'Supervisor')
        self.assertEqual(user_data['last_name'], 'User')
        self.assertEqual(user_data['role'], 'supervisor')
        self.assertEqual(set(user_data['user_access']), set(['inventory', 'warehouse']))
        self.assertEqual(set(user_data['admin_access']), set(['inventory', 'warehouses']))

    def test_sidebar_supervisor_without_admin_access(self):
        """Test that supervisors without admin_access can access the sidebar data with empty admin_access"""
        self.client.force_authenticate(user=self.supervisor_no_admin)
        response = self.client.get(self.url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        
        # Check user data
        user_data = response.data['data']
        self.assertEqual(user_data['id'], self.supervisor_no_admin.id)
        self.assertEqual(user_data['first_name'], 'Supervisor')
        self.assertEqual(user_data['last_name'], 'NoAdmin')
        self.assertEqual(user_data['role'], 'supervisor')
        self.assertEqual(set(user_data['user_access']), set(['inventory', 'warehouse']))
        self.assertEqual(set(user_data['admin_access']), set())

    def test_sidebar_unauthenticated(self):
        """Test that unauthenticated users cannot access the sidebar data"""
        response = self.client.get(self.url)
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)