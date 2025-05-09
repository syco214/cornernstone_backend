from django.db import models
from django.contrib.auth.models import AbstractUser
from django.contrib.postgres.fields import ArrayField
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model

# Define admin access options as simple constants
ADMIN_ACCESS_OPTIONS = [
    'users',
    'brands',
    'brokers',
    'categories',
    'customers',
    'forwarders',
    'inventory',
    'parent_companies',
    'suppliers',
    'warehouses',
]

# Define access options as simple constants
USER_ACCESS_OPTIONS = [
    'inventory',
    'quotations',
    'reservation_slips',
    'sales_orders',
    'accounting_aging_reports',
    'accounting_account_receivables',
    'accounting_workstreams',
    'importation',
    'delivery',
    'warehouse_inbound',
    'warehouse_delivery',
    'warehouse_audit',
    'shipments',
    'calendar',
]

# Define role options as simple constants
USER_ROLE_OPTIONS = [
    'admin',
    'user',
    'supervisor'
]

STATUS_CHOICES = [
    ('active', 'Active'),
    ('inactive', 'Inactive'),
]

class CustomUser(AbstractUser):
    
    first_name = models.CharField('first name', max_length=150)
    last_name = models.CharField('last name', max_length=150)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    role = models.CharField(
        max_length=20,
        choices=[(role, role.capitalize()) for role in USER_ROLE_OPTIONS],
        default='user'
    )
    user_access = ArrayField(
        models.CharField(
            max_length=40, 
            choices=[(access, access.capitalize()) for access in USER_ACCESS_OPTIONS]
        ),
        blank=True,
        default=list
    )
    admin_access = ArrayField(
        models.CharField(
            max_length=40, 
            choices=[(access, access.capitalize()) for access in ADMIN_ACCESS_OPTIONS]
        ),
        blank=True,
        default=list
    )
    
    class Meta:
        verbose_name = 'user'
        verbose_name_plural = 'users'
        ordering = ['first_name', 'last_name']
    
    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.username})"

class Brand(models.Model):
    name = models.CharField(max_length=100, unique=True)
    made_in = models.TextField(blank=True, null=True)
    show_made_in = models.BooleanField(default=True)
    remarks = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'brand'
        verbose_name_plural = 'brands'
        ordering = ['name']

    def __str__(self):
        return self.name

class Category(models.Model):
    name = models.CharField(max_length=100)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='children')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'category'
        verbose_name_plural = 'categories'
        ordering = ['name']
        unique_together = [['name', 'parent']]

    def __str__(self):
        if self.parent:
            return f"{self.parent} > {self.name}"
        return self.name
    
    @property
    def level(self):
        level = 0
        parent = self.parent
        while parent:
            level += 1
            parent = parent.parent
        return level
    
    @property
    def full_path(self):
        if not self.parent:
            return self.name
        return f"{self.parent.full_path} > {self.name}"
    
class Warehouse(models.Model):
    name = models.CharField(max_length=100)
    address = models.TextField()
    city = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        unique_together = [['name', 'city']]

    def __str__(self):
        return f"{self.name} ({self.city})"

class Shelf(models.Model):
    aisle = models.CharField(max_length=25)
    shelf = models.CharField(max_length=25)
    info = models.CharField(max_length=255)
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, related_name='shelves')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['aisle', 'shelf']
        unique_together = [['aisle', 'shelf', 'warehouse']]
        verbose_name_plural = 'shelves'

    def __str__(self):
        return f"{self.warehouse.name} > Aisle {self.aisle}, Shelf {self.shelf} ({self.info})"
    
class Supplier(models.Model):
    SUPPLIER_TYPES = [
        ('local', 'Local'),
        ('foreign', 'Foreign'),
    ]
    
    CURRENCY_CHOICES = [
        ('USD', 'USD'),
        ('EURO', 'EURO'),
        ('RMB', 'RMB'),
        ('PHP', 'PHP'),
    ]
    
    name = models.CharField(max_length=100)
    supplier_type = models.CharField(max_length=10, choices=SUPPLIER_TYPES)
    currency = models.CharField(max_length=4, choices=CURRENCY_CHOICES)
    phone_number = models.CharField(max_length=20)
    email = models.EmailField()
    delivery_terms = models.TextField(blank=True)
    remarks = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.get_supplier_type_display()})"

class SupplierAddress(models.Model):
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE, related_name='addresses')
    description = models.CharField(max_length=100)  # e.g., "Headquarters", "Warehouse", etc.
    address = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['description']
        verbose_name_plural = 'supplier addresses'

    def __str__(self):
        return f"{self.supplier.name} - {self.description}"

class SupplierContact(models.Model):
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE, related_name='contacts')
    contact_person = models.CharField(max_length=100)
    position = models.CharField(max_length=100)
    email = models.TextField()
    mobile_number = models.TextField()
    office_number = models.TextField()
    department = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['contact_person']

    def __str__(self):
        return f"{self.supplier.name} - {self.contact_person} ({self.position})"

