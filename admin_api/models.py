from django.db import models
from django.contrib.auth.models import AbstractUser
from django.contrib.postgres.fields import ArrayField
from django.core.exceptions import ValidationError

# Define access options as simple constants
USER_ACCESS_OPTIONS = [
    'inventory',
    'quotations',
    'sales_orders',
    'importation',
    'warehouse',
    'delivery',
    'payment',
    'customers',
    'sampling',
]

# Define role options as simple constants
USER_ROLE_OPTIONS = [
    'admin',
    'user',
    'supervisor'
]

class CustomUser(AbstractUser):
    
    email = models.EmailField('email address')
    first_name = models.CharField('first name', max_length=150)
    last_name = models.CharField('last name', max_length=150)
    role = models.CharField(
        max_length=20,
        choices=[(role, role.capitalize()) for role in USER_ROLE_OPTIONS],
        default='user'
    )
    user_access = ArrayField(
        models.CharField(
            max_length=20, 
            choices=[(access, access.capitalize()) for access in USER_ACCESS_OPTIONS]
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
    number = models.CharField(max_length=50)
    info = models.CharField(max_length=255)
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, related_name='shelves')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['number']
        unique_together = [['number', 'warehouse']]
        verbose_name_plural = 'shelves'

    def __str__(self):
        return f"{self.warehouse.name} > Shelf #{self.number} ({self.info})"
    
class Supplier(models.Model):
    SUPPLIER_TYPES = [
        ('local', 'Local'),
        ('foreign', 'Foreign'),
    ]
    
    name = models.CharField(max_length=100)
    registered_name = models.CharField(max_length=100)
    supplier_type = models.CharField(max_length=10, choices=SUPPLIER_TYPES)
    currency = models.CharField(max_length=3)  # ISO currency code (e.g., USD, EUR)
    phone_number = models.CharField(max_length=20)
    email = models.EmailField()
    inco_terms = models.TextField(blank=True)
    remarks = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        unique_together = [['name', 'registered_name']]

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
        return f"{self.supplier.name} - {self.name}"

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
    credit_limit = models.DecimalField(max_digits=12, decimal_places=2)
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
    email = models.EmailField()
    office_number = models.CharField(max_length=20)
    personal_number = models.CharField(max_length=20)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['contact_person']
        verbose_name = 'broker contact'
        verbose_name_plural = 'broker contacts'

    def __str__(self):
        return f"{self.broker.company_name} - {self.contact_person} ({self.position})"