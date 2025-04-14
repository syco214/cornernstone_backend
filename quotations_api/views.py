from django.shortcuts import render, get_object_or_404
from django.db.models import Q, F
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import PageNumberPagination
from django.db import transaction

from .models import Quotation
from .serializers import (
    QuotationListSerializer,
    QuotationDetailSerializer,
    QuotationCreateUpdateSerializer,
)


class QuotationView(APIView, PageNumberPagination):
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        # Use different serializers for list vs detail/create/update
        if self.request.method == 'GET':
            if 'pk' in self.kwargs:
                return QuotationDetailSerializer
            return QuotationListSerializer
        return QuotationCreateUpdateSerializer

    def get(self, request, pk=None):
        
        if pk:
            # Retrieve single quotation
            quotation = get_object_or_404(
                Quotation.objects.prefetch_related(
                    'items__inventory', 'sales_agents__agent', 'customer_contacts',
                    'additional_controls', 'attachments', 'terms_conditions',
                    'payment_terms', 'delivery_options', 'other_options',
                    'customer', 'created_by', 'last_modified_by'
                ),
                pk=pk
            )
            serializer_class = self.get_serializer_class()
            serializer = serializer_class(quotation, context={'request': request})
            return Response({'success': True, 'data': serializer.data})
        else:
            # List and search quotations
            queryset = Quotation.objects.select_related(
                'customer'
            ).prefetch_related(
                'sales_agents__agent' # Prefetch for main_sales_agent
            ).all()

            # --- Filtering ---
            # Specific field filters
            quote_number_search = request.query_params.get('quote_number', '')
            status_filter = request.query_params.get('status', '')
            customer_name_search = request.query_params.get('customer_name', '')
            sales_agent_name_search = request.query_params.get('sales_agent_name', '')

            if quote_number_search:
                queryset = queryset.filter(quote_number__icontains=quote_number_search)
            if status_filter and status_filter in Quotation.Status.values:
                queryset = queryset.filter(status=status_filter)
            if customer_name_search:
                queryset = queryset.filter(customer__name__icontains=customer_name_search)
            if sales_agent_name_search:
                # Filter based on any assigned agent's name/username
                queryset = queryset.filter(
                    Q(sales_agents__agent__username__icontains=sales_agent_name_search) |
                    Q(sales_agents__agent__first_name__icontains=sales_agent_name_search) |
                    Q(sales_agents__agent__last_name__icontains=sales_agent_name_search)
                ).distinct() # Use distinct because of M2M join

            # General search (if no specific filters are applied)
            general_search = request.query_params.get('search', '')
            if general_search and not any([quote_number_search, status_filter, customer_name_search, sales_agent_name_search]):
                 queryset = queryset.filter(
                    Q(quote_number__icontains=general_search) |
                    Q(customer__name__icontains=general_search) |
                    Q(status__icontains=general_search) |
                    Q(sales_agents__agent__username__icontains=general_search) |
                    Q(sales_agents__agent__first_name__icontains=general_search) |
                    Q(sales_agents__agent__last_name__icontains=general_search)
                 ).distinct()


            # --- Sorting ---
            sort_by = request.query_params.get('sort_by', 'created_on') # Default sort
            sort_direction = request.query_params.get('sort_direction', 'desc')
            sort_prefix = '-' if sort_direction == 'desc' else ''

            # Map API sort fields to model fields/annotations if necessary
            valid_sort_fields = {
                'quote_number': 'quote_number',
                'status': 'status',
                'customer': 'customer__name', # Sort by customer name
                'date': 'date',
                'total_amount': 'total_amount',
                'created_on': 'created_on',
                # Add 'sales_agent' if needed, might require annotation or careful ordering
            }

            if sort_by in valid_sort_fields:
                 order_field = valid_sort_fields[sort_by]
                 # Special case for main sales agent? Requires annotation or complex ordering.
                 # Simple approach: order by related customer name
                 queryset = queryset.order_by(f'{sort_prefix}{order_field}')
            else:
                 # Default sort if invalid field provided
                 queryset = queryset.order_by(f'{sort_prefix}created_on')

            # --- Pagination ---
            # This is the key change - use the PageNumberPagination methods directly
            page = self.paginate_queryset(queryset, request)
            if page is not None:
                serializer_class = self.get_serializer_class()
                serializer = serializer_class(page, many=True, context={'request': request})
                paginated_response = self.get_paginated_response(serializer.data)
                
                return Response({
                    'success': True,
                    'data': paginated_response.data['results'],
                    'meta': {
                        'pagination': {
                            'count': paginated_response.data['count'],
                            'page_size': self.page_size,
                            'current_page': self.page.number,
                            'total_pages': self.page.paginator.num_pages,
                            'next': paginated_response.data['next'],
                            'previous': paginated_response.data['previous'],
                        }
                    }
                })

            # Fallback if pagination is not used (e.g., page_size=0 or disabled)
            serializer_class = self.get_serializer_class()
            serializer = serializer_class(queryset, many=True, context={'request': request})
            return Response({'success': True, 'data': serializer.data})

    @transaction.atomic
    def post(self, request):
        """Create a new quotation"""
        serializer = QuotationCreateUpdateSerializer(data=request.data, context={'request': request})
        
        if serializer.is_valid():
            # Set the created_by field to the current user
            quotation = serializer.save(
                created_by=request.user,
                last_modified_by=request.user
            )
            
            # Return the created quotation with detail serializer
            detail_serializer = QuotationDetailSerializer(quotation, context={'request': request})
            return Response({
                'success': True,
                'data': detail_serializer.data,
                'message': 'Quotation created successfully'
            }, status=status.HTTP_201_CREATED)
        
        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
    
    @transaction.atomic
    def put(self, request, pk=None):
        """Update an existing quotation"""
        if not pk:
            return Response({
                'success': False,
                'errors': {'detail': 'Quotation ID is required'}
            }, status=status.HTTP_400_BAD_REQUEST)
        
        quotation = get_object_or_404(Quotation, pk=pk)
        serializer = QuotationCreateUpdateSerializer(
            quotation, 
            data=request.data, 
            context={'request': request},
            partial=True  # Allow partial updates
        )
        
        if serializer.is_valid():
            # Update the last_modified_by field
            quotation = serializer.save(last_modified_by=request.user)
            
            # Return the updated quotation with detail serializer
            detail_serializer = QuotationDetailSerializer(quotation, context={'request': request})
            return Response({
                'success': True,
                'data': detail_serializer.data,
                'message': 'Quotation updated successfully'
            })
        
        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
    
    @transaction.atomic
    def delete(self, request, pk=None):
        """Delete a quotation"""
        if not pk:
            return Response({
                'success': False,
                'errors': {'detail': 'Quotation ID is required'}
            }, status=status.HTTP_400_BAD_REQUEST)
        
        quotation = get_object_or_404(Quotation, pk=pk)
        quotation.delete()
        
        return Response({
            'success': True,
            'message': 'Quotation deleted successfully'
        })
