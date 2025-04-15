# quotations_api/models.py
import uuid
from decimal import Decimal
from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db.models import Sum, F, Case, When, Value, CharField, Q
from django.utils.translation import gettext_lazy as _

# Assuming these models exist in their respective apps
from admin_api.models import (
    Customer,
    CustomerContact,
    Brand,
    Inventory,
)

class TermsCondition(models.Model):
    """Stores reusable Terms & Conditions options."""
    name = models.CharField(max_length=255, unique=True)
    # content = models.TextField(blank=True, null=True) # Optional: Add if full text is needed

    class Meta:
        ordering = ['name']
        verbose_name = 'Terms & Condition'
        verbose_name_plural = 'Terms & Conditions'

    def __str__(self):
        return self.name

class PaymentTerm(models.Model):
    """Stores reusable Payment Term options."""
    name = models.CharField(max_length=255, unique=True)
    # content = models.TextField(blank=True, null=True) # Optional

    class Meta:
        ordering = ['name']
        verbose_name = 'Payment Term'
        verbose_name_plural = 'Payment Terms'

    def __str__(self):
        return self.name

class DeliveryOption(models.Model):
    """Stores reusable Delivery options."""
    name = models.CharField(max_length=255, unique=True)
    # content = models.TextField(blank=True, null=True) # Optional

    class Meta:
        ordering = ['name']
        verbose_name = 'Delivery Option'
        verbose_name_plural = 'Delivery Options'

    def __str__(self):
        return self.name

class OtherOption(models.Model):
    """Stores other reusable options."""
    name = models.CharField(max_length=255, unique=True)
    # content = models.TextField(blank=True, null=True) # Optional

    class Meta:
        ordering = ['name']
        verbose_name = 'Other Option'
        verbose_name_plural = 'Other Options'

    def __str__(self):
        return self.name

class Quotation(models.Model):
    """Represents a sales quotation."""
    class Status(models.TextChoices):
        DRAFT = 'draft', 'Draft'
        FOR_APPROVAL = 'for_approval', 'For Approval'
        APPROVED = 'approved', 'Approved'
        EXPIRED = 'expired', 'Expired'

    class Currency(models.TextChoices):
        USD = 'usd', 'USD'
        EURO = 'euro', 'EURO'
        RMB = 'rmb', 'RMB'
        PHP = 'php', 'PHP'

    quote_number = models.CharField(max_length=50, unique=True, editable=False)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    customer = models.ForeignKey(
        Customer,
        on_delete=models.PROTECT, # Prevent deleting customer if they have quotes
        related_name='quotations'
    )
    date = models.DateField()
    total_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0, editable=False) # Calculated field

    # Tracking
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='created_quotations',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        editable=False
    )
    created_on = models.DateTimeField(auto_now_add=True)
    last_modified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='modified_quotations',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        editable=False
    )
    last_modified_on = models.DateTimeField(auto_now=True)

    # Optional Fields
    purchase_request = models.TextField(blank=True, null=True)
    expiry_date = models.DateField(blank=True, null=True)
    currency = models.CharField(max_length=5, choices=Currency.choices, default=Currency.USD)
    notes = models.TextField(blank=True, null=True)
    price = models.TextField(blank=True, null=True) # Consider DecimalField if it's always numeric
    validity = models.TextField(blank=True, null=True) # Consider IntegerField if it's always days

    # Linked Options
    terms_conditions = models.ForeignKey(
        TermsCondition,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='quotations'
    )
    payment_terms = models.ForeignKey(
        PaymentTerm,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='quotations'
    )
    delivery_options = models.ForeignKey(
        DeliveryOption,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='quotations'
    )
    other_options = models.ForeignKey(
        OtherOption,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='quotations'
    )

    # Linked Contacts (Using existing admin_api model)
    customer_contacts = models.ManyToManyField(
        CustomerContact,
        related_name='quotations',
        blank=True
    )

    class Meta:
        ordering = ['-created_on']
        verbose_name = 'Quotation'
        verbose_name_plural = 'Quotations'

    def __str__(self):
        return f"Quotation #{self.quote_number} - {self.customer.name}"

    def save(self, *args, **kwargs):
        # Auto-generate quote number on first save
        if not self.pk: # Only generate if creating a new instance
             # Find the highest existing quote number (assuming format Q-######)
            last_quotation = Quotation.objects.order_by('id').last()
            if last_quotation:
                last_id = last_quotation.id
                new_id = last_id + 1
            else:
                new_id = 1
            self.quote_number = f"Q-{new_id:06d}" # Format as Q-000001

        # Recalculate total amount (consider doing this in serializer or signal for complex cases)
        # self.total_amount = sum(item.total_selling for item in self.items.all()) # Requires items to be saved first

        super().save(*args, **kwargs)

