import io
from decimal import Decimal
from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APITestCase
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken

from admin_api.models import Supplier, Inventory, Brand, Category
from purchase_order_api.models import (
    PurchaseOrder, 
    PurchaseOrderItem, 
    PurchaseOrderRoute,
    PurchaseOrderDownPayment,
    PackingList,
    PaymentDocument,
    InvoiceDocument
)

User = get_user_model()


class PurchaseOrderWorkflowTests(APITestCase):
    """Test cases for Purchase Order workflow operations"""
    
    def setUp(self):
        """Set up test data"""
        # Create test users with different roles
        self.admin_user = User.objects.create_user(
            username='admin',
            email='admin@test.com',
            password='testpass123',
            role='admin',
            user_access=['purchase_orders']
        )
        
        self.supervisor_user = User.objects.create_user(
            username='supervisor',
            email='supervisor@test.com',
            password='testpass123',
            role='supervisor',
            user_access=['purchase_orders']
        )
        
        self.user = User.objects.create_user(
            username='user',
            email='user@test.com',
            password='testpass123',
            role='user',
            user_access=['purchase_orders']
        )
        
        # Create test supplier
        self.supplier = Supplier.objects.create(
            name='Test Supplier',
            supplier_type='local',
            currency='USD',
            phone_number='123-456-7890',
            email='supplier@test.com',
            delivery_terms='FOB Test Port',
            remarks='Test supplier remarks'
        )
        
        # Create test brand and category for inventory
        self.brand = Brand.objects.create(name='Test Brand')
        self.category = Category.objects.create(name='Test Category')
        
        # Create test inventory items
        self.inventory1 = Inventory.objects.create(
            item_code='TEST001',
            cip_code='CIP001',
            product_name='Test Product 1',
            external_description='Test Item 1',
            unit='PCS',
            wholesale_price=Decimal('100.00'),
            supplier=self.supplier,
            brand=self.brand,
            category=self.category,
            created_by=self.user,
            last_modified_by=self.user
        )
        
        self.inventory2 = Inventory.objects.create(
            item_code='TEST002',
            cip_code='CIP002',
            product_name='Test Product 2',
            external_description='Test Item 2',
            unit='KG',
            wholesale_price=Decimal('50.00'),
            supplier=self.supplier,
            brand=self.brand,
            category=self.category,
            created_by=self.user,
            last_modified_by=self.user
        )
        
        # Create test purchase order
        self.purchase_order = PurchaseOrder.objects.create(
            supplier=self.supplier,
            supplier_type='local',
            delivery_terms='FOB Test Port',
            currency='USD',
            po_date='2024-01-01',
            created_by=self.user,
            last_modified_by=self.user
        )
        
        # Create test purchase order item
        self.po_item = PurchaseOrderItem.objects.create(
            purchase_order=self.purchase_order,
            inventory=self.inventory1,
            quantity=Decimal('10.00'),
            list_price=Decimal('100.00'),
            discount_type='none',
            discount_value=Decimal('0.00')
        )
        
        # Authenticate as admin user by default
        refresh = RefreshToken.for_user(self.admin_user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
    
    def test_submit_for_approval(self):
        """Test submitting a purchase order for approval"""
        url = reverse('purchase_order_api:po-submit-for-approval', kwargs={'pk': self.purchase_order.pk})
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertEqual(response.data['message'], 'Purchase order submitted for approval successfully')
        
        # Verify status change
        self.purchase_order.refresh_from_db()
        self.assertEqual(self.purchase_order.status, 'pending_approval')
        
        # Verify workflow step completion
        step1 = self.purchase_order.route_steps.filter(step=1).first()
        self.assertIsNotNone(step1)
        self.assertTrue(step1.is_completed)
    
    def test_submit_for_approval_invalid_status(self):
        """Test submitting PO for approval when not in draft status"""
        self.purchase_order.status = 'pending_approval'
        self.purchase_order.save()
        
        url = reverse('purchase_order_api:po-submit-for-approval', kwargs={'pk': self.purchase_order.pk})
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data['success'])
        self.assertIn('Cannot submit PO in', response.data['errors']['detail'])
    
    def test_approve_po(self):
        """Test approving a purchase order"""
        self.purchase_order.status = 'pending_approval'
        self.purchase_order.save()
        
        url = reverse('purchase_order_api:po-approve', kwargs={'pk': self.purchase_order.pk})
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertEqual(response.data['message'], 'Purchase order approved successfully')
        
        # Verify status change
        self.purchase_order.refresh_from_db()
        self.assertEqual(self.purchase_order.status, 'for_dp')
        self.assertEqual(self.purchase_order.approved_by, self.admin_user)
    
    def test_approve_po_invalid_status(self):
        """Test approving PO when not in pending approval status"""
        url = reverse('purchase_order_api:po-approve', kwargs={'pk': self.purchase_order.pk})
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data['success'])
        self.assertIn('Cannot approve PO in', response.data['errors']['detail'])
    
    def test_reject_po(self):
        """Test rejecting a purchase order"""
        self.purchase_order.status = 'pending_approval'
        self.purchase_order.save()
        
        url = reverse('purchase_order_api:po-reject', kwargs={'pk': self.purchase_order.pk})
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertEqual(response.data['message'], 'Purchase order rejected successfully')
        
        # Verify status change back to draft
        self.purchase_order.refresh_from_db()
        self.assertEqual(self.purchase_order.status, 'draft')
    
    def test_submit_dp_with_file(self):
        """Test submitting down payment with payment slip"""
        self.purchase_order.status = 'for_dp'
        self.purchase_order.save()
        
        # Create test file
        test_file = SimpleUploadedFile(
            'payment_slip.pdf',
            b'test payment slip content',
            content_type='application/pdf'
        )
        
        data = {
            'amount_paid': '500.00',
            'remarks': 'Test down payment',
            'payment_slip': test_file
        }
        
        url = reverse('purchase_order_api:po-submit-dp', kwargs={'pk': self.purchase_order.pk})
        response = self.client.post(url, data, format='multipart')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertEqual(response.data['message'], 'Down payment submitted successfully')
        
        # Verify down payment creation
        dp = PurchaseOrderDownPayment.objects.filter(purchase_order=self.purchase_order).first()
        self.assertIsNotNone(dp)
        self.assertEqual(dp.amount_paid, Decimal('500.00'))
        
        # Verify status change
        self.purchase_order.refresh_from_db()
        self.assertEqual(self.purchase_order.status, 'pending_dp_approval')
    
    def test_submit_dp_missing_amount(self):
        """Test submitting down payment without amount"""
        self.purchase_order.status = 'for_dp'
        self.purchase_order.save()
        
        data = {}  # Missing amount_paid
        
        url = reverse('purchase_order_api:po-submit-dp', kwargs={'pk': self.purchase_order.pk})
        response = self.client.post(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data['success'])
        self.assertIn('This field is required.', response.data['errors']['amount_paid'])
    
    def test_submit_dp_invalid_amount(self):
        """Test submitting down payment with invalid amount"""
        self.purchase_order.status = 'for_dp'
        self.purchase_order.save()
        
        data = {'amount_paid': '0'}  # Invalid amount (zero)
        
        url = reverse('purchase_order_api:po-submit-dp', kwargs={'pk': self.purchase_order.pk})
        response = self.client.post(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data['success'])
        self.assertIn('Amount must be greater than zero.', response.data['errors']['amount_paid'])
    
    def test_approve_dp(self):
        """Test approving down payment"""
        self.purchase_order.status = 'pending_dp_approval'
        self.purchase_order.save()
        
        url = reverse('purchase_order_api:po-approve-dp', kwargs={'pk': self.purchase_order.pk})
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertEqual(response.data['message'], 'Down payment approved successfully')
        
        # Verify status change
        self.purchase_order.refresh_from_db()
        self.assertEqual(self.purchase_order.status, 'confirm_ready_dates')
    
    def test_reject_dp(self):
        """Test rejecting down payment"""
        self.purchase_order.status = 'pending_dp_approval'
        self.purchase_order.save()
        
        url = reverse('purchase_order_api:po-reject-dp', kwargs={'pk': self.purchase_order.pk})
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertEqual(response.data['message'], 'Down payment rejected successfully')
        
        # Verify status change back to for_dp
        self.purchase_order.refresh_from_db()
        self.assertEqual(self.purchase_order.status, 'for_dp')
    
    def test_confirm_ready_dates_single_batch(self):
        """Test confirming ready dates with single batch"""
        self.purchase_order.status = 'confirm_ready_dates'
        self.purchase_order.save()
        
        data = {
            'items': [
                {
                    'item_id': self.po_item.pk,
                    'quantity': '10.00',
                    'ready_date': '2024-02-01'
                }
            ]
        }
        
        url = reverse('purchase_order_api:po-confirm-ready-dates', kwargs={'pk': self.purchase_order.pk})
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertEqual(response.data['message'], 'Ready dates confirmed successfully')
        
        # Verify status change
        self.purchase_order.refresh_from_db()
        self.assertEqual(self.purchase_order.status, 'packing_list_1')
        
        # Verify item ready date
        self.po_item.refresh_from_db()
        self.assertEqual(str(self.po_item.ready_date), '2024-02-01')
        self.assertEqual(self.po_item.batch_number, 1)
    
    def test_confirm_ready_dates_multiple_batches(self):
        """Test confirming ready dates with multiple batches"""
        # Create second item
        po_item2 = PurchaseOrderItem.objects.create(
            purchase_order=self.purchase_order,
            inventory=self.inventory2,
            quantity=Decimal('5.00'),
            list_price=Decimal('200.00'),
            discount_type='none',
            discount_value=Decimal('0.00')
        )
        
        self.purchase_order.status = 'confirm_ready_dates'
        self.purchase_order.save()
        
        data = {
            'items': [
                {
                    'item_id': self.po_item.pk,
                    'quantity': '5.00',
                    'ready_date': '2024-02-01'
                },
                {
                    'item_id': self.po_item.pk,
                    'quantity': '5.00',
                    'ready_date': '2024-02-15'
                },
                {
                    'item_id': po_item2.pk,
                    'quantity': '5.00',
                    'ready_date': '2024-02-01'
                }
            ]
        }
        
        url = reverse('purchase_order_api:po-confirm-ready-dates', kwargs={'pk': self.purchase_order.pk})
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        
        # Verify multiple items created for different ready dates
        items_batch_1 = self.purchase_order.items.filter(batch_number=1)
        items_batch_2 = self.purchase_order.items.filter(batch_number=2)
        
        self.assertTrue(items_batch_1.exists())
        self.assertTrue(items_batch_2.exists())
    
    def test_confirm_ready_dates_quantity_mismatch(self):
        """Test confirming ready dates with quantity mismatch"""
        self.purchase_order.status = 'confirm_ready_dates'
        self.purchase_order.save()
        
        data = {
            'items': [
                {
                    'item_id': self.po_item.pk,
                    'quantity': '5.00',  # Less than original 10.00
                    'ready_date': '2024-02-01'
                }
            ]
        }
        
        url = reverse('purchase_order_api:po-confirm-ready-dates', kwargs={'pk': self.purchase_order.pk})
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data['success'])
        self.assertIn('Total quantity for item', response.data['errors']['detail'])
    
    def test_submit_packing_list(self):
        """Test submitting packing list for batch 1"""
        # Set up workflow step
        PurchaseOrderRoute.objects.create(
            purchase_order=self.purchase_order,
            step=6,
            task='Packing List 1',
            is_required=True,
            access='purchase_orders',
            roles=['admin', 'supervisor', 'user']
        )
        
        # Create test document
        test_file = SimpleUploadedFile(
            'packing_list.pdf',
            b'test packing list content',
            content_type='application/pdf'
        )
        
        data = {
            'total_weight': '100.50',
            'total_packages': '5',
            'total_volume': '2.5',
            'document': test_file
        }
        
        url = reverse('purchase_order_api:submit-packing-list-1', kwargs={'pk': self.purchase_order.pk})
        response = self.client.post(url, data, format='multipart')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertIn('Packing list for batch 1 submitted successfully', response.data['message'])
        
        # Verify packing list creation
        packing_list = PackingList.objects.filter(
            purchase_order=self.purchase_order,
            batch_number=1
        ).first()
        self.assertIsNotNone(packing_list)
        self.assertEqual(packing_list.total_weight, Decimal('100.50'))
    
    def test_approve_import(self):
        """Test approving import for batch 1"""
        # Create packing list first
        PackingList.objects.create(
            purchase_order=self.purchase_order,
            batch_number=1,
            total_weight=Decimal('100.50'),
            total_packages=5,
            total_volume=Decimal('2.5'),
            document='test.pdf'
        )
        
        # Set up workflow step
        PurchaseOrderRoute.objects.create(
            purchase_order=self.purchase_order,
            step=7,
            task='Approve for Import 1',
            is_required=True,
            access='purchase_orders',
            roles=['admin', 'supervisor']
        )
        
        data = {'approve': True}
        
        url = reverse('purchase_order_api:approve-import-1', kwargs={'pk': self.purchase_order.pk})
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertIn('Import for batch 1 approved successfully', response.data['message'])
        
        # Verify packing list approval
        packing_list = PackingList.objects.get(
            purchase_order=self.purchase_order,
            batch_number=1
        )
        self.assertTrue(packing_list.approved)
    
    def test_reject_import(self):
        """Test rejecting import for batch 1"""
        # Create packing list first
        PackingList.objects.create(
            purchase_order=self.purchase_order,
            batch_number=1,
            total_weight=Decimal('100.50'),
            total_packages=5,
            total_volume=Decimal('2.5'),
            document='test.pdf'
        )
        
        # Set up workflow step
        PurchaseOrderRoute.objects.create(
            purchase_order=self.purchase_order,
            step=7,
            task='Approve for Import 1',
            is_required=True,
            access='purchase_orders',
            roles=['admin', 'supervisor']
        )
        
        data = {'approve': False}
        
        url = reverse('purchase_order_api:approve-import-1', kwargs={'pk': self.purchase_order.pk})
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertIn('Import for batch 1 rejected successfully', response.data['message'])
        
        # Verify packing list deletion
        self.assertFalse(PackingList.objects.filter(
            purchase_order=self.purchase_order,
            batch_number=1
        ).exists())
    
    def test_submit_payment(self):
        """Test submitting payment document for batch 1"""
        # Set up workflow step
        PurchaseOrderRoute.objects.create(
            purchase_order=self.purchase_order,
            step=8,
            task='Payment 1',
            is_required=True,
            access='purchase_orders',
            roles=['admin', 'supervisor', 'user']
        )
        
        # Create test document
        test_file = SimpleUploadedFile(
            'payment.pdf',
            b'test payment content',
            content_type='application/pdf'
        )
        
        data = {'document': test_file}
        
        url = reverse('purchase_order_api:submit-payment-1', kwargs={'pk': self.purchase_order.pk})
        response = self.client.post(url, data, format='multipart')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertIn('Payment for batch 1 submitted successfully', response.data['message'])
        
        # Verify payment document creation
        payment = PaymentDocument.objects.filter(
            purchase_order=self.purchase_order,
            batch_number=1
        ).first()
        self.assertIsNotNone(payment)
    
    def test_submit_invoice(self):
        """Test submitting invoice document for batch 1"""
        # Set up workflow step
        PurchaseOrderRoute.objects.create(
            purchase_order=self.purchase_order,
            step=9,
            task='Invoice 1',
            is_required=True,
            access='purchase_orders',
            roles=['admin', 'supervisor', 'user']
        )
        
        # Create test document
        test_file = SimpleUploadedFile(
            'invoice.pdf',
            b'test invoice content',
            content_type='application/pdf'
        )
        
        data = {'document': test_file}
        
        url = reverse('purchase_order_api:submit-invoice-1', kwargs={'pk': self.purchase_order.pk})
        response = self.client.post(url, data, format='multipart')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertIn('Invoice for batch 1 submitted successfully', response.data['message'])
        
        # Verify invoice document creation
        invoice = InvoiceDocument.objects.filter(
            purchase_order=self.purchase_order,
            batch_number=1
        ).first()
        self.assertIsNotNone(invoice)
    
    def test_get_po_route(self):
        """Test getting purchase order route steps"""
        url = reverse('purchase_order_api:purchase-order-route', kwargs={'po_id': self.purchase_order.pk})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertIsInstance(response.data['data'], list)
        
        # Verify initial workflow steps are created
        self.assertEqual(len(response.data['data']), 5)  # Initial 5 steps
        
        # Verify step details
        first_step = response.data['data'][0]
        self.assertEqual(first_step['step'], 1)
        self.assertEqual(first_step['task'], 'Draft')
    
    def test_permission_denied_regular_user_approve(self):
        """Test that regular users cannot approve POs"""
        # Switch to regular user
        refresh = RefreshToken.for_user(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
        
        self.purchase_order.status = 'pending_approval'
        self.purchase_order.save()
        
        url = reverse('purchase_order_api:po-approve', kwargs={'pk': self.purchase_order.pk})
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
    
    def test_supervisor_can_approve(self):
        """Test that supervisors can approve POs"""
        # Switch to supervisor user
        refresh = RefreshToken.for_user(self.supervisor_user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
        
        self.purchase_order.status = 'pending_approval'
        self.purchase_order.save()
        
        url = reverse('purchase_order_api:po-approve', kwargs={'pk': self.purchase_order.pk})
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
    
    def test_nonexistent_po_workflow(self):
        """Test workflow actions on non-existent PO"""
        url = reverse('purchase_order_api:po-submit-for-approval', kwargs={'pk': 99999})
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)