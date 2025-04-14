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

class TermCondition(models.Model):
    name = models.CharField(max_length=255, unique=True)
    text = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Term/Condition'
        verbose_name_plural = 'Terms & Conditions'

    def __str__(self) -> str:
        return self.name

class PaymentTermOption(models.Model):
    name = models.CharField(max_length=255, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Payment Term Option'
        verbose_name_plural = 'Payment Term Options'

    def __str__(self) -> str:
        return self.name

class DeliveryOption(models.Model):
    name = models.CharField(max_length=255, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Delivery Option'
        verbose_name_plural = 'Delivery Options'

    def __str__(self) -> str:
        return self.name

class OtherOption(models.Model):
    name = models.CharField(max_length=255, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Other Option'
        verbose_name_plural = 'Other Options'

    def __str__(self) -> str:
        return self.name
    
class Quotation(models.Model):
    class Status(models.TextChoices):
        DRAFT = 'draft', _('Draft')
        FOR_APPROVAL = 'for_approval', _('For Approval')
        APPROVED = 'approved', _('Approved')
        EXPIRED = 'expired', _('Expired')

    class Currency(models.TextChoices):
        USD = 'USD', _('US Dollar')
        EUR = 'EUR', _('Euro')
        RMB = 'RMB', _('Chinese Yuan')
        PHP = 'PHP', _('Philippine Peso')

    quote_number = models.CharField(max_length=50, unique=True, editable=False)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
    )
    customer = models.ForeignKey(
        Customer,
        on_delete=models.PROTECT,
        related_name='quotations',
    )
    date = models.DateField(auto_now_add=True) # Or default=date.today? Let's use auto_now_add for creation date
    total_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_quotations',
        editable=False,
    )
    created_on = models.DateTimeField(auto_now_add=True, editable=False)
    last_modified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='modified_quotations',
        editable=False,
    )
    last_modified_on = models.DateTimeField(auto_now=True, editable=False)
    purchase_request = models.TextField(blank=True)
    expiry_date = models.DateField(null=True, blank=True)
    currency = models.CharField(
        max_length=3,
        choices=Currency.choices,
        default=Currency.PHP,
    )
    notes = models.TextField(blank=True)
    # attach_files = models.FileField(upload_to='quotation_files/', blank=True, null=True) # For single file
    # For multiple files, a separate model is better:
    # terms_conditions = models.ForeignKey(TermCondition, on_delete=models.SET_NULL, null=True, blank=True) # If single selection
    terms_conditions = models.ManyToManyField(TermCondition, blank=True, related_name='quotations') # If multiple selections
    price_validity = models.CharField(max_length=255, blank=True) # Renamed 'Price' to 'price_validity' for clarity
    # payment = models.ForeignKey(PaymentTermOption, on_delete=models.SET_NULL, null=True, blank=True) # If single selection
    payment_terms = models.ManyToManyField(PaymentTermOption, blank=True, related_name='quotations') # If multiple selections
    # delivery = models.ForeignKey(DeliveryOption, on_delete=models.SET_NULL, null=True, blank=True) # If single selection
    delivery_options = models.ManyToManyField(DeliveryOption, blank=True, related_name='quotations') # If multiple selections
    validity_period = models.CharField(max_length=255, blank=True) # Renamed 'Validity' to 'validity_period'
    # others = models.ForeignKey(OtherOption, on_delete=models.SET_NULL, null=True, blank=True) # If single selection
    other_options = models.ManyToManyField(OtherOption, blank=True, related_name='quotations') # If multiple selections

    # Related managers for easy access
    # items defined via QuotationItem.quotation ForeignKey related_name='items'
    # sales_agents defined via QuotationSalesAgent.quotation ForeignKey related_name='sales_agents'
    # customer_contacts defined via ManyToManyField below
    # additional_controls defined via QuotationAdditionalControl.quotation OneToOneField related_name='additional_controls'
    # attachments defined via QuotationAttachment.quotation ForeignKey related_name='attachments'

    customer_contacts = models.ManyToManyField(
        CustomerContact,
        blank=True,
        related_name='quotations',
    )

    class Meta:
        ordering = ['-created_on', '-id']
        verbose_name = 'Quotation'
        verbose_name_plural = 'Quotations'

    def __str__(self) -> str:
        return f"Quote {self.quote_number} for {self.customer.name}"

    def _generate_quote_number(self) -> str:
        # Simple example: QUOTE-YYYYMMDD-ID
        # You might want a more robust sequential number generator
        return f"QUOTE-{self.created_on.strftime('%Y%m%d')}-{self.pk}"

    def update_total_amount(self) -> None:
        """Calculates and updates the total amount from related items."""
        total = self.items.aggregate(
            total=Sum(F('net_selling') * F('quantity'))
        )['total'] or Decimal('0.00')
        self.total_amount = total
        # Note: Saving here might cause recursion if called within save().
        # It's often better to calculate in save() or use signals.

    def save(self, *args, **kwargs):
        is_new = self._state.adding
        if is_new and not self.created_on:
            # Ensure created_on is set before generating quote number if using date
            super().save(*args, **kwargs) # Save once to get pk and created_on
            self.quote_number = self._generate_quote_number()
            kwargs['force_insert'] = False # Avoid re-inserting
            super().save(update_fields=['quote_number'], *args, **kwargs) # Save again with quote_number
        else:
            # Calculate total amount before saving updates
            # self.update_total_amount() # Be cautious with calling aggregate here
            super().save(*args, **kwargs)
        # Consider using signals (post_save on QuotationItem) to update total_amount reliably