class QuotationItem(models.Model):
    """Represents an item line within a quotation."""
    quotation = models.ForeignKey(Quotation, on_delete=models.CASCADE, related_name='items')
    inventory = models.ForeignKey(Inventory, on_delete=models.PROTECT, related_name='quotation_items') # Link to inventory item

    # Overridable fields from Inventory (or specific to this quote line)
    item_code = models.CharField(max_length=100, blank=True) # Store for reference, populated from inventory
    brand = models.ForeignKey(Brand, on_delete=models.SET_NULL, null=True, blank=True) # Store for reference
    show_brand = models.BooleanField(default=True)
    # made_in = models.CharField(max_length=100, blank=True, null=True) # Populated based on Brand logic
    wholesale_price = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True) # Override
    actual_landed_cost = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    estimated_landed_cost = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    notes = models.TextField(blank=True, null=True)
    unit = models.CharField(max_length=50, blank=True) # Override
    quantity = models.PositiveIntegerField(default=1)
    photo = models.ImageField(upload_to='quotation_item_photos/', null=True, blank=True) # Override
    show_photo = models.BooleanField(default=True)
    baseline_margin = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True) # Percentage
    external_description = models.TextField(blank=True, null=True) # Override

    # Discount fields
    has_discount = models.BooleanField(default=False)
    discount_type = models.CharField(max_length=10, choices=[('value', 'Value'), ('percentage', 'Percentage')], null=True, blank=True)
    discount_percentage = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    discount_value = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)

    # Calculated fields (Store if needed for performance, otherwise use properties/serializers)
    net_selling = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    total_selling = models.DecimalField(max_digits=15, decimal_places=2, default=0)

    # Fields to be populated by logic (not directly stored or managed via properties/serializers)
    # inventory_status: str
    # last_quoted_price: Decimal
    # landed_cost_x_discount: Decimal

    class Meta:
        ordering = ['id'] # Keep items in the order they were added
        verbose_name = 'Quotation Item'
        verbose_name_plural = 'Quotation Items'

    def __str__(self):
        return f"{self.quantity} x {self.item_code or self.inventory.item_code} for Quotation {self.quotation.quote_number}"

    def save(self, *args, **kwargs):
        # Populate fields from inventory if not provided (on creation)
        if not self.pk and self.inventory:
            self.item_code = self.inventory.item_code
            self.brand = self.inventory.brand
            if self.wholesale_price is None: # Only default if not overridden
                 self.wholesale_price = self.inventory.wholesale_price
            if not self.unit:
                 self.unit = self.inventory.unit
            # if not self.photo: # Careful with ImageField default
            #     self.photo = self.inventory.photo
            if self.external_description is None:
                 self.external_description = self.inventory.external_description

        # --- Calculation Logic ---
        # Basic Net Selling (before discount)
        base_price = self.wholesale_price if self.wholesale_price is not None else 0

        # Apply Discount
        if self.has_discount and self.discount_type:
            if self.discount_type == 'percentage' and self.discount_percentage is not None:
                discount_amount = base_price * (self.discount_percentage / 100)
                self.net_selling = base_price - discount_amount
            elif self.discount_type == 'value' and self.discount_value is not None:
                self.net_selling = base_price - self.discount_value
            else:
                self.net_selling = base_price # No valid discount applied
        else:
            self.net_selling = base_price

        # Total Selling
        self.total_selling = self.net_selling * self.quantity

        super().save(*args, **kwargs)
        # Note: Need to trigger Quotation total recalculation after saving/deleting items (e.g., via signals)

class QuotationSalesAgent(models.Model):
    """Links Sales Agents (Users) to a Quotation with a specific role."""
    class Role(models.TextChoices):
        MAIN = 'main', 'Main'
        SUPPORT = 'support', 'Support'

    quotation = models.ForeignKey(Quotation, on_delete=models.CASCADE, related_name='sales_agents')
    agent = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='quotation_assignments')
    role = models.CharField(max_length=10, choices=Role.choices, default=Role.SUPPORT)

    class Meta:
        ordering = ['role', 'agent__username']
        unique_together = ('quotation', 'agent') # An agent can only be assigned once per quote
        verbose_name = 'Quotation Sales Agent'
        verbose_name_plural = 'Quotation Sales Agents'

    def __str__(self):
        return f"{self.agent.get_full_name() or self.agent.username} ({self.get_role_display()}) for Quotation {self.quotation.quote_number}"

class QuotationAdditionalControls(models.Model):
    """Stores boolean control flags for a Quotation."""
    quotation = models.OneToOneField(Quotation, on_delete=models.CASCADE, related_name='additional_controls')
    show_carton_packing = models.BooleanField(default=True)
    do_not_show_all_photos = models.BooleanField(default=False)
    highlight_item_notes = models.BooleanField(default=False)
    show_devaluation_clause = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Quotation Additional Controls'
        verbose_name_plural = 'Quotation Additional Controls'

    def __str__(self):
        return f"Additional Controls for Quotation {self.quotation.quote_number}"

def quotation_attachment_path(instance, filename):
    # file will be uploaded to MEDIA_ROOT/quotation_attachments/<quotation_id>/<filename>
    return f'quotation_attachments/{instance.quotation.id}/{filename}'

class QuotationAttachment(models.Model):
    """Stores files attached to a Quotation."""
    quotation = models.ForeignKey(Quotation, on_delete=models.CASCADE, related_name='attachments')
    file = models.FileField(upload_to=quotation_attachment_path)
    uploaded_on = models.DateTimeField(auto_now_add=True)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='uploaded_quotation_attachments'
    )

    class Meta:
        ordering = ['-uploaded_on']
        verbose_name = 'Quotation Attachment'
        verbose_name_plural = 'Quotation Attachments'

    def __str__(self):
        return f"Attachment for Quotation {self.quotation.quote_number} ({self.file.name})"

class LastQuotedPrice(models.Model):
    inventory = models.ForeignKey(Inventory, on_delete=models.CASCADE, related_name='last_quoted_prices')
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='last_quoted_prices_received')
    last_price = models.DecimalField(max_digits=10, decimal_places=2)
    last_quoted_date = models.DateField(auto_now=True) # Automatically update on save
    quotation = models.ForeignKey(Quotation, on_delete=models.SET_NULL, null=True, blank=True, related_name='quoted_prices_history') # Link back to the quote

    class Meta:
        ordering = ['-last_quoted_date']
        unique_together = [['inventory', 'customer']] # Only store the latest price per item/customer pair
        verbose_name = 'Last Quoted Price'
        verbose_name_plural = 'Last Quoted Prices'

    def __str__(self) -> str:
        return f"Last price for {self.inventory.item_code} to {self.customer.name}: {self.last_price}"