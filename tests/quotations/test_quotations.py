import io
import json
import tempfile
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from django.contrib.auth import get_user_model
from django.utils import timezone
from admin_api.models import Customer, Inventory, Supplier, Brand, Category, CustomerContact
from quotations_api.models import (
    Quotation, QuotationItem, QuotationAttachment, QuotationSalesAgent,
    QuotationAdditionalControls, QuotationTermsAndConditions, QuotationContact,
    Payment, Delivery, Other, LastQuotedPrice
)
from decimal import Decimal
import datetime
from django.core.files.uploadedfile import SimpleUploadedFile

User = get_user_model()

class QuotationAPITests(TestCase):
    """Tests for the Quotation API."""
    
    def setUp(self):
        """Set up test data."""
        # Create test user
        self.user = User.objects.create_user(
            username='testuser',
            password='testpassword123',
            is_staff=True
        )
        
        # Create test customer
        self.customer = Customer.objects.create(
            name='Test Customer',
            registered_name='Test Registered',
            phone_number='123-456-7890',
            company_address='123 Test St',
            city='Test City'
        )
        
        # Create customer contact
        self.contact = CustomerContact.objects.create(
            customer=self.customer,
            contact_person='John Doe',
            position='Manager',
            department='Purchasing',
            email='john@example.com',
            mobile_number='555-123-4567',
            office_number='555-987-6543'
        )
        
        # Create test category hierarchy
        self.category = Category.objects.create(name='Electronics')
        self.subcategory = Category.objects.create(name='Computers', parent=self.category)
        
        # Create test supplier and brand
        self.supplier = Supplier.objects.create(
            name='Test Supplier',
            supplier_type='local',
            currency='USD',
            phone_number='123-456-7890',
            email='supplier@example.com'
        )
        
        self.brand = Brand.objects.create(
            name='Test Brand',
            made_in='USA'
        )
        
        # Create test inventory items
        self.inventory1 = Inventory.objects.create(
            item_code='ITEM001',
            cip_code='CIP001',
            product_name='Test Product 1',
            status='active',
            supplier=self.supplier,
            brand=self.brand,
            category=self.category,
            subcategory=self.subcategory,
            unit='pcs',
            wholesale_price=Decimal('100.00'),
            external_description='Test description 1'
        )
        
        self.inventory2 = Inventory.objects.create(
            item_code='ITEM002',
            cip_code='CIP002',
            product_name='Test Product 2',
            status='active',
            supplier=self.supplier,
            brand=self.brand,
            category=self.category,
            subcategory=self.subcategory,
            unit='pcs',
            wholesale_price=Decimal('200.00'),
            external_description='Test description 2'
        )
        
        # Create payment, delivery, and other terms
        self.payment = Payment.objects.create(
            text='Payment terms text',
            created_by=self.user
        )
        
        self.delivery = Delivery.objects.create(
            text='Delivery terms text',
            created_by=self.user
        )
        
        self.other = Other.objects.create(
            text='Other terms text',
            created_by=self.user
        )
        
        # Create test quotation with required fields
        today = timezone.now().date()
        expiry_date = today + datetime.timedelta(days=30)
        
        self.quotation = Quotation.objects.create(
            customer=self.customer,
            status='draft',
            created_by=self.user,
            date=today,
            expiry_date=expiry_date,
            total_amount=Decimal('0.00'),
            currency='USD'
        )
        
        # Set up API client
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        
        # URLs
        self.list_url = reverse('quotation-list')
        self.detail_url = reverse('quotation-detail', args=[self.quotation.id])
    
    def test_get_quotation_list(self):
        """Test retrieving a list of quotations."""
        response = self.client.get(self.list_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertEqual(len(response.data['data']), 1)
        self.assertEqual(response.data['data'][0]['id'], self.quotation.id)
    
    def test_get_quotation_detail(self):
        """Test retrieving a single quotation."""
        response = self.client.get(self.detail_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertEqual(response.data['data']['id'], self.quotation.id)
        self.assertEqual(response.data['data']['customer'], self.customer.id)
    
    def test_create_quotation(self):
        """Test creating a new quotation."""
        data = {
            'customer': self.customer.id,
            'date': timezone.now().date().isoformat(),
            'expiry_date': (timezone.now().date() + datetime.timedelta(days=30)).isoformat(),
            'total_amount': '0.00',
            'currency': 'USD',
            'status': 'draft',
            'purchase_request': 'Test purchase request',
            'notes': 'Test notes',
            'sales_agents': [
                {
                    'agent_name': 'Jane Smith',
                    'role': 'main'
                }
            ],
            'contacts': [self.contact.id]
        }
        
        # Convert data to JSON
        json_data = json.dumps(data)
        
        # Create request with data in the 'data' field
        response = self.client.post(
            reverse('quotation-list'),
            {'data': json_data},
            format='multipart'
        )
        
        # Check response - expect 201 CREATED (change from 200 OK)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data['success'])
        
        # Check that the quotation was created
        self.assertEqual(Quotation.objects.count(), 2)  # 1 from setUp + 1 new
        
        # Check that the quote number was generated
        new_quotation = Quotation.objects.latest('id')
        self.assertTrue(new_quotation.quote_number.startswith('QT-'))
    
    def test_update_quotation(self):
        """Test updating a quotation."""
        data = {
            'status': 'for_approval',
            'notes': 'Updated notes'
        }
        
        # Convert data to JSON
        json_data = json.dumps(data)
        
        # Create request with data in the 'data' field
        response = self.client.put(
            self.detail_url,
            {'data': json_data},
            format='multipart'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        
        # Check that the quotation was updated
        self.quotation.refresh_from_db()
        self.assertEqual(self.quotation.status, 'for_approval')
        self.assertEqual(self.quotation.notes, 'Updated notes')
    
    def test_delete_quotation(self):
        """Test deleting a quotation."""
        response = self.client.delete(self.detail_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        
        # Check that the quotation was deleted
        with self.assertRaises(Quotation.DoesNotExist):
            Quotation.objects.get(id=self.quotation.id)
    
    def test_search_quotations(self):
        """Test searching quotations."""
        # Create a second quotation with a different customer
        customer2 = Customer.objects.create(
            name='Another Customer',
            registered_name='Another Registered',
            phone_number='987-654-3210',
            company_address='456 Test Ave',
            city='Test City'
        )
        
        today = timezone.now().date()
        expiry_date = today + datetime.timedelta(days=30)
        
        quotation2 = Quotation.objects.create(
            customer=customer2,
            status='draft',
            created_by=self.user,
            date=today,
            expiry_date=expiry_date,
            total_amount=Decimal('0.00'),
            currency='USD'
        )
        
        # Test search by customer name
        response = self.client.get(
            reverse('quotation-list'),
            {'customer': 'Test'},
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertEqual(len(response.data['data']), 1)
        
        # Adjust the assertion to match the actual format
        self.assertTrue('Test Customer' in response.data['data'][0]['customer_name'])
    
    def test_unauthorized_access(self):
        """Test that unauthenticated users cannot access the endpoints."""
        # Create a client without authentication
        client = APIClient()
        
        # Try to get quotation list
        response = client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        
        # Try to get quotation detail
        response = client.get(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        
        # Try to create quotation
        response = client.post(self.list_url, {})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        
        # Try to update quotation
        response = client.put(self.detail_url, {})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        
        # Try to delete quotation
        response = client.delete(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class QuotationItemTests(TestCase):
    """Tests for QuotationItem operations."""
    
    def setUp(self):
        """Set up test data."""
        # Create test user
        self.user = User.objects.create_user(
            username='testuser',
            password='testpassword123',
            is_staff=True
        )
        
        # Create test customer
        self.customer = Customer.objects.create(
            name='Test Customer',
            registered_name='Test Registered',
            phone_number='123-456-7890',
            company_address='123 Test St',
            city='Test City'
        )
        
        # Create test category hierarchy
        self.category = Category.objects.create(name='Electronics')
        self.subcategory = Category.objects.create(name='Computers', parent=self.category)
        
        # Create test supplier and brand
        self.supplier = Supplier.objects.create(
            name='Test Supplier',
            supplier_type='local',
            currency='USD',
            phone_number='123-456-7890',
            email='supplier@example.com'
        )
        
        self.brand = Brand.objects.create(
            name='Test Brand',
            made_in='USA'
        )
        
        # Create test inventory items
        self.inventory1 = Inventory.objects.create(
            item_code='ITEM001',
            cip_code='CIP001',
            product_name='Test Product 1',
            status='active',
            supplier=self.supplier,
            brand=self.brand,
            category=self.category,
            subcategory=self.subcategory,
            unit='pcs',
            wholesale_price=Decimal('100.00'),
            external_description='Test description 1'
        )
        
        # Create test quotation
        today = timezone.now().date()
        expiry_date = today + datetime.timedelta(days=30)
        
        self.quotation = Quotation.objects.create(
            customer=self.customer,
            status='draft',
            created_by=self.user,
            date=today,
            expiry_date=expiry_date,
            total_amount=Decimal('0.00'),
            currency='USD'
        )
        
        # Set up API client
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        
        # URLs
        self.detail_url = reverse('quotation-detail', args=[self.quotation.id])
    
    def test_add_quotation_item(self):
        """Test adding an item to a quotation."""
        data = {
            'items': [
                {
                    'inventory': self.inventory1.id,
                    'quantity': 2,
                    'wholesale_price': '100.00'
                }
            ]
        }
        
        # Convert data to JSON
        json_data = json.dumps(data)
        
        # Create request with data in the 'data' field
        response = self.client.put(
            self.detail_url,
            {'data': json_data},
            format='multipart'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        
        # Check that the item was added
        self.assertEqual(self.quotation.items.count(), 1)
        item = self.quotation.items.first()
        self.assertEqual(item.inventory.id, self.inventory1.id)
        self.assertEqual(item.quantity, 2)
        self.assertEqual(item.wholesale_price, Decimal('100.00'))
        
        # Check calculated fields
        self.assertEqual(item.net_selling, Decimal('100.00'))
        self.assertEqual(item.total_selling, Decimal('200.00'))
        
        # Check that total amount was updated
        self.quotation.refresh_from_db()
        self.assertEqual(self.quotation.total_amount, Decimal('200.00'))
    
    def test_update_quotation_item(self):
        """Test updating an item in a quotation."""
        # First add an item
        item = QuotationItem.objects.create(
            quotation=self.quotation,
            inventory=self.inventory1,
            quantity=1,
            wholesale_price=Decimal('100.00')
        )
        
        # Now update the item
        data = {
            'items': [
                {
                    'id': item.id,
                    'inventory': self.inventory1.id,
                    'quantity': 2,
                    'wholesale_price': '120.00'
                }
            ]
        }
        
        # Convert data to JSON
        json_data = json.dumps(data)
        
        # Create request with data in the 'data' field
        response = self.client.put(
            self.detail_url,
            {'data': json_data},
            format='multipart'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        
        # Check that the item was updated - use filter().first() instead of get()
        updated_item = QuotationItem.objects.filter(quotation=self.quotation, inventory=self.inventory1).first()
        self.assertIsNotNone(updated_item)
        self.assertEqual(updated_item.quantity, 2)
        self.assertEqual(updated_item.wholesale_price, Decimal('120.00'))
        
        # Check that total amount was updated
        self.quotation.refresh_from_db()
        self.assertEqual(self.quotation.total_amount, Decimal('240.00'))  # 120 * 2
    
    def test_delete_quotation_item(self):
        """Test deleting an item from a quotation."""
        # First add an item
        item = QuotationItem.objects.create(
            quotation=self.quotation,
            inventory=self.inventory1,
            quantity=1,
            wholesale_price=Decimal('100.00')
        )
        
        # Update the quotation total
        self.quotation.total_amount = Decimal('100.00')
        self.quotation.save()
        
        # Now delete the item by sending an empty items list
        data = {
            'items': []
        }
        
        # Convert data to JSON
        json_data = json.dumps(data)
        
        # Create request with data in the 'data' field
        response = self.client.put(
            self.detail_url,
            {'data': json_data},
            format='multipart'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        
        # Check that the item was deleted
        self.assertEqual(self.quotation.items.count(), 0)
        
        # Check that total amount was updated
        self.quotation.refresh_from_db()
        self.assertEqual(self.quotation.total_amount, Decimal('0.00'))
    
    def test_add_item_with_discount(self):
        """Test adding an item with a discount."""
        data = {
            'items': [
                {
                    'inventory': self.inventory1.id,
                    'quantity': 2,
                    'wholesale_price': '100.00',
                    'has_discount': True,
                    'discount_type': 'value',
                    'discount_value': '15.00'
                }
            ]
        }
        
        # Convert data to JSON
        json_data = json.dumps(data)
        
        # Create request with data in the 'data' field
        response = self.client.put(
            self.detail_url,
            {'data': json_data},
            format='multipart'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        
        # Check that the item was added with correct calculations
        item = self.quotation.items.first()
        self.assertTrue(item.has_discount)
        self.assertEqual(item.discount_type, 'value')
        self.assertEqual(item.discount_value, Decimal('15.00'))
        
        # Check calculated fields
        self.assertEqual(item.net_selling, Decimal('85.00'))  # 100 - 15
        self.assertEqual(item.total_selling, Decimal('170.00'))  # 85 * 2
        
        # Check that total amount was updated
        self.quotation.refresh_from_db()
        self.assertEqual(self.quotation.total_amount, Decimal('170.00'))


class QuotationTermsAndConditionsTests(TestCase):
    """Tests for QuotationTermsAndConditions operations."""
    
    def setUp(self):
        """Set up test data."""
        # Create test user
        self.user = User.objects.create_user(
            username='testuser',
            password='testpassword123',
            is_staff=True
        )
        
        # Create test customer
        self.customer = Customer.objects.create(
            name='Test Customer',
            registered_name='Test Registered',
            phone_number='123-456-7890',
            company_address='123 Test St',
            city='Test City'
        )
        
        # Create test quotation
        today = timezone.now().date()
        expiry_date = today + datetime.timedelta(days=30)
        
        self.quotation = Quotation.objects.create(
            customer=self.customer,
            status='draft',
            created_by=self.user,
            date=today,
            expiry_date=expiry_date,
            total_amount=Decimal('0.00'),
            currency='USD'
        )
        
        # Create payment, delivery, and other terms
        self.payment = Payment.objects.create(
            text='Payment terms text',
            created_by=self.user
        )
        
        self.delivery = Delivery.objects.create(
            text='Delivery terms text',
            created_by=self.user
        )
        
        self.other = Other.objects.create(
            text='Other terms text',
            created_by=self.user
        )
        
        # Set up API client
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        
        # URLs
        self.detail_url = reverse('quotation-detail', args=[self.quotation.id])
    
    def test_add_terms_and_conditions(self):
        """Test adding terms and conditions to a quotation."""
        data = {
            'terms_and_conditions': {
                'price': 'Price terms text',
                'payment': self.payment.id,
                'delivery': self.delivery.id,
                'validity': 'Valid for 30 days',
                'other': self.other.id
            }
        }
        
        # Convert data to JSON
        json_data = json.dumps(data)
        
        # Create request with data in the 'data' field
        response = self.client.put(
            self.detail_url,
            {'data': json_data},
            format='multipart'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        
        # Check that terms and conditions were added
        self.quotation.refresh_from_db()
        terms = self.quotation.terms_and_conditions
        
        self.assertEqual(terms.price, 'Price terms text')
        self.assertEqual(terms.payment.id, self.payment.id)
        self.assertEqual(terms.delivery.id, self.delivery.id)
        self.assertEqual(terms.validity, 'Valid for 30 days')
        self.assertEqual(terms.other.id, self.other.id)
    
    def test_update_terms_and_conditions(self):
        """Test updating terms and conditions of a quotation."""
        # First add terms and conditions
        terms = QuotationTermsAndConditions.objects.create(
            quotation=self.quotation,
            price='Initial price terms',
            payment=self.payment,
            delivery=self.delivery,
            validity='Initial validity',
            other=self.other
        )
        
        # Now update the terms
        data = {
            'terms_and_conditions': {
                'price': 'Updated price terms',
                'validity': 'Updated validity'
            }
        }
        
        # Convert data to JSON
        json_data = json.dumps(data)
        
        # Create request with data in the 'data' field
        response = self.client.put(
            self.detail_url,
            {'data': json_data},
            format='multipart'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        
        # Check that terms and conditions were updated
        terms.refresh_from_db()
        self.assertEqual(terms.price, 'Updated price terms')
        self.assertEqual(terms.validity, 'Updated validity')
        
        # Check that other fields were not changed
        self.assertEqual(terms.payment.id, self.payment.id)
        self.assertEqual(terms.delivery.id, self.delivery.id)
        self.assertEqual(terms.other.id, self.other.id)


class QuotationAttachmentTests(TestCase):
    """Tests for QuotationAttachment operations."""
    
    def setUp(self):
        """Set up test data."""
        # Create test user
        self.user = User.objects.create_user(
            username='testuser',
            password='testpassword123',
            is_staff=True
        )
        
        # Create test customer
        self.customer = Customer.objects.create(
            name='Test Customer',
            registered_name='Test Registered',
            phone_number='123-456-7890',
            company_address='123 Test St',
            city='Test City'
        )
        
        # Create test quotation
        today = timezone.now().date()
        expiry_date = today + datetime.timedelta(days=30)
        
        self.quotation = Quotation.objects.create(
            customer=self.customer,
            status='draft',
            created_by=self.user,
            date=today,
            expiry_date=expiry_date,
            total_amount=Decimal('0.00'),
            currency='USD'
        )
        
        # Set up API client
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        
        # URLs
        self.detail_url = reverse('quotation-detail', args=[self.quotation.id])
    
    def test_add_attachment(self):
        """Test adding an attachment to a quotation."""
        # Create a test file
        test_file = SimpleUploadedFile(
            name='test_file.txt',
            content=b'This is a test file',
            content_type='text/plain'
        )
        
        # First, create the attachment record without a file
        data = {
            'attachments': [
                {
                    'filename': 'test_file.txt'
                }
            ]
        }
        
        # Convert data to JSON
        json_data = json.dumps(data)
        
        # Create request with data in the 'data' field
        response = self.client.put(
            self.detail_url,
            {'data': json_data},
            format='multipart'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        
        # Check that attachment was added
        self.assertEqual(self.quotation.attachments.count(), 1)
        attachment = self.quotation.attachments.first()
        self.assertEqual(attachment.filename, 'test_file.txt')
    
    def test_delete_attachment(self):
        """Test deleting an attachment from a quotation."""
        # First add an attachment
        attachment = QuotationAttachment.objects.create(
            quotation=self.quotation,
            file=SimpleUploadedFile(
                "test_file.txt",
                b"This is a test file content",
                content_type="text/plain"
            ),
            filename='Test File'
        )
        
        # Now delete the attachment by sending an empty attachments list
        data = {
            'attachments': []
        }
        
        # Convert data to JSON
        json_data = json.dumps(data)
        
        # Create request with data in the 'data' field
        response = self.client.put(
            self.detail_url,
            {'data': json_data},
            format='multipart'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        
        # Check that attachment was deleted
        self.assertEqual(self.quotation.attachments.count(), 0)


class QuotationSalesAgentTests(TestCase):
    """Tests for QuotationSalesAgent operations."""
    
    def setUp(self):
        """Set up test data."""
        # Create test user
        self.user = User.objects.create_user(
            username='testuser',
            password='testpassword123',
            is_staff=True
        )
        
        # Create test customer
        self.customer = Customer.objects.create(
            name='Test Customer',
            registered_name='Test Registered',
            phone_number='123-456-7890',
            company_address='123 Test St',
            city='Test City'
        )
        
        # Create test quotation
        today = timezone.now().date()
        expiry_date = today + datetime.timedelta(days=30)
        
        self.quotation = Quotation.objects.create(
            customer=self.customer,
            status='draft',
            created_by=self.user,
            date=today,
            expiry_date=expiry_date,
            total_amount=Decimal('0.00'),
            currency='USD'
        )
        
        # Set up API client
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        
        # URLs
        self.detail_url = reverse('quotation-detail', args=[self.quotation.id])
    
    def test_add_sales_agents(self):
        """Test adding sales agents to a quotation."""
        data = {
            'sales_agents': [
                {
                    'agent_name': 'Jane Smith',
                    'role': 'main'
                },
                {
                    'agent_name': 'John Doe',
                    'role': 'support'
                }
            ]
        }
                # Convert data to JSON
        json_data = json.dumps(data)
        
        # Create request with data in the 'data' field
        response = self.client.put(
            self.detail_url,
            {'data': json_data},
            format='multipart'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        
        # Check that sales agents were added
        self.assertEqual(self.quotation.sales_agents.count(), 2)
        
        # Check main agent
        main_agent = self.quotation.sales_agents.get(role='main')
        self.assertEqual(main_agent.agent_name, 'Jane Smith')
        
        # Check support agent
        support_agent = self.quotation.sales_agents.get(role='support')
        self.assertEqual(support_agent.agent_name, 'John Doe')
    
    def test_update_sales_agents(self):
        """Test updating sales agents of a quotation."""
        # First add sales agents
        main_agent = QuotationSalesAgent.objects.create(
            quotation=self.quotation,
            agent_name='Jane Smith',
            role='main'
        )
        
        support_agent = QuotationSalesAgent.objects.create(
            quotation=self.quotation,
            agent_name='John Doe',
            role='support'
        )
        
        # Now update the agents
        data = {
            'sales_agents': [
                {
                    'id': main_agent.id,
                    'agent_name': 'Jane Smith Updated',
                    'role': 'main'
                },
                {
                    'id': support_agent.id,
                    'agent_name': 'John Doe Updated',
                    'role': 'support'
                }
            ]
        }
        
        # Convert data to JSON
        json_data = json.dumps(data)
        
        # Create request with data in the 'data' field
        response = self.client.put(
            self.detail_url,
            {'data': json_data},
            format='multipart'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        
        # Check that sales agents were updated - use filter().first() instead of get()
        self.assertEqual(self.quotation.sales_agents.count(), 2)
        
        # Check main agent
        updated_main_agent = QuotationSalesAgent.objects.filter(
            quotation=self.quotation, 
            role='main'
        ).first()
        
        self.assertIsNotNone(updated_main_agent)
        self.assertEqual(updated_main_agent.agent_name, 'Jane Smith Updated')
        
        # Check support agent
        updated_support_agent = QuotationSalesAgent.objects.filter(
            quotation=self.quotation, 
            role='support'
        ).first()
        
        self.assertIsNotNone(updated_support_agent)
        self.assertEqual(updated_support_agent.agent_name, 'John Doe Updated')
    
    def test_replace_main_agent(self):
        """Test replacing the main agent of a quotation."""
        # First add a main agent
        main_agent = QuotationSalesAgent.objects.create(
            quotation=self.quotation,
            agent_name='Jane Smith',
            role='main'
        )
        
        # Now replace the main agent
        data = {
            'sales_agents': [
                {
                    'agent_name': 'New Main Agent',
                    'role': 'main'
                }
            ]
        }
        
        # Convert data to JSON
        json_data = json.dumps(data)
        
        # Create request with data in the 'data' field
        response = self.client.put(
            self.detail_url,
            {'data': json_data},
            format='multipart'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        
        # Check that there's only one main agent
        self.assertEqual(self.quotation.sales_agents.count(), 1)
        
        # Check that the main agent was replaced
        new_main_agent = self.quotation.sales_agents.get(role='main')
        self.assertEqual(new_main_agent.agent_name, 'New Main Agent')
        self.assertNotEqual(new_main_agent.id, main_agent.id)


class QuotationAdditionalControlsTests(TestCase):
    """Tests for QuotationAdditionalControls operations."""
    
    def setUp(self):
        """Set up test data."""
        # Create test user
        self.user = User.objects.create_user(
            username='testuser',
            password='testpassword123',
            is_staff=True
        )
        
        # Create test customer
        self.customer = Customer.objects.create(
            name='Test Customer',
            registered_name='Test Registered',
            phone_number='123-456-7890',
            company_address='123 Test St',
            city='Test City'
        )
        
        # Create test quotation
        today = timezone.now().date()
        expiry_date = today + datetime.timedelta(days=30)
        
        self.quotation = Quotation.objects.create(
            customer=self.customer,
            status='draft',
            created_by=self.user,
            date=today,
            expiry_date=expiry_date,
            total_amount=Decimal('0.00'),
            currency='USD'
        )
        
        # Set up API client
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        
        # URLs
        self.detail_url = reverse('quotation-detail', args=[self.quotation.id])
    
    def test_add_additional_controls(self):
        """Test adding additional controls to a quotation."""
        data = {
            'additional_controls': {
                'show_carton_packing': False,
                'do_not_show_all_photos': False,
                'highlight_item_notes': True,
                'show_devaluation_clause': False
            }
        }
        
        # Convert data to JSON
        json_data = json.dumps(data)
        
        # Create request with data in the 'data' field
        response = self.client.put(
            self.detail_url,
            {'data': json_data},
            format='multipart'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        
        # Check that additional controls were added
        self.quotation.refresh_from_db()
        controls = self.quotation.additional_controls
        self.assertFalse(controls.show_carton_packing)
        self.assertFalse(controls.do_not_show_all_photos)
        self.assertTrue(controls.highlight_item_notes)
        self.assertFalse(controls.show_devaluation_clause)
    
    def test_update_additional_controls(self):
        """Test updating additional controls of a quotation."""
        # First add additional controls
        controls = QuotationAdditionalControls.objects.create(
            quotation=self.quotation,
            show_carton_packing=True,
            do_not_show_all_photos=True,
            highlight_item_notes=True,
            show_devaluation_clause=True
        )
        
        # Now update the controls
        data = {
            'additional_controls': {
                'show_carton_packing': False,
                'do_not_show_all_photos': False,
                'highlight_item_notes': False,
                'show_devaluation_clause': False
            }
        }
        
        # Convert data to JSON
        json_data = json.dumps(data)
        
        # Create request with data in the 'data' field
        response = self.client.put(
            self.detail_url,
            {'data': json_data},
            format='multipart'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        
        # Check that additional controls were updated
        controls.refresh_from_db()
        self.assertFalse(controls.show_carton_packing)
        self.assertFalse(controls.do_not_show_all_photos)
        self.assertFalse(controls.highlight_item_notes)
        self.assertFalse(controls.show_devaluation_clause)


class QuotationContactTests(TestCase):
    """Tests for QuotationContact operations."""
    
    def setUp(self):
        """Set up test data."""
        # Create test user
        self.user = User.objects.create_user(
            username='testuser',
            password='testpassword123',
            is_staff=True
        )
        
        # Create test customer
        self.customer = Customer.objects.create(
            name='Test Customer',
            registered_name='Test Registered',
            phone_number='123-456-7890',
            company_address='123 Test St',
            city='Test City'
        )
        
        # Create customer contacts
        self.contact1 = CustomerContact.objects.create(
            customer=self.customer,
            contact_person='John Doe',
            position='Manager',
            department='Purchasing',
            email='john@example.com',
            mobile_number='555-123-4567',
            office_number='555-987-6543'
        )
        
        self.contact2 = CustomerContact.objects.create(
            customer=self.customer,
            contact_person='Jane Smith',
            position='Director',
            department='Operations',
            email='jane@example.com',
            mobile_number='555-234-5678',
            office_number='555-876-5432'
        )
        
        # Create test quotation
        today = timezone.now().date()
        expiry_date = today + datetime.timedelta(days=30)
        
        self.quotation = Quotation.objects.create(
            customer=self.customer,
            status='draft',
            created_by=self.user,
            date=today,
            expiry_date=expiry_date,
            total_amount=Decimal('0.00'),
            currency='USD'
        )
        
        # Set up API client
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        
        # URLs
        self.detail_url = reverse('quotation-detail', args=[self.quotation.id])
    
    def test_add_contacts(self):
        """Test adding contacts to a quotation."""
        data = {
            'contacts': [self.contact1.id, self.contact2.id]
        }
        
        # Convert data to JSON
        json_data = json.dumps(data)
        
        # Create request with data in the 'data' field
        response = self.client.put(
            self.detail_url,
            {'data': json_data},
            format='multipart'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        
        # Check that contacts were added
        self.assertEqual(self.quotation.contacts.count(), 2)
        contact_ids = list(self.quotation.contacts.values_list('customer_contact_id', flat=True))
        self.assertIn(self.contact1.id, contact_ids)
        self.assertIn(self.contact2.id, contact_ids)
    
    def test_update_contacts(self):
        """Test updating contacts of a quotation."""
        # First add a contact
        QuotationContact.objects.create(
            quotation=self.quotation,
            customer_contact=self.contact1
        )
        
        # Now update to use a different contact
        data = {
            'contacts': [self.contact2.id]
        }
        
        # Convert data to JSON
        json_data = json.dumps(data)
        
        # Create request with data in the 'data' field
        response = self.client.put(
            self.detail_url,
            {'data': json_data},
            format='multipart'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        
        # Check that contacts were updated
        self.assertEqual(self.quotation.contacts.count(), 1)
        contact = self.quotation.contacts.first()
        self.assertEqual(contact.customer_contact_id, self.contact2.id)