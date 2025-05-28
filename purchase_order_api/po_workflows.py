from django.utils import timezone
from django.core.exceptions import PermissionDenied
from .models import PurchaseOrder, PurchaseOrderRoute, PurchaseOrderDownPayment

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
        purchase_order.status = 'completed'
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