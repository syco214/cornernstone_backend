from django.db import models
from django.db import models
from django.conf import settings
from django.utils import timezone
from django.db.models import Sum, F, ExpressionWrapper, DecimalField
from admin_api.models import Supplier, Inventory, USER_ACCESS_OPTIONS, USER_ROLE_OPTIONS
from decimal import Decimal
from django.contrib.postgres.fields import ArrayField

class PurchaseOrder(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('pending_approval', 'Pending PO Approval'),
        ('for_dp', 'For Down Payment'),
        ('pending_dp_approval', 'Pending DP Approval'),
        ('confirm_ready_dates', 'Confirm Ready Dates'),
        ('packing_list_1', 'Packing List 1'),
        ('packing_list_2', 'Packing List 2'),
        ('packing_list_3', 'Packing List 3'),
        ('approve_for_import_1', 'Approve for Import 1'),
        ('approve_for_import_2', 'Approve for Import 2'),
        ('approve_for_import_3', 'Approve for Import 3'),
        ('payment_1', 'Payment 1'),
        ('payment_2', 'Payment 2'),
        ('payment_3', 'Payment 3'),
        ('invoice_1', 'Invoice 1'),
        ('invoice_2', 'Invoice 2'),
        ('invoice_3', 'Invoice 3'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]

    CURRENCY_CHOICES = [ # Consistent with Quotation
        ('USD', 'USD'),
        ('EUR', 'EURO'), # Corrected to EUR from EURO for consistency if needed
        ('RMB', 'RMB'),
        ('PHP', 'PHP'),
        # Add other currencies as needed
    ]
    SUPPLIER_TYPE_CHOICES = [
        ('local', 'Local'),
        ('foreign', 'Foreign'),
    ]

    po_number = models.CharField(max_length=50, unique=True, editable=False)
    supplier = models.ForeignKey(Supplier, on_delete=models.PROTECT, related_name='purchase_orders')
    supplier_type = models.CharField(max_length=10, choices=SUPPLIER_TYPE_CHOICES)
    delivery_terms = models.CharField(max_length=255) # E.g., "FOB Shanghai", "CIF Manila"
    currency = models.CharField(max_length=4, choices=CURRENCY_CHOICES)
    supplier_address = models.TextField(blank=True) # Can be pre-filled from Supplier
    country = models.CharField(max_length=100) # Can be pre-filled from Supplier

    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='draft')
    notes = models.TextField(blank=True)

    # Amounts - these will be calculated
    items_gross_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0.00) # Sum of (qty*list_price) for all items
    items_total_discount_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0.00) # Sum of discounts from all items
    subtotal_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0.00) # items_gross_amount - items_total_discount_amount
    order_level_discount_charge_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0.00) # Net from PurchaseOrderDiscountCharge
    grand_total_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0.00) # subtotal_amount + order_level_discount_charge_amount

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_purchase_orders'
    )
    last_modified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='modified_purchase_orders'
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='approved_purchase_orders'
    )
    created_on = models.DateTimeField(auto_now_add=True)
    last_modified_on = models.DateTimeField(auto_now=True)
    po_date = models.DateField(default=timezone.now)


    class Meta:
        ordering = ['-po_date', '-po_number']

    def __str__(self) -> str:
        return f'PO #{self.po_number} - {self.supplier.name}'

    def _generate_po_number(self) -> str:
        date_str = timezone.now().strftime('%Y%m%d')
        last_po = PurchaseOrder.objects.filter(po_number__startswith=f'PO-{date_str}').order_by('po_number').last()
        if last_po:
            seq_num = int(last_po.po_number.split('-')[-1]) + 1
        else:
            seq_num = 1
        return f'PO-{date_str}-{seq_num:04d}'

    def update_totals(self, save_instance: bool = True) -> None:
        """Recalculates all monetary totals for the purchase order."""
        # 1. Calculate item-related totals
        item_aggregates = self.items.aggregate(
            total_gross=Sum(ExpressionWrapper(F('quantity') * F('list_price'), output_field=DecimalField())),
            total_item_discount=Sum('calculated_discount_amount')
        )
        self.items_gross_amount = item_aggregates['total_gross'] or Decimal('0.00')
        self.items_total_discount_amount = item_aggregates['total_item_discount'] or Decimal('0.00')
        self.subtotal_amount = self.items_gross_amount - self.items_total_discount_amount

        # 2. Calculate order-level discounts/charges
        current_order_level_disc_charge = Decimal('0.00')
        for dc in self.discounts_charges.all():
            amount = dc.calculate_amount(self.subtotal_amount)
            if not isinstance(amount, Decimal):
                amount = Decimal(str(amount))
            current_order_level_disc_charge += amount
        self.order_level_discount_charge_amount = current_order_level_disc_charge

        # 3. Calculate grand total
        self.grand_total_amount = self.subtotal_amount + self.order_level_discount_charge_amount

        if save_instance:
            self.save(update_fields=[
                'items_gross_amount', 'items_total_discount_amount',
                'subtotal_amount', 'order_level_discount_charge_amount',
                'grand_total_amount'
            ])

    def save(self, *args, **kwargs) -> None:
        if not self.pk and not self.po_number : # Only generate if new and not set
            self.po_number = self._generate_po_number()

        # Determine if we should skip totals update (e.g., during initial creation via serializer)
        skip_totals_update = kwargs.pop('skip_totals_update', False)
        
        super().save(*args, **kwargs)

        if not skip_totals_update:
            # If items or discounts_charges might have changed, totals need update.
            # This is typically handled after nested serializers save.
            # For direct saves or if related items are managed outside serializer's main save,
            # ensure update_totals is called.
            pass # Totals update will be called by serializer or explicitly after related changes.


