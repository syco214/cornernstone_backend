from datetime import datetime
import json
from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from .models import Quotation, Payment, Delivery, Other
from admin_api.models import Customer, CustomerContact
from .serializers import (
    QuotationSerializer, QuotationCreateUpdateSerializer, CustomerListSerializer,
    PaymentSerializer, DeliverySerializer, OtherSerializer, CustomerContactSerializer
)

class QuotationView(APIView, PageNumberPagination):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk=None):
        # If pk is provided, return a single quotation with all related data
        if pk:
            quotation = get_object_or_404(Quotation, pk=pk)
            serializer = QuotationSerializer(quotation)
            return Response({
                'success': True,
                'data': serializer.data
            })
        
        # Get search parameters for specific fields
        quote_number_search = request.query_params.get('quote_number', '')
        status = request.query_params.get('status', '')
        customer = request.query_params.get('customer', '')
        date_from = request.query_params.get('date_from', '')
        date_to = request.query_params.get('date_to', '')
        
        # Get general search parameter
        general_search = request.query_params.get('search', '')
        
        # Get sorting parameters
        sort_by = request.query_params.get('sort_by', '-date')
        sort_direction = request.query_params.get('sort_direction', 'asc')
        
        # Query quotations
        quotations = Quotation.objects.all()

        # Apply field-specific search filters
        if quote_number_search:
            quotations = quotations.filter(quote_number__icontains=quote_number_search)
        
        if status and status in dict(Quotation.STATUS_CHOICES):
            quotations = quotations.filter(status=status)
            
        if customer:
            quotations = quotations.filter(customer__name__icontains=customer)
            
        if date_from:
            try:
                date_from_obj = datetime.strptime(date_from, '%Y-%m-%d').date()
                quotations = quotations.filter(date__gte=date_from_obj)
            except ValueError:
                pass
                
        if date_to:
            try:
                date_to_obj = datetime.strptime(date_to, '%Y-%m-%d').date()
                quotations = quotations.filter(date__lte=date_to_obj)
            except ValueError:
                pass

        # Apply general search filter if no specific filters are provided
        if general_search and not any([quote_number_search, status, customer, date_from, date_to]):
            quotations = quotations.filter(
                Q(quote_number__icontains=general_search) |
                Q(customer__name__icontains=general_search) |
                Q(sales_agents__agent_name__icontains=general_search)
            ).distinct()

        # Apply sorting
        sort_prefix = '-' if sort_direction == 'desc' else ''
        sort_field = sort_by.lstrip('-')
        sort_order = f"{sort_prefix}{sort_field}"
        quotations = quotations.order_by(sort_order)
        
        # Pagination
        page = self.paginate_queryset(quotations, request)
        if page is not None:
            serializer = QuotationSerializer(page, many=True)
            paginated_response = self.get_paginated_response(serializer.data)
            
            return Response({
                'success': True,
                'data': paginated_response.data['results'],
                'meta': {
                    'pagination': {
                        'count': paginated_response.data['count'],
                        'next': paginated_response.data['next'],
                        'previous': paginated_response.data['previous'],
                    },
                    'currency_options': ['USD', 'EURO', 'RMB', 'PHP'],
                    'status_options': ['draft', 'for_approval', 'approved', 'expired'],
                }
            })

        # Fallback if pagination fails
        serializer = QuotationSerializer(quotations, many=True)
        return Response({
            'success': True,
            'data': serializer.data,
            'meta': {
                'currency_options': ['USD', 'EURO', 'RMB', 'PHP'],
                'status_options': ['draft', 'for_approval', 'approved', 'expired'],
            }
        })

    def post(self, request):
        try:
            # Extract the JSON data from the 'data' field
            if 'data' in request.data:
                json_data = json.loads(request.data['data'])
                
                # Process attachments if any
                if 'attachments' in json_data and json_data['attachments']:
                    attachments_data = []
                    for i, attachment in enumerate(json_data['attachments']):
                        file_key = f'attachments[{i}][file]'
                        if file_key in request.data:
                            attachment_data = {
                                'file': request.data[file_key],
                                'filename': attachment.get('filename', '')
                            }
                            attachments_data.append(attachment_data)
                    
                    # Replace the attachments in json_data with the processed ones
                    json_data['attachments'] = attachments_data
                
                serializer = QuotationCreateUpdateSerializer(data=json_data, context={'request': request})
                
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
                        error_messages[field] = errors[0] if isinstance(errors, list) else errors
                    return Response({
                        'success': False,
                        'errors': error_messages
                    }, status=status.HTTP_400_BAD_REQUEST)
            else:
                return Response({
                    'success': False,
                    'errors': {'detail': 'No data provided'}
                }, status=status.HTTP_400_BAD_REQUEST)
                
        except Exception as e:
            return Response({
                'success': False,
                'errors': {'detail': str(e)}
            }, status=status.HTTP_400_BAD_REQUEST)
    
    def put(self, request, pk):
        """Update a quotation"""
        try:
            quotation = get_object_or_404(Quotation, pk=pk)
            
            # Parse the JSON data
            data = {}
            if 'data' in request.data:
                try:
                    data = json.loads(request.data['data'])
                except json.JSONDecodeError as e:
                    return Response({
                        'success': False,
                        'errors': {'detail': f'Invalid JSON data: {str(e)}'}
                    }, status=status.HTTP_400_BAD_REQUEST)
            else:
                # If no 'data' field, use the request.data directly
                data = request.data
            
            # Handle file uploads
            files = request.FILES.getlist('files') if 'files' in request.FILES else []
            
            # Create serializer with the data
            serializer = QuotationCreateUpdateSerializer(
                quotation, 
                data=data,
                partial=True,  # Allow partial updates
                context={'request': request, 'files': files}
            )
            
            if serializer.is_valid():
                updated_quotation = serializer.save()
                
                # Return the updated quotation
                return Response({
                    'success': True,
                    'data': QuotationSerializer(updated_quotation).data
                })
            else:
                return Response({
                    'success': False,
                    'errors': serializer.errors
                }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            import traceback
            return Response({
                'success': False,
                'errors': {'detail': str(e)}
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def delete(self, request, pk):
        quotation = get_object_or_404(Quotation, pk=pk)
        quotation.delete()
        return Response({
            'success': True,
            'data': None
        }, status=status.HTTP_200_OK)

class CustomerListView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        # Get only active customers
        customers = Customer.objects.filter(status='active')
        serializer = CustomerListSerializer(customers, many=True)
        
        return Response({
            'success': True,
            'data': serializer.data
        })

class PaymentView(APIView, PageNumberPagination):
    permission_classes = [IsAuthenticated]
    
    def get(self, request, pk=None):
        if pk:
            payment = get_object_or_404(Payment, pk=pk)
            serializer = PaymentSerializer(payment)
            return Response({
                'success': True,
                'data': serializer.data
            })
        
        # Get search parameter
        search = request.query_params.get('search', '')
        
        # Query payments
        payments = Payment.objects.all()
        
        # Apply search filter
        if search:
            payments = payments.filter(text__icontains=search)
        
        # Order by most recent
        payments = payments.order_by('-created_on')
        
        # Pagination
        page = self.paginate_queryset(payments, request)
        if page is not None:
            serializer = PaymentSerializer(page, many=True)
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
        serializer = PaymentSerializer(payments, many=True)
        return Response({
            'success': True,
            'data': serializer.data
        })
    
    def post(self, request):
        serializer = PaymentSerializer(data=request.data)
        if serializer.is_valid():
            # Set the created_by field
            payment = serializer.save(created_by=request.user)
            return Response({
                'success': True,
                'data': PaymentSerializer(payment).data
            }, status=status.HTTP_201_CREATED)
        else:
            return Response({
                'success': False,
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, pk):
        payment = get_object_or_404(Payment, pk=pk)
        payment.delete()
        return Response({
            'success': True,
            'data': None
        }, status=status.HTTP_200_OK)

class DeliveryView(APIView, PageNumberPagination):
    permission_classes = [IsAuthenticated]
    
    def get(self, request, pk=None):
        if pk:
            delivery = get_object_or_404(Delivery, pk=pk)
            serializer = DeliverySerializer(delivery)
            return Response({
                'success': True,
                'data': serializer.data
            })
        
        # Get search parameter
        search = request.query_params.get('search', '')
        
        # Query deliveries
        deliveries = Delivery.objects.all()
        
        # Apply search filter
        if search:
            deliveries = deliveries.filter(text__icontains=search)
        
        # Order by most recent
        deliveries = deliveries.order_by('-created_on')
        
        # Pagination
        page = self.paginate_queryset(deliveries, request)
        if page is not None:
            serializer = DeliverySerializer(page, many=True)
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
        serializer = DeliverySerializer(deliveries, many=True)
        return Response({
            'success': True,
            'data': serializer.data
        })
    
    def post(self, request):
        serializer = DeliverySerializer(data=request.data)
        if serializer.is_valid():
            # Set the created_by field
            delivery = serializer.save(created_by=request.user)
            return Response({
                'success': True,
                'data': DeliverySerializer(delivery).data
            }, status=status.HTTP_201_CREATED)
        else:
            return Response({
                'success': False,
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, pk):
        delivery = get_object_or_404(Delivery, pk=pk)
        delivery.delete()
        return Response({
            'success': True,
            'data': None
        }, status=status.HTTP_200_OK)

class OtherView(APIView, PageNumberPagination):
    permission_classes = [IsAuthenticated]
    
    def get(self, request, pk=None):
        if pk:
            other = get_object_or_404(Other, pk=pk)
            serializer = OtherSerializer(other)
            return Response({
                'success': True,
                'data': serializer.data
            })
        
        # Get search parameter
        search = request.query_params.get('search', '')
        
        # Query others
        others = Other.objects.all()
        
        # Apply search filter
        if search:
            others = others.filter(text__icontains=search)
        
        # Order by most recent
        others = others.order_by('-created_on')
        
        # Pagination
        page = self.paginate_queryset(others, request)
        if page is not None:
            serializer = OtherSerializer(page, many=True)
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
        serializer = OtherSerializer(others, many=True)
        return Response({
            'success': True,
            'data': serializer.data
        })
    
    def post(self, request):
        serializer = OtherSerializer(data=request.data)
        if serializer.is_valid():
            # Set the created_by field
            other = serializer.save(created_by=request.user)
            return Response({
                'success': True,
                'data': OtherSerializer(other).data
            }, status=status.HTTP_201_CREATED)
        else:
            return Response({
                'success': False,
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, pk):
        other = get_object_or_404(Other, pk=pk)
        other.delete()
        return Response({
            'success': True,
            'data': None
        }, status=status.HTTP_200_OK)

class CustomerContactListView(APIView, PageNumberPagination):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        customer_id = request.query_params.get('customer_id')
        
        if not customer_id:
            return Response({
                'success': False,
                'errors': {'detail': 'Customer ID is required'}
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Get contacts for the specified customer
        contacts = CustomerContact.objects.filter(customer_id=customer_id)
        
        # Apply search if provided
        search = request.query_params.get('search', '')
        if search:
            contacts = contacts.filter(contact_person__icontains=search)
        
        # Paginate results
        page = self.paginate_queryset(contacts, request)
        if page is not None:
            serializer = CustomerContactSerializer(page, many=True)
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
        serializer = CustomerContactSerializer(contacts, many=True)
        return Response({
            'success': True,
            'data': serializer.data
        })
    
    def post(self, request):
        """Add a new contact to the customer's contacts"""
        serializer = CustomerContactSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({
                'success': True,
                'data': serializer.data
            }, status=status.HTTP_201_CREATED)
        else:
            return Response({
                'success': False,
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)