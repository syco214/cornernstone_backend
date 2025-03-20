from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from django.contrib.auth import get_user_model
from admin_api.models import Supplier, SupplierAddress, SupplierContact, SupplierPaymentTerm, SupplierBank
import json

User = get_user_model()

class SupplierViewTests(TestCase):
    """Test suite for Supplier API views."""

    def setUp(self):
        """Set up test data."""
        # Create test user
        self.user = User.objects.create_user(
            username='testuser',
            password='testpassword123',
            is_staff=True
        )
        
        # Create test suppliers
        self.supplier1 = Supplier.objects.create(
            name='Test Supplier 1',
            supplier_type='local',
            currency='USD',
            phone_number='123-456-7890',
            email='supplier1@example.com',
            delivery_terms='FOB',
            remarks='Test remarks'
        )
        
        self.supplier2 = Supplier.objects.create(
            name='Test Supplier 2',
            supplier_type='foreign',
            currency='EURO',
            phone_number='987-654-3210',
            email='supplier2@example.com',
            delivery_terms='CIF',
            remarks='Another test remarks'
        )
        
        # Create address for supplier1
        self.address1 = SupplierAddress.objects.create(
            supplier=self.supplier1,
            description='Headquarters',
            address='123 Test Street, Test City, Test Country'
        )
        
        # Create contact for supplier1
        self.contact1 = SupplierContact.objects.create(
            supplier=self.supplier1,
            contact_person='John Doe',
            position='Sales Manager',
            department='Sales'
        )
        
        # Create bank for supplier1
        self.bank1 = SupplierBank.objects.create(
            supplier=self.supplier1,
            bank_name='Test Bank',
            bank_address='456 Bank Street, Bank City, Bank Country',
            account_number='123456789',
            currency='USD',
            iban='US123456789',
            swift_code='TESTBANKXXX',
            intermediary_bank='Intermediary Test Bank',
            intermediary_swift_name='INTERBANKXXX',
            beneficiary_name='Test Supplier Company',
            beneficiary_address='123 Beneficiary St, Beneficiary City'
        )
        
        # Create payment term for supplier1 with new structure
        self.payment_term1 = SupplierPaymentTerm.objects.create(
            supplier=self.supplier1,
            name='Net 30',
            credit_limit=10000.00,
            payment_terms='Net 30',
            dp_percentage=0.00,
            terms_days=30
        )
        
        # Set up API client
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        
        # URLs
        self.list_url = reverse('suppliers')
        self.detail_url = lambda pk: reverse('supplier-detail', args=[pk])
    
    def test_get_suppliers_list(self):
        """Test retrieving a list of suppliers."""
        response = self.client.get(self.list_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertEqual(len(response.data['data']), 2)
    
    def test_get_supplier_detail(self):
        """Test retrieving a single supplier with all related data."""
        response = self.client.get(self.detail_url(self.supplier1.id))
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        
        data = response.data['data']
        self.assertEqual(data['name'], 'Test Supplier 1')
        self.assertEqual(data['supplier_type'], 'local')
        
        # Check related data
        self.assertEqual(len(data['addresses']), 1)
        self.assertEqual(data['addresses'][0]['description'], 'Headquarters')
        
        self.assertEqual(len(data['contacts']), 1)
        self.assertEqual(data['contacts'][0]['contact_person'], 'John Doe')
        
        # Check bank data
        self.assertEqual(len(data['banks']), 1)
        self.assertEqual(data['banks'][0]['bank_name'], 'Test Bank')
        self.assertEqual(data['banks'][0]['swift_code'], 'TESTBANKXXX')
        
        self.assertIsNotNone(data['payment_term'])
        self.assertEqual(data['payment_term']['name'], 'Net 30')
    
    def test_create_supplier(self):
        """Test creating a new supplier with related data."""
        data = {
            'name': 'New Test Supplier',
            'supplier_type': 'local',
            'currency': 'USD',
            'phone_number': '555-123-4567',
            'email': 'newsupplier@example.com',
            'delivery_terms': 'EXW',
            'remarks': 'New supplier remarks',
            'addresses': [
                {
                    'description': 'Main Office',
                    'address': '456 New Street, New City, New Country'
                }
            ],
            'contacts': [
                {
                    'contact_person': 'Jane Smith',
                    'position': 'Procurement Officer',
                    'department': 'Procurement'
                }
            ],
            'banks': [
                {
                    'bank_name': 'New Bank',
                    'bank_address': '789 Bank Avenue, Bank City',
                    'account_number': '987654321',
                    'currency': 'USD',
                    'iban': 'US987654321',
                    'swift_code': 'NEWBANKXXX',
                    'intermediary_bank': 'New Intermediary Bank',
                    'intermediary_swift_name': 'NEWINTERBANKXXX',
                    'beneficiary_name': 'New Supplier Company',
                    'beneficiary_address': '789 New Beneficiary St'
                }
            ],
            'payment_term': {
                'name': 'Net 45',
                'credit_limit': 15000.00,
                'payment_terms': 'Net 45',
                'dp_percentage': 0.00,
                'terms_days': 45
            }
        }
        
        response = self.client.post(
            self.list_url,
            data=json.dumps(data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data['success'])
        
        # Verify supplier was created in database
        self.assertEqual(Supplier.objects.count(), 3)
        new_supplier = Supplier.objects.get(name='New Test Supplier')
        
        # Verify related objects were created
        self.assertEqual(new_supplier.addresses.count(), 1)
        self.assertEqual(new_supplier.contacts.count(), 1)
        self.assertEqual(new_supplier.banks.count(), 1)
        self.assertTrue(hasattr(new_supplier, 'payment_term'))
    
    def test_update_supplier(self):
        """Test updating an existing supplier."""
        data = {
            'name': 'Updated Supplier Name',
            'email': 'updated@example.com',
            'addresses': [
                {
                    'id': self.address1.id,
                    'description': 'Updated HQ',
                    'address': self.address1.address
                },
                {
                    'description': 'New Branch',
                    'address': '789 Branch St, Branch City'
                }
            ],
            'contacts': [
                {
                    'id': self.contact1.id,
                    'contact_person': 'Updated Person',
                    'position': self.contact1.position,
                    'department': self.contact1.department
                }
            ],
            'banks': [
                {
                    'id': self.bank1.id,
                    'bank_name': 'Updated Bank',
                    'bank_address': self.bank1.bank_address,
                    'account_number': 'UPDATED123456',
                    'currency': self.bank1.currency,
                    'iban': self.bank1.iban,
                    'swift_code': 'UPDATEDSWIFT',
                    'intermediary_bank': self.bank1.intermediary_bank,
                    'intermediary_swift_name': self.bank1.intermediary_swift_name,
                    'beneficiary_name': self.bank1.beneficiary_name,
                    'beneficiary_address': self.bank1.beneficiary_address
                },
                {
                    'bank_name': 'Second Bank',
                    'bank_address': '999 Second Bank St, Second City',
                    'account_number': '999888777',
                    'currency': 'EUR',
                    'iban': 'EU999888777',
                    'swift_code': 'SECONDBANKXXX',
                    'intermediary_bank': 'Second Intermediary',
                    'intermediary_swift_name': 'SECONDINTERXXX',
                    'beneficiary_name': 'Updated Supplier Company',
                    'beneficiary_address': '999 Updated Address St'
                }
            ],
            'payment_term': {
                'name': 'Updated Terms',
                'credit_limit': 20000.00,
                'payment_terms': 'Net 60',
                'dp_percentage': 10.00,
                'terms_days': 60
            }
        }
        
        response = self.client.put(
            self.detail_url(self.supplier1.id),
            data=json.dumps(data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        
        # Refresh from database
        self.supplier1.refresh_from_db()
        
        # Verify supplier was updated
        self.assertEqual(self.supplier1.name, 'Updated Supplier Name')
        self.assertEqual(self.supplier1.email, 'updated@example.com')
        
        # Verify related objects were updated
        self.assertEqual(self.supplier1.addresses.count(), 2)
        self.address1.refresh_from_db()
        self.assertEqual(self.address1.description, 'Updated HQ')
        
        self.contact1.refresh_from_db()
        self.assertEqual(self.contact1.contact_person, 'Updated Person')
        
        # Verify bank was updated and new one added
        self.assertEqual(self.supplier1.banks.count(), 2)
        self.bank1.refresh_from_db()
        self.assertEqual(self.bank1.bank_name, 'Updated Bank')
        self.assertEqual(self.bank1.swift_code, 'UPDATEDSWIFT')
        
        # Verify second bank was created
        self.assertTrue(self.supplier1.banks.filter(bank_name='Second Bank').exists())
        
        self.payment_term1.refresh_from_db()
        self.assertEqual(self.payment_term1.name, 'Updated Terms')
        self.assertEqual(self.payment_term1.credit_limit, 20000.00)
        self.assertEqual(self.payment_term1.payment_terms, 'Net 60')
        self.assertEqual(self.payment_term1.dp_percentage, 10.00)
        self.assertEqual(self.payment_term1.terms_days, 60)
    
    def test_delete_supplier(self):
        """Test deleting a supplier."""
        response = self.client.delete(self.detail_url(self.supplier1.id))
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        
        # Verify supplier was deleted
        self.assertEqual(Supplier.objects.count(), 1)
        
        # Verify related objects were deleted (cascade)
        self.assertEqual(SupplierAddress.objects.filter(supplier=self.supplier1).count(), 0)
        self.assertEqual(SupplierContact.objects.filter(supplier=self.supplier1).count(), 0)
        self.assertEqual(SupplierBank.objects.filter(supplier=self.supplier1).count(), 0)
        self.assertEqual(SupplierPaymentTerm.objects.filter(supplier=self.supplier1).count(), 0)
    
    def test_search_suppliers(self):
        """Test searching suppliers."""
        response = self.client.get(f"{self.list_url}?search=Test Supplier 1")
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertEqual(len(response.data['data']), 1)
        self.assertEqual(response.data['data'][0]['name'], 'Test Supplier 1')
    
    def test_filter_by_supplier_type(self):
        """Test filtering suppliers by type."""
        response = self.client.get(f"{self.list_url}?supplier_type=foreign")
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertEqual(len(response.data['data']), 1)
        self.assertEqual(response.data['data'][0]['name'], 'Test Supplier 2')
    
    def test_sort_suppliers(self):
        """Test sorting suppliers."""
        # Sort by name descending
        response = self.client.get(f"{self.list_url}?sort_by=name&sort_direction=desc")
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertEqual(response.data['data'][0]['name'], 'Test Supplier 2')
        self.assertEqual(response.data['data'][1]['name'], 'Test Supplier 1')
    
    def test_unauthorized_access(self):
        """Test that unauthenticated users cannot access the API."""
        # Create a new client without authentication
        client = APIClient()
        
        response = client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        
        response = client.post(self.list_url, {})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)