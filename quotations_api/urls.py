from django.urls import path
from .views import QuotationView, CustomerListView, PaymentView

urlpatterns = [
    path('', QuotationView.as_view(), name='quotation-list'),
    path('<int:pk>/', QuotationView.as_view(), name='quotation-detail'),
    path('customers/', CustomerListView.as_view(), name='customer-list'),
    path('payments/', PaymentView.as_view(), name='payment-list'),
    path('payments/<int:pk>/', PaymentView.as_view(), name='payment-detail'),
]