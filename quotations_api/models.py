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