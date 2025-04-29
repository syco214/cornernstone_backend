from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from rest_framework import status
from rest_framework.test import APITestCase
from quotations_api.models import Quotation, Customer, LastQuotedPrice, QuotationItem
from quotations_api.serializers import QuotationSerializer
from admin_api.models import Inventory, Supplier, Brand, Category
from decimal import Decimal
import datetime

User = get_user_model()

class QuotationStatusViewTests(APITestCase):
    def setUp(self):
        # Create user groups
        self.supervisor_group = Group.objects.create(name='Supervisor')
        
        # Create users with different permissions
        self.regular_user = User.objects.create_user(
            username='regularuser',
            email='regular@example.com',
            password='regularpassword'
        )
        
        self.supervisor_user = User.objects.create_user(
            username='supervisoruser',
            email='supervisor@example.com',
            password='supervisorpassword'
        )
        self.supervisor_user.groups.add(self.supervisor_group)
        
        self.admin_user = User.objects.create_user(
            username='adminuser',
            email='admin@example.com',
            password='adminpassword',
            is_staff=True
        )
        
        # Create test customer
        self.customer = Customer.objects.create(
            name='Test Customer',
            registered_name='Test Registered Name',
            phone_number='123-456-7890',
            company_address='123 Test Street',
            city='Test City'
        )
        
        # Create required related objects for Inventory
        self.supplier = Supplier.objects.create(
            name='Test Supplier',
            supplier_type='local',
            currency='USD',
            phone_number='555-1234',
            email='supplier@example.com'
        )
        
        self.brand = Brand.objects.create(
            name='Test Brand',
            made_in='Test Country'
        )
        
        self.category = Category.objects.create(
            name='Test Category'
        )
        
        # Create test inventory item with required fields
        self.inventory_item = Inventory.objects.create(
            item_code='TEST001',
            cip_code='CIP001',
            product_name='Test Product',
            supplier=self.supplier,
            brand=self.brand,
            category=self.category,
            status='active'
        )
        
        # Create test quotation
        self.quotation = Quotation.objects.create(
            quote_number='QT-2023-001',
            customer=self.customer,
            date=datetime.date.today(),
            total_amount=Decimal('1000.00'),
            expiry_date=datetime.date.today() + datetime.timedelta(days=30),
            currency='USD',
            status='draft',
            created_by=self.regular_user,
            last_modified_by=self.regular_user
        )
        
        # Create quotation item with correct fields
        self.quotation_item = QuotationItem.objects.create(
            quotation=self.quotation,
            inventory=self.inventory_item,
            quantity=1,
            unit='pc',
            wholesale_price=Decimal('1000.00'),
            net_selling=Decimal('1000.00'),
            total_selling=Decimal('1000.00')
        )
        
        # URL for the status update endpoint
        self.url = reverse('quotation-status-update', kwargs={'pk': self.quotation.pk})
    
    def test_update_status_draft_to_for_approval(self):
        """Test updating status from draft to for_approval by regular user"""
        self.client.force_authenticate(user=self.regular_user)
        
        data = {'status': 'for_approval'}
        response = self.client.post(self.url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['success'], True)
        self.assertEqual(response.data['data']['status'], 'for_approval')
        
        # Verify database was updated
        self.quotation.refresh_from_db()
        self.assertEqual(self.quotation.status, 'for_approval')
        self.assertEqual(self.quotation.last_modified_by, self.regular_user)
    
    def test_update_status_for_approval_to_approved_by_admin(self):
        """Test updating status from for_approval to approved by admin"""
        # First set status to for_approval
        self.quotation.status = 'for_approval'
        self.quotation.save()
        
        self.client.force_authenticate(user=self.admin_user)
        
        data = {'status': 'approved'}
        response = self.client.post(self.url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['success'], True)
        self.assertEqual(response.data['data']['status'], 'approved')
        
        # Verify database was updated
        self.quotation.refresh_from_db()
        self.assertEqual(self.quotation.status, 'approved')
        self.assertEqual(self.quotation.last_modified_by, self.admin_user)
        
        # Verify LastQuotedPrice was created
        last_quoted_price = LastQuotedPrice.objects.filter(
            inventory=self.inventory_item,
            customer=self.customer
        ).first()
        
        self.assertIsNotNone(last_quoted_price)
        self.assertEqual(last_quoted_price.price, self.quotation_item.wholesale_price)  # Changed from selling_price to wholesale_price
        self.assertEqual(last_quoted_price.quotation, self.quotation)
    
    def test_update_status_for_approval_to_approved_by_supervisor(self):
        """Test updating status from for_approval to approved by supervisor"""
        # First set status to for_approval
        self.quotation.status = 'for_approval'
        self.quotation.save()
        
        self.client.force_authenticate(user=self.supervisor_user)
        
        data = {'status': 'approved'}
        response = self.client.post(self.url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['success'], True)
        self.assertEqual(response.data['data']['status'], 'approved')
        
        # Verify database was updated
        self.quotation.refresh_from_db()
        self.assertEqual(self.quotation.status, 'approved')
    
    def test_update_status_for_approval_to_rejected(self):
        """Test updating status from for_approval to rejected"""
        # First set status to for_approval
        self.quotation.status = 'for_approval'
        self.quotation.save()
        
        self.client.force_authenticate(user=self.admin_user)
        
        data = {'status': 'rejected'}
        response = self.client.post(self.url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['success'], True)
        self.assertEqual(response.data['data']['status'], 'rejected')
        
        # Verify database was updated
        self.quotation.refresh_from_db()
        self.assertEqual(self.quotation.status, 'rejected')
    
    def test_regular_user_cannot_approve(self):
        """Test that regular users cannot approve quotations"""
        # First set status to for_approval
        self.quotation.status = 'for_approval'
        self.quotation.save()
        
        self.client.force_authenticate(user=self.regular_user)
        
        data = {'status': 'approved'}
        response = self.client.post(self.url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data['success'], False)
        self.assertIn('You do not have permission', response.data['errors']['detail'])
        
        # Verify database was not updated
        self.quotation.refresh_from_db()
        self.assertEqual(self.quotation.status, 'for_approval')
    
    def test_invalid_status_transition(self):
        """Test invalid status transition"""
        self.client.force_authenticate(user=self.admin_user)
        
        # Try to change from draft to approved (not allowed)
        data = {'status': 'approved'}
        response = self.client.post(self.url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['success'], False)
        self.assertIn('Cannot change status', response.data['errors']['status'])
        
        # Verify database was not updated
        self.quotation.refresh_from_db()
        self.assertEqual(self.quotation.status, 'draft')
    
    def test_invalid_status_value(self):
        """Test providing an invalid status value"""
        self.client.force_authenticate(user=self.regular_user)
        
        data = {'status': 'invalid_status'}
        response = self.client.post(self.url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['success'], False)
        self.assertEqual(response.data['errors']['status'], 'Invalid status value')
        
        # Verify database was not updated
        self.quotation.refresh_from_db()
        self.assertEqual(self.quotation.status, 'draft')
    
    def test_missing_status(self):
        """Test not providing a status value"""
        self.client.force_authenticate(user=self.regular_user)
        
        data = {}  # Empty data
        response = self.client.post(self.url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['success'], False)
        self.assertEqual(response.data['errors']['status'], 'Invalid status value')
    
    def test_nonexistent_quotation(self):
        """Test updating status for a non-existent quotation"""
        self.client.force_authenticate(user=self.regular_user)
        
        url = reverse('quotation-status-update', kwargs={'pk': 9999})  # Non-existent ID
        data = {'status': 'for_approval'}
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
    
    def test_unauthorized_access(self):
        """Test that unauthenticated users cannot access the endpoint"""
        # Logout
        self.client.force_authenticate(user=None)
        
        data = {'status': 'for_approval'}
        response = self.client.post(self.url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)