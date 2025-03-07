from rest_framework import serializers
from django.contrib.auth import authenticate, get_user_model
from .models import CustomUser, Brand, Category

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