from rest_framework import serializers
from django.db import transaction
from django.conf import settings # Keep for AUTH_USER_MODEL if used implicitly
from .models import (
    Quotation, QuotationItem, QuotationSalesAgent,
    QuotationAdditionalControls, QuotationAttachment, TermsCondition,
    PaymentTerm, DeliveryOption, OtherOption
)
# Corrected imports from admin_api
from admin_api.models import (
    Customer, CustomerContact, Inventory, Brand, CustomUser # Added CustomUser
)
from admin_api.serializers import (
    CustomerContactSerializer, BrandSerializer, UserSerializer # Added UserSerializer
)
# Removed incorrect import: from users.serializers import UserSerializer

# --- Reusable Option Serializers ---

class TermsConditionSerializer(serializers.ModelSerializer):
    class Meta:
        model = TermsCondition
        fields = ['id', 'name']

class PaymentTermSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentTerm
        fields = ['id', 'name']

class DeliveryOptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeliveryOption
        fields = ['id', 'name']

class OtherOptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = OtherOption
        fields = ['id', 'name']

# --- Nested Component Serializers ---

class InventoryNestedSerializer(serializers.ModelSerializer):
    """Minimal inventory details for nesting."""
    brand_name = serializers.CharField(source='brand.name', read_only=True)
    # Ensure stock_quantity is in the Inventory model if used here
    stock_quantity = serializers.IntegerField(read_only=True)

    class Meta:
        model = Inventory
        fields = [
            'id', 'item_code', 'brand_name', 'unit', 'wholesale_price',
            'photo', 'external_description', 'stock_quantity'
        ]
        read_only_fields = fields

class QuotationItemSerializer(serializers.ModelSerializer):
    """Serializer for Quotation Items (Read & Write)."""
    inventory_id = serializers.PrimaryKeyRelatedField(
        queryset=Inventory.objects.all(), source='inventory', write_only=True
    )
    brand_id = serializers.PrimaryKeyRelatedField(
        queryset=Brand.objects.all(), source='brand', write_only=True, required=False, allow_null=True
    )

    inventory_detail = InventoryNestedSerializer(source='inventory', read_only=True)
    brand_detail = BrandSerializer(source='brand', read_only=True)
    made_in = serializers.SerializerMethodField(read_only=True)
    inventory_status = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = QuotationItem
        fields = [
            'id',
            'inventory_id', # Write
            'inventory_detail', # Read
            'item_code', # Read-only (populated from inventory)
            'brand_id', # Write
            'brand_detail', # Read
            'show_brand',
            'made_in', # Read (calculated)
            'wholesale_price', # Override
            'actual_landed_cost',
            'estimated_landed_cost',
            'notes',
            'unit', # Override
            'quantity',
            'photo', # Override (handle file upload separately if needed)
            'show_photo',
            'baseline_margin',
            'inventory_status', # Read (calculated)
            'external_description', # Override
            'has_discount',
            'discount_type',
            'discount_percentage',
            'discount_value',
            'net_selling', # Read-only (calculated in model save)
            'total_selling', # Read-only (calculated in model save)
        ]
        read_only_fields = ['id', 'item_code', 'net_selling', 'total_selling', 'made_in', 'inventory_status']

    def get_made_in(self, obj: QuotationItem) -> str | None:
        if obj.show_brand and obj.brand and hasattr(obj.brand, 'made_in'):
             return obj.brand.made_in
        return None

    def get_inventory_status(self, obj: QuotationItem) -> str:
        stock = obj.inventory.stock_quantity if obj.inventory and hasattr(obj.inventory, 'stock_quantity') else 0
        quantity = obj.quantity

        if quantity > 1:
            if stock <= 0:
                return "For Importation"
            elif quantity > stock:
                return f"{stock} pcs In Stock, Balance for Importation"
            else:
                return "In Stock"
        else:
            if stock <= 0:
                return "For Importation"
            else:
                return f"{stock} pcs in stock"

