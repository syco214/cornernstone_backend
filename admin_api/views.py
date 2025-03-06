from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
from .serializers import LoginSerializer
from django.shortcuts import get_object_or_404
from django.db.models import Q
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated

from .models import CustomUser, USER_ACCESS_OPTIONS, USER_ROLE_OPTIONS
from .serializers import UserSerializer, SidebarUserSerializer

# Create your views here.

class LoginView(APIView):
    permission_classes = [AllowAny]
    serializer_class = LoginSerializer

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
            user = serializer.validated_data
            refresh = RefreshToken.for_user(user)

            return Response({
                'success': True,
                'data': {
                    'token': str(refresh.access_token),
                    'refresh': str(refresh),
                    'user': {
                        'username': user.username,
                        'id': user.id,
                    }
                }
            })
        except Exception as e:
            return Response({
                'success': False,
                'error': 'Invalid credentials'
            }, status=status.HTTP_401_UNAUTHORIZED)

class SidebarView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        user = request.user
        serializer = SidebarUserSerializer(user)
        
        return Response({
            'success': True,
            'data': serializer.data
        }, status=status.HTTP_200_OK)
    
class UserView(APIView, PageNumberPagination):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk=None):
        # If pk is provided, return a single user
        if pk:
            user = get_object_or_404(CustomUser, pk=pk)
            serializer = UserSerializer(user)
            return Response({
                'success': True,
                'data': serializer.data,
                'meta': {
                    'user_access_options': USER_ACCESS_OPTIONS,
                    'user_role_options': USER_ROLE_OPTIONS
                }
            })
        
        # Otherwise, return a list of users
        # Get search parameters
        search = request.query_params.get('search', '')
        sort_by = request.query_params.get('sort_by', 'id')
        sort_direction = request.query_params.get('sort_direction', 'asc')

        # Query users
        users = CustomUser.objects.all()

        # Apply search filter
        if search:
            users = users.filter(
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search) |
                Q(username__icontains=search) |
                Q(email__icontains=search)
            )

        # Apply sorting
        sort_prefix = '-' if sort_direction == 'desc' else ''
        users = users.order_by(f'{sort_prefix}{sort_by}')

        # Pagination is handled by the mixin
        page = self.paginate_queryset(users, request)
        if page is not None:
            serializer = UserSerializer(page, many=True)
            paginated_response = self.get_paginated_response(serializer.data)
            
            # Restructure to match our API format
            return Response({
                'success': True,
                'data': paginated_response.data['results'],
                'meta': {
                    'pagination': {
                        'count': paginated_response.data['count'],
                        'next': paginated_response.data['next'],
                        'previous': paginated_response.data['previous'],
                    },
                    'user_access_options': USER_ACCESS_OPTIONS,
                    'user_role_options': USER_ROLE_OPTIONS
                }
            })

        # Fallback if pagination fails
        serializer = UserSerializer(users, many=True)
        return Response({
            'success': True,
            'data': serializer.data,
            'meta': {
                'user_access_options': USER_ACCESS_OPTIONS,
                'user_role_options': USER_ROLE_OPTIONS
            }
        })

    def post(self, request):
        serializer = UserSerializer(data=request.data)
        try:
            if serializer.is_valid():
                serializer.save()
                return Response({
                    'success': True,
                    'data': serializer.data,
                    'meta': {
                        'user_access_options': USER_ACCESS_OPTIONS,
                        'user_role_options': USER_ROLE_OPTIONS
                    }
                }, status=status.HTTP_201_CREATED)
            else:
                # Format validation errors
                error_messages = {}
                for field, errors in serializer.errors.items():
                    # Convert list of errors to single string
                    error_messages[field] = errors[0] if isinstance(errors, list) else errors
                return Response({
                    'success': False,
                    'errors': error_messages
                }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({
                'success': False,
                'errors': {'detail': str(e)}
            }, status=status.HTTP_400_BAD_REQUEST)
    
    def put(self, request, pk):
        user = get_object_or_404(CustomUser, pk=pk)
        serializer = UserSerializer(user, data=request.data, partial=True)
        try:
            if serializer.is_valid():
                serializer.save()
                return Response({
                    'success': True,
                    'data': serializer.data,
                    'meta': {
                        'user_access_options': USER_ACCESS_OPTIONS,
                        'user_role_options': USER_ROLE_OPTIONS
                    }
                })
            else:
                # Format validation errors
                error_messages = {}
                for field, errors in serializer.errors.items():
                    error_messages[field] = errors[0] if isinstance(errors, list) else errors
                return Response({
                    'success': False,
                    'errors': error_messages
                }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({
                'success': False,
                'errors': {'detail': str(e)}
            }, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, pk):
        user = get_object_or_404(CustomUser, pk=pk)
        user.delete()
        return Response({
            'success': True,
            'data': None
        }, status=status.HTTP_200_OK)