class QuotationAttachment(models.Model):
    quotation = models.ForeignKey(Quotation, on_delete=models.CASCADE, related_name='attachments')
    file = models.FileField(upload_to='quotation_attachments/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"Attachment for {self.quotation.quote_number} - {self.file.name}"


class QuotationItem(models.Model):
    class DiscountType(models.TextChoices):
        VALUE = 'value', _('Value')
        PERCENTAGE = 'percentage', _('Percentage')

    quotation = models.ForeignKey(Quotation, on_delete=models.CASCADE, related_name='items')
    inventory = models.ForeignKey(Inventory, on_delete=models.PROTECT, related_name='quotation_items')
    # Fields copied/defaulted from Inventory (can be overridden)
    item_code = models.CharField(max_length=50, editable=False) # Copied from inventory
    brand_name = models.CharField(max_length=100, editable=False) # Copied from inventory.brand
    show_brand = models.BooleanField(default=True)
    made_in = models.TextField(blank=True, null=True, editable=False) # Copied from inventory.brand
    show_made_in = models.BooleanField(default=True) # Copied from inventory.brand
    wholesale_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True) # Copied, can override
    unit = models.CharField(max_length=50, blank=True) # Copied from inventory
    photo = models.ImageField(upload_to='quotation_item_photos/', null=True, blank=True) # Copied, can override
    show_photo = models.BooleanField(default=True)
    external_description = models.TextField(blank=True) # Copied from inventory

    # Quotation specific fields
    actual_landed_cost = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    estimated_landed_cost = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    notes = models.TextField(blank=True)
    quantity = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('1.00'))
    baseline_margin = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True) # Percentage?
    # inventory_status calculated via property
    # last_quoted_price needs lookup logic (maybe via LastQuotedPrice model)
    has_discount = models.BooleanField(default=False)
    discount_type = models.CharField(
        max_length=10,
        choices=DiscountType.choices,
        null=True,
        blank=True,
    )
    discount_percentage = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    discount_value = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    # net_selling calculated via property
    # total_selling calculated via property

    class Meta:
        ordering = ['id'] # Order by addition sequence within a quote
        unique_together = [['quotation', 'inventory']] # Prevent adding same item twice? Or allow? Allowing for now.

    def __str__(self) -> str:
        return f"{self.item_code} for Quote {self.quotation.quote_number}"

    @property
    def inventory_stock(self) -> Decimal:
        # Helper to get current stock, handling potential None
        return self.inventory.stock_on_hand or Decimal('0.00')

    @property
    def inventory_status(self) -> str:
        stock = self.inventory_stock
        qty = self.quantity

        if qty > 1:
            if stock == 0:
                return "For Importation"
            elif stock > 0 and qty > stock:
                return f"{stock:.0f} pcs In Stock, Balance for Importation" # Assuming pcs means integer units
            elif stock > 0 and qty <= stock:
                return "In Stock"
        elif qty == 1:
            if stock == 0:
                return "For Importation"
            elif stock > 0:
                return f"{stock:.0f} pcs in stock"
        return "Status Unknown" # Fallback

    @property
    def landed_cost_x_discount(self) -> Decimal | None:
        # Placeholder - Define calculation logic based on requirements
        # Needs clarification on which cost (actual/estimated) and how discount applies
        cost = self.actual_landed_cost or self.estimated_landed_cost
        if cost is None:
            return None
        # Simple example: apply discount value if present
        if self.has_discount and self.discount_type == self.DiscountType.VALUE and self.discount_value is not None:
             return cost - self.discount_value # Or is it discount *on* cost? Needs clarification
        # Add logic for percentage discount if needed
        return cost # No discount applied in this example

    @property
    def net_selling(self) -> Decimal:
        # Placeholder - Define calculation logic based on requirements
        # Example: Wholesale price minus discount
        price = self.wholesale_price or Decimal('0.00')
        discount_amount = Decimal('0.00')

        if self.has_discount:
            if self.discount_type == self.DiscountType.VALUE and self.discount_value is not None:
                discount_amount = self.discount_value
            elif self.discount_type == self.DiscountType.PERCENTAGE and self.discount_percentage is not None:
                discount_amount = price * (self.discount_percentage / Decimal('100.00'))

        return price - discount_amount

    @property
    def total_selling(self) -> Decimal:
        return self.net_selling * self.quantity

    def save(self, *args, **kwargs):
        if self._state.adding or not self.item_code:
            # Populate fields from inventory on creation
            self.item_code = self.inventory.item_code
            self.brand_name = self.inventory.brand.name
            self.made_in = self.inventory.brand.made_in
            self.show_made_in = self.inventory.brand.show_made_in
            if self.wholesale_price is None: # Only default if not provided
                 self.wholesale_price = self.inventory.wholesale_price
            self.unit = self.inventory.unit
            if not self.photo: # Only default if not provided
                 self.photo = self.inventory.photo
            self.external_description = self.inventory.external_description
        super().save(*args, **kwargs)
        # Consider using signals to update Quotation.total_amount