class SupplierPaymentTerm(models.Model):
    supplier = models.OneToOneField(Supplier, on_delete=models.CASCADE, related_name='payment_term')
    name = models.CharField(max_length=100)
    credit_limit = models.DecimalField(max_digits=15, decimal_places=2)

    payment_terms = models.CharField(max_length=100)
    dp_percentage = models.DecimalField(max_digits=5, decimal_places=2)
    terms_days = models.PositiveIntegerField()
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.supplier.name} - {self.name}"

class SupplierBank(models.Model):
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE, related_name='banks')
    bank_name = models.CharField(max_length=100)
    bank_address = models.TextField()
    account_number = models.CharField(max_length=50)
    currency = models.CharField(max_length=3)  # ISO currency code (e.g., USD, EUR)
    iban = models.CharField(max_length=50, blank=True)
    swift_code = models.CharField(max_length=20)
    intermediary_bank = models.CharField(max_length=100, blank=True)
    intermediary_swift_name = models.CharField(max_length=100, blank=True)
    beneficiary_name = models.CharField(max_length=100)
    beneficiary_address = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['bank_name']
        verbose_name_plural = 'supplier banks'

    def __str__(self):
        return f"{self.supplier.name} - {self.bank_name} ({self.currency})"
    
class ParentCompany(models.Model):
    name = models.CharField(max_length=100)
    consolidate_payment_terms = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        verbose_name_plural = 'parent companies'

    def __str__(self):
        return self.name

class ParentCompanyPaymentTerm(models.Model):
    parent_company = models.OneToOneField(
        ParentCompany, 
        on_delete=models.CASCADE, 
        related_name='payment_term'
    )
    name = models.CharField(max_length=100)
    credit_limit = models.DecimalField(max_digits=15, decimal_places=2)
    stock_payment_terms = models.CharField(max_length=100)
    stock_dp_percentage = models.DecimalField(max_digits=5, decimal_places=2)
    stock_terms_days = models.PositiveIntegerField()
    import_payment_terms = models.CharField(max_length=100)
    import_dp_percentage = models.DecimalField(max_digits=5, decimal_places=2)
    import_terms_days = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.parent_company.name} - {self.name}"

class Customer(models.Model):
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
    ]
    
    name = models.CharField(max_length=100)
    registered_name = models.CharField(max_length=100)
    tin = models.CharField(max_length=20, blank=True)
    phone_number = models.CharField(max_length=20)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='active')
    has_parent = models.BooleanField(default=False)
    parent_company = models.ForeignKey(
        ParentCompany, 
        on_delete=models.SET_NULL, 
        related_name='customer_set',
        null=True, 
        blank=True
    )
    company_address = models.TextField()
    city = models.CharField(max_length=100)
    vat_type = models.CharField(max_length=50, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        unique_together = [['name', 'registered_name']]

    def __str__(self):
        return f"{self.name} ({self.get_status_display()})"

class CustomerAddress(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='addresses')
    delivery_address = models.TextField()
    delivery_schedule = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['delivery_address']
        verbose_name_plural = 'customer addresses'

    def __str__(self):
        return f"{self.customer.name} - {self.delivery_address}"

class CustomerContact(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='contacts')
    contact_person = models.CharField(max_length=100)
    position = models.CharField(max_length=100)
    department = models.CharField(max_length=100)
    email = models.TextField()
    mobile_number = models.TextField()
    office_number = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['contact_person']

    def __str__(self):
        return f"{self.customer.name} - {self.contact_person} ({self.position})"

class CustomerPaymentTerm(models.Model):
    customer = models.OneToOneField(Customer, on_delete=models.CASCADE, related_name='payment_term')
    name = models.CharField(max_length=100)
    credit_limit = models.DecimalField(max_digits=15, decimal_places=2)
    
    # Stock payment terms
    stock_payment_terms = models.CharField(max_length=100)
    stock_dp_percentage = models.DecimalField(max_digits=5, decimal_places=2)
    stock_terms_days = models.PositiveIntegerField()
    
    # Import payment terms
    import_payment_terms = models.CharField(max_length=100)
    import_dp_percentage = models.DecimalField(max_digits=5, decimal_places=2)
    import_terms_days = models.PositiveIntegerField()
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.customer.name} - {self.name}"

class Broker(models.Model):
    PAYMENT_CHOICES = [
        ('cod', 'COD'),
        ('terms', 'Payment Terms'),
    ]
    
    company_name = models.CharField(max_length=100)
    address = models.TextField()
    email = models.EmailField()
    phone_number = models.CharField(max_length=20)
    payment_type = models.CharField(max_length=10, choices=PAYMENT_CHOICES, default='cod')
    payment_terms_days = models.PositiveIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['company_name']
        verbose_name = 'broker'
        verbose_name_plural = 'brokers'

    def __str__(self):
        return self.company_name
    
    def clean(self):
        # Ensure payment_terms_days is provided when payment_type is 'terms'
        if self.payment_type == 'terms' and self.payment_terms_days is None:
            raise ValidationError({'payment_terms_days': 'Payment terms days is required when payment type is Payment Terms'})

