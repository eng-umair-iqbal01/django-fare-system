from django.db import models
from django.contrib.auth.models import User


class Bus(models.Model):
    bus_number = models.CharField(max_length=10, unique=True)
    route_name = models.CharField(max_length=255)
    current_stop = models.CharField(max_length=255, default="Not Assigned")

    def __str__(self):
        return f"Bus {self.bus_number} - {self.route_name} (Stop: {self.current_stop})"


class BusDriver(models.Model):
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="bus_driver"
    )
    full_name = models.CharField(max_length=100)
    bus = models.ForeignKey(
        Bus, on_delete=models.SET_NULL, null=True, blank=True, related_name="drivers"
    )

    def __str__(self):
        return f"{self.full_name} - {self.bus.bus_number if self.bus else 'No Bus Assigned'}"
