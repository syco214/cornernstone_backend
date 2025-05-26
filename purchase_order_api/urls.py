from django.urls import path
from .views import PurchaseOrderView, PurchaseOrderWorkflowView

app_name = 'purchase_order_api'

urlpatterns = [
    path('', PurchaseOrderView.as_view(), name='purchase-order-list'),
    path('<int:pk>/', PurchaseOrderView.as_view(), name='purchase-order-detail'),
    path('<int:pk>/submit_for_approval/', PurchaseOrderWorkflowView.as_view(), {'action': 'submit_for_approval'}, name='po-submit-for-approval'),
    path('<int:pk>/approve/', PurchaseOrderWorkflowView.as_view(), {'action': 'approve'}, name='po-approve'),
    path('<int:pk>/reject/', PurchaseOrderWorkflowView.as_view(), {'action': 'reject'}, name='po-reject'),
    path('<int:pk>/complete_step/', PurchaseOrderWorkflowView.as_view(), {'action': 'complete_step'}, name='po-complete-step'),
]