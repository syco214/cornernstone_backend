from rest_framework import serializers
from .models import (
    Quotation, QuotationAttachment, QuotationSalesAgent
)
from admin_api.models import Customer

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

class QuotationSerializer(serializers.ModelSerializer):
    attachments = QuotationAttachmentSerializer(many=True, read_only=True)
    sales_agents = QuotationSalesAgentSerializer(many=True, read_only=True)
    customer_name = serializers.StringRelatedField(source='customer', read_only=True)
    main_agent = serializers.SerializerMethodField()
    
    class Meta:
        model = Quotation
        fields = [
            'id', 'quote_number', 'status', 'customer', 'customer_name', 'date',
            'total_amount', 'created_by', 'created_on', 'last_modified_by',
            'last_modified_on', 'purchase_request', 'expiry_date', 'currency',
            'notes', 'attachments', 'sales_agents', 'main_agent'
        ]
        read_only_fields = [
            'id', 'quote_number', 'created_on', 'last_modified_on',
            'created_by', 'last_modified_by'
        ]
    
    def get_main_agent(self, obj):
        main_agent = obj.sales_agents.filter(role='main').first()
        if main_agent:
            return main_agent.agent_name
        return None

class QuotationCreateUpdateSerializer(serializers.ModelSerializer):
    attachments = QuotationAttachmentSerializer(many=True, required=False)
    sales_agents = QuotationSalesAgentSerializer(many=True, required=False)
    
    class Meta:
        model = Quotation
        fields = [
            'id', 'quote_number', 'status', 'customer', 'date',
            'total_amount', 'purchase_request', 'expiry_date', 'currency',
            'notes', 'attachments', 'sales_agents'
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
            
        return quotation
    
    def update(self, instance, validated_data):
        attachments_data = validated_data.pop('attachments', None)
        sales_agents_data = validated_data.pop('sales_agents', None)
        
        # Set the last_modified_by field
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            validated_data['last_modified_by'] = request.user
        
        # Update quotation fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
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