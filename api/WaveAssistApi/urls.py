"""
URL configuration for WaveAssistApi project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from WaveAssistApiApp import views

from django.views.decorators.csrf import csrf_exempt


urlpatterns = [
    path('admin/', admin.site.urls),
    path("load_all_clients/", csrf_exempt(views.load_all_clients), name="load_all_clients"),
    path("load_node_data/", csrf_exempt(views.load_node_data), name="load_node_data"),
    path("load_project_data/", csrf_exempt(views.load_project_data), name="load_project_data"),
]

