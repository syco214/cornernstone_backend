from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken
from admin_api.models import Category

User = get_user_model()

class CategoryViewTests(TestCase):
    """Tests for the Category API endpoints"""
    
    def setUp(self):
        """Set up test data and authentication"""
        self.client = APIClient()
        self.categories_url = reverse('categories')
        
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
        
        # Create test categories with hierarchy
        self.root_category1 = Category.objects.create(
            name='Root Category 1'
        )
        
        self.root_category2 = Category.objects.create(
            name='Root Category 2'
        )
        
        self.child_category1 = Category.objects.create(
            name='Child Category 1',
            parent=self.root_category1
        )
        
        self.child_category2 = Category.objects.create(
            name='Child Category 2',
            parent=self.root_category1
        )
        
        self.grandchild_category = Category.objects.create(
            name='Grandchild Category',
            parent=self.child_category1
        )
        
        # Authenticate as admin
        self.admin_token = RefreshToken.for_user(self.admin_user).access_token
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.admin_token}')
        
        # Category detail URL
        self.category_detail_url = reverse('category-detail', args=[self.root_category1.id])
        
        # New category data for creation tests
        self.new_category_data = {
            'name': 'New Category',
            'parent': None
        }
        
        self.new_child_category_data = {
            'name': 'New Child Category',
            'parent': self.root_category2.id
        }
        
        # Update data for PUT tests
        self.update_data = {
            'name': 'Updated Category'
        }

    def test_get_categories_list(self):
        """Test retrieving list of categories"""
        response = self.client.get(self.categories_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertEqual(len(response.data['data']), 5)  # 5 categories total
        
        # Check pagination metadata
        self.assertIn('meta', response.data)
        self.assertIn('pagination', response.data['meta'])
        self.assertEqual(response.data['meta']['pagination']['count'], 5)

    def test_get_root_categories(self):
        """Test retrieving only root categories"""
        response = self.client.get(f"{self.categories_url}?parent=root")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertEqual(len(response.data['data']), 2)  # 2 root categories

    def test_get_child_categories(self):
        """Test retrieving child categories of a specific parent"""
        response = self.client.get(f"{self.categories_url}?parent={self.root_category1.id}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertEqual(len(response.data['data']), 2)  # 2 child categories under root_category1

    def test_get_tree_view(self):
        """Test retrieving categories in tree view"""
        response = self.client.get(f"{self.categories_url}?tree=true")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertEqual(len(response.data['data']), 2)  # 2 root categories
        
        # Check that children are included
        root1_data = next(cat for cat in response.data['data'] if cat['name'] == 'Root Category 1')
        self.assertIn('children', root1_data)
        self.assertEqual(len(root1_data['children']), 2)  # 2 children under root_category1
        
        # Check that grandchildren are included
        child1_data = next(child for child in root1_data['children'] if child['name'] == 'Child Category 1')
        self.assertIn('children', child1_data)
        self.assertEqual(len(child1_data['children']), 1)  # 1 grandchild

    def test_get_categories_with_search(self):
        """Test retrieving categories with search parameter"""
        response = self.client.get(f"{self.categories_url}?search=Child")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertEqual(len(response.data['data']), 3)  # 3 categories with 'Child' in name

    def test_get_categories_with_sorting(self):
        """Test retrieving categories with sorting parameters"""
        response = self.client.get(f"{self.categories_url}?sort_by=name&sort_direction=desc")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        # First category should be 'Root Category 2' when sorted by name in descending order
        self.assertEqual(response.data['data'][0]['name'], 'Root Category 2')

    def test_get_single_category(self):
        """Test retrieving a single category by ID"""
        response = self.client.get(self.category_detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertEqual(response.data['data']['name'], 'Root Category 1')
        self.assertIsNone(response.data['data']['parent'])
        self.assertEqual(response.data['data']['level'], 0)
        self.assertEqual(response.data['data']['full_path'], 'Root Category 1')

    def test_get_child_category_details(self):
        """Test retrieving a child category with level and full path"""
        child_url = reverse('category-detail', args=[self.child_category1.id])
        response = self.client.get(child_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertEqual(response.data['data']['name'], 'Child Category 1')
        self.assertEqual(response.data['data']['parent'], self.root_category1.id)
        self.assertEqual(response.data['data']['level'], 1)
        self.assertEqual(response.data['data']['full_path'], 'Root Category 1 > Child Category 1')

    def test_create_root_category(self):
        """Test creating a new root category"""
        response = self.client.post(self.categories_url, self.new_category_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data['success'])
        self.assertEqual(response.data['data']['name'], 'New Category')
        self.assertIsNone(response.data['data']['parent'])
        self.assertEqual(response.data['data']['level'], 0)
        
        # Verify category was created in database
        self.assertTrue(Category.objects.filter(name='New Category', parent=None).exists())

    def test_create_child_category(self):
        """Test creating a new child category"""
        response = self.client.post(self.categories_url, self.new_child_category_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data['success'])
        self.assertEqual(response.data['data']['name'], 'New Child Category')
        self.assertEqual(response.data['data']['parent'], self.root_category2.id)
        self.assertEqual(response.data['data']['level'], 1)
        
        # Verify category was created in database
        self.assertTrue(Category.objects.filter(name='New Child Category', parent=self.root_category2).exists())

    def test_create_category_invalid_data(self):
        """Test creating a category with invalid data"""
        invalid_data = {
            'name': '',  # Empty name
            'parent': None
        }
        response = self.client.post(self.categories_url, invalid_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data['success'])
        self.assertIn('errors', response.data)
        self.assertIn('name', response.data['errors'])

    def test_create_duplicate_category(self):
        """Test creating a category with a name that already exists under same parent"""
        duplicate_data = {
            'name': 'Child Category 1',  # Already exists under root_category1
            'parent': self.root_category1.id
        }
        response = self.client.post(self.categories_url, duplicate_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data['success'])
        self.assertIn('errors', response.data)

    def test_update_category(self):
        """Test updating a category"""
        response = self.client.put(self.category_detail_url, self.update_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertEqual(response.data['data']['name'], 'Updated Category')
        
        # Verify category was updated in database
        updated_category = Category.objects.get(id=self.root_category1.id)
        self.assertEqual(updated_category.name, 'Updated Category')

    def test_update_category_parent(self):
        """Test updating a category's parent"""
        update_parent_data = {
            'parent': self.root_category2.id
        }
        child_url = reverse('category-detail', args=[self.child_category2.id])
        response = self.client.put(child_url, update_parent_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertEqual(response.data['data']['parent'], self.root_category2.id)
        
        # Verify category was updated in database
        updated_category = Category.objects.get(id=self.child_category2.id)
        self.assertEqual(updated_category.parent.id, self.root_category2.id)

    def test_delete_category(self):
        """Test deleting a category"""
        response = self.client.delete(self.category_detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        
        # Verify category is deleted
        with self.assertRaises(Category.DoesNotExist):
            Category.objects.get(id=self.root_category1.id)
        
        # Verify children are also deleted (cascade)
        with self.assertRaises(Category.DoesNotExist):
            Category.objects.get(id=self.child_category1.id)
        
        with self.assertRaises(Category.DoesNotExist):
            Category.objects.get(id=self.child_category2.id)
        
        with self.assertRaises(Category.DoesNotExist):
            Category.objects.get(id=self.grandchild_category.id)

    def test_unauthenticated_access(self):
        """Test accessing category endpoints without authentication"""
        self.client.credentials()  # Remove authentication
        response = self.client.get(self.categories_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)