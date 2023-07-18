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
from WaveAssistApiApp import engine_views
from django.views.decorators.csrf import csrf_exempt


urlpatterns = [
    path('admin/', admin.site.urls),
    path("", csrf_exempt(views.index), name="index"),
    path("load_all_projects/", csrf_exempt(engine_views.load_all_projects), name="load_all_projects"),
    path("load_node_data/", csrf_exempt(engine_views.load_node_data), name="load_node_data"),
    path("download_project_file_data/", csrf_exempt(engine_views.download_project_file_data), name="download_project_file_data"),
    path("update_project_refresh_status/", csrf_exempt(engine_views.update_project_refresh_status), name="update_project_refresh_status"),
    path("set_data_for_key/", csrf_exempt(views.set_data_for_key), name="set_data_for_key"),
    path("load_project_data/", csrf_exempt(views.load_project_data), name="load_project_data"),
    path("login/", csrf_exempt(views.login), name="login"),
]

