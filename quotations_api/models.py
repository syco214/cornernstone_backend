from django.contrib.auth import get_user_model
from django.db import models
from django.utils import timezone
from django.db import models
from django.utils import timezone
from django.contrib.auth import get_user_model
from admin_api.models import Customer  # Import Customer from admin_api

User = get_user_model()

class Quotation(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('for_approval', 'For Approval'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('expired', 'Expired'),
    ]
    
    CURRENCY_CHOICES = [
        ('USD', 'USD'),
        ('EURO', 'EURO'),
        ('RMB', 'RMB'),
        ('PHP', 'PHP'),
    ]
    
    quote_number = models.CharField(max_length=50, unique=True, editable=False)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='quotations')
    date = models.DateField()
    total_amount = models.DecimalField(max_digits=15, decimal_places=2)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_quotations')
    created_on = models.DateTimeField(auto_now_add=True)
    last_modified_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='modified_quotations')
    last_modified_on = models.DateTimeField(auto_now=True)
    purchase_request = models.TextField(blank=True)
    expiry_date = models.DateField()
    currency = models.CharField(max_length=4, choices=CURRENCY_CHOICES)
    notes = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-date', 'quote_number']
    
    def __str__(self):
        return f"Quote #{self.quote_number} - {self.customer.name}"
    
    def save(self, *args, **kwargs):
        if not self.quote_number:
            # Generate quote number: QT-YYYYMMDD-XXXX
            date_str = timezone.now().strftime('%Y%m%d')
            last_quote = Quotation.objects.filter(quote_number__startswith=f'QT-{date_str}').order_by('quote_number').last()
            
            if last_quote:
                # Extract the sequence number and increment
                seq_num = int(last_quote.quote_number.split('-')[-1]) + 1
            else:
                seq_num = 1
                
            self.quote_number = f'QT-{date_str}-{seq_num:04d}'
            
        super().save(*args, **kwargs)

class QuotationAttachment(models.Model):
    quotation = models.ForeignKey(Quotation, on_delete=models.CASCADE, related_name='attachments')
    file = models.FileField(upload_to='quotation_attachments/')
    filename = models.CharField(max_length=255)
    uploaded_on = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.quotation.quote_number} - {self.filename}"

class QuotationSalesAgent(models.Model):
    ROLE_CHOICES = [
        ('main', 'Main'),
        ('support', 'Support'),
    ]
    
    quotation = models.ForeignKey(Quotation, on_delete=models.CASCADE, related_name='sales_agents')
    agent_name = models.CharField(max_length=100)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    
    class Meta:
        ordering = ['role', 'agent_name']
        constraints = [
            models.UniqueConstraint(
                fields=['quotation', 'role'],
                condition=models.Q(role='main'),
                name='unique_main_agent_per_quotation'
            )
        ]
    
    def __str__(self):
        return f"{self.quotation.quote_number} - {self.agent_name} ({self.get_role_display()})"

class QuotationAdditionalControls(models.Model):
    quotation = models.OneToOneField(Quotation, on_delete=models.CASCADE, related_name='additional_controls')
    show_carton_packing = models.BooleanField(default=True)
    do_not_show_all_photos = models.BooleanField(default=True)
    highlight_item_notes = models.BooleanField(default=True)
    show_devaluation_clause = models.BooleanField(default=True)
    
    def __str__(self):
        return f"Additional Controls for {self.quotation.quote_number}"

class Payment(models.Model):
    """Model to store reusable payment terms"""
    text = models.TextField()
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_payments')
    created_on = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.text[:50]

class Delivery(models.Model):
    """Model to store reusable delivery terms"""
    text = models.TextField()
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_deliveries')
    created_on = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.text[:50]

class Other(models.Model):
    """Model to store reusable other terms"""
    text = models.TextField()
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_others')
    created_on = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.text[:50]

