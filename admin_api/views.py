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

from .models import USER_ACCESS_OPTIONS, USER_ROLE_OPTIONS, CustomUser, Brand, Category
from .serializers import UserSerializer, SidebarUserSerializer, BrandSerializer, CategorySerializer, CategoryTreeSerializer

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

class BrandView(APIView, PageNumberPagination):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk=None):
        # If pk is provided, return a single brand
        if pk:
            brand = get_object_or_404(Brand, pk=pk)
            serializer = BrandSerializer(brand)
            return Response({
                'success': True,
                'data': serializer.data
            })
        
        # Otherwise, return a list of brands
        # Get search parameters
        search = request.query_params.get('search', '')
        sort_by = request.query_params.get('sort_by', 'name')
        sort_direction = request.query_params.get('sort_direction', 'asc')

        # Query brands
        brands = Brand.objects.all()

        # Apply search filter
        if search:
            brands = brands.filter(
                Q(name__icontains=search) |
                Q(made_in__icontains=search) |
                Q(remarks__icontains=search)
            )

        # Apply sorting
        sort_prefix = '-' if sort_direction == 'desc' else ''
        brands = brands.order_by(f'{sort_prefix}{sort_by}')

        # Pagination is handled by the mixin
        page = self.paginate_queryset(brands, request)
        if page is not None:
            serializer = BrandSerializer(page, many=True)
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
                    }
                }
            })

        # Fallback if pagination fails
        serializer = BrandSerializer(brands, many=True)
        return Response({
            'success': True,
            'data': serializer.data
        })

    def post(self, request):
        serializer = BrandSerializer(data=request.data)
        try:
            if serializer.is_valid():
                serializer.save()
                return Response({
                    'success': True,
                    'data': serializer.data
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
        brand = get_object_or_404(Brand, pk=pk)
        serializer = BrandSerializer(brand, data=request.data, partial=True)
        try:
            if serializer.is_valid():
                serializer.save()
                return Response({
                    'success': True,
                    'data': serializer.data
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
        brand = get_object_or_404(Brand, pk=pk)
        brand.delete()
        return Response({
            'success': True,
            'data': None
        }, status=status.HTTP_200_OK)

class CategoryView(APIView, PageNumberPagination):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk=None):
        # If pk is provided, return a single category
        if pk:
            category = get_object_or_404(Category, pk=pk)
            serializer = CategorySerializer(category)
            return Response({
                'success': True,
                'data': serializer.data
            })
        
        # Get query parameters
        search = request.query_params.get('search', '')
        sort_by = request.query_params.get('sort_by', 'name')
        sort_direction = request.query_params.get('sort_direction', 'asc')
        tree_view = request.query_params.get('tree', 'false').lower() == 'true'
        parent_id = request.query_params.get('parent', None)
        
        # Query categories
        if parent_id:
            if parent_id == 'root':
                # Get only root categories (no parent)
                categories = Category.objects.filter(parent=None)
            else:
                # Get categories under specific parent
                categories = Category.objects.filter(parent_id=parent_id)
        else:
            # Get all categories
            categories = Category.objects.all()

        # Apply search filter
        if search:
            categories = categories.filter(
                Q(name__icontains=search) |
                Q(remarks__icontains=search)
            )

        # Apply sorting
        sort_prefix = '-' if sort_direction == 'desc' else ''
        categories = categories.order_by(f'{sort_prefix}{sort_by}')

        # Handle tree view (only for root level when requested)
        if tree_view and not parent_id and not search:
            root_categories = Category.objects.filter(parent=None)
            serializer = CategoryTreeSerializer(root_categories, many=True)
            return Response({
                'success': True,
                'data': serializer.data
            })
        
        # Pagination for flat view
        page = self.paginate_queryset(categories, request)
        if page is not None:
            serializer = CategorySerializer(page, many=True)
            paginated_response = self.get_paginated_response(serializer.data)
            
            return Response({
                'success': True,
                'data': paginated_response.data['results'],
                'meta': {
                    'pagination': {
                        'count': paginated_response.data['count'],
                        'next': paginated_response.data['next'],
                        'previous': paginated_response.data['previous'],
                    }
                }
            })

        # Fallback if pagination fails
        serializer = CategorySerializer(categories, many=True)
        return Response({
            'success': True,
            'data': serializer.data
        })

    def post(self, request):
        serializer = CategorySerializer(data=request.data)
        try:
            if serializer.is_valid():
                # Check for circular references
                parent_id = request.data.get('parent')
                if parent_id:
                    parent = get_object_or_404(Category, pk=parent_id)
                    # Prevent a category from being its own ancestor
                    current_parent = parent
                    while current_parent:
                        if str(current_parent.id) == request.data.get('id', '-1'):
                            return Response({
                                'success': False,
                                'errors': {'parent': 'Circular reference detected. A category cannot be its own ancestor.'}
                            }, status=status.HTTP_400_BAD_REQUEST)
                        current_parent = current_parent.parent
                
                serializer.save()
                return Response({
                    'success': True,
                    'data': serializer.data
                }, status=status.HTTP_201_CREATED)
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
    
    def put(self, request, pk):
        category = get_object_or_404(Category, pk=pk)
        serializer = CategorySerializer(category, data=request.data, partial=True)
        try:
            if serializer.is_valid():
                # Check for circular references
                parent_id = request.data.get('parent')
                if parent_id:
                    # Prevent setting itself as parent
                    if str(parent_id) == str(pk):
                        return Response({
                            'success': False,
                            'errors': {'parent': 'A category cannot be its own parent.'}
                        }, status=status.HTTP_400_BAD_REQUEST)
                    
                    # Prevent setting one of its descendants as parent
                    descendants = self._get_all_descendants(category)
                    if int(parent_id) in [desc.id for desc in descendants]:
                        return Response({
                            'success': False,
                            'errors': {'parent': 'Cannot set a descendant as parent (circular reference).'}
                        }, status=status.HTTP_400_BAD_REQUEST)
                
                serializer.save()
                return Response({
                    'success': True,
                    'data': serializer.data
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
        category = get_object_or_404(Category, pk=pk)
        category.delete()
        return Response({
            'success': True,
            'data': None
        }, status=status.HTTP_200_OK)
    
    def _get_all_descendants(self, category):
        """Helper method to get all descendants of a category"""
        descendants = []
        children = Category.objects.filter(parent=category)
        
        for child in children:
            descendants.append(child)
            descendants.extend(self._get_all_descendants(child))
        
        return descendants