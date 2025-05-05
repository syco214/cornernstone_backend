# inventory_api/urls.py

from django.urls import path
from .views import (
    InventoryView, 
    InventoryGeneralView, 
    InventoryDescriptionView, 
    InventoryTemplateView, 
    InventoryUploadView,
    SupplierListView,
)

urlpatterns = [
    path('', InventoryView.as_view(), name='inventory-list'),
    path('<int:pk>/', InventoryView.as_view(), name='inventory-detail'),
    path('general/', InventoryGeneralView.as_view(), name='inventory-general-create'),
    path('<int:pk>/general/', InventoryGeneralView.as_view(), name='inventory-general-update'),
    path('<int:pk>/description/', InventoryDescriptionView.as_view(), name='inventory-description-update'),
    path('download-template/', InventoryTemplateView.as_view(), name='inventory-download-template'),
    path('upload/', InventoryUploadView.as_view(), name='inventory-upload'),
    path('suppliers/', SupplierListView.as_view(), name='supplier-list'),
]