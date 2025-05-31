from django.urls import path
from .views import (
    PurchaseOrderView, 
    PurchaseOrderWorkflowView, 
    PurchaseOrderRouteView,
    PurchaseOrderItemsTemplateView,
    PurchaseOrderItemsUploadView,
)

app_name = 'purchase_order_api'

urlpatterns = [
    path('', PurchaseOrderView.as_view(), name='purchase-order-list'),
    path('<int:pk>/', PurchaseOrderView.as_view(), name='purchase-order-detail'),
    path('<int:pk>/workflow/submit_for_approval/', PurchaseOrderWorkflowView.as_view(), {'action': 'submit_for_approval'}, name='po-submit-for-approval'),
    path('<int:pk>/workflow/approve_po/', PurchaseOrderWorkflowView.as_view(), {'action': 'approve_po'}, name='po-approve'),
    path('<int:pk>/workflow/reject_po/', PurchaseOrderWorkflowView.as_view(), {'action': 'reject_po'}, name='po-reject'),
    path('<int:pk>/workflow/submit_dp/', PurchaseOrderWorkflowView.as_view(), {'action': 'submit_dp'}, name='po-submit-dp'),
    path('<int:pk>/workflow/approve_dp/', PurchaseOrderWorkflowView.as_view(), {'action': 'approve_dp'}, name='po-approve-dp'),
    path('<int:pk>/workflow/reject_dp/', PurchaseOrderWorkflowView.as_view(), {'action': 'reject_dp'}, name='po-reject-dp'),
    path('<int:pk>/workflow/confirm_ready_dates/', PurchaseOrderWorkflowView.as_view(), {'action': 'confirm_ready_dates'}, name='po-confirm-ready-dates'), 
    path('<int:po_id>/route/', PurchaseOrderRouteView.as_view(), name='purchase-order-route'),
    
    # Template download and upload
    path('<int:pk>/items/template/', PurchaseOrderItemsTemplateView.as_view(), name='purchase-order-items-template'),
    path('<int:pk>/items/upload/', PurchaseOrderItemsUploadView.as_view(), name='purchase-order-items-upload'),
]

# Batch specific workflow URLs - examples for each batch number
for batch_number in range(1, 4):  # Assuming max 3 batches
    urlpatterns += [
        path(f'<int:pk>/workflow/submit_packing_list_{batch_number}/',
             PurchaseOrderWorkflowView.as_view(),
             {'action': f'submit_packing_list_{batch_number}'},
             name=f'submit-packing-list-{batch_number}'),
        
        path(f'<int:pk>/workflow/approve_import_{batch_number}/',
             PurchaseOrderWorkflowView.as_view(),
             {'action': f'approve_import_{batch_number}'},
             name=f'approve-import-{batch_number}'),
        
        path(f'<int:pk>/workflow/submit_payment_{batch_number}/',
             PurchaseOrderWorkflowView.as_view(),
             {'action': f'submit_payment_{batch_number}'},
             name=f'submit-payment-{batch_number}'),
        
        path(f'<int:pk>/workflow/submit_invoice_{batch_number}/',
             PurchaseOrderWorkflowView.as_view(),
             {'action': f'submit_invoice_{batch_number}'},
             name=f'submit-invoice-{batch_number}'),
    ]