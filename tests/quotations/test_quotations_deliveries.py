from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase
from quotations_api.models import Delivery
from quotations_api.serializers import DeliverySerializer
import json

User = get_user_model()

class DeliveryViewTests(APITestCase):
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
        
        # Create test deliveries
        self.delivery1 = Delivery.objects.create(
            text='Standard delivery within 30 days',
            created_by=self.user
        )
        self.delivery2 = Delivery.objects.create(
            text='Express delivery within 7 days',
            created_by=self.user
        )
        self.delivery3 = Delivery.objects.create(
            text='Next day delivery service',
            created_by=self.admin_user
        )
        
        # URLs - using the correct URL names from urls.py
        self.list_url = reverse('quotations_api:delivery-list-create')
        self.detail_url = reverse('quotations_api:delivery-detail', kwargs={'pk': self.delivery1.pk})
        
        # Authenticate
        self.client.force_authenticate(user=self.user)

    def test_get_delivery_list(self):
        response = self.client.get(self.list_url)
        deliveries = Delivery.objects.all().order_by('-created_on')
        serializer = DeliverySerializer(deliveries, many=True)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['success'], True)
        self.assertEqual(len(response.data['data']), 3)
        self.assertEqual(response.data['data'][0]['id'], serializer.data[0]['id'])

    def test_get_delivery_detail(self):
        response = self.client.get(self.detail_url)
        delivery = Delivery.objects.get(pk=self.delivery1.pk)
        serializer = DeliverySerializer(delivery)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['success'], True)
        self.assertEqual(response.data['data'], serializer.data)

    def test_create_delivery(self):
        data = {'text': 'New delivery option with special handling'}
        response = self.client.post(self.list_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['success'], True)
        self.assertEqual(response.data['data']['text'], data['text'])
        self.assertEqual(Delivery.objects.count(), 4)
        
        # Verify created_by was set correctly
        new_delivery = Delivery.objects.get(text=data['text'])
        self.assertEqual(new_delivery.created_by, self.user)

    def test_create_delivery_invalid_data(self):
        data = {'text': ''}  # Empty text field
        response = self.client.post(self.list_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['success'], False)
        self.assertIn('text', response.data['errors'])
        self.assertEqual(Delivery.objects.count(), 3)  # No new delivery created

    def test_delete_delivery(self):
        response = self.client.delete(self.detail_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['success'], True)
        self.assertEqual(Delivery.objects.count(), 2)
        with self.assertRaises(Delivery.DoesNotExist):
            Delivery.objects.get(pk=self.delivery1.pk)

    def test_delete_nonexistent_delivery(self):
        url = reverse('quotations_api:delivery-detail', kwargs={'pk': 999})  # Non-existent ID
        response = self.client.delete(url)
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_search_delivery(self):
        # Search for "express"
        response = self.client.get(f"{self.list_url}?search=express")
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['success'], True)
        self.assertEqual(len(response.data['data']), 1)
        self.assertEqual(response.data['data'][0]['text'], self.delivery2.text)
        
        # Search for "delivery" (should return all)
        response = self.client.get(f"{self.list_url}?search=delivery")
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['data']), 3)
        
        # Search for non-existent term
        response = self.client.get(f"{self.list_url}?search=nonexistent")
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['data']), 0)

    def test_pagination(self):
        # Create more deliveries to test pagination
        for i in range(10):
            Delivery.objects.create(
                text=f'Pagination test delivery {i}',
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