class PurchaseOrderItem(models.Model):
    ITEM_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('ordered', 'Ordered'), # Confirmed with supplier
        ('partially_received', 'Partially Received'),
        ('fully_received', 'Fully Received'),
        ('cancelled', 'Cancelled'),
    ]
    DISCOUNT_TYPE_CHOICES = [
        ('percentage', 'Percentage'),
        ('fixed', 'Fixed Amount'),
        ('none', 'No Discount'),
    ]

    purchase_order = models.ForeignKey(PurchaseOrder, on_delete=models.CASCADE, related_name='items')
    inventory = models.ForeignKey(Inventory, on_delete=models.PROTECT, related_name='po_items')
    # item_code, brand, external_description, unit can be sourced from inventory

    external_description = models.TextField(blank=True) # Can override inventory's
    unit = models.CharField(max_length=50, blank=True) # Can override inventory's
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    list_price = models.DecimalField(max_digits=15, decimal_places=2) # Price per unit in PO's currency

    discount_type = models.CharField(max_length=15, choices=DISCOUNT_TYPE_CHOICES, null=True, blank=True)
    discount_value = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True) # Percentage (e.g., 10 for 10%) or fixed amount

    calculated_discount_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0.00, editable=False)
    line_total = models.DecimalField(max_digits=15, decimal_places=2, editable=False) # (qty * list_price) - calculated_discount_amount

    quantity_received = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    status = models.CharField(max_length=50, choices=ITEM_STATUS_CHOICES, default='pending')
    ready_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)

    batch_number = models.PositiveSmallIntegerField(null=True, blank=True, 
                                                 help_text="Batch number for grouping items by ready date")

    class Meta:
        ordering = ['id'] # Or any other preferred order

    def __str__(self) -> str:
        return f'{self.inventory.item_code} for PO {self.purchase_order.po_number}'

    @property
    def item_code(self) -> str:
        return self.inventory.item_code

    @property
    def brand(self) -> str:
        return self.inventory.brand_name # Assuming brand_name on Inventory model

    @property
    def balance_quantity(self) -> models.DecimalField:
        return self.quantity - self.quantity_received

    def _calculate_totals(self):
        """Calculate line total based on quantity, price and discount."""
        # Calculate gross line total (quantity * list_price)
        gross_line_total = self.quantity * self.list_price
        
        # Calculate discount amount
        if self.discount_type == 'percentage' and self.discount_value:
            # Convert percentage to decimal value
            discount_percentage = Decimal(str(self.discount_value)) / Decimal('100')
            self.calculated_discount_amount = gross_line_total * discount_percentage
        elif self.discount_type == 'amount' and self.discount_value:
            # Fixed amount discount
            self.calculated_discount_amount = Decimal(str(self.discount_value))
        else:
            # No discount
            self.calculated_discount_amount = Decimal('0.00')
        
        # Calculate final line total
        self.line_total = round(gross_line_total - self.calculated_discount_amount, 2)

    def save(self, *args, **kwargs) -> None:
        if not self.external_description and self.inventory:
            self.external_description = self.inventory.external_description
        if not self.unit and self.inventory:
            self.unit = self.inventory.unit
        
        self._calculate_totals()
        super().save(*args, **kwargs)
        # After saving an item, the PO totals might need an update
        if self.purchase_order:
             self.purchase_order.update_totals()