class BrokerContact(models.Model):
    broker = models.ForeignKey(Broker, on_delete=models.CASCADE, related_name='contacts')
    contact_person = models.CharField(max_length=100)
    position = models.CharField(max_length=100)
    department = models.CharField(max_length=100)
    email = models.TextField()
    office_number = models.TextField()
    personal_number = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['contact_person']
        verbose_name = 'broker contact'
        verbose_name_plural = 'broker contacts'

    def __str__(self):
        return f"{self.broker.company_name} - {self.contact_person} ({self.position})"

class Forwarder(models.Model):
    PAYMENT_CHOICES = [
        ('cod', 'COD'),
        ('terms', 'Payment Terms'),
    ]
    
    company_name = models.CharField(max_length=100)
    address = models.TextField()
    email = models.EmailField()
    phone_number = models.CharField(max_length=20)
    payment_type = models.CharField(max_length=10, choices=PAYMENT_CHOICES, default='cod')
    payment_terms_days = models.PositiveIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['company_name']
        verbose_name = 'forwarder'
        verbose_name_plural = 'forwarders'

    def __str__(self):
        return self.company_name
    
    def clean(self):
        # Ensure payment_terms_days is provided when payment_type is 'terms'
        if self.payment_type == 'terms' and self.payment_terms_days is None:
            raise ValidationError({'payment_terms_days': 'Payment terms days is required when payment type is Payment Terms'})

class ForwarderContact(models.Model):
    forwarder = models.ForeignKey(Forwarder, on_delete=models.CASCADE, related_name='contacts')
    contact_person = models.CharField(max_length=100)
    position = models.CharField(max_length=100)
    department = models.CharField(max_length=100)
    email = models.TextField()
    office_number = models.TextField()
    personal_number = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['contact_person']
        verbose_name = 'forwarder contact'
        verbose_name_plural = 'forwarder contacts'

    def __str__(self):
        return f"{self.forwarder.company_name} - {self.contact_person} ({self.position})"

User = get_user_model()

class Inventory(models.Model):
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
    ]
    
    PRODUCT_TAGGING_CHOICES = [
        ('never_sold', 'Never Sold'),
        ('discontinued', 'Discontinued'),
        ('dormant', 'Dormant'),
        ('none', 'None'),
    ]
    
    # General Information
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_inventories')
    created_at = models.DateTimeField(auto_now_add=True)
    last_modified_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='modified_inventories')
    last_modified_at = models.DateTimeField(auto_now=True)
    
    item_code = models.CharField(max_length=50, unique=True)
    cip_code = models.CharField(max_length=50, unique=True)
    product_name = models.CharField(max_length=200)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='active')
    
    supplier = models.ForeignKey('Supplier', on_delete=models.PROTECT, related_name='inventories')
    brand = models.ForeignKey('Brand', on_delete=models.PROTECT, related_name='inventories')
    product_tagging = models.CharField(max_length=50, choices=PRODUCT_TAGGING_CHOICES, default='never_sold')
    audit_status = models.BooleanField(default=False)
    
    category = models.ForeignKey('Category', on_delete=models.PROTECT, related_name='inventories')
    subcategory = models.ForeignKey('Category', on_delete=models.PROTECT, related_name='subcategory_inventories', null=True, blank=True)
    sub_level_category = models.ForeignKey('Category', on_delete=models.PROTECT, related_name='sub_level_inventories', null=True, blank=True)

    # Flag to track if description has been added
    has_description = models.BooleanField(default=False)
    
    # New description fields
    unit = models.CharField(max_length=50, blank=True)
    landed_cost_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    landed_cost_unit = models.CharField(max_length=50, blank=True)
    packaging_amount = models.IntegerField(null=True, blank=True)
    packaging_units = models.CharField(max_length=50, blank=True)
    packaging_package = models.CharField(max_length=100, blank=True)
    external_description = models.TextField(blank=True)
    length = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    length_unit = models.CharField(max_length=20, blank=True)
    color = models.CharField(max_length=50, blank=True)
    width = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    width_unit = models.CharField(max_length=20, blank=True)
    height = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    height_unit = models.CharField(max_length=20, blank=True)
    volume = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    volume_unit = models.CharField(max_length=20, blank=True)
    materials = models.TextField(blank=True)
    pattern = models.TextField(blank=True)
    photo = models.ImageField(upload_to='inventory_photos/', null=True, blank=True)
    list_price_currency = models.CharField(max_length=3, blank=True)
    list_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    wholesale_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    remarks = models.TextField(blank=True)
    
    # Inventory tracking fields (not editable through admin, default to 0)
    stock_on_hand = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    reserved_pending_so = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    available_for_sale = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    incoming_pending_po = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    incoming_stock = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_expected = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    class Meta:
        verbose_name = 'inventory'
        verbose_name_plural = 'inventories'
        ordering = ['item_code']
    
    def __str__(self):
        return f"{self.item_code} - {self.product_name}"
    
    def clean(self):
        # Validate category hierarchy
        if self.subcategory and self.subcategory.parent != self.category:
            raise ValidationError({'subcategory': 'Subcategory must belong to the selected category.'})
        
        if self.sub_level_category and self.sub_level_category.parent != self.subcategory:
            raise ValidationError({'sub_level_category': 'Sub-level category must belong to the selected subcategory.'})