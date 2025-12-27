from django.contrib.auth.models import User
from django.db import models
from bus.models import Bus, BusDriver  # Import Bus and BusDriver from bus app
from students.models import Student


class AdminProfile(models.Model):
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="admin_profile"
    )
    role = models.CharField(max_length=50, default="Administrator")

    def __str__(self):
        return self.user.username