class QuotationSalesAgentSerializer(serializers.ModelSerializer):
    """Serializer for Sales Agents linked to a Quotation."""
    # Use the imported CustomUser for the queryset
    agent_id = serializers.PrimaryKeyRelatedField(
        queryset=CustomUser.objects.all(), source='agent', write_only=True
    )
    # Use the imported UserSerializer from admin_api
    agent_detail = UserSerializer(source='agent', read_only=True)

    class Meta:
        model = QuotationSalesAgent
        fields = ['id', 'agent_id', 'agent_detail', 'role']
        read_only_fields = ['id']

class QuotationAdditionalControlsSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuotationAdditionalControls
        exclude = ['quotation', 'id']

class QuotationAttachmentSerializer(serializers.ModelSerializer):
    file_url = serializers.SerializerMethodField(read_only=True)
    file_name = serializers.SerializerMethodField(read_only=True)
    # Optional: Add uploader details if needed, using the correct UserSerializer
    # uploaded_by_detail = UserSerializer(source='uploaded_by', read_only=True)

    class Meta:
        model = QuotationAttachment
        fields = [
            'id', 'file', 'file_url', 'file_name',
            'uploaded_on', 'uploaded_by', # 'uploaded_by_detail'
        ]
        read_only_fields = ['id', 'file_url', 'file_name', 'uploaded_on', 'uploaded_by'] # uploaded_by is set implicitly

    def get_file_url(self, obj: QuotationAttachment) -> str | None:
        request = self.context.get('request')
        if request and obj.file:
            return request.build_absolute_uri(obj.file.url)
        return None

    def get_file_name(self, obj: QuotationAttachment) -> str | None:
        if obj.file:
            return obj.file.name.split('/')[-1] # Get base filename
        return None

# --- Main Quotation Serializers ---

class QuotationListSerializer(serializers.ModelSerializer):
    """Serializer for listing quotations."""
    customer_name = serializers.CharField(source='customer.name', read_only=True)
    main_sales_agent_name = serializers.SerializerMethodField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    currency_display = serializers.CharField(source='get_currency_display', read_only=True)

    class Meta:
        model = Quotation
        fields = [
            'id', 'quote_number', 'status', 'status_display', 'customer', 'customer_name',
            'date', 'total_amount', 'currency', 'currency_display',
            'main_sales_agent_name', 'created_on',
        ]

    def get_main_sales_agent_name(self, obj: Quotation) -> str | None:
        main_agent_link = obj.sales_agents.filter(role=QuotationSalesAgent.Role.MAIN).first()
        if main_agent_link and main_agent_link.agent:
            # Use get_full_name() if available, otherwise username
            return main_agent_link.agent.get_full_name() or main_agent_link.agent.username
        return None

class QuotationDetailSerializer(serializers.ModelSerializer):
    """Serializer for retrieving a single quotation with full details."""
    customer_detail = serializers.SerializerMethodField(read_only=True) # Use method field for flexibility
    items = QuotationItemSerializer(many=True, read_only=True)
    sales_agents = QuotationSalesAgentSerializer(many=True, read_only=True)
    additional_controls = QuotationAdditionalControlsSerializer(read_only=True)
    attachments = QuotationAttachmentSerializer(many=True, read_only=True)
    customer_contacts = CustomerContactSerializer(many=True, read_only=True) # Use existing serializer

    # Include details for linked options
    terms_conditions = TermsConditionSerializer(read_only=True)
    payment_terms = PaymentTermSerializer(read_only=True)
    delivery_options = DeliveryOptionSerializer(read_only=True)
    other_options = OtherOptionSerializer(read_only=True)

    # Display fields
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    currency_display = serializers.CharField(source='get_currency_display', read_only=True)
    created_by = UserSerializer(read_only=True) # Use correct UserSerializer
    last_modified_by = UserSerializer(read_only=True) # Use correct UserSerializer

    class Meta:
        model = Quotation
        fields = '__all__' # Include all fields from the model

    def get_customer_detail(self, obj: Quotation) -> dict | None:
        # Example: Return basic customer info. Adjust as needed.
        if obj.customer:
            return {
                'id': obj.customer.id,
                'name': obj.customer.name,
                # Add other fields if required by the frontend form
            }
        return None

    def get_fields(self):
        """Pass context down to nested serializers (e.g., for request object)."""
        fields = super().get_fields()
        # Ensure context is passed to nested serializers that might need the request
        fields['attachments'].context.update(self.context)
        # Add others if they need context (e.g., ItemSerializer if photo URL needs request)
        # fields['items'].context.update(self.context)
        return fields


class QuotationCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializer for creating and updating quotations with nested data."""
    # Nested writable serializers
    items = QuotationItemSerializer(many=True, required=False)
    sales_agents = QuotationSalesAgentSerializer(many=True, required=False)
    additional_controls = QuotationAdditionalControlsSerializer(required=False)
    # Note: Attachments are typically handled separately (e.g., dedicated upload endpoint)
    # attachments = QuotationAttachmentSerializer(many=True, read_only=True) # Read-only here

    # Writable FKs and M2M
    customer = serializers.PrimaryKeyRelatedField(queryset=Customer.objects.all())
    customer_contacts = serializers.PrimaryKeyRelatedField(
        queryset=CustomerContact.objects.all(), many=True, required=False
    )
    terms_conditions = serializers.PrimaryKeyRelatedField(queryset=TermsCondition.objects.all(), required=False, allow_null=True)
    payment_terms = serializers.PrimaryKeyRelatedField(queryset=PaymentTerm.objects.all(), required=False, allow_null=True)
    delivery_options = serializers.PrimaryKeyRelatedField(queryset=DeliveryOption.objects.all(), required=False, allow_null=True)
    other_options = serializers.PrimaryKeyRelatedField(queryset=OtherOption.objects.all(), required=False, allow_null=True)

    # Read-only fields shown after create/update
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    currency_display = serializers.CharField(source='get_currency_display', read_only=True)
    total_amount = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)
    quote_number = serializers.CharField(read_only=True)
    # Use correct UserSerializer for read-only display
    created_by = UserSerializer(read_only=True)
    last_modified_by = UserSerializer(read_only=True)

    class Meta:
        model = Quotation
        fields = [
            # Writable fields
            'status', 'customer', 'date', 'purchase_request', 'expiry_date',
            'currency', 'notes', 'price', 'validity',
            'terms_conditions', 'payment_terms', 'delivery_options', 'other_options',
            'customer_contacts', # M2M write
            'items', # Nested write
            'sales_agents', # Nested write
            'additional_controls', # Nested write
            # Read-only fields
            'id', 'quote_number', 'total_amount', 'status_display', 'currency_display',
            'created_by', 'created_on', 'last_modified_by', 'last_modified_on',
        ]
        read_only_fields = [
            'id', 'quote_number', 'total_amount', 'created_by', 'created_on',
            'last_modified_by', 'last_modified_on',
        ]

    def _update_nested(self, quotation, nested_data, serializer_class, related_manager_name):
        """Helper to update nested one-to-many relationships."""
        manager = getattr(quotation, related_manager_name)
        existing_items = {item.id: item for item in manager.all()}
        validated_ids = set()
        context = self.context # Pass context down

        for item_data in nested_data:
            item_id = item_data.get('id', None)
            if item_id: # Update existing item
                if item_id in existing_items:
                    instance = existing_items[item_id]
                    # Pass context when initializing serializer for update
                    serializer = serializer_class(instance, data=item_data, partial=True, context=context)
                    if serializer.is_valid(raise_exception=True):
                        serializer.save()
                    validated_ids.add(item_id)
            else: # Create new item
                # Pass context when initializing serializer for create
                serializer = serializer_class(data=item_data, context=context)
                if serializer.is_valid(raise_exception=True):
                    serializer.save(quotation=quotation) # Link to parent

        # Delete items not included in the update
        for item_id, instance in existing_items.items():
            if item_id not in validated_ids:
                instance.delete()

    def _update_total_amount(self, instance):
        """Recalculates and saves the total amount for the quotation."""
        # Ensure items are refreshed from DB before summing
        instance.refresh_from_db(fields=['items'])
        total = sum(item.total_selling for item in instance.items.all())
        if instance.total_amount != total:
            # Get user from context for last_modified_by
            request = self.context.get('request')
            user = request.user if request and request.user.is_authenticated else None
            instance.total_amount = total
            instance.last_modified_by = user # Update modifier when total changes
            instance.save(update_fields=['total_amount', 'last_modified_on', 'last_modified_by'])

    @transaction.atomic
    def create(self, validated_data):
        items_data = validated_data.pop('items', [])
        agents_data = validated_data.pop('sales_agents', [])
        controls_data = validated_data.pop('additional_controls', None)
        contacts_data = validated_data.pop('customer_contacts', [])

        request = self.context.get('request')
        user = request.user if request and request.user.is_authenticated else None
        validated_data['created_by'] = user
        validated_data['last_modified_by'] = user

        # Generate quote number (Example: Q-YYYYMMDD-XXXX) - Implement your logic
        # This should ideally be more robust (e.g., using sequences or atomic counters)
        from django.utils import timezone
        import random
        prefix = f"Q-{timezone.now().strftime('%Y%m%d')}"
        last_quote = Quotation.objects.filter(quote_number__startswith=prefix).order_by('quote_number').last()
        if last_quote:
            last_num = int(last_quote.quote_number.split('-')[-1])
            next_num = last_num + 1
        else:
            next_num = 1
        validated_data['quote_number'] = f"{prefix}-{next_num:04d}"


        quotation = Quotation.objects.create(**validated_data)

        # Pass context when creating nested items
        item_serializer = QuotationItemSerializer(data=items_data, many=True, context=self.context)
        if item_serializer.is_valid(raise_exception=True):
            item_serializer.save(quotation=quotation)

        agent_serializer = QuotationSalesAgentSerializer(data=agents_data, many=True, context=self.context)
        if agent_serializer.is_valid(raise_exception=True):
            agent_serializer.save(quotation=quotation)

        if controls_data:
            # Pass context if needed by controls serializer
            controls_serializer = QuotationAdditionalControlsSerializer(data=controls_data, context=self.context)
            if controls_serializer.is_valid(raise_exception=True):
                 controls_serializer.save(quotation=quotation)

        if contacts_data:
            quotation.customer_contacts.set(contacts_data)

        self._update_total_amount(quotation)

        return quotation

    @transaction.atomic
    def update(self, instance, validated_data):
        items_data = validated_data.pop('items', None)
        agents_data = validated_data.pop('sales_agents', None)
        controls_data = validated_data.pop('additional_controls', None)
        contacts_data = validated_data.pop('customer_contacts', None)

        request = self.context.get('request')
        user = request.user if request and request.user.is_authenticated else None
        validated_data['last_modified_by'] = user

        m2m_fields = ['customer_contacts']
        regular_fields_data = {k: v for k, v in validated_data.items() if k not in m2m_fields}

        for attr, value in regular_fields_data.items():
             if attr not in ['items', 'sales_agents', 'additional_controls']:
                 setattr(instance, attr, value)
        instance.save()

        if items_data is not None:
            self._update_nested(instance, items_data, QuotationItemSerializer, 'items')

        if agents_data is not None:
            self._update_nested(instance, agents_data, QuotationSalesAgentSerializer, 'sales_agents')

        if controls_data is not None:
            controls_instance = getattr(instance, 'additional_controls', None)
            if controls_instance:
                # Pass context for update
                serializer = QuotationAdditionalControlsSerializer(controls_instance, data=controls_data, partial=True, context=self.context)
                if serializer.is_valid(raise_exception=True):
                    serializer.save()
            else:
                 # Pass context for create
                serializer = QuotationAdditionalControlsSerializer(data=controls_data, context=self.context)
                if serializer.is_valid(raise_exception=True):
                    serializer.save(quotation=instance)


        if contacts_data is not None:
            instance.customer_contacts.set(contacts_data)

        self._update_total_amount(instance)

        return instance

class CustomerSerializer(serializers.ModelSerializer):
    """
    Serializer for Customer model.
    """
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    parent_company_name = serializers.CharField(source='parent_company.name', read_only=True, allow_null=True)

    class Meta:
        model = Customer
        fields = [
            'id', 'name', 'registered_name', 'tin', 'phone_number', 
            'status', 'status_display', 'has_parent', 'parent_company', 
            'parent_company_name', 'company_address', 'city', 'vat_type',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']