class PurchaseOrderDiscountCharge(models.Model):
    purchase_order = models.ForeignKey(PurchaseOrder, on_delete=models.CASCADE, related_name='discounts_charges')
    description = models.CharField(max_length=255)
    is_percentage = models.BooleanField(default=False) # True if value is a percentage, False if flat amount
    value = models.DecimalField(max_digits=15, decimal_places=2) # The percentage (e.g., 5 for 5%) or flat amount
    is_deduction = models.BooleanField(default=False) # True for discount (negative effect), False for charge (positive effect)

    class Meta:
        ordering = ['id']

    def __str__(self) -> str:
        type_str = "Discount" if self.is_deduction else "Charge"
        return f'{type_str}: {self.description} for PO {self.purchase_order.po_number}'

    def calculate_amount(self, basis_amount: models.DecimalField) -> models.DecimalField:
        """Calculates the actual monetary value of this discount/charge."""
        calculated = Decimal('0.00')
        if self.is_percentage:
            calculated = (Decimal(str(self.value)) / Decimal('100')) * Decimal(str(basis_amount))
        else:
            calculated = Decimal(str(self.value))
        
        return -calculated if self.is_deduction else calculated

    def save(self, *args, **kwargs) -> None:
        super().save(*args, **kwargs)
        if self.purchase_order:
            self.purchase_order.update_totals()
    
    def delete(self, *args, **kwargs) -> tuple[int, dict[str, int]]:
        po = self.purchase_order
        result = super().delete(*args, **kwargs)
        if po:
            po.update_totals()
        return result


class PurchaseOrderPaymentTerm(models.Model):
    purchase_order = models.OneToOneField(PurchaseOrder, on_delete=models.CASCADE, related_name='payment_term')
    credit_limit = models.DecimalField(max_digits=15, decimal_places=2)
    
    payment_terms_description = models.CharField(max_length=255) # E.g., "Net 30 days", "50% Downpayment, Balance upon Delivery"
    dp_percentage = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True) # Downpayment percentage
    terms_days = models.PositiveIntegerField(null=True, blank=True) # E.g., 30 for Net 30
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f'Payment Terms for PO {self.purchase_order.po_number}'

def default_roles():
    return ['admin', 'supervisor']

class PurchaseOrderRoute(models.Model):
    """Model to track the workflow/route of a purchase order"""
    purchase_order = models.ForeignKey(PurchaseOrder, on_delete=models.CASCADE, related_name='route_steps')
    step = models.PositiveIntegerField()  # Step number in the workflow
    is_completed = models.BooleanField(default=False)
    is_required = models.BooleanField(default=True)  # Is this step required before proceeding
    task = models.TextField(blank=True)
    access = models.CharField(
        max_length=50,
        choices=[(option, option.replace('_', ' ').title()) for option in USER_ACCESS_OPTIONS],
        default='purchase_orders',
        help_text='User role/permission required to complete this step'
    )
    roles = ArrayField(
        models.CharField(
            max_length=20,
            choices=[(role, role.title()) for role in USER_ROLE_OPTIONS]
        ),
        default=default_roles,  # Using the function we defined above
        help_text='User roles that can complete this step'
    )
    completed_at = models.DateTimeField(null=True, blank=True)
    completed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='completed_po_steps'
    )

    class Meta:
        ordering = ['purchase_order', 'step']
        unique_together = ['purchase_order', 'step']

    def __str__(self):
        return f"Step {self.step} for PO {self.purchase_order.po_number}: {self.task}"

    def complete(self, user=None):
        """Mark this step as completed"""
        self.is_completed = True
        self.completed_at = timezone.now()
        self.completed_by = user
        self.save()

class PurchaseOrderDownPayment(models.Model):
    """Model to track purchase order down payments"""
    purchase_order = models.ForeignKey(PurchaseOrder, on_delete=models.CASCADE, related_name='down_payments')
    amount_paid = models.DecimalField(max_digits=15, decimal_places=2)
    payment_slip = models.FileField(upload_to='po_payment_slips/', null=True, blank=True)
    remarks = models.TextField(blank=True)

    def __str__(self):
        return f"DP for PO {self.purchase_order.po_number}: {self.amount_paid}"