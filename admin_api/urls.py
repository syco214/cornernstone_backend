from django.urls import path
from .views import LoginView, UserView, SidebarView

urlpatterns = [
    path('login/', LoginView.as_view(), name='login'),
    path('users/', UserView.as_view(), name='users'),
    path('users/<int:pk>/', UserView.as_view(), name='user-detail'),
    path('sidebar/', SidebarView.as_view(), name='sidebar'),
]