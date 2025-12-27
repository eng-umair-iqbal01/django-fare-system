from django.urls import path
from .views import (
    admin_dashboard,
    add_student,
    update_student,
    delete_student,
    add_bus_driver,
    update_bus_driver,
    delete_bus_driver,
    bus_list,
    add_bus,
    update_bus,
    delete_bus,
)

urlpatterns = [
    path("dashboard/", admin_dashboard, name="admin_dashboard"),
    path("add-student/", add_student, name="add_student"),
    path("update-student/<int:student_id>/", update_student, name="update_student"),
    path("delete-student/<int:student_id>/", delete_student, name="delete_student"),
    path("add-bus-driver/", add_bus_driver, name="add_bus_driver"),
    path(
        "update-bus-driver/<int:driver_id>/",
        update_bus_driver,
        name="update_bus_driver",
    ),
    path(
        "delete-bus-driver/<int:driver_id>/",
        delete_bus_driver,
        name="delete_bus_driver",
    ),
    path("buses/", bus_list, name="bus_list"),
    path("buses/add/", add_bus, name="add_bus"),
    path("buses/edit/<int:bus_id>/", update_bus, name="update_bus"),
    path("buses/delete/<int:bus_id>/", delete_bus, name="delete_bus"),
]
