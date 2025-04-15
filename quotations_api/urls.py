from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# Create a router and register our viewsets with it.
router = DefaultRouter()
router.register(r'quotations', views.QuotationViewSet, basename='quotation')
router.register(r'terms-conditions', views.TermsConditionViewSet, basename='termscondition')
router.register(r'payment-terms', views.PaymentTermViewSet, basename='paymentterm')
router.register(r'delivery-options', views.DeliveryOptionViewSet, basename='deliveryoption')
router.register(r'other-options', views.OtherOptionViewSet, basename='otheroption')
router.register(r'customers', views.CustomerViewSet)

# The API URLs are now determined automatically by the router.
urlpatterns = [
    path('', include(router.urls)),
]