class QuotationSalesAgent(models.Model):
    class Role(models.TextChoices):
        MAIN = 'main', _('Main')
        SUPPORT = 'support', _('Support')

    quotation = models.ForeignKey(Quotation, on_delete=models.CASCADE, related_name='sales_agents')
    # Assuming sales agent is a User or a dedicated SalesAgent model
    # Using User for now:
    agent = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='quotation_assignments')
    role = models.CharField(max_length=10, choices=Role.choices, default=Role.SUPPORT)

    class Meta:
        ordering = ['role', 'agent__username'] # Main agent first
        unique_together = [['quotation', 'agent']] # One role per agent per quote

    def __str__(self) -> str:
        return f"{self.agent.get_full_name() or self.agent.username} ({self.get_role_display()}) for Quote {self.quotation.quote_number}"

    def clean(self):
        # Ensure only one main agent per quotation
        if self.role == self.Role.MAIN:
            main_agents = QuotationSalesAgent.objects.filter(
                quotation=self.quotation,
                role=self.Role.MAIN
            ).exclude(pk=self.pk) # Exclude self if updating
            if main_agents.exists():
                raise ValidationError(_('A quotation can only have one main sales agent.'))
        super().clean()

    def save(self, *args, **kwargs):
        self.full_clean() # Run validation before saving
        super().save(*args, **kwargs)


class QuotationAdditionalControl(models.Model):
    quotation = models.OneToOneField(Quotation, on_delete=models.CASCADE, related_name='additional_controls')
    show_carton_packing = models.BooleanField(default=False)
    do_not_show_all_photos = models.BooleanField(default=False)
    highlight_item_notes = models.BooleanField(default=False)
    show_devaluation_clause = models.BooleanField(default=True)

    def __str__(self) -> str:
        return f"Additional Controls for Quote {self.quotation.quote_number}"


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