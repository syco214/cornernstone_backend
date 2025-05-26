from django.utils import timezone
from .models import PurchaseOrder, PurchaseOrderRoute

class POWorkflow:
    """
    Handles purchase order workflow operations
    """
    INITIAL_WORKFLOW_STEPS = [
        (1, "Detailed Review", True),
        (2, "PO Approval", True),
        (3, "For DP", True),
        (4, "DP Approval", True),
        (5, "Confirm Ready Date", True),
    ]

    @classmethod
    def initialize_workflow(cls, purchase_order, user=None):
        """
        Initialize the workflow steps for a new purchase order
        """
        # Delete any existing steps if they exist
        purchase_order.route_steps.all().delete()
        
        # Create new steps
        for step_num, task, is_required in cls.INITIAL_WORKFLOW_STEPS:
            PurchaseOrderRoute.objects.create(
                purchase_order=purchase_order,
                step=step_num,
                task=task,
                is_required=is_required
            )
    
    @classmethod
    def submit_for_approval(cls, purchase_order, user=None):
        """
        Submit the purchase order for approval
        """
        # Update the PO status
        purchase_order.status = 'pending_approval'
        purchase_order.save()
        
        # Mark the first step as completed
        step1 = purchase_order.route_steps.filter(step=1).first()
        if step1 and not step1.is_completed:
            step1.complete(user)
        
        return purchase_order
    
    @classmethod
    def approve_po(cls, purchase_order, user=None):
        """
        Approve the purchase order and move to the next workflow stage
        """
        # Update the PO status and approved_by
        purchase_order.status = 'approved'
        purchase_order.approved_by = user
        purchase_order.save()
        
        # Mark the second step as completed
        step2 = purchase_order.route_steps.filter(step=2).first()
        if step2 and not step2.is_completed:
            step2.complete(user)
        
        return purchase_order
    
    @classmethod
    def reject_po(cls, purchase_order, user=None):
        """
        Reject the purchase order
        """
        purchase_order.status = 'rejected'
        purchase_order.save()
        return purchase_order
    
    @classmethod
    def complete_step(cls, purchase_order, step_number, user=None):
        """
        Complete a specific workflow step
        """
        step = purchase_order.route_steps.filter(step=step_number).first()
        if step and not step.is_completed:
            step.complete(user)
            
            # Update PO status based on step completion
            if step_number == 3:  # For DP
                purchase_order.status = 'processing'
                purchase_order.save()
            elif step_number == 4:  # DP Approval
                # No status change, still processing
                pass
            elif step_number == 5:  # Confirm Ready Date
                # This would depend on your business logic
                # Maybe update expected_delivery_date or another field
                pass
        
        return purchase_order