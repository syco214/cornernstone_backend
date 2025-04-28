from django.urls import path
from .views import (
    QuotationView, CustomerListView, PaymentView, DeliveryView, OtherView, 
    CustomerContactListView, QuotationPDFView, QuotationItemsTemplateView, 
    QuotationItemsUploadView, QuotationStatusView, LastQuotedPriceView
)

urlpatterns = [
    path('', QuotationView.as_view(), name='quotation-list'),
    path('<int:pk>/', QuotationView.as_view(), name='quotation-detail'),
    path('<int:pk>/download-items-template/', QuotationItemsTemplateView.as_view(), name='quotation-download-template'),
    path('<int:pk>/upload-items/', QuotationItemsUploadView.as_view(), name='quotation-upload-items'),
    path('customers/', CustomerListView.as_view(), name='customer-list'),
    path('payments/', PaymentView.as_view(), name='payment-list-create'),
    path('payments/<int:pk>/', PaymentView.as_view(), name='payment-detail'),
    path('deliveries/', DeliveryView.as_view(), name='delivery-list-create'),
    path('deliveries/<int:pk>/', DeliveryView.as_view(), name='delivery-detail'),
    path('others/', OtherView.as_view(), name='other-list-create'),
    path('others/<int:pk>/', OtherView.as_view(), name='other-detail'),
    path('customer-contacts/', CustomerContactListView.as_view(), name='customer-contact-list'),
    path('<int:pk>/pdf/', QuotationPDFView.as_view(), name='quotation-pdf'),
    path('<int:pk>/status/', QuotationStatusView.as_view(), name='quotation-status-update'),
    path('last-quoted-prices/', LastQuotedPriceView.as_view(), name='last-quoted-prices'),
]