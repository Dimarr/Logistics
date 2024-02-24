from django.db import models

class Vehicle(models.Model):
    # Vehicle fields
    make = models.CharField(max_length=24, blank=False)  # Nissan
    model = models.CharField(max_length=24, blank=False)  # GT-R
    year = models.IntegerField(null=False, blank=False)  # 2020
    is_active = models.BooleanField(db_index=True, default=True)


class DeliveryJob(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(blank=True, null=True)
    destination_location = models.CharField(max_length=100)
    delivery_slot = models.DateTimeField(null=True)
    income = models.DecimalField(max_digits=10, decimal_places=2)
    costs = models.DecimalField(max_digits=10, decimal_places=2)
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE, null=True)

