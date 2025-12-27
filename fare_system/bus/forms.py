from django import forms
from .models import Bus


class BusForm(forms.ModelForm):
    class Meta:
        model = Bus
        fields = ["bus_number", "route_name", "current_stop"]
