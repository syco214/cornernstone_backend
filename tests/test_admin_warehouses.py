from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework import status
import json

from admin_api.models import Warehouse, Shelf

User = get_user_model()

class WarehouseTests(APITestCase):
    """
    Test suite for Warehouse API endpoints
    """
    
    def setUp(self):
        """
        Set up test data and authenticate
        """
        # Create test user and authenticate
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpassword123',
            is_staff=True
        )
        self.client.force_authenticate(user=self.user)
        
        # Create test warehouses
        self.warehouse1 = Warehouse.objects.create(
            name='Downtown Warehouse',
            address='123 Main St',
            city='New York'
        )
        
        self.warehouse2 = Warehouse.objects.create(
            name='Uptown Storage',
            address='456 Broadway',
            city='Chicago'
        )
        
        # Create shelves for warehouse1
        self.shelf1 = Shelf.objects.create(
            warehouse=self.warehouse1,
            number='A1',
            info='Electronics'
        )
        
        self.shelf2 = Shelf.objects.create(
            warehouse=self.warehouse1,
            number='B2',
            info='Clothing'
        )
        
        # URLs
        self.warehouses_url = reverse('warehouses')
        self.warehouse_detail_url = lambda pk: reverse('warehouse-detail', kwargs={'pk': pk})
    
    def test_get_warehouses_list(self):
        """
        Test retrieving a list of all warehouses
        """
        response = self.client.get(self.warehouses_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertEqual(len(response.data['data']), 2)
        self.assertIn('meta', response.data)
        self.assertIn('pagination', response.data['meta'])
    
    def test_get_warehouse_detail(self):
        """
        Test retrieving a single warehouse with its shelves
        """
        response = self.client.get(self.warehouse_detail_url(self.warehouse1.id))
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertEqual(response.data['data']['name'], 'Downtown Warehouse')
        self.assertEqual(len(response.data['data']['shelves']), 2)
    
    def test_search_warehouses(self):
        """
        Test searching warehouses by name, city, or address
        """
        # Search by name
        response = self.client.get(f"{self.warehouses_url}?search=Downtown")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['data']), 1)
        self.assertEqual(response.data['data'][0]['name'], 'Downtown Warehouse')
        
        # Search by city
        response = self.client.get(f"{self.warehouses_url}?search=Chicago")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['data']), 1)
        self.assertEqual(response.data['data'][0]['name'], 'Uptown Storage')
        
        # Search by address
        response = self.client.get(f"{self.warehouses_url}?search=Broadway")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['data']), 1)
        self.assertEqual(response.data['data'][0]['name'], 'Uptown Storage')
        
        # Search with no results
        response = self.client.get(f"{self.warehouses_url}?search=NonExistent")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['data']), 0)
    
    def test_sort_warehouses(self):
        """
        Test sorting warehouses by different fields
        """
        # Sort by name ascending (default)
        response = self.client.get(f"{self.warehouses_url}?sort_by=name&sort_direction=asc")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['data'][0]['name'], 'Downtown Warehouse')
        self.assertEqual(response.data['data'][1]['name'], 'Uptown Storage')
        
        # Sort by name descending
        response = self.client.get(f"{self.warehouses_url}?sort_by=name&sort_direction=desc")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['data'][0]['name'], 'Uptown Storage')
        self.assertEqual(response.data['data'][1]['name'], 'Downtown Warehouse')
        
        # Sort by city
        response = self.client.get(f"{self.warehouses_url}?sort_by=city&sort_direction=asc")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['data'][0]['city'], 'Chicago')
        self.assertEqual(response.data['data'][1]['city'], 'New York')
    
    def test_create_warehouse_basic(self):
        """
        Test creating a warehouse without shelves
        """
        data = {
            'name': 'West Side Warehouse',
            'address': '789 West Ave',
            'city': 'Los Angeles'
        }
        
        response = self.client.post(
            self.warehouses_url,
            data=json.dumps(data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data['success'])
        self.assertEqual(response.data['data']['name'], 'West Side Warehouse')
        
        # Verify warehouse was created in database
        self.assertTrue(Warehouse.objects.filter(name='West Side Warehouse').exists())
    
    def test_create_warehouse_with_shelves(self):
        """
        Test creating a warehouse with shelves
        """
        data = {
            'name': 'East Side Warehouse',
            'address': '321 East St',
            'city': 'Boston',
            'shelves': [
                {'number': 'C3', 'info': 'Books'},
                {'number': 'D4', 'info': 'Toys'}
            ]
        }
        
        response = self.client.post(
            self.warehouses_url,
            data=json.dumps(data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data['success'])
        self.assertEqual(response.data['data']['name'], 'East Side Warehouse')
        self.assertEqual(len(response.data['data']['shelves']), 2)
        
        # Verify warehouse and shelves were created in database
        warehouse = Warehouse.objects.get(name='East Side Warehouse')
        self.assertEqual(warehouse.shelves.count(), 2)
        self.assertTrue(warehouse.shelves.filter(number='C3').exists())
        self.assertTrue(warehouse.shelves.filter(number='D4').exists())
    
    def test_create_warehouse_invalid_data(self):
        """
        Test creating a warehouse with invalid data
        """
        # Missing required field (name)
        data = {
            'address': '789 West Ave',
            'city': 'Los Angeles'
        }
        
        response = self.client.post(
            self.warehouses_url,
            data=json.dumps(data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data['success'])
        self.assertIn('errors', response.data)
        self.assertIn('name', response.data['errors'])
    
    def test_update_warehouse_basic(self):
        """
        Test updating basic warehouse information
        """
        data = {
            'name': 'Updated Warehouse Name',
            'city': 'Updated City'
        }
        
        response = self.client.put(
            self.warehouse_detail_url(self.warehouse1.id),
            data=json.dumps(data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertEqual(response.data['data']['name'], 'Updated Warehouse Name')
        self.assertEqual(response.data['data']['city'], 'Updated City')
        
        # Verify warehouse was updated in database
        self.warehouse1.refresh_from_db()
        self.assertEqual(self.warehouse1.name, 'Updated Warehouse Name')
        self.assertEqual(self.warehouse1.city, 'Updated City')
    
    def test_update_warehouse_add_shelves(self):
        """
        Test adding new shelves to a warehouse
        """
        data = {
            'shelves': [
                {'id': self.shelf1.id, 'number': 'A1', 'info': 'Electronics'},
                {'id': self.shelf2.id, 'number': 'B2', 'info': 'Clothing'},
                {'number': 'E5', 'info': 'New Shelf'}
            ]
        }
        
        response = self.client.put(
            self.warehouse_detail_url(self.warehouse1.id),
            data=json.dumps(data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertEqual(len(response.data['data']['shelves']), 3)
        
        # Verify new shelf in database
        self.warehouse1.refresh_from_db()
        self.assertEqual(self.warehouse1.shelves.count(), 3)
        self.assertTrue(self.warehouse1.shelves.filter(number='E5').exists())
    
    def test_update_warehouse_modify_shelves(self):
        """
        Test modifying existing shelves in a warehouse
        """
        data = {
            'shelves': [
                {'id': self.shelf1.id, 'number': 'A1', 'info': 'Updated Info'},
                {'id': self.shelf2.id, 'number': 'B2-Updated', 'info': 'Clothing'}
            ]
        }
        
        response = self.client.put(
            self.warehouse_detail_url(self.warehouse1.id),
            data=json.dumps(data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        
        # Verify shelf updates in database
        self.shelf1.refresh_from_db()
        self.shelf2.refresh_from_db()
        self.assertEqual(self.shelf1.info, 'Updated Info')
        self.assertEqual(self.shelf2.number, 'B2-Updated')
    
    def test_update_warehouse_remove_shelves(self):
        """
        Test removing shelves from a warehouse
        """
        data = {
            'shelves': [
                {'id': self.shelf1.id, 'number': 'A1', 'info': 'Electronics'}
                # shelf2 is omitted, which should delete it
            ]
        }
        
        response = self.client.put(
            self.warehouse_detail_url(self.warehouse1.id),
            data=json.dumps(data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertEqual(len(response.data['data']['shelves']), 1)
        
        # Verify shelf was deleted from database
        self.warehouse1.refresh_from_db()
        self.assertEqual(self.warehouse1.shelves.count(), 1)
        self.assertFalse(self.warehouse1.shelves.filter(id=self.shelf2.id).exists())
    
    def test_delete_warehouse(self):
        """
        Test deleting a warehouse and its shelves
        """
        # Count warehouses and shelves before deletion
        warehouse_count_before = Warehouse.objects.count()
        shelf_count_before = Shelf.objects.count()
        
        response = self.client.delete(self.warehouse_detail_url(self.warehouse1.id))
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        
        # Verify warehouse was deleted
        self.assertEqual(Warehouse.objects.count(), warehouse_count_before - 1)
        self.assertFalse(Warehouse.objects.filter(id=self.warehouse1.id).exists())
        
        # Verify shelves were deleted (cascade delete)
        self.assertEqual(Shelf.objects.count(), shelf_count_before - 2)
        self.assertFalse(Shelf.objects.filter(warehouse_id=self.warehouse1.id).exists())
    
    def test_unauthenticated_access(self):
        """
        Test that unauthenticated users cannot access the API
        """
        # Log out
        self.client.force_authenticate(user=None)
        
        # Try to access warehouses list
        response = self.client.get(self.warehouses_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        
        # Try to access warehouse detail
        response = self.client.get(self.warehouse_detail_url(self.warehouse1.id))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        
        # Try to create a warehouse
        data = {'name': 'Test Warehouse', 'address': 'Test Address', 'city': 'Test City'}
        response = self.client.post(
            self.warehouses_url,
            data=json.dumps(data),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)