class QuotationTermsAndConditions(models.Model):
    """Model to store terms and conditions for a quotation"""
    quotation = models.OneToOneField(Quotation, on_delete=models.CASCADE, related_name='terms_and_conditions')
    price = models.TextField(blank=True, null=True)
    payment = models.ForeignKey(Payment, on_delete=models.SET_NULL, null=True, blank=True, related_name='quotations')
    delivery = models.ForeignKey(Delivery, on_delete=models.SET_NULL, null=True, blank=True, related_name='quotations')
    validity = models.TextField(blank=True, null=True)
    other = models.ForeignKey(Other, on_delete=models.SET_NULL, null=True, blank=True, related_name='quotations')
    
    def __str__(self):
        return f"Terms for {self.quotation.quote_number}"

class QuotationContact(models.Model):
    """Model to store contact information for a quotation"""
    quotation = models.ForeignKey(Quotation, on_delete=models.CASCADE, related_name='contacts')
    customer_contact = models.ForeignKey(
        'admin_api.CustomerContact', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='quotation_contacts'
    )
    
    class Meta:
        ordering = ['customer_contact__contact_person']
    
    def __str__(self):
        if self.customer_contact:
            return f"{self.quotation.quote_number} - {self.customer_contact.contact_person}"
        return f"{self.quotation.quote_number} - Unknown Contact"

class QuotationItem(models.Model):
    quotation = models.ForeignKey(Quotation, on_delete=models.CASCADE, related_name='items')
    inventory = models.ForeignKey('admin_api.Inventory', on_delete=models.PROTECT)
    
    # Fields that can be overridden from inventory
    wholesale_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    unit = models.CharField(max_length=50, blank=True)
    photo = models.ImageField(upload_to='quotation_item_photos/', null=True, blank=True)
    external_description = models.TextField(blank=True)
    
    # Additional fields
    show_brand = models.BooleanField(default=True)
    show_made_in = models.BooleanField(default=True)
    actual_landed_cost = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    estimated_landed_cost = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    notes = models.TextField(blank=True)
    quantity = models.PositiveIntegerField(default=1)
    show_photo = models.BooleanField(default=True)
    baseline_margin = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    # Discount fields
    has_discount = models.BooleanField(default=False)
    discount_type = models.CharField(max_length=10, choices=[('value', 'Value'), ('percentage', 'Percentage')], default='percentage')
    discount_percentage = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    discount_value = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    # Calculated fields (stored for performance)
    landed_cost_discount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    net_selling = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    total_selling = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['id']
    
    def __str__(self):
        return f"{self.inventory.item_code} - {self.inventory.product_name}"
    
    def save(self, *args, **kwargs):
        # Calculate fields before saving
        self.calculate_fields()
        super().save(*args, **kwargs)
    
    def calculate_fields(self):
        # Calculate landed_cost_discount
        if self.estimated_landed_cost:
            self.landed_cost_discount = self.estimated_landed_cost
        
        # Calculate net_selling based on discount
        if self.wholesale_price:
            if self.has_discount:
                if self.discount_type == 'percentage' and self.discount_percentage:
                    self.net_selling = self.wholesale_price * (1 - self.discount_percentage / 100)
                elif self.discount_type == 'value' and self.discount_value:
                    self.net_selling = self.wholesale_price - self.discount_value
                else:
                    self.net_selling = self.wholesale_price
            else:
                self.net_selling = self.wholesale_price
        
        # Calculate total_selling
        if self.net_selling and self.quantity:
            self.total_selling = self.net_selling * self.quantity

class LastQuotedPrice(models.Model):
    inventory = models.ForeignKey('admin_api.Inventory', on_delete=models.CASCADE)
    customer = models.ForeignKey('admin_api.Customer', on_delete=models.CASCADE)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    quotation = models.ForeignKey(Quotation, on_delete=models.CASCADE)
    quoted_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['inventory', 'customer']
        ordering = ['-quoted_at']
    
    def __str__(self):
        return f"{self.inventory.item_code} - {self.customer.name}: {self.price}"