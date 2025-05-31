from django.utils import timezone
from django.core.exceptions import PermissionDenied
from .models import PurchaseOrderRoute, PurchaseOrderDownPayment, PurchaseOrderItem, PackingList, PaymentDocument, InvoiceDocument
from decimal import Decimal
from datetime import datetime
from django.core.exceptions import ValidationError

class POWorkflow:
    """
    Handles purchase order workflow operations
    """
    INITIAL_WORKFLOW_STEPS = [
        (1, "Draft", True, "purchase_orders", ['admin', 'supervisor', 'user']),
        (2, "PO Approval", True, "purchase_orders", ['admin', 'supervisor']),  # Only admin/supervisor can approve
        (3, "For DP", True, "purchase_orders", ['admin', 'supervisor', 'user']),
        (4, "DP Approval", True, "purchase_orders", ['admin', 'supervisor']),  # Only admin/supervisor can approve
        (5, "Confirm Ready Date", True, "purchase_orders", ['admin', 'supervisor', 'user']),
    ]

    @classmethod
    def check_user_permission(cls, user, access, roles):
        """
        Check if the user has the required access and role
        """
        if not user:
            return False
        
        if user.role == 'admin':
            return True
        
        # Check if user has the required role (singular in your model)
        user_role = user.role
        if user_role not in roles:
            return False
        
        # Check if user has the required access
        user_access_list = user.user_access
        if access not in user_access_list:
            return False
        
        return True
        
    @classmethod
    def initialize_workflow(cls, purchase_order, user=None):
        """
        Initialize the workflow steps for a new purchase order
        """
        # Delete any existing steps if they exist
        purchase_order.route_steps.all().delete()
        
        # Create new steps
        for step_number, task, is_required, access, roles in cls.INITIAL_WORKFLOW_STEPS:
            PurchaseOrderRoute.objects.get_or_create(
                purchase_order=purchase_order,
                step=step_number,
                defaults={
                    'task': task,
                    'is_required': is_required,
                    'is_completed': False,
                    'access': access,
                    'roles': roles
                }
            )
        
        return purchase_order
    
    @classmethod
    def submit_for_approval(cls, purchase_order, user=None):
        """
        Submit the purchase order for approval
        """
        # Get the first step and check permissions
        step1 = purchase_order.route_steps.filter(step=1).first()
        if step1 and not cls.check_user_permission(user, step1.access, step1.roles):
            raise PermissionDenied("You don't have permission to submit this purchase order for approval")
        
        # Update the PO status
        purchase_order.status = 'pending_approval'
        purchase_order.save()
        
        # Mark the first step as completed
        if step1 and not step1.is_completed:
            step1.complete(user)
        
        return purchase_order
    
    @classmethod
    def approve_po(cls, purchase_order, user=None):
        """
        Approve the purchase order and move to the next workflow stage
        """
        # Get the second step and check permissions
        step2 = purchase_order.route_steps.filter(step=2).first()
        if step2 and not cls.check_user_permission(user, step2.access, step2.roles):
            raise PermissionDenied("You don't have permission to approve this purchase order")
        
        # Mark the PO approval step as completed
        if step2 and not step2.is_completed:
            step2.complete(user)
        
        # Move to For DP status
        purchase_order.status = 'for_dp'
        purchase_order.approved_by = user
        purchase_order.save()
        
        return purchase_order
    
    @classmethod
    def reject_po(cls, purchase_order, user=None):
        """
        Reject the purchase order, sending it back to draft
        """
        # Get the second step and check permissions (same as approve)
        step2 = purchase_order.route_steps.filter(step=2).first()
        if step2 and not cls.check_user_permission(user, step2.access, step2.roles):
            raise PermissionDenied("You don't have permission to reject this purchase order")
        
        # Reset to draft status
        purchase_order.status = 'draft'
        purchase_order.save()
        
        # Reset step 1 (Draft) to be completed again
        step1 = purchase_order.route_steps.filter(step=1).first()
        if step1:
            step1.is_completed = False
            step1.completed_at = None
            step1.completed_by = None
            step1.save()
        
        return purchase_order
    
    @classmethod
    def submit_down_payment(cls, purchase_order, data, user=None):
        """
        Submit a down payment for a purchase order
        """
        # Get the third step and check permissions
        step3 = purchase_order.route_steps.filter(step=3).first()
        if step3 and not cls.check_user_permission(user, step3.access, step3.roles):
            raise PermissionDenied("You don't have permission to submit down payment")
        
        # Check if down payment already exists
        existing_dp = PurchaseOrderDownPayment.objects.filter(purchase_order=purchase_order).first()
        
        if existing_dp:
            # Update existing down payment
            existing_dp.amount_paid = data['amount_paid']
            existing_dp.remarks = data.get('remarks', '')
            
            # Only update payment slip if a new one is provided
            if 'payment_slip' in data and data['payment_slip'] is not None:
                # Delete old file to avoid storage issues
                if existing_dp.payment_slip:
                    try:
                        existing_dp.payment_slip.delete(save=False)
                    except Exception:
                        # Continue even if file deletion fails
                        pass
                    
                existing_dp.payment_slip = data['payment_slip']
            
            existing_dp.save()
            down_payment = existing_dp
        else:
            # Create new down payment record
            down_payment = PurchaseOrderDownPayment.objects.create(
                purchase_order=purchase_order,
                amount_paid=data['amount_paid'],
                payment_slip=data.get('payment_slip'),
                remarks=data.get('remarks', ''),
            )
        
        # Mark the For DP step as completed
        if step3 and not step3.is_completed:
            step3.complete(user)
        
        # Update PO status to pending DP approval
        purchase_order.status = 'pending_dp_approval'
        purchase_order.save()
        
        return purchase_order, down_payment
    
    @classmethod
    def approve_down_payment(cls, purchase_order, user=None):
        """
        Approve the down payment and move to the next workflow step
        """
        # Get the fourth step and check permissions
        step4 = purchase_order.route_steps.filter(step=4).first()
        if step4 and not cls.check_user_permission(user, step4.access, step4.roles):
            raise PermissionDenied("You don't have permission to approve down payment")
        
        # Mark the DP approval step as completed
        if step4 and not step4.is_completed:
            step4.complete(user)
        
        # Move to the completed status
        purchase_order.status = 'confirm_ready_dates'
        purchase_order.save()
        
        return purchase_order
    
    @classmethod
    def reject_down_payment(cls, purchase_order, user=None):
        """
        Reject the down payment and reset for resubmission
        """
        # Get the fourth step and check permissions (same as approve)
        step4 = purchase_order.route_steps.filter(step=4).first()
        if step4 and not cls.check_user_permission(user, step4.access, step4.roles):
            raise PermissionDenied("You don't have permission to reject down payment")
        
        # Reset the DP step (step 3)
        step3 = purchase_order.route_steps.filter(step=3).first()
        if step3 and step3.is_completed:
            step3.is_completed = False
            step3.completed_at = None
            step3.completed_by = None
            step3.save()
        
        # Update PO status back to for_dp
        purchase_order.status = 'for_dp'
        purchase_order.save()
        
        return purchase_order

    @classmethod
    def confirm_ready_dates(cls, purchase_order, data, user=None):
        # Get the fifth step and check permissions
        step5 = purchase_order.route_steps.filter(step=5).first()
        if step5 and not cls.check_user_permission(user, step5.access, step5.roles):
            raise PermissionDenied("You don't have permission to confirm ready dates")
        
        # Process items and validate
        items_data = data.get('items', [])
        
        # Validate total quantities for each original item
        original_items = {}
        for item_data in items_data:
            item_id = item_data.get('item_id')
            quantity = Decimal(str(item_data.get('quantity', 0)))
            
            if item_id not in original_items:
                try:
                    original_item = purchase_order.items.get(id=item_id)
                    original_items[item_id] = {
                        'original': original_item,
                        'total_split_quantity': quantity
                    }
                except PurchaseOrderItem.DoesNotExist:
                    raise ValidationError(f"Item with ID {item_id} does not exist in this purchase order")
            else:
                original_items[item_id]['total_split_quantity'] += quantity
        
        # Check if total quantities match the original items
        for item_id, item_info in original_items.items():
            original_quantity = item_info['original'].quantity
            split_quantity = item_info['total_split_quantity']
            
            if split_quantity != original_quantity:
                raise ValidationError(
                    f"Total quantity for item {item_id} must equal the original quantity. "
                    f"Original: {original_quantity}, Submitted: {split_quantity}"
                )
        
        # Process items by ready date
        items_by_date = {}
        for item_data in items_data:
            item_id = item_data.get('item_id')
            ready_date_str = item_data.get('ready_date')
            quantity = Decimal(str(item_data.get('quantity', 0)))
            
            if not ready_date_str:
                raise ValidationError("Ready date is required for all items")
            
            try:
                ready_date = datetime.strptime(ready_date_str, '%Y-%m-%d').date()
            except ValueError:
                raise ValidationError(f"Invalid date format for {ready_date_str}. Use YYYY-MM-DD")
            
            if ready_date not in items_by_date:
                items_by_date[ready_date] = []
            
            items_by_date[ready_date].append({
                'item_id': item_id,
                'quantity': quantity
            })
        
        # Check if we have at most 3 ready dates
        if len(items_by_date) > 3:
            raise ValidationError("A maximum of 3 different ready dates is allowed")
        
        # Clear previous ready dates
        for item in purchase_order.items.all():
            if hasattr(item, 'batch_number'):
                item.batch_number = None
            item.ready_date = None
            item.save()
        
        # Sort dates and assign batch numbers
        sorted_dates = sorted(items_by_date.keys())
        for batch_number, ready_date in enumerate(sorted_dates, 1):
            # Process items for this batch/ready date
            for item_data in items_by_date[ready_date]:
                original_item = original_items[item_data['item_id']]['original']
                quantity = item_data['quantity']
                
                # If this is the only split for this item, update the original
                if len([i for i in items_data if i['item_id'] == item_data['item_id']]) == 1:
                    original_item.ready_date = ready_date
                    original_item.batch_number = batch_number
                    original_item.save()
                else:
                    # Check if this is for an existing split
                    existing_split = purchase_order.items.filter(
                        inventory=original_item.inventory,
                        ready_date=ready_date
                    ).exclude(id=original_item.id).first()
                    
                    if existing_split:
                        # Update existing split
                        existing_split.quantity = quantity
                        existing_split.batch_number = batch_number
                        existing_split.save()
                    else:
                        # Create a new split item
                        PurchaseOrderItem.objects.create(
                            purchase_order=purchase_order,
                            inventory=original_item.inventory,
                            external_description=original_item.external_description,
                            unit=original_item.unit,
                            quantity=quantity,
                            list_price=original_item.list_price,
                            discount_type=original_item.discount_type,
                            discount_value=original_item.discount_value,
                            ready_date=ready_date,
                            batch_number=batch_number,
                            notes=f"Split from item #{original_item.id}"
                        )
                        
                        # Update the original item quantity if it hasn't been assigned a ready date yet
                        if original_item.ready_date is None:
                            remaining_quantity = original_item.quantity - quantity
                            original_item.quantity = remaining_quantity
                            original_item.save()
        
        # Create workflow steps for each batch/ready date
        cls._create_ready_date_workflow_steps(purchase_order, len(sorted_dates))
        
        # Mark the current step as completed
        if step5 and not step5.is_completed:
            step5.complete(user)
        
        # Update PO status to reflect ready dates confirmed
        purchase_order.status = 'packing_list_1'
        purchase_order.save()
        
        return purchase_order

    @classmethod
    def _create_ready_date_workflow_steps(cls, purchase_order, num_batches):
        """
        Create workflow steps for each ready date batch
        """
        # Get the highest existing step number
        last_step = purchase_order.route_steps.order_by('-step').first()
        next_step_number = last_step.step + 1 if last_step else 6  # Start at 6 if no steps exist
        
        # Define the step types
        step_types = [
            ("Packing List", True, "purchase_orders", ['admin', 'supervisor', 'user']),
            ("Approve for Import", True, "purchase_orders", ['admin', 'supervisor']),
            ("Payment", True, "purchase_orders", ['admin', 'supervisor', 'user']),
            ("Invoice", True, "purchase_orders", ['admin', 'supervisor', 'user'])
        ]
        
        # Create steps for each batch
        for batch_number in range(1, num_batches + 1):
            for step_name, is_required, access, roles in step_types:
                # Simplified task naming: "Packing List 1", "Approve for Import 1", etc.
                task = f"{step_name} {batch_number}"
                
                PurchaseOrderRoute.objects.create(
                    purchase_order=purchase_order,
                    step=next_step_number,
                    task=task,
                    is_required=is_required,
                    is_completed=False,
                    access=access,
                    roles=roles
                )
                
                next_step_number += 1
        
        # Add a final PO Summary step after all batch-specific steps
        PurchaseOrderRoute.objects.create(
            purchase_order=purchase_order,
            step=next_step_number,
            task="PO Summary",
            is_required=True,
            is_completed=False,
            access="purchase_orders",
            roles=['admin', 'supervisor', 'user']
        )
        
        return purchase_order

    @classmethod
    def submit_packing_list(cls, purchase_order, batch_number, data, user=None):
        """Submit a packing list for a specific batch"""
        # Find the corresponding route step
        step = purchase_order.route_steps.filter(
            task=f"Packing List {batch_number}"
        ).first()
        
        if not step:
            raise ValidationError(f"No 'Packing List {batch_number}' step found for this purchase order")
        
        if step.is_completed:
            raise ValidationError(f"Packing list for batch {batch_number} has already been submitted")
        
        if not cls.check_user_permission(user, step.access, step.roles):
            raise PermissionDenied("You don't have permission to submit packing lists")
        
        # Validate required fields
        required_fields = ['total_weight', 'total_packages', 'total_volume']
        for field in required_fields:
            if field not in data or not data[field]:
                raise ValidationError(f"{field} is required")
        
        # Validate document
        if 'document' not in data:
            raise ValidationError("Packing list document is required")
        
        # Create the packing list
        try:
            packing_list = PackingList.objects.create(
                purchase_order=purchase_order,
                batch_number=batch_number,
                total_weight=Decimal(str(data['total_weight'])),
                total_packages=int(data['total_packages']),
                total_volume=Decimal(str(data['total_volume'])),
                document=data['document']
            )
        except Exception as e:
            raise
        
        # Mark the step as completed
        try:
            step.complete(user)
            
            # Update the purchase order status to the next step
            purchase_order.status = f"approve_for_import_{batch_number}"
            purchase_order.save(update_fields=['status'])
        except Exception as e:
            raise
        
        return packing_list

    @classmethod
    def approve_import(cls, purchase_order, batch_number, approve, user=None):
        """Approve or reject the import based on packing list"""
        # Find the corresponding route step
        step = purchase_order.route_steps.filter(
            task=f"Approve for Import {batch_number}"
        ).first()
        
        if not step:
            raise ValidationError(f"No 'Approve for Import {batch_number}' step found for this purchase order")
        
        if step.is_completed:
            raise ValidationError(f"Import approval for batch {batch_number} has already been completed")
        
        if not cls.check_user_permission(user, step.access, step.roles):
            raise PermissionDenied("You don't have permission to approve imports")
        
        # Get the packing list
        try:
            packing_list = PackingList.objects.get(purchase_order=purchase_order, batch_number=batch_number)
        except PackingList.DoesNotExist:
            raise ValidationError(f"No packing list found for batch {batch_number}")
        
        # Approve or reject the packing list
        if approve:
            packing_list.approved = True
            packing_list.save()
            # Mark the step as completed
            step.complete(user)
            
            # Update the purchase order status to the next step
            purchase_order.status = f"payment_{batch_number}"
            purchase_order.save(update_fields=['status'])
        else:
            # Delete the packing list if rejected
            packing_list.delete()
            
            # Find the packing list step and mark it as not completed
            packing_list_step = purchase_order.route_steps.filter(
                task=f"Packing List {batch_number}"
            ).first()
            
            if packing_list_step:
                packing_list_step.is_completed = False
                packing_list_step.completed_at = None
                packing_list_step.completed_by = None
                packing_list_step.save()
                
                # Reset the status back to packing list for this batch
                purchase_order.status = f"packing_list_{batch_number}"
                purchase_order.save(update_fields=['status'])
        
        return packing_list if approve else None

    @classmethod
    def submit_payment(cls, purchase_order, batch_number, data, user=None):
        """Submit payment document for a specific batch"""
        # Find the corresponding route step
        step = purchase_order.route_steps.filter(
            task=f"Payment {batch_number}"
        ).first()
        
        if not step:
            raise ValidationError(f"No 'Payment {batch_number}' step found for this purchase order")
        
        if step.is_completed:
            raise ValidationError(f"Payment for batch {batch_number} has already been submitted")
        
        if not cls.check_user_permission(user, step.access, step.roles):
            raise PermissionDenied("You don't have permission to submit payments")
        
        # Validate document
        if 'document' not in data:
            raise ValidationError("Payment document is required")
        
        # Create the payment document
        payment = PaymentDocument.objects.create(
            purchase_order=purchase_order,
            batch_number=batch_number,
            document=data['document']
        )
        
        # Mark the step as completed
        step.complete(user)
        
        # Update the purchase order status to the next step
        purchase_order.status = f"invoice_{batch_number}"
        purchase_order.save(update_fields=['status'])
        
        return payment

    @classmethod
    def submit_invoice(cls, purchase_order, batch_number, data, user=None):
        """Submit invoice document for a specific batch"""
        # Find the corresponding route step
        step = purchase_order.route_steps.filter(
            task=f"Invoice {batch_number}"
        ).first()
        
        if not step:
            raise ValidationError(f"No 'Invoice {batch_number}' step found for this purchase order")
        
        if step.is_completed:
            raise ValidationError(f"Invoice for batch {batch_number} has already been submitted")
        
        if not cls.check_user_permission(user, step.access, step.roles):
            raise PermissionDenied("You don't have permission to submit invoices")
        
        # Validate document
        if 'document' not in data:
            raise ValidationError("Invoice document is required")
        
        # Create the invoice document
        invoice = InvoiceDocument.objects.create(
            purchase_order=purchase_order,
            batch_number=batch_number,
            document=data['document']
        )
        
        # Mark the step as completed
        step.complete(user)
        
        # Determine if this is the last batch or if we need to move to the next batch
        total_batches = cls.get_total_batches(purchase_order)
        
        if batch_number < total_batches:
            # Move to the next batch
            next_batch = batch_number + 1
            purchase_order.status = f"packing_list_{next_batch}"
        else:
            # This was the last batch, automatically complete the PO
            # First, mark the PO Summary step as completed (if it exists)
            po_summary_step = purchase_order.route_steps.filter(task="PO Summary").first()
            if po_summary_step and not po_summary_step.is_completed:
                po_summary_step.complete(user)
            
            # Mark the purchase order as completed
            purchase_order.status = "completed"
        
        purchase_order.save(update_fields=['status'])
        
        return invoice
        
    @classmethod
    def get_total_batches(cls, purchase_order):
        """Helper method to determine the total number of batches for this PO"""
        # Look for the highest batch number in the route steps
        batch_steps = purchase_order.route_steps.filter(task__startswith="Packing List ")
        
        if not batch_steps.exists():
            return 0
            
        batch_numbers = []
        for step in batch_steps:
            # Extract batch number from task name
            try:
                batch_number = int(step.task.replace("Packing List ", ""))
                batch_numbers.append(batch_number)
            except (ValueError, TypeError):
                continue
                
        return max(batch_numbers) if batch_numbers else 0