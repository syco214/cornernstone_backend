from django.urls import path
from .views import PurchaseOrderView

app_name = 'purchase_order_api'

urlpatterns = [
    path('', PurchaseOrderView.as_view(), name='purchase-order-list'),
    path('<int:pk>/', PurchaseOrderView.as_view(), name='purchase-order-detail'),
]