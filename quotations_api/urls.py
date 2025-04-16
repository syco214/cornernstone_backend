from django.urls import path
from .views import QuotationView, CustomerListView

urlpatterns = [
    path('', QuotationView.as_view(), name='quotations'),
    path('<int:pk>/', QuotationView.as_view(), name='quotation-detail'),
    path('customers/', CustomerListView.as_view(), name='customer-list'),
]