from django.urls import path
from .views import QuotationView, CustomerListView, PaymentView, DeliveryView

urlpatterns = [
    path('', QuotationView.as_view(), name='quotation-list'),
    path('<int:pk>/', QuotationView.as_view(), name='quotation-detail'),
    path('customers/', CustomerListView.as_view(), name='customer-list'),
    path('payments/', PaymentView.as_view(), name='payment-list-create'),
    path('payments/<int:pk>/', PaymentView.as_view(), name='payment-detail'),
    path('deliveries/', DeliveryView.as_view(), name='delivery-list-create'),
    path('deliveries/<int:pk>/', DeliveryView.as_view(), name='delivery-detail'),
]