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
from WaveAssistApiApp import dashboard_views, data_views, deployment_views, debug_views, worker_views, template_views

from django.views.decorators.csrf import csrf_exempt
from WaveAssistApiApp import manage_views

urlpatterns = [
    path('admin/', admin.site.urls),

    ##Dashboard URL's
    path("", csrf_exempt(dashboard_views.index), name="index"),
    path("login/", csrf_exempt(dashboard_views.login), name="login"),


    ##Manage URL's
    path("manage/get_started/", csrf_exempt(manage_views.get_started), name="get_started"),

    path("manage/create_user/", csrf_exempt(manage_views.create_user), name="create_user"),
    path("manage/fetch_all_projects/", csrf_exempt(manage_views.fetch_all_projects), name="fetch_all_projects"),
    path("manage/create_project/", csrf_exempt(manage_views.create_project), name="create_project"),

    path("manage/fetch_project_variables/", csrf_exempt(manage_views.fetch_project_variables), name="fetch_project_variables"),
    path("manage/fetch_nodes/", csrf_exempt(manage_views.fetch_nodes), name="fetch_nodes"),
    path("manage/fetch_environments/", csrf_exempt(manage_views.fetch_environments), name="fetch_environments"),
    path("manage/fetch_deployments/", csrf_exempt(manage_views.fetch_deployments), name="fetch_deployments"),

    path("manage/delete_project/", csrf_exempt(manage_views.delete_project), name="delete_project"),
    path("manage/create_data_key/", csrf_exempt(manage_views.create_data_key), name="create_data_key"),
    path("manage/delete_data_key/", csrf_exempt(manage_views.delete_data_key), name="delete_io_data"),
    path("manage/create_node/", csrf_exempt(manage_views.create_node), name="create_node"),
    path("manage/update_node/", csrf_exempt(manage_views.update_node), name="update_node"),
    path("manage/delete_node/", csrf_exempt(manage_views.delete_node), name="delete_node"),
    path("manage/update_code/", csrf_exempt(manage_views.update_code), name="update_code"),
    path("manage/activate_integration/", csrf_exempt(manage_views.activate_integration), name="activate_integration"),
    path("manage/deactivate_integration/", csrf_exempt(manage_views.deactivate_integration), name="deactivate_integration"),
    path("manage/create_dashboard_section/", csrf_exempt(manage_views.create_dashboard_section), name="create_dashboard_section"),
    path("manage/update_dashboard_section/", csrf_exempt(manage_views.update_dashboard_section), name="update_dashboard_section"),
    path("manage/delete_dashboard_section/", csrf_exempt(manage_views.delete_dashboard_section), name="delete_dashboard_section"),
    path("manage/create_data_run/", csrf_exempt(manage_views.create_data_run), name="create_data_run"),
    path("manage/update_data_run/", csrf_exempt(manage_views.update_data_run), name="update_data_run"),
    path("manage/delete_data_run/", csrf_exempt(manage_views.delete_data_run), name="delete_data_run"),

    ##Data URL's
    path("data/upload_data_file/", csrf_exempt(data_views.upload_data_file), name="upload_data_file"),
    path("data/fetch_data_for_key/", csrf_exempt(data_views.fetch_data_for_key), name="fetch_data_for_key"),
    path("data/set_data_for_key/", csrf_exempt(data_views.set_data_for_key), name="set_data_for_key"),

    ##Build URL's
    path("deploy/deploy_project/", csrf_exempt(deployment_views.deploy_project), name="deploy_project"),
    path("deploy/stop_deployment/", csrf_exempt(deployment_views.stop_deployment), name="stop_deployment"),
    path("deploy/run_dag/", csrf_exempt(deployment_views.run_dag), name="run_dag"),
    path("deploy/generate_dag_image/", csrf_exempt(deployment_views.generate_dag_image), name="generate_dag_image"),
    path("deploy/run_code/", csrf_exempt(deployment_views.run_code), name="run_code"),

    ##Debug URL's
    path("debug/fetch_logs/", csrf_exempt(debug_views.fetch_logs), name="fetch_logs"),
    path("debug/fetch_installed_packages/", csrf_exempt(debug_views.fetch_installed_packages), name="fetch_installed_packages"),
    path("debug/uninstall_package/", csrf_exempt(debug_views.uninstall_package), name="uninstall_package"),
    path("debug/install_package/", csrf_exempt(debug_views.install_package), name="install_package"),
    path("debug/reinstall_package/", csrf_exempt(debug_views.reinstall_package), name="reinstall_package"),

    ##Template URL's
    path("template/deploy_template/", csrf_exempt(template_views.deploy_template), name="deploy_template"),


    ##Worker URL's
    path("fetch_config/", csrf_exempt(worker_views.fetch_config), name="fetch_config"),

]



