from rest_framework import serializers
from django.db.models import Sum
from .models import (
    Quotation, QuotationAttachment, QuotationSalesAgent, QuotationAdditionalControls,
    Payment, Delivery, Other, QuotationTermsAndConditions, QuotationContact, QuotationItem, LastQuotedPrice
)
from admin_api.models import Customer, CustomerContact, Inventory
import json

class QuotationAttachmentSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(required=False)
    
    class Meta:
        model = QuotationAttachment
        fields = ['id', 'file', 'filename', 'uploaded_on']
        read_only_fields = ['id', 'uploaded_on']

class QuotationSalesAgentSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(required=False)
    
    class Meta:
        model = QuotationSalesAgent
        fields = ['id', 'agent_name', 'role']
        read_only_fields = ['id']

class QuotationAdditionalControlsSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuotationAdditionalControls
        fields = ['show_carton_packing', 'do_not_show_all_photos', 'highlight_item_notes', 'show_devaluation_clause']

class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = ['id', 'text', 'created_on']

class DeliverySerializer(serializers.ModelSerializer):
    class Meta:
        model = Delivery
        fields = ['id', 'text', 'created_on']

class OtherSerializer(serializers.ModelSerializer):
    class Meta:
        model = Other
        fields = ['id', 'text', 'created_on']

class QuotationTermsAndConditionsSerializer(serializers.ModelSerializer):
    payment_text = serializers.SerializerMethodField()
    delivery_text = serializers.SerializerMethodField()
    other_text = serializers.SerializerMethodField()
    
    class Meta:
        model = QuotationTermsAndConditions
        fields = ['price', 'payment', 'payment_text', 'delivery', 'delivery_text', 'validity', 'other', 'other_text']
    
    def get_payment_text(self, obj):
        return obj.payment.text if obj.payment else None
    
    def get_delivery_text(self, obj):
        return obj.delivery.text if obj.delivery else None
    
    def get_other_text(self, obj):
        return obj.other.text if obj.other else None

class CustomerContactSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomerContact
        fields = [
            'id', 'customer', 'contact_person', 'position', 'department', 
            'email', 'mobile_number', 'office_number'
        ]
        extra_kwargs = {
            'customer': {'required': True}
        }

class QuotationContactSerializer(serializers.ModelSerializer):
    contact_details = CustomerContactSerializer(source='customer_contact', read_only=True)
    
    class Meta:
        model = QuotationContact
        fields = ['id', 'customer_contact', 'contact_details']

class QuotationItemSerializer(serializers.ModelSerializer):
    item_code = serializers.CharField(source='inventory.item_code', read_only=True)
    product_name = serializers.CharField(source='inventory.product_name', read_only=True)
    brand = serializers.CharField(source='inventory.brand.name', read_only=True)
    made_in = serializers.CharField(source='inventory.brand.country', read_only=True)
    inventory_stock = serializers.DecimalField(source='inventory.stock_on_hand', max_digits=10, decimal_places=2, read_only=True)
    inventory_status = serializers.SerializerMethodField()
    last_quoted_price = serializers.SerializerMethodField()
    
    class Meta:
        model = QuotationItem
        fields = [
            'id', 'quotation', 'inventory', 'item_code', 'product_name', 'brand', 'made_in',
            'show_brand', 'show_made_in', 'wholesale_price', 'actual_landed_cost',
            'estimated_landed_cost', 'notes', 'unit', 'quantity', 'photo', 'show_photo',
            'baseline_margin', 'inventory_stock', 'inventory_status', 'external_description',
            'last_quoted_price', 'landed_cost_discount', 'has_discount', 'discount_type',
            'discount_percentage', 'discount_value', 'net_selling', 'total_selling'
        ]
        read_only_fields = ['id', 'inventory_status', 'last_quoted_price', 'landed_cost_discount', 'net_selling', 'total_selling']
    
    def get_inventory_status(self, obj):
        stock = obj.inventory.stock_on_hand
        quantity = obj.quantity
        
        if quantity > 1:
            if stock == 0:
                return "For Importation"
            elif stock > 0 and quantity > stock:
                return f"{stock} pcs In Stock, Balance for Importation"
            elif stock > 0 and quantity <= stock:
                return "In Stock"
        else:  # quantity = 1
            if stock == 0:
                return "For Importation"
            else:
                return f"{stock} pcs in stock"
    
    def get_last_quoted_price(self, obj):
        # Get the customer from the quotation
        customer = obj.quotation.customer
        
        # Find the last quoted price for this inventory and customer
        try:
            last_price = LastQuotedPrice.objects.filter(
                inventory=obj.inventory,
                customer=customer
            ).exclude(quotation=obj.quotation).order_by('-quoted_at').first()
            
            if last_price:
                return last_price.price
        except Exception:
            pass
        
        return None
    
    def create(self, validated_data):
        # Get inventory data to pre-populate fields
        inventory = validated_data.get('inventory')
        
        # Pre-populate fields from inventory if not provided
        if inventory:
            if 'wholesale_price' not in validated_data or validated_data['wholesale_price'] is None:
                validated_data['wholesale_price'] = inventory.wholesale_price
            
            if 'unit' not in validated_data or not validated_data['unit']:
                validated_data['unit'] = inventory.unit
            
            if 'external_description' not in validated_data or not validated_data['external_description']:
                validated_data['external_description'] = inventory.external_description
        
        # Create the item
        item = QuotationItem.objects.create(**validated_data)
        
        # Update or create LastQuotedPrice
        if item.wholesale_price and item.quotation.customer:
            LastQuotedPrice.objects.update_or_create(
                inventory=item.inventory,
                customer=item.quotation.customer,
                defaults={
                    'price': item.wholesale_price,
                    'quotation': item.quotation
                }
            )
        
        return item
    
