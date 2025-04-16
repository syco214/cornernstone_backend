from datetime import datetime
import json
from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from .models import Quotation
from admin_api.models import Customer
from .serializers import (
    QuotationSerializer, QuotationCreateUpdateSerializer, CustomerListSerializer
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
        quotation = get_object_or_404(Quotation, pk=pk)
        serializer = QuotationCreateUpdateSerializer(quotation, data=request.data, partial=True, context={'request': request})
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