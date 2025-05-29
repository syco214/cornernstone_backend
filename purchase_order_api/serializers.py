from rest_framework import serializers
from django.db import transaction
from .models import (
    PurchaseOrder, PurchaseOrderItem, PurchaseOrderDiscountCharge, PurchaseOrderPaymentTerm, PurchaseOrderRoute, PurchaseOrderDownPayment)
from admin_api.models import Supplier, Inventory
from django.contrib.auth import get_user_model
from admin_api.serializers import UserSerializer
from django.db.models import Min
User = get_user_model()

class PurchaseOrderItemSerializer(serializers.ModelSerializer):
    item_code = serializers.CharField(source='inventory.item_code', read_only=True)
    brand = serializers.CharField(source='inventory.brand_name', read_only=True)
    balance_quantity = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = PurchaseOrderItem
        fields = [
            'id', 'purchase_order', 'inventory', 'item_code', 'brand',
            'external_description', 'unit', 'quantity', 'list_price',
            'discount_type', 'discount_value', 'calculated_discount_amount',
            'line_total', 'quantity_received', 'status',
            'ready_date', 'batch_number', 'notes', 'balance_quantity',
        ]
        read_only_fields = [
            'id', 'purchase_order', 'calculated_discount_amount', 'line_total',
            'balance_quantity',
        ]

    def to_internal_value(self, data):
        """
        Override to handle inventory field and set defaults properly.
        """
        # Make a copy to avoid modifying the input
        data = data.copy()
        
        # If inventory is already an object, extract its ID
        if 'inventory' in data and not isinstance(data['inventory'], (int, str)):
            data['inventory'] = data['inventory'].id
        
        # Set default values
        if 'discount_type' not in data or not data.get('discount_type'):
            data['discount_type'] = 'none'
        
        if 'discount_value' not in data or data.get('discount_value') is None:
            data['discount_value'] = 0
        
        return super().to_internal_value(data)

    def create(self, validated_data):
        """
        Create a PurchaseOrderItem instance with proper handling of inventory.
        """
        # Ensure inventory is properly handled
        inventory = validated_data.get('inventory')
        
        # Populating defaults from inventory if not provided
        if inventory:
            if 'external_description' not in validated_data or not validated_data['external_description']:
                validated_data['external_description'] = inventory.external_description
            if 'unit' not in validated_data or not validated_data['unit']:
                validated_data['unit'] = inventory.unit
        
        # Set default values for fields that might cause issues
        if 'discount_type' not in validated_data:
            validated_data['discount_type'] = 'none'
        if 'discount_value' not in validated_data:
            validated_data['discount_value'] = 0
        if 'status' not in validated_data:
            validated_data['status'] = 'pending'
        
        # Create the instance
        return super().create(validated_data)

class PurchaseOrderDiscountChargeSerializer(serializers.ModelSerializer):
    class Meta:
        model = PurchaseOrderDiscountCharge
        fields = [
            'id', 'purchase_order', 'description', 'is_percentage',
            'value', 'is_deduction',
        ]
        read_only_fields = ['id', 'purchase_order']


class PurchaseOrderPaymentTermSerializer(serializers.ModelSerializer):
    class Meta:
        model = PurchaseOrderPaymentTerm
        fields = [
            'id', 'purchase_order', 'payment_terms_description', 'credit_limit',
            'dp_percentage', 'terms_days', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'purchase_order', 'created_at', 'updated_at']


class PurchaseOrderRouteSerializer(serializers.ModelSerializer):
    completed_by = UserSerializer(read_only=True)
    access_display = serializers.CharField(source='get_access_display', read_only=True)
    
    class Meta:
        model = PurchaseOrderRoute
        fields = [
            'id', 'purchase_order', 'step', 'is_completed', 'is_required', 
            'task', 'access', 'access_display', 'roles', 'completed_at', 'completed_by'
        ]
        read_only_fields = ['id', 'purchase_order', 'step', 'task', 'is_required']


