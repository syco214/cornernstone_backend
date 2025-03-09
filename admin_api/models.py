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
    'supervisor'
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

class Category(models.Model):
    name = models.CharField(max_length=100)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='children')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'category'
        verbose_name_plural = 'categories'
        ordering = ['name']
        unique_together = [['name', 'parent']]

    def __str__(self):
        if self.parent:
            return f"{self.parent} > {self.name}"
        return self.name
    
    @property
    def level(self):
        level = 0
        parent = self.parent
        while parent:
            level += 1
            parent = parent.parent
        return level
    
    @property
    def full_path(self):
        if not self.parent:
            return self.name
        return f"{self.parent.full_path} > {self.name}"
    
class Warehouse(models.Model):
    name = models.CharField(max_length=100)
    address = models.TextField()
    city = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        unique_together = [['name', 'city']]

    def __str__(self):
        return f"{self.name} ({self.city})"

class Shelf(models.Model):
    number = models.CharField(max_length=50)
    info = models.CharField(max_length=255)
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, related_name='shelves')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['number']
        unique_together = [['number', 'warehouse']]
        verbose_name_plural = 'shelves'

    def __str__(self):
        return f"{self.warehouse.name} > Shelf #{self.number} ({self.info})"