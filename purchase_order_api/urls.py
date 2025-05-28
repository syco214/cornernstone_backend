from django.urls import path
from .views import PurchaseOrderView, PurchaseOrderWorkflowView, PurchaseOrderRouteView

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
    path('<int:po_id>/route/', PurchaseOrderRouteView.as_view(), name='purchase-order-route'),
]