class PurchaseOrderSerializer(serializers.ModelSerializer):
    """Serializer for GET requests (read-only detailed view)."""
    created_by_username = serializers.StringRelatedField(source='created_by', read_only=True)
    last_modified_by_username = serializers.StringRelatedField(source='last_modified_by', read_only=True)
    approved_by_username = serializers.StringRelatedField(source='approved_by', read_only=True)
    supplier_name = serializers.StringRelatedField(source='supplier', read_only=True)
    
    items = PurchaseOrderItemSerializer(many=True, read_only=True)
    discounts_charges = PurchaseOrderDiscountChargeSerializer(many=True, read_only=True)
    payment_term = PurchaseOrderPaymentTermSerializer(read_only=True)
    route_steps = PurchaseOrderRouteSerializer(many=True, read_only=True)
    down_payment = serializers.SerializerMethodField()
    items_by_batch = serializers.SerializerMethodField()

    status_display = serializers.CharField(source='get_status_display', read_only=True)
    currency_display = serializers.CharField(source='get_currency_display', read_only=True)
    supplier_type_display = serializers.CharField(source='get_supplier_type_display', read_only=True)

    class Meta:
        model = PurchaseOrder
        fields = [
            'id', 'po_number', 'supplier', 'supplier_name', 'supplier_type', 'supplier_type_display',
            'delivery_terms', 'currency', 'currency_display', 'supplier_address', 'country',
            'status', 'status_display', 'notes', 'items_gross_amount', 'items_total_discount_amount',
            'subtotal_amount', 'order_level_discount_charge_amount', 'grand_total_amount',
            'created_by', 'created_by_username', 'last_modified_by', 'last_modified_by_username',
            'approved_by', 'approved_by_username', 'created_on', 'last_modified_on',
            'po_date',
            'items', 'discounts_charges', 'payment_term', 'route_steps', 'down_payment',
            'items_by_batch'
        ]
        read_only_fields = fields  # All fields are read-only for this serializer
    
    def get_down_payment(self, obj):
        """Get the down payment for this PO if it exists"""
        down_payment = obj.down_payments.first()
        if not down_payment:
            return None
            
        # Get request from context to build absolute URL
        request = self.context.get('request')
        payment_slip_url = None
        
        if down_payment.payment_slip and request:
            payment_slip_url = request.build_absolute_uri(down_payment.payment_slip.url)
            
        return {
            'id': down_payment.id,
            'amount_paid': down_payment.amount_paid,
            'payment_slip': payment_slip_url,
            'remarks': down_payment.remarks,
        }

    def get_items_by_batch(self, obj):
        """Group items by batch number"""
        batches = {}
        
        # Get all items with batch numbers
        items_with_batch = obj.items.exclude(batch_number__isnull=True).order_by('batch_number')
        
        for item in items_with_batch:
            batch_num = item.batch_number
            if batch_num not in batches:
                # Find the earliest ready date for this batch
                ready_date = obj.items.filter(batch_number=batch_num).aggregate(
                    Min('ready_date')
                )['ready_date__min']
                
                batches[batch_num] = {
                    'batch_number': batch_num,
                    'ready_date': ready_date,
                    'items': []
                }
            
            # Add item to its batch
            batches[batch_num]['items'].append(PurchaseOrderItemSerializer(item).data)
        
        # Convert dict to list and sort by batch number
        return [batch_data for _, batch_data in sorted(batches.items())]


class PurchaseOrderCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializer for POST/PUT requests."""
    items = PurchaseOrderItemSerializer(many=True, required=False)
    discounts_charges = PurchaseOrderDiscountChargeSerializer(many=True, required=False)
    payment_term = PurchaseOrderPaymentTermSerializer(required=False)

    # Writable related fields
    supplier = serializers.PrimaryKeyRelatedField(queryset=Supplier.objects.all())
    # created_by, last_modified_by, approved_by will be set in the view or by default

    class Meta:
        model = PurchaseOrder
        fields = [
            'id', 'po_number', 'supplier', 'supplier_type', 'delivery_terms',
            'currency', 'supplier_address', 'country', 'status', 'notes',
            'po_date','items', 'discounts_charges', 'payment_term',
            # Calculated total fields are not included for direct input
        ]
        read_only_fields = ['id', 'po_number'] # po_number is auto-generated

    def validate_supplier_type(self, value: str) -> str:
        if value not in dict(PurchaseOrder.SUPPLIER_TYPE_CHOICES):
            raise serializers.ValidationError('Invalid supplier type.')
        return value

    def validate_currency(self, value: str) -> str:
        if value not in dict(PurchaseOrder.CURRENCY_CHOICES):
            raise serializers.ValidationError('Invalid currency.')
        return value

    def validate_status(self, value: str) -> str:
        if value not in dict(PurchaseOrder.STATUS_CHOICES):
            raise serializers.ValidationError('Invalid status.')
        return value

    def _update_or_create_nested_objects(self, instance: PurchaseOrder, nested_data: list, serializer_class, relation_name: str, parent_field_name: str) -> None:
        """Helper to update/create/delete nested objects."""
        existing_items_qs = getattr(instance, relation_name)
        existing_items_map = {item.id: item for item in existing_items_qs.all()}
        
        final_item_ids = set()

        for item_data in nested_data:
            item_id = item_data.get('id')
            item_data[parent_field_name] = instance.pk # Ensure parent is linked

            if item_id and item_id in existing_items_map: # Update
                item_instance = existing_items_map[item_id]
                serializer = serializer_class(item_instance, data=item_data, partial=True)
                final_item_ids.add(item_id)
            else: # Create
                serializer = serializer_class(data=item_data)
            
            if serializer.is_valid(raise_exception=True):
                saved_item = serializer.save(**{parent_field_name: instance}) # Explicitly pass parent
                final_item_ids.add(saved_item.id)

        # Delete items not in the final set
        ids_to_delete = set(existing_items_map.keys()) - final_item_ids
        if ids_to_delete:
            existing_items_qs.filter(id__in=ids_to_delete).delete()

    def _update_or_create_one_to_one(self, instance: PurchaseOrder, nested_data: dict, serializer_class, relation_name: str) -> None:
        """Helper for OneToOne related objects."""
        current_related_obj = getattr(instance, relation_name, None)
        if not nested_data: # If data is null/empty, delete if exists
            if current_related_obj:
                current_related_obj.delete()
            return

        serializer_kwargs = {'data': nested_data}
        if current_related_obj:
            serializer_kwargs['instance'] = current_related_obj
        
        serializer = serializer_class(**serializer_kwargs)
        if serializer.is_valid(raise_exception=True):
            serializer.save(purchase_order=instance)


    @transaction.atomic
    def create(self, validated_data: dict) -> PurchaseOrder:
        items_data = validated_data.pop('items', [])
        discounts_charges_data = validated_data.pop('discounts_charges', [])
        payment_term_data = validated_data.pop('payment_term', None)
        
        request = self.context.get('request')
        if request and hasattr(request, 'user') and request.user.is_authenticated:
            validated_data['created_by'] = request.user
            validated_data['last_modified_by'] = request.user

        # Create PO first, without totals update
        purchase_order = PurchaseOrder.objects.create(**validated_data)

        # Create nested items
        for item_data in items_data:
            item_data['purchase_order'] = purchase_order.pk  # Link item to PO
            
            # Ensure inventory is a primary key
            if isinstance(item_data.get('inventory'), Inventory):
                item_data['inventory'] = item_data['inventory'].pk
            
            item_serializer = PurchaseOrderItemSerializer(data=item_data)
            if item_serializer.is_valid(raise_exception=True):
                item_serializer.save(purchase_order=purchase_order)  # Save with explicit PO

        # Create nested discounts/charges
        for dc_data in discounts_charges_data:
            dc_data['purchase_order'] = purchase_order.pk
            dc_serializer = PurchaseOrderDiscountChargeSerializer(data=dc_data)
            if dc_serializer.is_valid(raise_exception=True):
                dc_serializer.save(purchase_order=purchase_order)
        
        # Create payment term
        if payment_term_data:
            payment_term_data['purchase_order'] = purchase_order.pk
            pt_serializer = PurchaseOrderPaymentTermSerializer(data=payment_term_data)
            if pt_serializer.is_valid(raise_exception=True):
                pt_serializer.save(purchase_order=purchase_order)
        
        purchase_order.update_totals(save_instance=True)  # Now calculate and save totals
        return purchase_order

    @transaction.atomic
    def update(self, instance: PurchaseOrder, validated_data: dict) -> PurchaseOrder:
        items_data = validated_data.pop('items', None)
        discounts_charges_data = validated_data.pop('discounts_charges', None)
        payment_term_data = validated_data.pop('payment_term', None) # Can be {} or None

        request = self.context.get('request')
        if request and hasattr(request, 'user') and request.user.is_authenticated:
            instance.last_modified_by = request.user

        # Update PurchaseOrder instance fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save(skip_totals_update=True) # Save PO fields first, skip auto totals for now

        # Update/Create/Delete items
        if items_data is not None:
            self._update_or_create_nested_objects(
                instance, items_data, PurchaseOrderItemSerializer, 'items', 'purchase_order'
            )

        # Update/Create/Delete discounts/charges
        if discounts_charges_data is not None:
            self._update_or_create_nested_objects(
                instance, discounts_charges_data, PurchaseOrderDiscountChargeSerializer, 'discounts_charges', 'purchase_order'
            )
        
        # Update/Create/Delete payment term
        # If payment_term_data is an empty dict {}, it means clear the payment term.
        # If None, it means no change was specified for payment_term.
        if payment_term_data is not None: # Process if key 'payment_term' was in request
            self._update_or_create_one_to_one(
                instance, payment_term_data, PurchaseOrderPaymentTermSerializer, 'payment_term'
            )
        
        instance.update_totals(save_instance=True) # Recalculate and save totals
        return instance

class PurchaseOrderDownPaymentSerializer(serializers.ModelSerializer):
    payment_slip_url = serializers.SerializerMethodField()
    
    class Meta:
        model = PurchaseOrderDownPayment
        fields = [
            'id', 'purchase_order', 'amount_paid', 'payment_slip', 'payment_slip_url','remarks'
        ]
    
    def get_payment_slip_url(self, obj):
        if obj.payment_slip and 'request' in self.context:
            return self.context['request'].build_absolute_uri(obj.payment_slip.url)
        return None