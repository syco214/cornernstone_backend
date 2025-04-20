from rest_framework import serializers
from .models import (
    Quotation, QuotationAttachment, QuotationSalesAgent, QuotationAdditionalControls,
    Payment, Delivery, Other, QuotationTermsAndConditions, QuotationContact
)
from admin_api.models import Customer, CustomerContact
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

class QuotationSerializer(serializers.ModelSerializer):
    attachments = QuotationAttachmentSerializer(many=True, read_only=True)
    sales_agents = QuotationSalesAgentSerializer(many=True, read_only=True)
    customer_name = serializers.StringRelatedField(source='customer', read_only=True)
    main_agent = serializers.SerializerMethodField()
    additional_controls = QuotationAdditionalControlsSerializer(read_only=True)
    terms_and_conditions = QuotationTermsAndConditionsSerializer(read_only=True)
    contacts = QuotationContactSerializer(many=True, read_only=True)
    
    class Meta:
        model = Quotation
        fields = [
            'id', 'quote_number', 'status', 'customer', 'customer_name',
            'date', 'expiry_date', 'total_amount', 'currency',
            'purchase_request', 'notes', 'created_on', 'last_modified_on',
            'attachments', 'sales_agents', 'main_agent', 'additional_controls',
            'terms_and_conditions', 'contacts'
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
    
    class Meta:
        model = Quotation
        fields = [
            'id', 'quote_number', 'status', 'customer', 'date',
            'total_amount', 'purchase_request', 'expiry_date', 'currency',
            'notes', 'attachments', 'sales_agents', 'additional_controls',
            'contacts'
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
            
        return quotation
    
    def update(self, instance, validated_data):
        # Extract nested data
        attachments_data = validated_data.pop('attachments', None)
        sales_agents_data = validated_data.pop('sales_agents', None)
        contacts_data = validated_data.pop('contacts', None)
        additional_controls_data = validated_data.pop('additional_controls', None)
        
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

class CustomerListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = ['id', 'name', 'registered_name']