from rest_framework import serializers
from django.contrib.auth import authenticate, get_user_model
from .models import CustomUser, Brand, Category, Warehouse, Shelf

User = get_user_model()

class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        user = authenticate(**data)
        if user and user.is_active:
            return user
        raise serializers.ValidationError('Incorrect credentials')
    
class SidebarUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'first_name', 'last_name', 'role', 'user_access']
        read_only_fields = ['id', 'first_name', 'last_name', 'role', 'user_access']

class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False)
    
    class Meta:
        model = CustomUser
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name', 
            'role', 'user_access', 'password', 
            'is_active', 'date_joined'
        ]
        read_only_fields = ['id', 'date_joined']
    
    def create(self, validated_data):
        password = validated_data.pop('password', None)
        user = CustomUser(**validated_data)
        if password:
            user.set_password(password)
        user.save()
        return user
    
    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        
        # Update all other fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        # Handle password separately
        if password:
            instance.set_password(password)
        
        instance.save()
        return instance
    
class BrandSerializer(serializers.ModelSerializer):
    class Meta:
        model = Brand
        fields = ['id', 'name', 'made_in', 'show_made_in', 'remarks', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']

class CategorySerializer(serializers.ModelSerializer):
    level = serializers.IntegerField(read_only=True)
    full_path = serializers.CharField(read_only=True)
    
    class Meta:
        model = Category
        fields = ['id', 'name', 'parent', 'level', 'full_path', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at', 'level', 'full_path']

class CategoryTreeSerializer(serializers.ModelSerializer):
    children = serializers.SerializerMethodField()
    level = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = Category
        fields = ['id', 'name', 'level', 'children', 'created_at', 'updated_at']
    
    def get_children(self, obj):
        children = Category.objects.filter(parent=obj)
        if not children:
            return []
        return CategoryTreeSerializer(children, many=True).data

class ShelfSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(required=False)  # For handling updates
    
    class Meta:
        model = Shelf
        fields = ['id', 'number', 'info']
        read_only_fields = ['id']

class WarehouseSerializer(serializers.ModelSerializer):
    shelves = ShelfSerializer(many=True, read_only=True)
    
    class Meta:
        model = Warehouse
        fields = ['id', 'name', 'address', 'city', 'shelves', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']

class WarehouseCreateUpdateSerializer(serializers.ModelSerializer):
    shelves = ShelfSerializer(many=True, required=False)
    
    class Meta:
        model = Warehouse
        fields = ['id', 'name', 'address', 'city', 'shelves', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def create(self, validated_data):
        shelves_data = validated_data.pop('shelves', [])
        warehouse = Warehouse.objects.create(**validated_data)
        
        # Create shelves
        for shelf_data in shelves_data:
            Shelf.objects.create(warehouse=warehouse, **shelf_data)
            
        return warehouse
    
    def update(self, instance, validated_data):
        shelves_data = validated_data.pop('shelves', None)
        
        # Update warehouse fields
        instance.name = validated_data.get('name', instance.name)
        instance.address = validated_data.get('address', instance.address)
        instance.city = validated_data.get('city', instance.city)
        instance.save()
        
        # Update shelves if provided
        if shelves_data is not None:
            # Get existing shelf IDs
            existing_shelf_ids = set(instance.shelves.values_list('id', flat=True))
            updated_shelf_ids = set()
            
            # Create or update shelves
            for shelf_data in shelves_data:
                shelf_id = shelf_data.get('id')
                
                if shelf_id:
                    # Update existing shelf
                    try:
                        shelf = Shelf.objects.get(id=shelf_id, warehouse=instance)
                        shelf.number = shelf_data.get('number', shelf.number)
                        shelf.info = shelf_data.get('info', shelf.info)
                        shelf.save()
                        updated_shelf_ids.add(shelf_id)
                    except Shelf.DoesNotExist:
                        # If ID doesn't exist, create new shelf
                        Shelf.objects.create(warehouse=instance, **{k: v for k, v in shelf_data.items() if k != 'id'})
                else:
                    # Create new shelf
                    shelf = Shelf.objects.create(warehouse=instance, **shelf_data)
                    updated_shelf_ids.add(shelf.id)
            
            # Delete shelves that weren't updated
            shelves_to_delete = existing_shelf_ids - updated_shelf_ids
            Shelf.objects.filter(id__in=shelves_to_delete).delete()
            
        return instance