class QuotationSerializer(serializers.ModelSerializer):
    attachments = QuotationAttachmentSerializer(many=True, read_only=True)
    sales_agents = QuotationSalesAgentSerializer(many=True, read_only=True)
    customer_name = serializers.StringRelatedField(source='customer', read_only=True)
    main_agent = serializers.SerializerMethodField()
    additional_controls = QuotationAdditionalControlsSerializer(read_only=True)
    terms_and_conditions = QuotationTermsAndConditionsSerializer(read_only=True)
    contacts = QuotationContactSerializer(many=True, read_only=True)
    items = QuotationItemSerializer(many=True, read_only=True)
    
    class Meta:
        model = Quotation
        fields = [
            'id', 'quote_number', 'status', 'customer', 'customer_name',
            'date', 'expiry_date', 'total_amount', 'currency',
            'purchase_request', 'notes', 'created_on', 'last_modified_on',
            'attachments', 'sales_agents', 'main_agent', 'additional_controls',
            'terms_and_conditions', 'contacts', 'items'
        ]
        read_only_fields = [
            'id', 'quote_number', 'created_on', 'last_modified_on',
            'created_by', 'last_modified_by'
        ]
    
    def get_main_agent(self, obj):
        main_agent = obj.sales_agents.filter(role='main').first()
        if main_agent:
            return QuotationSalesAgentSerializer(main_agent).data
        return None

