from django.contrib import admin
from .models import Bus, BusDriver


@admin.register(Bus)
class BusAdmin(admin.ModelAdmin):
    list_display = ("bus_number", "route_name", "current_stop")
    search_fields = ("bus_number", "route_name")
    list_filter = ("route_name",)


@admin.register(BusDriver)
class BusDriverAdmin(admin.ModelAdmin):
    list_display = ("full_name", "bus")
    search_fields = ("full_name",)
    list_filter = ("bus",)
