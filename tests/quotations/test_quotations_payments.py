from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase
from quotations_api.models import Payment
from quotations_api.serializers import PaymentSerializer

User = get_user_model()

class PaymentViewTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpassword'
        )
        self.admin_user = User.objects.create_user(
            username='adminuser',
            email='admin@example.com',
            password='adminpassword',
            is_staff=True
        )
        
        # Create test payments
        self.payment1 = Payment.objects.create(
            text='Payment due within 30 days',
            created_by=self.user
        )
        self.payment2 = Payment.objects.create(
            text='50% advance payment required',
            created_by=self.user
        )
        self.payment3 = Payment.objects.create(
            text='Payment via bank transfer only',
            created_by=self.admin_user
        )
        
        # URLs - using the correct URL names from urls.py
        self.list_url = reverse('payment-list-create')
        self.detail_url = reverse('payment-detail', kwargs={'pk': self.payment1.pk})
        
        # Authenticate
        self.client.force_authenticate(user=self.user)

    def test_get_payment_list(self):
        response = self.client.get(self.list_url)
        payments = Payment.objects.all().order_by('-created_on')
        serializer = PaymentSerializer(payments, many=True)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['success'], True)
        self.assertEqual(len(response.data['data']), 3)
        self.assertEqual(response.data['data'][0]['id'], serializer.data[0]['id'])

    def test_get_payment_detail(self):
        response = self.client.get(self.detail_url)
        payment = Payment.objects.get(pk=self.payment1.pk)
        serializer = PaymentSerializer(payment)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['success'], True)
        self.assertEqual(response.data['data'], serializer.data)

    def test_create_payment(self):
        data = {'text': 'Payment in three installments'}
        response = self.client.post(self.list_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['success'], True)
        self.assertEqual(response.data['data']['text'], data['text'])
        self.assertEqual(Payment.objects.count(), 4)
        
        # Verify created_by was set correctly
        new_payment = Payment.objects.get(text=data['text'])
        self.assertEqual(new_payment.created_by, self.user)

    def test_create_payment_invalid_data(self):
        data = {'text': ''}  # Empty text field
        response = self.client.post(self.list_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['success'], False)
        self.assertIn('text', response.data['errors'])
        self.assertEqual(Payment.objects.count(), 3)  # No new payment created

    def test_delete_payment(self):
        response = self.client.delete(self.detail_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['success'], True)
        self.assertEqual(Payment.objects.count(), 2)
        with self.assertRaises(Payment.DoesNotExist):
            Payment.objects.get(pk=self.payment1.pk)

    def test_delete_nonexistent_payment(self):
        url = reverse('payment-detail', kwargs={'pk': 999})  # Non-existent ID
        response = self.client.delete(url)
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_search_payment(self):
        # Search for "advance"
        response = self.client.get(f"{self.list_url}?search=advance")
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['success'], True)
        self.assertEqual(len(response.data['data']), 1)
        self.assertEqual(response.data['data'][0]['text'], self.payment2.text)
        
        # Search for "payment" (should return all)
        response = self.client.get(f"{self.list_url}?search=payment")
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['data']), 3)
        
        # Search for non-existent term
        response = self.client.get(f"{self.list_url}?search=nonexistent")
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['data']), 0)

    def test_pagination(self):
        # Create more payments to test pagination
        for i in range(10):
            Payment.objects.create(
                text=f'Pagination test payment {i}',
                created_by=self.user
            )
        
        # Default page size should be applied
        response = self.client.get(self.list_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['success'], True)
        self.assertIn('meta', response.data)
        self.assertIn('pagination', response.data['meta'])
        self.assertIn('count', response.data['meta']['pagination'])
        self.assertEqual(response.data['meta']['pagination']['count'], 13)  # 3 original + 10 new
        
        # Test second page
        if response.data['meta']['pagination']['next']:
            next_url = response.data['meta']['pagination']['next']
            # Extract the page parameter
            page_param = next_url.split('page=')[1].split('&')[0]
            response = self.client.get(f"{self.list_url}?page={page_param}")
            
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(response.data['success'], True)
            self.assertGreater(len(response.data['data']), 0)

    def test_unauthorized_access(self):
        # Logout
        self.client.force_authenticate(user=None)
        
        # Try to access endpoints
        list_response = self.client.get(self.list_url)
        detail_response = self.client.get(self.detail_url)
        create_response = self.client.post(self.list_url, {'text': 'Test'}, format='json')
        delete_response = self.client.delete(self.detail_url)
        
        self.assertEqual(list_response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(detail_response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(create_response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(delete_response.status_code, status.HTTP_401_UNAUTHORIZED)