class QuotationCreateUpdateSerializer(serializers.ModelSerializer):
    attachments = QuotationAttachmentSerializer(many=True, required=False)
    sales_agents = QuotationSalesAgentSerializer(many=True, required=False)
    additional_controls = QuotationAdditionalControlsSerializer(required=False)
    contacts = serializers.PrimaryKeyRelatedField(
        queryset=CustomerContact.objects.all(),
        many=True,
        required=False,
        write_only=True
    )
    items = QuotationItemSerializer(many=True, required=False)
    
    class Meta:
        model = Quotation
        fields = [
            'id', 'quote_number', 'status', 'customer', 'date',
            'total_amount', 'purchase_request', 'expiry_date', 'currency',
            'notes', 'attachments', 'sales_agents', 'additional_controls',
            'contacts', 'items'
        ]
        read_only_fields = ['id', 'quote_number']
    
    def validate_sales_agents(self, value):
        # Check that there is exactly one main agent
        main_agents = [agent for agent in value if agent.get('role') == 'main']
        if len(main_agents) != 1:
            raise serializers.ValidationError("Exactly one main sales agent is required.")
        return value
    
    def create(self, validated_data):
        attachments_data = validated_data.pop('attachments', [])
        sales_agents_data = validated_data.pop('sales_agents', [])
        additional_controls_data = validated_data.pop('additional_controls', None)
        contacts_data = validated_data.pop('contacts', [])
        items_data = validated_data.pop('items', [])
        
        # Set the created_by field
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            validated_data['created_by'] = request.user
            validated_data['last_modified_by'] = request.user
        
        quotation = Quotation.objects.create(**validated_data)
        
        # Create attachments
        for attachment_data in attachments_data:
            QuotationAttachment.objects.create(quotation=quotation, **attachment_data)
        
        # Create sales agents
        for agent_data in sales_agents_data:
            QuotationSalesAgent.objects.create(quotation=quotation, **agent_data)
        
        # Create additional controls
        if additional_controls_data:
            QuotationAdditionalControls.objects.create(quotation=quotation, **additional_controls_data)
        else:
            # Create with default values
            QuotationAdditionalControls.objects.create(quotation=quotation)
        
        # Create quotation contacts
        for contact in contacts_data:
            QuotationContact.objects.create(
                quotation=quotation,
                customer_contact=contact
            )
        
        # Create quotation items
        for item_data in items_data:
            # Get inventory data to pre-populate fields
            inventory_id = item_data.get('inventory')
            if inventory_id:
                try:
                    inventory = Inventory.objects.get(id=inventory_id)
                    
                    # Pre-populate fields from inventory if not provided
                    if 'wholesale_price' not in item_data or item_data['wholesale_price'] is None:
                        item_data['wholesale_price'] = inventory.wholesale_price
                    
                    if 'unit' not in item_data or not item_data['unit']:
                        item_data['unit'] = inventory.unit
                    
                    if 'external_description' not in item_data or not item_data['external_description']:
                        item_data['external_description'] = inventory.external_description
                except Inventory.DoesNotExist:
                    pass
            
            # Create the item
            QuotationItem.objects.create(quotation=quotation, **item_data)
        
        # Calculate and update total amount
        self._update_total_amount(quotation)
            
        return quotation
    
    def update(self, instance, validated_data):
        # Extract nested data
        attachments_data = validated_data.pop('attachments', None)
        sales_agents_data = validated_data.pop('sales_agents', None)
        contacts_data = validated_data.pop('contacts', None)
        additional_controls_data = validated_data.pop('additional_controls', None)
        items_data = validated_data.pop('items', None)
        
        # Get the request from context
        request = self.context.get('request')
        
        # Extract terms and conditions data from the request
        terms_data = None
        if request and 'data' in request.data:
            try:
                request_data = json.loads(request.data['data'])
                if 'terms_and_conditions' in request_data:
                    terms_data = request_data['terms_and_conditions']
            except (json.JSONDecodeError, KeyError):
                pass
        
        # Update the quotation instance with validated data
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        # Set the last modified by user
        if request and hasattr(request, 'user'):
            instance.last_modified_by = request.user
        
        instance.save()
        
        # Update attachments if provided
        if attachments_data is not None:
            self._update_nested_objects(
                instance.attachments, 
                attachments_data, 
                QuotationAttachment, 
                'quotation'
            )
        
        # Update sales agents if provided
        if sales_agents_data is not None:
            self._update_nested_objects(
                instance.sales_agents, 
                sales_agents_data, 
                QuotationSalesAgent, 
                'quotation'
            )
        
        # Update additional controls if provided
        if additional_controls_data is not None:
            try:
                controls = instance.additional_controls
                for attr, value in additional_controls_data.items():
                    setattr(controls, attr, value)
                controls.save()
            except QuotationAdditionalControls.DoesNotExist:
                QuotationAdditionalControls.objects.create(
                    quotation=instance, 
                    **additional_controls_data
                )
        
        # Update contacts if provided
        if contacts_data is not None:
            # Clear existing contacts
            QuotationContact.objects.filter(quotation=instance).delete()
            
            # Create new contacts
            for contact in contacts_data:
                QuotationContact.objects.create(
                    quotation=instance,
                    customer_contact=contact
                )
        
        # Update items if provided
        if items_data is not None:
            self._update_nested_objects(
                instance.items, 
                items_data, 
                QuotationItem, 
                'quotation'
            )
            
            # Update total amount
            self._update_total_amount(instance)
        
        # Update terms and conditions if provided
        if terms_data is not None:
            try:
                terms = instance.terms_and_conditions
                
                # Update simple fields
                if 'price' in terms_data:
                    terms.price = terms_data['price']
                if 'validity' in terms_data:
                    terms.validity = terms_data['validity']
                
                # Update related fields
                if 'payment' in terms_data and terms_data['payment']:
                    terms.payment_id = terms_data['payment']
                if 'delivery' in terms_data and terms_data['delivery']:
                    terms.delivery_id = terms_data['delivery']
                if 'other' in terms_data and terms_data['other']:
                    terms.other_id = terms_data['other']
                
                terms.save()
            except QuotationTermsAndConditions.DoesNotExist:
                # Create new terms and conditions
                terms_obj = {
                    'quotation': instance,
                    'price': terms_data.get('price'),
                    'validity': terms_data.get('validity')
                }
                
                # Add related fields if they exist
                if 'payment' in terms_data and terms_data['payment']:
                    terms_obj['payment_id'] = terms_data['payment']
                if 'delivery' in terms_data and terms_data['delivery']:
                    terms_obj['delivery_id'] = terms_data['delivery']
                if 'other' in terms_data and terms_data['other']:
                    terms_obj['other_id'] = terms_data['other']
                
                QuotationTermsAndConditions.objects.create(**terms_obj)
        
        return instance
    
    def _update_nested_objects(self, queryset, data_list, model_class, parent_field_name):
        """
        Helper method to update nested objects (attachments, sales agents, items)
        """
        # Get existing IDs
        existing_ids = set(queryset.values_list('id', flat=True))
        updated_ids = set()

        # Special handling for sales agents to avoid unique constraint violations
        if model_class == QuotationSalesAgent:
            # First, delete any existing main agents if we're adding a new one
            main_agent_in_data = any(data.get('role') == 'main' for data in data_list)
            if main_agent_in_data:
                queryset.filter(role='main').delete()

        # Create or update objects
        for data in data_list:
            obj_id = data.get('id')

            if obj_id:
                # Update existing object
                try:
                    obj = queryset.get(id=obj_id)
                    for attr, value in data.items():
                        if attr != 'id':
                            setattr(obj, attr, value)
                    obj.save()
                    updated_ids.add(obj_id)
                except model_class.DoesNotExist:
                    # If ID doesn't exist, create new object
                    kwargs = {parent_field_name: queryset.instance, **{k: v for k, v in data.items() if k != 'id'}}
                    obj = model_class.objects.create(**kwargs)
                    updated_ids.add(obj.id)
            else:
                # Create new object
                kwargs = {parent_field_name: queryset.instance, **data}
                obj = model_class.objects.create(**kwargs)
                updated_ids.add(obj.id)

        # Delete objects that weren't updated
        objects_to_delete = existing_ids - updated_ids
        queryset.filter(id__in=objects_to_delete).delete()
    
    def _update_total_amount(self, quotation):
        total = quotation.items.aggregate(total=Sum('total_selling'))['total'] or 0
        quotation.total_amount = total
        quotation.save(update_fields=['total_amount'])

class CustomerListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = ['id', 'name', 'registered_name']

class QuotationStatusUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Quotation
        fields = ['status']
        
    def validate_status(self, value):
        """Validate the status transition"""
        current_status = self.instance.status
        
        # Define valid transitions
        valid_transitions = {
            'draft': ['for_approval'],
            'for_approval': ['approved', 'rejected', 'draft'],
            'approved': ['expired'],
            'rejected': ['draft'],
            'expired': []
        }
        
        if value not in valid_transitions.get(current_status, []):
            raise serializers.ValidationError(
                f"Cannot change status from '{current_status}' to '{value}'. "
                f"Valid transitions are: {', '.join(valid_transitions.get(current_status, []))}"
            )
        
        return value
    
    def validate(self, data):
        """Additional validation based on user permissions"""
        user = self.context['request'].user
        new_status = data.get('status')
        
        # Check if user has permission for this status change
        if new_status in ['approved', 'rejected']:
            # Only admin/supervisor can approve or reject
            if not (user.is_staff or user.groups.filter(name='Supervisor').exists()):
                raise serializers.ValidationError({
                    'status': 'You do not have permission to approve or reject quotations'
                })
        
        return data

class LastQuotedPriceSerializer(serializers.ModelSerializer):
    inventory_code = serializers.CharField(source='inventory.item_code', read_only=True)
    inventory_name = serializers.CharField(source='inventory.item_name', read_only=True)
    customer_name = serializers.CharField(source='customer.name', read_only=True)
    quotation_number = serializers.CharField(source='quotation.quote_number', read_only=True)
    
    class Meta:
        model = LastQuotedPrice
        fields = [
            'id', 'inventory', 'customer', 'price', 'quotation', 'quoted_at',
            'inventory_code', 'inventory_name', 'customer_name', 'quotation_number'
        ]
        read_only_fields = ['quoted_at']