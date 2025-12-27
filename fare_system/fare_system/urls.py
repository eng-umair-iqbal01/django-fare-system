from django.contrib import admin
from django.urls import path, include
from .views import home

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", home, name="home"),  # Home page
    path("administration/", include("administration.urls")),  # Administration app
    path("bus/", include("bus.urls")),  # Bus app
    path("students/", include("students.urls")),  # Students app
    path("users/", include("users.urls")),  # Users app (for login, user management)
]
