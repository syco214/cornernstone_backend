from rest_framework import serializers
from django.db import transaction
from django.contrib.auth import get_user_model
from decimal import Decimal

from .models import (
    Quotation,
    QuotationItem,
    QuotationSalesAgent,
    QuotationAdditionalControl,
    QuotationAttachment,
    LastQuotedPrice,
    TermCondition,
    PaymentTermOption,
    DeliveryOption,
    OtherOption,
)
# Assuming these serializers exist for related models
from admin_api.serializers import (
    CustomerSerializer, # Use a simpler version if needed for nesting
    UserSerializer, # Basic user info
    CustomerContactSerializer, # Basic contact info
    InventorySerializer, # Basic inventory info
)
from admin_api.models import (
    Customer, CustomerContact, Inventory
)


User = get_user_model()

# --- Read Serializers (for GET requests) ---

class TermConditionSerializer(serializers.ModelSerializer):
    class Meta:
        model = TermCondition
        fields = ['id', 'name', 'text', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']

class PaymentTermOptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentTermOption
        fields = ['id', 'name', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']

class DeliveryOptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeliveryOption
        fields = ['id', 'name', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']

class OtherOptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = OtherOption
        fields = ['id', 'name', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class QuotationAttachmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuotationAttachment
        fields = ['id', 'file', 'uploaded_at']


class QuotationItemSerializer(serializers.ModelSerializer):
    # Calculated fields
    inventory_status = serializers.CharField(read_only=True)
    net_selling = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    total_selling = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)
    last_quoted_price = serializers.SerializerMethodField()

    # Basic inventory info for context
    inventory_detail = InventorySerializer(source='inventory', read_only=True)

    class Meta:
        model = QuotationItem
        fields = [
            'id',
            'inventory', # Keep FK for potential linking/updates
            'inventory_detail', # Read-only nested data
            'item_code',
            'brand_name',
            'show_brand',
            'made_in',
            'show_made_in',
            'wholesale_price',
            'unit',
            'photo',
            'show_photo',
            'external_description',
            'actual_landed_cost',
            'estimated_landed_cost',
            'notes',
            'quantity',
            'baseline_margin',
            'inventory_status', # Property
            'last_quoted_price',
            'has_discount',
            'discount_type',
            'discount_percentage',
            'discount_value',
            'net_selling', # Property
            'total_selling', # Property
        ]
        read_only_fields = [
            'item_code', 'brand_name', 'made_in', 'unit',
            'external_description', 'inventory_status',
            'net_selling', 'total_selling', 'last_quoted_price',
            'inventory_detail',
        ]

    def get_last_quoted_price(self, obj: QuotationItem) -> Decimal | None:
        # Implement logic to fetch from LastQuotedPrice model
        # Ensure the related quotation object is available (might need prefetching in view)
        if not hasattr(obj, 'quotation') or not hasattr(obj.quotation, 'customer'):
             # Handle cases where related objects might not be loaded (e.g., during creation serialization)
             return None
        last_price_obj = LastQuotedPrice.objects.filter(
            inventory=obj.inventory,
            customer=obj.quotation.customer
        ).order_by('-last_quoted_date').first() # Ensure we get the latest one
        return last_price_obj.last_price if last_price_obj else None


class QuotationSalesAgentSerializer(serializers.ModelSerializer):
    agent_name = serializers.SerializerMethodField()
    
    class Meta:
        model = QuotationSalesAgent
        fields = ('id', 'agent', 'role', 'agent_name')
        read_only_fields = ('quotation',)
    
    def get_agent_name(self, obj):
        return f"{obj.agent.first_name} {obj.agent.last_name}" if obj.agent else ""


class QuotationAdditionalControlSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuotationAdditionalControl
        exclude = ['id', 'quotation'] # Exclude FK


class QuotationListSerializer(serializers.ModelSerializer):
    """Serializer for listing quotations (less detail)."""
    customer_name = serializers.CharField(source='customer.name', read_only=True)
    main_sales_agent = serializers.SerializerMethodField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = Quotation
        fields = [
            'id',
            'quote_number',
            'status',
            'status_display',
            'customer',
            'customer_name',
            'date',
            'total_amount',
            'main_sales_agent',
            'currency',
            'expiry_date',
            'created_on',
        ]

    def get_main_sales_agent(self, obj: Quotation) -> str | None:
        main_agent = obj.sales_agents.filter(role=QuotationSalesAgent.Role.MAIN).first()
        if main_agent:
            # Use get_full_name() if available, otherwise username
            return main_agent.agent.get_full_name() or main_agent.agent.username
        return None


class QuotationDetailSerializer(serializers.ModelSerializer):
    """Serializer for retrieving a single quotation (full detail)."""
    customer = CustomerSerializer(read_only=True)
    created_by = UserSerializer(read_only=True)
    last_modified_by = UserSerializer(read_only=True)
    items = QuotationItemSerializer(many=True, read_only=True)
    sales_agents = QuotationSalesAgentSerializer(many=True, read_only=True)
    customer_contacts = CustomerContactSerializer(many=True, read_only=True)
    additional_controls = QuotationAdditionalControlSerializer(read_only=True)
    attachments = QuotationAttachmentSerializer(many=True, read_only=True)
    terms_conditions = TermConditionSerializer(many=True, read_only=True)
    payment_terms = PaymentTermOptionSerializer(many=True, read_only=True)
    delivery_options = DeliveryOptionSerializer(many=True, read_only=True)
    other_options = OtherOptionSerializer(many=True, read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    currency_display = serializers.CharField(source='get_currency_display', read_only=True)
    customer_name = serializers.SerializerMethodField()
    main_sales_agent_name = serializers.SerializerMethodField()
    created_by_name = serializers.SerializerMethodField()
    last_modified_by_name = serializers.SerializerMethodField()

    class Meta:
        model = Quotation
        fields = [
            'id', 'quote_number', 'status', 'status_display', 'customer', 'date',
            'total_amount', 'created_by', 'created_on', 'last_modified_by',
            'last_modified_on', 'purchase_request', 'expiry_date', 'currency',
            'currency_display', 'notes', 'price_validity', 'validity_period',
            'items', 'sales_agents', 'customer_contacts', 'additional_controls',
            'attachments', 'terms_conditions', 'payment_terms', 'delivery_options',
            'other_options', 'customer_name', 'main_sales_agent_name', 'created_by_name', 'last_modified_by_name'
        ]

    def get_customer_name(self, obj):
        return obj.customer.name if obj.customer else ""
    
    def get_main_sales_agent_name(self, obj):
        main_agent = obj.sales_agents.filter(role='main').first()
        if main_agent and main_agent.agent:
            return f"{main_agent.agent.first_name} {main_agent.agent.last_name}"
        return ""
    
    def get_created_by_name(self, obj):
        if obj.created_by:
            return f"{obj.created_by.first_name} {obj.created_by.last_name}"
        return ""
    
    def get_last_modified_by_name(self, obj):
        if obj.last_modified_by:
            return f"{obj.last_modified_by.first_name} {obj.last_modified_by.last_name}"
        return ""


# --- Write/Update Serializers (for POST/PUT/PATCH) ---
# These will be more complex, especially for nested creates/updates.
# We'll start with the basic structure and refine later.

class QuotationItemWriteSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(required=False) # For updates

    class Meta:
        model = QuotationItem
        fields = [
            'id',
            'inventory', # Need FK to link to existing inventory
            'show_brand',
            # 'show_made_in', # This comes from Brand, not set here
            'wholesale_price', # Allow override
            'photo', # Allow override
            'show_photo',
            'actual_landed_cost',
            'estimated_landed_cost',
            'notes',
            'quantity',
            'baseline_margin',
            'has_discount',
            'discount_type',
            'discount_percentage',
            'discount_value',
        ]
        # No read_only_fields here as we are writing


class QuotationSalesAgentWriteSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(required=False)

    class Meta:
        model = QuotationSalesAgent
        fields = ['id', 'agent', 'role']


class QuotationAdditionalControlWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuotationAdditionalControl
        fields = [
            'show_carton_packing',
            'do_not_show_all_photos',
            'highlight_item_notes',
            'show_devaluation_clause',
        ]


class QuotationCreateUpdateSerializer(serializers.ModelSerializer):
    items = QuotationItemWriteSerializer(many=True, required=False)
    sales_agents = QuotationSalesAgentWriteSerializer(many=True, required=False)
    customer_contacts = serializers.PrimaryKeyRelatedField(
        queryset=CustomerContact.objects.all(),
        many=True,
        required=False
    )
    additional_controls = QuotationAdditionalControlWriteSerializer(required=False)
    attachments = QuotationAttachmentSerializer(many=True, required=False)
    terms_conditions = serializers.PrimaryKeyRelatedField(
        queryset=TermCondition.objects.all(),
        required=False,
        allow_null=True
    )
    payment_terms = serializers.PrimaryKeyRelatedField(
        queryset=PaymentTermOption.objects.all(),
        required=False,
        allow_null=True
    )
    delivery_options = serializers.PrimaryKeyRelatedField(
        queryset=DeliveryOption.objects.all(),
        required=False,
        allow_null=True
    )
    other_options = serializers.PrimaryKeyRelatedField(
        queryset=OtherOption.objects.all(),
        required=False,
        allow_null=True
    )
    
    class Meta:
        model = Quotation
        fields = [
            'id', 'quote_number', 'status', 'customer', 'date', 'total_amount',
            'purchase_request', 'expiry_date', 'currency', 'notes', 'price',
            'validity', 'items', 'sales_agents', 'customer_contacts',
            'additional_controls', 'attachments', 'terms_conditions',
            'payment_terms', 'delivery_options', 'other_options'
        ]
        read_only_fields = ['id', 'quote_number', 'total_amount', 'created_by', 'created_on', 'last_modified_by', 'last_modified_on']
    
    @transaction.atomic
    def create(self, validated_data):
        # Extract nested data
        items_data = validated_data.pop('items', [])
        sales_agents_data = validated_data.pop('sales_agents', [])
        customer_contacts_data = validated_data.pop('customer_contacts', [])
        additional_controls_data = validated_data.pop('additional_controls', None)
        attachments_data = validated_data.pop('attachments', [])
        
        # Create the quotation
        quotation = Quotation.objects.create(**validated_data)
        
        # Create related objects
        self._create_items(quotation, items_data)
        self._create_sales_agents(quotation, sales_agents_data)
        
        # Add customer contacts (using existing CustomerContact objects)
        if customer_contacts_data:
            quotation.customer_contacts.set(customer_contacts_data)
        
        if additional_controls_data:
            self._create_additional_controls(quotation, additional_controls_data)
        
        self._create_attachments(quotation, attachments_data)
        
        # Calculate and update total amount
        self._update_total_amount(quotation)
        
        return quotation
    
    @transaction.atomic
    def update(self, instance, validated_data):
        # Extract nested data
        items_data = validated_data.pop('items', None)
        sales_agents_data = validated_data.pop('sales_agents', None)
        customer_contacts_data = validated_data.pop('customer_contacts', None)
        additional_controls_data = validated_data.pop('additional_controls', None)
        attachments_data = validated_data.pop('attachments', None)
        
        # Update the quotation fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        # Update related objects if provided
        if items_data is not None:
            self._update_items(instance, items_data)
        
        if sales_agents_data is not None:
            self._update_sales_agents(instance, sales_agents_data)
        
        # Update customer contacts if provided
        if customer_contacts_data is not None:
            instance.customer_contacts.set(customer_contacts_data)
        
        if additional_controls_data is not None:
            self._update_additional_controls(instance, additional_controls_data)
        
        if attachments_data is not None:
            self._update_attachments(instance, attachments_data)
        
        # Calculate and update total amount
        self._update_total_amount(instance)
        
        return instance
    
    def _create_items(self, quotation, items_data):
        for item_data in items_data:
            QuotationItem.objects.create(quotation=quotation, **item_data)
    
    def _create_sales_agents(self, quotation, sales_agents_data):
        for agent_data in sales_agents_data:
            QuotationSalesAgent.objects.create(quotation=quotation, **agent_data)
    
    def _create_additional_controls(self, quotation, additional_controls_data):
        if additional_controls_data:
            QuotationAdditionalControl.objects.create(quotation=quotation, **additional_controls_data)
    
    def _create_attachments(self, quotation, attachments_data):
        for attachment_data in attachments_data:
            QuotationAttachment.objects.create(quotation=quotation, **attachment_data)
    
    def _update_items(self, quotation, items_data):
        # Delete existing items
        quotation.items.all().delete()
        # Create new items
        self._create_items(quotation, items_data)
    
    def _update_sales_agents(self, quotation, sales_agents_data):
        # Delete existing sales agents
        quotation.sales_agents.all().delete()
        # Create new sales agents
        self._create_sales_agents(quotation, sales_agents_data)
    
    def _update_additional_controls(self, quotation, additional_controls_data):
        # Delete existing additional controls
        quotation.additional_controls.all().delete()
        # Create new additional controls if provided
        if additional_controls_data:
            self._create_additional_controls(quotation, additional_controls_data)
    
    def _update_attachments(self, quotation, attachments_data):
        # Delete existing attachments
        quotation.attachments.all().delete()
        # Create new attachments
        self._create_attachments(quotation, attachments_data)
    
    def _update_total_amount(self, quotation):
        # Calculate total amount based on items
        total = sum(item.total_selling for item in quotation.items.all())
        quotation.total_amount = total
        quotation.save(update_fields=['total_amount'])
