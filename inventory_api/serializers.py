from rest_framework import serializers
from django.conf import settings
from django.contrib.auth import get_user_model

# Reuse models from admin_api
from admin_api.models import Inventory

User = get_user_model()

class InventorySerializer(serializers.ModelSerializer):
    brand_name = serializers.SerializerMethodField()
    supplier_name = serializers.SerializerMethodField()
    category_name = serializers.SerializerMethodField()
    subcategory_name = serializers.SerializerMethodField()
    sub_level_category_name = serializers.SerializerMethodField()
    made_in = serializers.SerializerMethodField()
    created_by_name = serializers.SerializerMethodField()
    last_modified_by_name = serializers.SerializerMethodField()
    photo_url = serializers.SerializerMethodField()
    
    class Meta:
        model = Inventory
        fields = [
            'id', 'created_by', 'created_by_name', 'created_at', 
            'last_modified_by', 'last_modified_by_name', 'last_modified_at',
            'item_code', 'cip_code', 'product_name', 'status', 
            'supplier', 'supplier_name', 'brand', 'brand_name', 'made_in',
            'product_tagging', 'audit_status', 'category', 'category_name', 
            'subcategory', 'subcategory_name', 
            'sub_level_category', 'sub_level_category_name',
            'has_description', 'unit', 'landed_cost_price', 'landed_cost_unit', 
            'packaging_amount', 'packaging_units', 'packaging_package',
            'external_description', 'length', 'length_unit',
            'color', 'width', 'width_unit', 'height', 'height_unit',
            'volume', 'volume_unit', 'materials', 'pattern', 'photo', 'photo_url',
            'list_price_currency', 'list_price', 'wholesale_price', 'remarks',
            'stock_on_hand', 'reserved_pending_so', 'available_for_sale',
            'incoming_pending_po', 'incoming_stock', 'total_expected'
        ]
        read_only_fields = [
            'id', 'created_at', 'last_modified_at', 'created_by', 'last_modified_by',
            'stock_on_hand', 'reserved_pending_so', 'available_for_sale',
            'incoming_pending_po', 'incoming_stock', 'total_expected'
        ]
    
    def get_brand_name(self, obj):
        return obj.brand.name if obj.brand else None
    
    def get_supplier_name(self, obj):
        return obj.supplier.name if obj.supplier else None
    
    def get_category_name(self, obj):
        return obj.category.name if obj.category else None
    
    def get_subcategory_name(self, obj):
        return obj.subcategory.name if obj.subcategory else None
    
    def get_sub_level_category_name(self, obj):
        return obj.sub_level_category.name if obj.sub_level_category else None
    
    def get_made_in(self, obj):
        return obj.brand.made_in if obj.brand and obj.brand.show_made_in else None
    
    def get_created_by_name(self, obj):
        return f"{obj.created_by.first_name} {obj.created_by.last_name}" if obj.created_by else None
    
    def get_last_modified_by_name(self, obj):
        return f"{obj.last_modified_by.first_name} {obj.last_modified_by.last_name}" if obj.last_modified_by else None
    
    def get_photo_url(self, obj):
        request = self.context.get('request')
        if obj.photo and hasattr(obj.photo, 'url'):
            if request:
                absolute_uri = request.build_absolute_uri(obj.photo.url)
                return absolute_uri
            else:
                base_url = getattr(settings, 'BASE_URL', '')
                media_url = getattr(settings, 'MEDIA_URL', '/media/')
                photo_path = obj.photo.url.lstrip('/')
                media_url = media_url.rstrip('/') + '/'
                base_url = base_url.rstrip('/')
                fallback_url = f"{base_url}{media_url}{photo_path}"
                return fallback_url
        return None
    
    def validate(self, data):
        # Validate category hierarchy
        category = data.get('category')
        subcategory = data.get('subcategory')
        sub_level_category = data.get('sub_level_category')
        
        if subcategory and (not category or subcategory.parent != category):
            raise serializers.ValidationError(
                {"subcategory": "Subcategory must belong to the selected category."}
            )
        
        if sub_level_category and (not subcategory or sub_level_category.parent != subcategory):
            raise serializers.ValidationError(
                {"sub_level_category": "Sub-level category must belong to the selected subcategory."}
            )
            
        return data
    
    def create(self, validated_data):
        # Set the current user as created_by and last_modified_by
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            validated_data['created_by'] = request.user
            validated_data['last_modified_by'] = request.user
        
        return super().create(validated_data)
    
    def update(self, instance, validated_data):
        # Set the current user as last_modified_by
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            validated_data['last_modified_by'] = request.user
        
        # If description fields are being updated, set has_description to True
        description_fields = [
            'unit', 'landed_cost_price', 'landed_cost_unit', 'packaging_amount', 
            'packaging_units', 'packaging_package', 'external_description', 'length', 
            'length_unit', 'color', 'width', 'width_unit', 'height', 'height_unit',
            'volume', 'volume_unit', 'materials', 'pattern', 'photo', 'list_price_currency',
            'list_price', 'wholesale_price', 'remarks'
        ]
        if any(field in validated_data for field in description_fields):
            validated_data['has_description'] = True
        
        return super().update(instance, validated_data)