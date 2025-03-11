from django.urls import path
from .views import LoginView, UserView, SidebarView, BrandView, CategoryView, WarehouseView, SupplierView, ParentCompanyView, CustomerView, BrokerView, ForwarderView

urlpatterns = [
    path('login/', LoginView.as_view(), name='login'),
    path('sidebar/', SidebarView.as_view(), name='sidebar'),
    path('users/', UserView.as_view(), name='users'),
    path('users/<int:pk>/', UserView.as_view(), name='user-detail'),
    path('brands/', BrandView.as_view(), name='brands'),
    path('brands/<int:pk>/', BrandView.as_view(), name='brand-detail'),
    path('categories/', CategoryView.as_view(), name='categories'),
    path('categories/<int:pk>/', CategoryView.as_view(), name='category-detail'),
    path('warehouses/', WarehouseView.as_view(), name='warehouses'),
    path('warehouses/<int:pk>/', WarehouseView.as_view(), name='warehouse-detail'),
    path('suppliers/', SupplierView.as_view(), name='suppliers'),
    path('suppliers/<int:pk>/', SupplierView.as_view(), name='supplier-detail'),
    path('parent-companies/', ParentCompanyView.as_view(), name='parent-companies'),
    path('parent-companies/<int:pk>/', ParentCompanyView.as_view(), name='parent-company-detail'),
    path('customers/', CustomerView.as_view(), name='customers'),
    path('customers/<int:pk>/', CustomerView.as_view(), name='customer-detail'),
    path('brokers/', BrokerView.as_view(), name='brokers'),
    path('brokers/<int:pk>/', BrokerView.as_view(), name='broker-detail'),
    path('forwarders/', ForwarderView.as_view(), name='forwarders'),
    path('forwarders/<int:pk>/', ForwarderView.as_view(), name='forwarder-detail'),
]