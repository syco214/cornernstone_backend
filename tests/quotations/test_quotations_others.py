from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase
from quotations_api.models import Other
from quotations_api.serializers import OtherSerializer

User = get_user_model()

class OtherViewTests(APITestCase):
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
        
        # Create test other terms
        self.other1 = Other.objects.create(
            text='All disputes will be settled in arbitration',
            created_by=self.user
        )
        self.other2 = Other.objects.create(
            text='Client responsible for obtaining necessary permits',
            created_by=self.user
        )
        self.other3 = Other.objects.create(
            text='Warranty valid for 12 months after delivery',
            created_by=self.admin_user
        )
        
        # URLs - using the correct URL names from urls.py
        self.list_url = reverse('other-list-create')
        self.detail_url = reverse('other-detail', kwargs={'pk': self.other1.pk})
        
        # Authenticate
        self.client.force_authenticate(user=self.user)

    def test_get_other_list(self):
        response = self.client.get(self.list_url)
        others = Other.objects.all().order_by('-created_on')
        serializer = OtherSerializer(others, many=True)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['success'], True)
        self.assertEqual(len(response.data['data']), 3)
        self.assertEqual(response.data['data'][0]['id'], serializer.data[0]['id'])

    def test_get_other_detail(self):
        response = self.client.get(self.detail_url)
        other = Other.objects.get(pk=self.other1.pk)
        serializer = OtherSerializer(other)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['success'], True)
        self.assertEqual(response.data['data'], serializer.data)

    def test_create_other(self):
        data = {'text': 'Force majeure clause applies to all agreements'}
        response = self.client.post(self.list_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['success'], True)
        self.assertEqual(response.data['data']['text'], data['text'])
        self.assertEqual(Other.objects.count(), 4)
        
        # Verify created_by was set correctly
        new_other = Other.objects.get(text=data['text'])
        self.assertEqual(new_other.created_by, self.user)

    def test_create_other_invalid_data(self):
        data = {'text': ''}  # Empty text field
        response = self.client.post(self.list_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['success'], False)
        self.assertIn('text', response.data['errors'])
        self.assertEqual(Other.objects.count(), 3)  # No new term created

    def test_delete_other(self):
        response = self.client.delete(self.detail_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['success'], True)
        self.assertEqual(Other.objects.count(), 2)
        with self.assertRaises(Other.DoesNotExist):
            Other.objects.get(pk=self.other1.pk)

    def test_delete_nonexistent_other(self):
        url = reverse('other-detail', kwargs={'pk': 999})  # Non-existent ID
        response = self.client.delete(url)
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_search_other(self):
        # Search for "disputes"
        response = self.client.get(f"{self.list_url}?search=disputes")
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['success'], True)
        self.assertEqual(len(response.data['data']), 1)
        self.assertEqual(response.data['data'][0]['text'], self.other1.text)
        
        # Search for "warranty"
        response = self.client.get(f"{self.list_url}?search=warranty")
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['data']), 1)
        self.assertEqual(response.data['data'][0]['text'], self.other3.text)
        
        # Search for non-existent term
        response = self.client.get(f"{self.list_url}?search=nonexistent")
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['data']), 0)

    def test_pagination(self):
        # Create more other terms to test pagination
        for i in range(10):
            Other.objects.create(
                text=f'Pagination test term {i}',
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