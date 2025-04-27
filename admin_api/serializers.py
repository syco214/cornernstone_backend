from rest_framework import serializers
from django.contrib.auth import authenticate, get_user_model
from .models import CustomUser, Brand, Category, Warehouse, Shelf, Supplier, SupplierAddress, SupplierContact, SupplierPaymentTerm, SupplierBank, ParentCompany, ParentCompanyPaymentTerm, Customer, CustomerAddress, CustomerContact, CustomerPaymentTerm, Broker, BrokerContact, Forwarder, ForwarderContact, Inventory
from django.conf import settings

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
        fields = ['id', 'first_name', 'last_name', 'role', 'user_access', 'admin_access']
        read_only_fields = ['id', 'first_name', 'last_name', 'role', 'user_access', 'admin_access']

class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False)
    
    class Meta:
        model = CustomUser
        fields = [
            'id', 'username', 'status','first_name', 'last_name', 
            'role', 'user_access', 'admin_access', 'password', 
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
        fields = ['id', 'aisle', 'shelf', 'info']
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
                        shelf.aisle = shelf_data.get('aisle', shelf.aisle)
                        shelf.shelf = shelf_data.get('shelf', shelf.shelf)
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

class SupplierBankSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(required=False)
    
    class Meta:
        model = SupplierBank
        fields = [
            'id', 'bank_name', 'bank_address', 'account_number', 
            'currency', 'iban', 'swift_code', 'intermediary_bank',
            'intermediary_swift_name', 'beneficiary_name', 'beneficiary_address'
        ]
        read_only_fields = ['id']

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
        fields = ['id', 'contact_person', 'position', 'department', 'email', 'mobile_number', 'office_number']
        read_only_fields = ['id']

class SupplierPaymentTermSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(required=False)
    
    class Meta:
        model = SupplierPaymentTerm
        fields = [
            'id', 'name', 'credit_limit', 
            'payment_terms', 'dp_percentage', 'terms_days'
        ]
        read_only_fields = ['id']

class SupplierSerializer(serializers.ModelSerializer):
    addresses = SupplierAddressSerializer(many=True, read_only=True)
    contacts = SupplierContactSerializer(many=True, read_only=True)
    payment_term = SupplierPaymentTermSerializer(read_only=True)
    banks = SupplierBankSerializer(many=True, read_only=True)
    
    class Meta:
        model = Supplier
        fields = [
            'id', 'name', 'supplier_type', 'currency',
            'phone_number', 'email', 'delivery_terms', 'remarks',
            'addresses', 'contacts', 'payment_term', 'banks',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

class SupplierCreateUpdateSerializer(serializers.ModelSerializer):
    addresses = SupplierAddressSerializer(many=True, required=False)
    contacts = SupplierContactSerializer(many=True, required=False)
    payment_term = SupplierPaymentTermSerializer(required=False)
    banks = SupplierBankSerializer(many=True, required=False)
    
    class Meta:
        model = Supplier
        fields = [
            'id', 'name', 'supplier_type', 'currency',
            'phone_number', 'email', 'delivery_terms', 'remarks',
            'addresses', 'contacts', 'payment_term', 'banks',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def create(self, validated_data):
        addresses_data = validated_data.pop('addresses', [])
        contacts_data = validated_data.pop('contacts', [])
        payment_term_data = validated_data.pop('payment_term', None)
        banks_data = validated_data.pop('banks', [])
        
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
        
        # Create banks
        for bank_data in banks_data:
            SupplierBank.objects.create(supplier=supplier, **bank_data)
            
        return supplier
    
    def update(self, instance, validated_data):
        addresses_data = validated_data.pop('addresses', None)
        contacts_data = validated_data.pop('contacts', None)
        payment_term_data = validated_data.pop('payment_term', None)
        banks_data = validated_data.pop('banks', None)
        
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
        
        # Update banks if provided
        if banks_data is not None:
            self._update_nested_objects(
                instance.banks, 
                banks_data, 
                SupplierBank, 
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
        Helper method to update nested objects (addresses, contacts, banks)
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

class CustomerAddressSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(required=False)
    
    class Meta:
        model = CustomerAddress
        fields = ['id', 'delivery_address', 'delivery_schedule']
        read_only_fields = ['id']

class CustomerContactSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(required=False)
    
    class Meta:
        model = CustomerContact
        fields = ['id', 'contact_person', 'position', 'department', 'email', 'mobile_number', 'office_number']
        read_only_fields = ['id']

class CustomerPaymentTermSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(required=False)
    
    class Meta:
        model = CustomerPaymentTerm
        fields = [
            'id', 'name', 'credit_limit', 
            'stock_payment_terms', 'stock_dp_percentage', 'stock_terms_days',
            'import_payment_terms', 'import_dp_percentage', 'import_terms_days'
        ]
        read_only_fields = ['id']

class CustomerSerializer(serializers.ModelSerializer):
    addresses = CustomerAddressSerializer(many=True, read_only=True)
    contacts = CustomerContactSerializer(many=True, read_only=True)
    payment_term = CustomerPaymentTermSerializer(read_only=True)
    parent_company_name = serializers.SerializerMethodField()
    
    class Meta:
        model = Customer
        fields = [
            'id', 'name', 'registered_name', 'tin', 'phone_number', 
            'status', 'has_parent', 'parent_company', 'parent_company_name',
            'company_address', 'city', 'vat_type',
            'addresses', 'contacts', 'payment_term',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'parent_company_name']
    
    def get_parent_company_name(self, obj):
        if obj.parent_company:
            return obj.parent_company.name
        return None

class CustomerCreateUpdateSerializer(serializers.ModelSerializer):
    addresses = CustomerAddressSerializer(many=True, required=False)
    contacts = CustomerContactSerializer(many=True, required=False)
    payment_term = CustomerPaymentTermSerializer(required=False)
    
    class Meta:
        model = Customer
        fields = [
            'id', 'name', 'registered_name', 'tin', 'phone_number', 
            'status', 'has_parent', 'parent_company',
            'company_address', 'city', 'vat_type',
            'addresses', 'contacts', 'payment_term',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def validate(self, data):
        # Validate that parent_company is provided if has_parent is True
        if data.get('has_parent', False) and not data.get('parent_company'):
            raise serializers.ValidationError(
                {"parent_company": "Parent company must be specified when has_parent is True."}
            )
        
        # Ensure parent_company is None if has_parent is False
        if 'has_parent' in data and not data.get('has_parent', False):
            data['parent_company'] = None
            
        return data
    
    def create(self, validated_data):
        addresses_data = validated_data.pop('addresses', [])
        contacts_data = validated_data.pop('contacts', [])
        payment_term_data = validated_data.pop('payment_term', None)
        
        customer = Customer.objects.create(**validated_data)
        
        # Create addresses
        for address_data in addresses_data:
            CustomerAddress.objects.create(customer=customer, **address_data)
        
        # Create contacts
        for contact_data in contacts_data:
            CustomerContact.objects.create(customer=customer, **contact_data)
        
        # Create payment term if provided
        if payment_term_data:
            CustomerPaymentTerm.objects.create(customer=customer, **payment_term_data)
            
        return customer
    
    def update(self, instance, validated_data):
        addresses_data = validated_data.pop('addresses', None)
        contacts_data = validated_data.pop('contacts', None)
        payment_term_data = validated_data.pop('payment_term', None)
        
        # Update customer fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        # Update addresses if provided
        if addresses_data is not None:
            self._update_nested_objects(
                instance.addresses, 
                addresses_data, 
                CustomerAddress, 
                'customer'
            )
        
        # Update contacts if provided
        if contacts_data is not None:
            self._update_nested_objects(
                instance.contacts, 
                contacts_data, 
                CustomerContact, 
                'customer'
            )
        
        # Update payment term if provided
        if payment_term_data is not None:
            try:
                payment_term = instance.payment_term
                for attr, value in payment_term_data.items():
                    setattr(payment_term, attr, value)
                payment_term.save()
            except CustomerPaymentTerm.DoesNotExist:
                CustomerPaymentTerm.objects.create(customer=instance, **payment_term_data)
            
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

class BrokerContactSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(required=False)
    
    class Meta:
        model = BrokerContact
        fields = [
            'id', 'contact_person', 'position', 'department', 
            'email', 'office_number', 'personal_number'
        ]
        read_only_fields = ['id']

class BrokerSerializer(serializers.ModelSerializer):
    contacts = BrokerContactSerializer(many=True, read_only=True)
    
    class Meta:
        model = Broker
        fields = [
            'id', 'company_name', 'address', 'email', 'phone_number',
            'payment_type', 'payment_terms_days', 'contacts',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

class BrokerCreateUpdateSerializer(serializers.ModelSerializer):
    contacts = BrokerContactSerializer(many=True, required=False)
    
    class Meta:
        model = Broker
        fields = [
            'id', 'company_name', 'address', 'email', 'phone_number',
            'payment_type', 'payment_terms_days', 'contacts',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def validate(self, data):
        # Validate that payment_terms_days is provided when payment_type is 'terms'
        if data.get('payment_type') == 'terms' and data.get('payment_terms_days') is None:
            raise serializers.ValidationError(
                {"payment_terms_days": "Payment terms days is required when payment type is Payment Terms."}
            )
        
        # Ensure payment_terms_days is None when payment_type is 'cod'
        if data.get('payment_type') == 'cod':
            data['payment_terms_days'] = None
            
        return data
    
    def create(self, validated_data):
        contacts_data = validated_data.pop('contacts', [])
        
        broker = Broker.objects.create(**validated_data)
        
        # Create contacts
        for contact_data in contacts_data:
            BrokerContact.objects.create(broker=broker, **contact_data)
            
        return broker
    
    def update(self, instance, validated_data):
        contacts_data = validated_data.pop('contacts', None)
        
        # Update broker fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        # Update contacts if provided
        if contacts_data is not None:
            self._update_nested_contacts(instance, contacts_data)
            
        return instance
    
    def _update_nested_contacts(self, broker, contacts_data):
        """
        Helper method to update nested contact objects
        """
        # Get existing IDs
        existing_ids = set(broker.contacts.values_list('id', flat=True))
        updated_ids = set()
        
        # Create or update contacts
        for contact_data in contacts_data:
            contact_id = contact_data.get('id')
            
            if contact_id:
                # Update existing contact
                try:
                    contact = broker.contacts.get(id=contact_id)
                    for attr, value in contact_data.items():
                        if attr != 'id':
                            setattr(contact, attr, value)
                    contact.save()
                    updated_ids.add(contact_id)
                except BrokerContact.DoesNotExist:
                    # If ID doesn't exist, create new contact
                    contact = BrokerContact.objects.create(
                        broker=broker, 
                        **{k: v for k, v in contact_data.items() if k != 'id'}
                    )
                    updated_ids.add(contact.id)
            else:
                # Create new contact
                contact = BrokerContact.objects.create(broker=broker, **contact_data)
                updated_ids.add(contact.id)
        
        # Delete contacts that weren't updated
        contacts_to_delete = existing_ids - updated_ids
        broker.contacts.filter(id__in=contacts_to_delete).delete()

class ForwarderContactSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(required=False)
    
    class Meta:
        model = ForwarderContact
        fields = [
            'id', 'contact_person', 'position', 'department', 
            'email', 'office_number', 'personal_number'
        ]
        read_only_fields = ['id']

class ForwarderSerializer(serializers.ModelSerializer):
    contacts = ForwarderContactSerializer(many=True, read_only=True)
    
    class Meta:
        model = Forwarder
        fields = [
            'id', 'company_name', 'address', 'email', 'phone_number',
            'payment_type', 'payment_terms_days', 'contacts',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

class ForwarderCreateUpdateSerializer(serializers.ModelSerializer):
    contacts = ForwarderContactSerializer(many=True, required=False)
    
    class Meta:
        model = Forwarder
        fields = [
            'id', 'company_name', 'address', 'email', 'phone_number',
            'payment_type', 'payment_terms_days', 'contacts',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def validate(self, data):
        # Validate that payment_terms_days is provided when payment_type is 'terms'
        if data.get('payment_type') == 'terms' and data.get('payment_terms_days') is None:
            raise serializers.ValidationError(
                {"payment_terms_days": "Payment terms days is required when payment type is Payment Terms."}
            )
        
        # Ensure payment_terms_days is None when payment_type is 'cod'
        if data.get('payment_type') == 'cod':
            data['payment_terms_days'] = None
            
        return data
    
    def create(self, validated_data):
        contacts_data = validated_data.pop('contacts', [])
        
        forwarder = Forwarder.objects.create(**validated_data)
        
        # Create contacts
        for contact_data in contacts_data:
            ForwarderContact.objects.create(forwarder=forwarder, **contact_data)
            
        return forwarder
    
    def update(self, instance, validated_data):
        contacts_data = validated_data.pop('contacts', None)
        
        # Update forwarder fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        # Update contacts if provided
        if contacts_data is not None:
            self._update_nested_contacts(instance, contacts_data)
            
        return instance
    
    def _update_nested_contacts(self, forwarder, contacts_data):
        """
        Helper method to update nested contact objects
        """
        # Get existing IDs
        existing_ids = set(forwarder.contacts.values_list('id', flat=True))
        updated_ids = set()
        
        # Create or update contacts
        for contact_data in contacts_data:
            contact_id = contact_data.get('id')
            
            if contact_id:
                # Update existing contact
                try:
                    contact = forwarder.contacts.get(id=contact_id)
                    for attr, value in contact_data.items():
                        if attr != 'id':
                            setattr(contact, attr, value)
                    contact.save()
                    updated_ids.add(contact_id)
                except ForwarderContact.DoesNotExist:
                    # If ID doesn't exist, create new contact
                    contact = ForwarderContact.objects.create(
                        forwarder=forwarder, 
                        **{k: v for k, v in contact_data.items() if k != 'id'}
                    )
                    updated_ids.add(contact.id)
            else:
                # Create new contact
                contact = ForwarderContact.objects.create(forwarder=forwarder, **contact_data)
                updated_ids.add(contact.id)
        
        # Delete contacts that weren't updated
        contacts_to_delete = existing_ids - updated_ids
        forwarder.contacts.filter(id__in=contacts_to_delete).delete()

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
            'volume', 'volume_unit', 'materials', 'photo', 'photo_url',
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
        print(f"DEBUG: Request object exists: {request is not None}")
        
        if obj.photo and hasattr(obj.photo, 'url'):
            print(f"DEBUG: Photo URL from Django: {obj.photo.url}")
            
            if request:
                # Debug request information
                print(f"DEBUG: Request host: {request.get_host()}")
                print(f"DEBUG: Request scheme: {request.scheme}")
                print(f"DEBUG: X-Forwarded-Host header: {request.META.get('HTTP_X_FORWARDED_HOST', 'Not present')}")
                print(f"DEBUG: X-Forwarded-Proto header: {request.META.get('HTTP_X_FORWARDED_PROTO', 'Not present')}")
                
                # Build the absolute URI
                absolute_uri = request.build_absolute_uri(obj.photo.url)
                print(f"DEBUG: Final absolute URI: {absolute_uri}")
                return absolute_uri
            else:
                # Fallback for contexts without a request
                base_url = getattr(settings, 'BASE_URL', '')
                media_url = getattr(settings, 'MEDIA_URL', '/media/')
                photo_path = obj.photo.url.lstrip('/')
                media_url = media_url.rstrip('/') + '/'
                base_url = base_url.rstrip('/')
                
                # Debug fallback URL construction
                print(f"DEBUG: Base URL from settings: {base_url}")
                print(f"DEBUG: Media URL from settings: {media_url}")
                print(f"DEBUG: Photo path: {photo_path}")
                
                fallback_url = f"{base_url}{media_url}{photo_path}"
                print(f"DEBUG: Final fallback URL: {fallback_url}")
                return fallback_url
        
        print("DEBUG: No photo or photo URL attribute")
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
            'volume', 'volume_unit', 'materials', 'photo', 'list_price_currency',
            'list_price', 'wholesale_price', 'remarks'
        ]
        if any(field in validated_data for field in description_fields):
            validated_data['has_description'] = True
        
        return super().update(instance, validated_data)