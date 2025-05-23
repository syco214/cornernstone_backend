import json
from datetime import datetime
from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated

from .models import PurchaseOrder
from .serializers import PurchaseOrderSerializer, PurchaseOrderCreateUpdateSerializer
from django.core.exceptions import FieldDoesNotExist

class PurchaseOrderView(APIView, PageNumberPagination):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk=None):
        # If pk is provided, return a single purchase order with all related data
        if pk:
            # For single object retrieval, it's good to optimize with select_related/prefetch_related
            purchase_order = get_object_or_404(
                PurchaseOrder.objects.select_related(
                    'supplier', 'created_by', 'last_modified_by', 'approved_by', 'payment_term'
                ).prefetch_related(
                    'items__inventory', 'discounts_charges'
                ), 
                pk=pk
            )
            serializer = PurchaseOrderSerializer(purchase_order) # Use the detailed serializer
            return Response({
                'success': True,
                'data': serializer.data
            })
        
        # Get search parameters for specific fields
        po_number_search = request.query_params.get('po_number', '')
        status_search = request.query_params.get('status', '')
        supplier_search = request.query_params.get('supplier', '') # Search by supplier name
        date_from_str = request.query_params.get('date_from', '')
        date_to_str = request.query_params.get('date_to', '')
        
        # Get general search parameter
        general_search = request.query_params.get('search', '')
        
        # Get sorting parameters
        sort_by = request.query_params.get('sort_by', '-po_date') # Default sort for POs
        sort_direction = request.query_params.get('sort_direction', 'asc') # Default direction
        
        queryset = PurchaseOrder.objects.all()

        # Apply field-specific search filters
        if po_number_search:
            queryset = queryset.filter(po_number__icontains=po_number_search)
        
        if status_search and status_search in dict(PurchaseOrder.STATUS_CHOICES):
            queryset = queryset.filter(status=status_search)
            
        if supplier_search:
            queryset = queryset.filter(supplier__name__icontains=supplier_search)
            
        if date_from_str:
            try:
                date_from_obj = datetime.strptime(date_from_str, '%Y-%m-%d').date()
                queryset = queryset.filter(po_date__gte=date_from_obj)
            except ValueError:
                pass # Ignore invalid date format
                
        if date_to_str:
            try:
                date_to_obj = datetime.strptime(date_to_str, '%Y-%m-%d').date()
                queryset = queryset.filter(po_date__lte=date_to_obj)
            except ValueError:
                pass # Ignore invalid date format

        # Apply general search filter if no specific filters are provided
        if general_search and not any([po_number_search, status_search, supplier_search, date_from_str, date_to_str]):
            queryset = queryset.filter(
                Q(po_number__icontains=general_search) |
                Q(supplier__name__icontains=general_search) |
                Q(items__inventory__item_code__icontains=general_search) | # Example related field search
                Q(items__external_description__icontains=general_search) | # Example related field search
                Q(notes__icontains=general_search) # Search in PO notes
            ).distinct()

        # Apply sorting
        sort_prefix = '-' if sort_direction == 'desc' else ''
        sort_field_cleaned = sort_by.lstrip('-') # Remove existing prefix if any
        sort_field_actual = sort_field_cleaned # Assuming sort_by uses direct model field names or valid relations
        sort_order = f'{sort_prefix}{sort_field_actual}'
        
        try:
            # Attempt to order. This will raise FieldError if sort_order is invalid.
            queryset = queryset.order_by(sort_order)
        except FieldDoesNotExist: # More specific exception for invalid field names
            # Fallback to default sort if sort_by is invalid
            queryset = queryset.order_by('-po_date') # Default sort for PO
        except Exception: # Catch any other ordering error and fallback
            queryset = queryset.order_by('-po_date')


        # Pagination
        page = self.paginate_queryset(queryset, request)

        # Prepare meta data (consistent with your QuotationView structure)
        meta_data = {
            'currency_options': [choice[0] for choice in PurchaseOrder.CURRENCY_CHOICES],
            'status_options': [choice[0] for choice in PurchaseOrder.STATUS_CHOICES],
            'supplier_type_options': [choice[0] for choice in PurchaseOrder.SUPPLIER_TYPE_CHOICES],
        }
        
        if page is not None:
            serializer = PurchaseOrderSerializer(page, many=True) # Use the detailed serializer
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
                    **meta_data
                }
            })

        # Fallback if pagination fails or is not used
        serializer = PurchaseOrderSerializer(queryset, many=True) # Use the detailed serializer
        return Response({
            'success': True,
            'data': serializer.data,
            'meta': meta_data
        })

    def post(self, request):
        if 'data' in request.data and isinstance(request.data['data'], str):
            try:
                payload = json.loads(request.data['data'])
            except json.JSONDecodeError:
                return Response({
                    'success': False, 
                    'errors': {'detail': 'Invalid JSON in data field.'}
                }, status=status.HTTP_400_BAD_REQUEST)
        else:
            payload = request.data

        serializer = PurchaseOrderCreateUpdateSerializer(data=payload, context={'request': request})
        if serializer.is_valid():
            try:
                purchase_order = serializer.save()
                # Return full detail using the read serializer
                return Response({
                    'success': True,
                    'data': PurchaseOrderSerializer(purchase_order).data
                }, status=status.HTTP_201_CREATED)
            except Exception as e: # Catch potential errors during save (e.g. DB constraints)
                return Response({
                    'success': False,
                    'errors': {'detail': str(e)}
                }, status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response({
                'success': False,
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request, pk):
        purchase_order = get_object_or_404(PurchaseOrder, pk=pk)
        raw_data = request.data
        payload = {}

        if 'data' in raw_data and isinstance(raw_data.get('data'), (str, bytes)):
            try:
                payload = json.loads(raw_data['data'])
            except json.JSONDecodeError:
                return Response({
                    'success': False,
                    'errors': {'detail': 'Invalid JSON in data field.'}
                }, status=status.HTTP_400_BAD_REQUEST)
        elif isinstance(raw_data, dict): # If it's already a dict (e.g. application/json)
             payload = raw_data
        else:
            return Response({
                'success': False,
                'errors': {'detail': 'Invalid request payload.'}
            }, status=status.HTTP_400_BAD_REQUEST)


        serializer = PurchaseOrderCreateUpdateSerializer(
            purchase_order,
            data=payload,
            partial=True, # Allow partial updates
            context={'request': request}
        )
        if serializer.is_valid():
            try:
                updated_purchase_order = serializer.save()
                return Response({
                    'success': True,
                    'data': PurchaseOrderSerializer(updated_purchase_order).data
                })
            except Exception as e:
                return Response({
                    'success': False,
                    'errors': {'detail': str(e)}
                }, status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response({
                'success': False,
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        purchase_order = get_object_or_404(PurchaseOrder, pk=pk)
        try:
            if purchase_order.status not in ['draft', 'cancelled', 'rejected']:
                return Response({
                    'success': False,
                    'errors': {'detail': f'Cannot delete PO in {purchase_order.get_status_display()} status.'}
                }, status=status.HTTP_400_BAD_REQUEST)
            purchase_order.delete()
            return Response({
                'success': True,
                'data': None # Or a confirmation message
            }, status=status.HTTP_200_OK) # Or HTTP_204_NO_CONTENT
        except Exception as e: # Catch potential errors during delete (e.g. ProtectedError)
             return Response({
                'success': False,
                'errors': {'detail': str(e)}
            }, status=status.HTTP_400_BAD_REQUEST)