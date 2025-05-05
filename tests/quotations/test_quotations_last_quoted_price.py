from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase
from quotations_api.models import Quotation, LastQuotedPrice
from admin_api.models import Inventory, Customer, Supplier, Brand, Category
from decimal import Decimal
import datetime

User = get_user_model()

class LastQuotedPriceViewTests(APITestCase):
    def setUp(self):
        # Create test user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpassword'
        )
        
        # Create test suppliers
        self.supplier = Supplier.objects.create(
            name='Test Supplier',
            supplier_type='local',
            currency='USD',
            phone_number='555-1234',
            email='supplier@example.com'
        )
        
        # Create test brands
        self.brand = Brand.objects.create(
            name='Test Brand',
            made_in='Test Country'
        )
        
        # Create test categories
        self.category = Category.objects.create(
            name='Test Category'
        )
        
        # Create test customers
        self.customer1 = Customer.objects.create(
            name='Customer One',
            registered_name='Customer One Inc.',
            phone_number='123-456-7890',
            company_address='123 Test Street',
            city='Test City'
        )
        
        self.customer2 = Customer.objects.create(
            name='Customer Two',
            registered_name='Customer Two Inc.',
            phone_number='987-654-3210',
            company_address='456 Test Avenue',
            city='Test City'
        )
        
        # Create test inventory items
        self.inventory1 = Inventory.objects.create(
            item_code='INV001',
            cip_code='CIP001',
            product_name='Product One',
            supplier=self.supplier,
            brand=self.brand,
            category=self.category,
            status='active'
        )
        
        self.inventory2 = Inventory.objects.create(
            item_code='INV002',
            cip_code='CIP002',
            product_name='Product Two',
            supplier=self.supplier,
            brand=self.brand,
            category=self.category,
            status='active'
        )
        
        # Create test quotations
        self.quotation1 = Quotation.objects.create(
            quote_number='QT-2023-001',
            customer=self.customer1,
            date=datetime.date.today(),
            expiry_date=datetime.date.today() + datetime.timedelta(days=30),
            currency='USD',
            status='approved',
            created_by=self.user,
            last_modified_by=self.user,
            total_amount=Decimal('1000.00')  # Added total_amount
        )
        
        self.quotation2 = Quotation.objects.create(
            quote_number='QT-2023-002',
            customer=self.customer2,
            date=datetime.date.today(),
            expiry_date=datetime.date.today() + datetime.timedelta(days=30),
            currency='USD',
            status='approved',
            created_by=self.user,
            last_modified_by=self.user,
            total_amount=Decimal('2000.00')  # Added total_amount
        )
        
        # Create test last quoted prices
        self.last_quoted_price1 = LastQuotedPrice.objects.create(
            inventory=self.inventory1,
            customer=self.customer1,
            price=Decimal('100.00'),
            quotation=self.quotation1
        )
        
        self.last_quoted_price2 = LastQuotedPrice.objects.create(
            inventory=self.inventory1,
            customer=self.customer2,
            price=Decimal('110.00'),
            quotation=self.quotation2
        )
        
        self.last_quoted_price3 = LastQuotedPrice.objects.create(
            inventory=self.inventory2,
            customer=self.customer1,
            price=Decimal('200.00'),
            quotation=self.quotation1
        )
        
        # URL for the last quoted price endpoint
        self.url = reverse('quotations_api:last-quoted-prices')
    
    def test_get_all_last_quoted_prices(self):
        """Test retrieving all last quoted prices"""
        self.client.force_authenticate(user=self.user)
        
        response = self.client.get(self.url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['success'], True)
        self.assertEqual(len(response.data['data']), 3)
        
        # Check that the response contains the expected data
        self.assertEqual(response.data['data'][0]['price'], '200.00')  # Most recent first
        self.assertEqual(response.data['data'][1]['price'], '110.00')
        self.assertEqual(response.data['data'][2]['price'], '100.00')
    
    def test_filter_by_customer(self):
        """Test filtering last quoted prices by customer"""
        self.client.force_authenticate(user=self.user)
        
        url = f"{self.url}?customer_id={self.customer1.id}"
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['success'], True)
        self.assertEqual(len(response.data['data']), 2)
        
        # Check that only customer1's prices are returned
        customer_ids = [item['customer'] for item in response.data['data']]
        self.assertTrue(all(customer_id == self.customer1.id for customer_id in customer_ids))
    
    def test_filter_by_inventory(self):
        """Test filtering last quoted prices by inventory"""
        self.client.force_authenticate(user=self.user)
        
        url = f"{self.url}?inventory_id={self.inventory1.id}"
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['success'], True)
        self.assertEqual(len(response.data['data']), 2)
        
        # Check that only inventory1's prices are returned
        inventory_ids = [item['inventory'] for item in response.data['data']]
        self.assertTrue(all(inventory_id == self.inventory1.id for inventory_id in inventory_ids))
    
    def test_filter_by_customer_and_inventory(self):
        """Test filtering last quoted prices by both customer and inventory"""
        self.client.force_authenticate(user=self.user)
        
        url = f"{self.url}?customer_id={self.customer1.id}&inventory_id={self.inventory1.id}"
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['success'], True)
        self.assertEqual(len(response.data['data']), 1)
        
        # Check that only the specific customer-inventory combination is returned
        self.assertEqual(response.data['data'][0]['customer'], self.customer1.id)
        self.assertEqual(response.data['data'][0]['inventory'], self.inventory1.id)
    
    def test_pagination(self):
        """Test that pagination works correctly"""
        self.client.force_authenticate(user=self.user)
        
        # Create more inventory items and last quoted prices to trigger pagination
        for i in range(15):  # Create 15 more to ensure we have more than one page
            # Create a new inventory item for each iteration
            inventory = Inventory.objects.create(
                item_code=f'INV{100+i}',
                cip_code=f'CIP{100+i}',
                product_name=f'Product {100+i}',
                supplier=self.supplier,
                brand=self.brand,
                category=self.category,
                status='active'
            )
            
            # Create a new LastQuotedPrice with the new inventory
            LastQuotedPrice.objects.create(
                inventory=inventory,
                customer=self.customer2,
                price=Decimal(f'{300 + i}.00'),
                quotation=self.quotation2
            )
        
        # Test with default pagination (10 items per page)
        response = self.client.get(self.url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['success'], True)
        self.assertEqual(len(response.data['data']), 10)  # Default is 10 items per page
        
        # Check pagination metadata
        self.assertEqual(response.data['meta']['pagination']['count'], 18)  # 3 original + 15 new
        self.assertIsNotNone(response.data['meta']['pagination']['next'])
        self.assertIsNone(response.data['meta']['pagination']['previous'])
        
        # Check second page
        url = f"{self.url}?page=2"
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['data']), 8)  # 8 items on the second page
        self.assertIsNone(response.data['meta']['pagination']['next'])
        self.assertIsNotNone(response.data['meta']['pagination']['previous'])
    
    def test_unauthorized_access(self):
        """Test that unauthenticated users cannot access the endpoint"""
        # Logout
        self.client.force_authenticate(user=None)
        
        response = self.client.get(self.url)
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)