from django.db import models
from django.contrib.auth.models import AbstractUser
from django.contrib.postgres.fields import ArrayField

# Define access options as simple constants
USER_ACCESS_OPTIONS = [
    'inventory',
    'quotations',
    'sales_orders',
    'importation',
    'warehouse',
    'delivery',
    'payment',
    'customers',
    'sampling',
]

# Define role options as simple constants
USER_ROLE_OPTIONS = [
    'admin',
    'user',
]

class CustomUser(AbstractUser):
    
    email = models.EmailField('email address')
    first_name = models.CharField('first name', max_length=150)
    last_name = models.CharField('last name', max_length=150)
    role = models.CharField(
        max_length=20,
        choices=[(role, role.capitalize()) for role in USER_ROLE_OPTIONS],
        default='user'
    )
    user_access = ArrayField(
        models.CharField(
            max_length=20, 
            choices=[(access, access.capitalize()) for access in USER_ACCESS_OPTIONS]
        ),
        blank=True,
        default=list
    )
    
    class Meta:
        verbose_name = 'user'
        verbose_name_plural = 'users'
        ordering = ['first_name', 'last_name']
    
    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.username})"

class Brand(models.Model):
    name = models.CharField(max_length=100, unique=True)
    made_in = models.TextField(blank=True, null=True)
    show_made_in = models.BooleanField(default=True)
    remarks = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'brand'
        verbose_name_plural = 'brands'
        ordering = ['name']

    def __str__(self):
        return self.name