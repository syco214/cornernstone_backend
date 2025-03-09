from django.urls import path
from .views import LoginView, UserView, SidebarView, BrandView, CategoryView, WarehouseView

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
]