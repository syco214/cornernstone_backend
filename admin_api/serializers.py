from rest_framework import serializers
from django.contrib.auth import authenticate, get_user_model
from .models import CustomUser, Brand, Category, Warehouse, Shelf, Supplier, SupplierAddress, SupplierContact, SupplierPaymentTerm, ParentCompany, ParentCompanyPaymentTerm, Customer

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

class SupplierAddressSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(required=False)
    
    class Meta:
        model = SupplierAddress
        fields = ['id', 'description', 'address']
        read_only_fields = ['id']

class SupplierContactSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(required=False)
    
    class Meta:
        model = SupplierContact
        fields = ['id', 'contact_person', 'position', 'department']
        read_only_fields = ['id']

class SupplierPaymentTermSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(required=False)
    
    class Meta:
        model = SupplierPaymentTerm
        fields = [
            'id', 'name', 'credit_limit', 
            'stock_payment_terms', 'stock_dp_percentage', 'stock_terms_days',
            'import_payment_terms', 'import_dp_percentage', 'import_terms_days'
        ]
        read_only_fields = ['id']

class SupplierSerializer(serializers.ModelSerializer):
    addresses = SupplierAddressSerializer(many=True, read_only=True)
    contacts = SupplierContactSerializer(many=True, read_only=True)
    payment_term = SupplierPaymentTermSerializer(read_only=True)
    
    class Meta:
        model = Supplier
        fields = [
            'id', 'name', 'registered_name', 'supplier_type', 'currency',
            'phone_number', 'email', 'inco_terms', 'remarks',
            'addresses', 'contacts', 'payment_term',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

class SupplierCreateUpdateSerializer(serializers.ModelSerializer):
    addresses = SupplierAddressSerializer(many=True, required=False)
    contacts = SupplierContactSerializer(many=True, required=False)
    payment_term = SupplierPaymentTermSerializer(required=False)
    
    class Meta:
        model = Supplier
        fields = [
            'id', 'name', 'registered_name', 'supplier_type', 'currency',
            'phone_number', 'email', 'inco_terms', 'remarks',
            'addresses', 'contacts', 'payment_term',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def create(self, validated_data):
        addresses_data = validated_data.pop('addresses', [])
        contacts_data = validated_data.pop('contacts', [])
        payment_term_data = validated_data.pop('payment_term', None)
        
        supplier = Supplier.objects.create(**validated_data)
        
        # Create addresses
        for address_data in addresses_data:
            SupplierAddress.objects.create(supplier=supplier, **address_data)
        
        # Create contacts
        for contact_data in contacts_data:
            SupplierContact.objects.create(supplier=supplier, **contact_data)
        
        # Create payment term if provided
        if payment_term_data:
            SupplierPaymentTerm.objects.create(supplier=supplier, **payment_term_data)
            
        return supplier
    
    def update(self, instance, validated_data):
        addresses_data = validated_data.pop('addresses', None)
        contacts_data = validated_data.pop('contacts', None)
        payment_term_data = validated_data.pop('payment_term', None)
        
        # Update supplier fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        # Update addresses if provided
        if addresses_data is not None:
            self._update_nested_objects(
                instance.addresses, 
                addresses_data, 
                SupplierAddress, 
                'supplier'
            )
        
        # Update contacts if provided
        if contacts_data is not None:
            self._update_nested_objects(
                instance.contacts, 
                contacts_data, 
                SupplierContact, 
                'supplier'
            )
        
        # Update payment term if provided
        if payment_term_data is not None:
            try:
                payment_term = instance.payment_term
                for attr, value in payment_term_data.items():
                    setattr(payment_term, attr, value)
                payment_term.save()
            except SupplierPaymentTerm.DoesNotExist:
                SupplierPaymentTerm.objects.create(supplier=instance, **payment_term_data)
            
        return instance
    
    def _update_nested_objects(self, queryset, data_list, model_class, parent_field_name):
        """
        Helper method to update nested objects (addresses, contacts)
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

class ParentCompanyPaymentTermSerializer(serializers.ModelSerializer):
    class Meta:
        model = ParentCompanyPaymentTerm
        fields = [
            'id', 'name', 'credit_limit', 
            'stock_payment_terms', 'stock_dp_percentage', 'stock_terms_days',
            'import_payment_terms', 'import_dp_percentage', 'import_terms_days'
        ]
        read_only_fields = ['id']

class ParentCompanySerializer(serializers.ModelSerializer):
    payment_term = ParentCompanyPaymentTermSerializer(read_only=True)
    customers = serializers.SerializerMethodField()
    
    class Meta:
        model = ParentCompany
        fields = ['id', 'name', 'consolidate_payment_terms', 'payment_term', 'customers', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_customers(self, obj):
        customers = Customer.objects.filter(parent_company=obj)
        return [{'id': customer.id, 'name': customer.name} for customer in customers]

class ParentCompanyCreateUpdateSerializer(serializers.ModelSerializer):
    payment_term = ParentCompanyPaymentTermSerializer(required=False)
    
    class Meta:
        model = ParentCompany
        fields = ['id', 'name', 'consolidate_payment_terms', 'payment_term', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def create(self, validated_data):
        payment_term_data = validated_data.pop('payment_term', None)
        parent_company = ParentCompany.objects.create(**validated_data)
        
        # Create payment term if provided
        if payment_term_data:
            ParentCompanyPaymentTerm.objects.create(parent_company=parent_company, **payment_term_data)
            
        return parent_company
    
    def update(self, instance, validated_data):
        payment_term_data = validated_data.pop('payment_term', None)
        
        # Update parent company fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        # Update payment term if provided
        if payment_term_data is not None:
            try:
                payment_term = instance.payment_term
                for attr, value in payment_term_data.items():
                    setattr(payment_term, attr, value)
                payment_term.save()
            except ParentCompanyPaymentTerm.DoesNotExist:
                ParentCompanyPaymentTerm.objects.create(parent_company=instance, **payment_term_data)
            
        return instance