from django.db.models import Q # Import Q object for complex lookups if needed
from rest_framework import viewsets, permissions, status, filters
from rest_framework.response import Response
# Removed DjangoFilterBackend import
# from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.generics import get_object_or_404 # Import get_object_or_404

from .models import (
    Quotation, TermsCondition, PaymentTerm, DeliveryOption, OtherOption,
)
from admin_api.models import Customer
from .serializers import (
    QuotationListSerializer, QuotationDetailSerializer, QuotationCreateUpdateSerializer,
    TermsConditionSerializer, PaymentTermSerializer, DeliveryOptionSerializer,
    OtherOptionSerializer,
)
from admin_api.serializers import CustomerSerializer

# --- Reusable Option ViewSets ---

class TermsConditionViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows Terms & Conditions to be viewed or edited.
    Uses default pagination settings.
    Manual filtering for 'name'. Search and Ordering handled by DRF filters.
    """
    queryset = TermsCondition.objects.all()
    serializer_class = TermsConditionSerializer
    permission_classes = [permissions.IsAuthenticated]
    # Removed DjangoFilterBackend
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    # filterset_fields = ['name'] # Removed
    search_fields = ['name', 'text'] # Keep search fields
    ordering_fields = ['name', 'id']
    ordering = ['name']

    def get_queryset(self):
        """
        Override to apply manual filtering based on query parameters.
        """
        queryset = super().get_queryset()
        name_param = self.request.query_params.get('name', None)

        if name_param:
            # Use icontains for case-insensitive partial match, like search
            # Or use exact/iexact if needed
            queryset = queryset.filter(name__icontains=name_param)

        return queryset

class PaymentTermViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows Payment Terms to be viewed or edited.
    Uses default pagination settings.
    Manual filtering for 'name'. Search and Ordering handled by DRF filters.
    """
    queryset = PaymentTerm.objects.all()
    serializer_class = PaymentTermSerializer
    permission_classes = [permissions.IsAuthenticated]
    # Removed DjangoFilterBackend
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    # filterset_fields = ['name'] # Removed
    search_fields = ['name'] # Keep search fields
    ordering_fields = ['name', 'id']
    ordering = ['name']

    def get_queryset(self):
        """
        Override to apply manual filtering based on query parameters.
        """
        queryset = super().get_queryset()
        name_param = self.request.query_params.get('name', None)

        if name_param:
            queryset = queryset.filter(name__icontains=name_param)

        return queryset

class DeliveryOptionViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows Delivery Options to be viewed or edited.
    Uses default pagination settings.
    Manual filtering for 'name'. Search and Ordering handled by DRF filters.
    """
    queryset = DeliveryOption.objects.all()
    serializer_class = DeliveryOptionSerializer
    permission_classes = [permissions.IsAuthenticated]
    # Removed DjangoFilterBackend
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    # filterset_fields = ['name'] # Removed
    search_fields = ['name'] # Keep search fields
    ordering_fields = ['name', 'id']
    ordering = ['name']

    def get_queryset(self):
        """
        Override to apply manual filtering based on query parameters.
        """
        queryset = super().get_queryset()
        name_param = self.request.query_params.get('name', None)

        if name_param:
            queryset = queryset.filter(name__icontains=name_param)

        return queryset

class OtherOptionViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows Other Options to be viewed or edited.
    Uses default pagination settings.
    Manual filtering for 'name'. Search and Ordering handled by DRF filters.
    """
    queryset = OtherOption.objects.all()
    serializer_class = OtherOptionSerializer
    permission_classes = [permissions.IsAuthenticated]
    # Removed DjangoFilterBackend
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    # filterset_fields = ['name'] # Removed
    search_fields = ['name'] # Keep search fields
    ordering_fields = ['name', 'id']
    ordering = ['name']

    def get_queryset(self):
        """
        Override to apply manual filtering based on query parameters.
        """
        queryset = super().get_queryset()
        name_param = self.request.query_params.get('name', None)

        if name_param:
            queryset = queryset.filter(name__icontains=name_param)

        return queryset


# --- Main Quotation ViewSet ---

class QuotationViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows Quotations to be viewed, created, edited, or deleted.

    Handles nested creation/update of items, sales agents, and additional controls.
    Uses default pagination settings.
    Manual filtering implemented in get_queryset.
    Search and Ordering handled by DRF filters.
    """
    # Base queryset remains the same
    queryset = Quotation.objects.select_related(
        'customer', 'created_by', 'last_modified_by',
        'terms_conditions', 'payment_terms', 'delivery_options', 'other_options',
        'additional_controls'
    ).prefetch_related(
        'items', 'items__inventory', #'items__brand', # Brand is on inventory now
        'sales_agents', 'sales_agents__agent',
        'customer_contacts',
        'attachments'
    ).order_by('-created_on') # Default ordering can be applied here or via OrderingFilter
    permission_classes = [permissions.IsAuthenticated]
    # Removed DjangoFilterBackend
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]

    # filterset_fields removed

    # Search and ordering fields remain the same
    search_fields = [
        'quote_number',
        'customer__name',
        'customer__registered_name', # Added registered name
        'purchase_request',
        'notes',
        'items__inventory__item_code', # Adjusted for nested inventory
        'items__inventory__product_name', # Adjusted for nested inventory
        'items__external_description',
        'sales_agents__agent__username', # Search by agent username
        'sales_agents__agent__first_name',
        'sales_agents__agent__last_name',
    ]

    ordering_fields = [
        'quote_number', 'status', 'customer__name', 'date', 'total_amount',
        'created_on', 'last_modified_on', 'expiry_date'
    ]
    # Default ordering can be set here or overridden by query param 'ordering'
    ordering = ['-created_on']

    def get_queryset(self):
        """
        Override to apply manual filtering based on query parameters.
        Search and Ordering are handled by the filter_backends.
        """
        queryset = super().get_queryset() # Start with the base queryset

        # --- Apply filters based on query parameters ---
        status = self.request.query_params.get('status', None)
        customer_id = self.request.query_params.get('customer', None)
        created_by_id = self.request.query_params.get('created_by', None)
        agent_id = self.request.query_params.get('sales_agents__agent', None) # Match potential param name

        date_exact = self.request.query_params.get('date', None)
        date_gte = self.request.query_params.get('date__gte', None)
        date_lte = self.request.query_params.get('date__lte', None)

        expiry_date_exact = self.request.query_params.get('expiry_date', None)
        expiry_date_gte = self.request.query_params.get('expiry_date__gte', None)
        expiry_date_lte = self.request.query_params.get('expiry_date__lte', None)

        created_on_date_exact = self.request.query_params.get('created_on__date', None)
        created_on_date_gte = self.request.query_params.get('created_on__date__gte', None)
        created_on_date_lte = self.request.query_params.get('created_on__date__lte', None)

        # Apply filters sequentially
        if status:
            # Handle potential multiple statuses (e.g., status=draft,approved)
            status_list = [s.strip() for s in status.split(',') if s.strip()]
            if status_list:
                queryset = queryset.filter(status__in=status_list)
        if customer_id:
            queryset = queryset.filter(customer_id=customer_id) # Filter by FK ID
        if created_by_id:
            queryset = queryset.filter(created_by_id=created_by_id)
        if agent_id:
            # Ensure distinct results if filtering across a M2M relationship
            queryset = queryset.filter(sales_agents__agent_id=agent_id).distinct()

        # Date filtering (add try-except for validation if needed)
        if date_exact:
            queryset = queryset.filter(date=date_exact)
        if date_gte:
            queryset = queryset.filter(date__gte=date_gte)
        if date_lte:
            queryset = queryset.filter(date__lte=date_lte)

        # Expiry Date filtering
        if expiry_date_exact:
            queryset = queryset.filter(expiry_date=expiry_date_exact)
        if expiry_date_gte:
            queryset = queryset.filter(expiry_date__gte=expiry_date_gte)
        if expiry_date_lte:
            queryset = queryset.filter(expiry_date__lte=expiry_date_lte)

        # Created On filtering (filtering on the date part)
        if created_on_date_exact:
            queryset = queryset.filter(created_on__date=created_on_date_exact)
        if created_on_date_gte:
            queryset = queryset.filter(created_on__date__gte=created_on_date_gte)
        if created_on_date_lte:
            queryset = queryset.filter(created_on__date__lte=created_on_date_lte)

        # Note: General 'search' and 'ordering' are handled by SearchFilter and OrderingFilter

        return queryset

    def get_serializer_class(self):
        """
        Return different serializers for list/detail vs create/update actions.
        """
        if self.action == 'list':
            return QuotationListSerializer
        elif self.action in ['retrieve']:
            return QuotationDetailSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return QuotationCreateUpdateSerializer
        return QuotationDetailSerializer # Default fallback

    def get_serializer_context(self):
        """
        Pass request context to the serializer.
        """
        context = super().get_serializer_context()
        context['request'] = self.request
        return context

    # Removed the incorrect 'get' method that was pasted here.
    # The default list/retrieve actions from ModelViewSet will use the
    # queryset returned by the overridden get_queryset method.

    # perform_create/perform_update handled by serializer context

    # Example custom action (commented out)
    # @action(detail=True, methods=['post'], permission_classes=[permissions.IsAdminUser])
    # def approve(self, request, pk=None):
    #     # ... implementation ...
    #     pass

# Add CustomerViewSet
class CustomerViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint that allows Customers to be viewed.
    """
    queryset = Customer.objects.filter(status='active')  # Only active customers by default
    serializer_class = CustomerSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def list(self, request, *args, **kwargs):
        print("CustomerViewSet.list called")
        try:
            # Get the queryset and apply any filters
            queryset = self.filter_queryset(self.get_queryset())
            
            # Print the count of customers
            print(f"Found {queryset.count()} customers")
            
            # Paginate the results
            page = self.paginate_queryset(queryset)
            if page is not None:
                serializer = self.get_serializer(page, many=True)
                print(f"Returning {len(serializer.data)} customers after pagination")
                return self.get_paginated_response(serializer.data)

            # If pagination is not required
            serializer = self.get_serializer(queryset, many=True)
            print(f"Returning all {len(serializer.data)} customers")
            return Response(serializer.data)
        except Exception as e:
            print(f"Error in CustomerViewSet.list: {str(e)}")
            return Response(
                {"detail": "An error occurred while fetching customers."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )