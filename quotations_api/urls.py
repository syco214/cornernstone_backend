from django.urls import path
from .views import QuotationView

app_name = 'quotations_api'

urlpatterns = [
    path('', QuotationView.as_view(), name='quotation-list'),  # For listing all quotations
    path('<int:pk>/', QuotationView.as_view(), name='quotation-detail'),
]