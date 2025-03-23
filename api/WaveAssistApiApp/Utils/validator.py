from ..models import *
import WaveAssistApiApp.Utils.utils as utils
import re
import django_celery_beat.models as celery_models
import pytz

def validate_user_and_project(request, access_level_gte=1):
    uid = request.POST.get('uid', '')
    try:
        user_object = User.objects.get(uid=uid)
    except:
        return False, 'User not found', None, None

    project_key = request.POST.get('project_key', '')
    try:
        project_object = Project.objects.get(project_key=project_key)
    except:
        return False, 'Project not found', None, None

    if not utils.does_user_have_access_to_project(user_object, project_object, access_gte=access_level_gte):
        return False, 'You do not have access to this project', None, None

    return True, '', user_object, project_object


def validate_crontab_fields(minute, hour, day_of_month, month_of_year, day_of_week, timezone):
    cron_regex = re.compile(r'^(\*|([0-5]?\d)(-[0-5]?\d)?(\/[0-5]?\d)?(,[0-5]?\d(-[0-5]?\d)?(\/[0-5]?\d)?)*)$')
    fields = {
        'minute': minute,
        'hour': hour,
        'day_of_month': day_of_month,
        'month_of_year': month_of_year,
        'day_of_week': day_of_week,
    }

    for field_name, field_value in fields.items():
        if not cron_regex.match(field_value):
            return False, f'Invalid value for {field_name}: {field_value}'

    # Validate timezone
    if timezone not in pytz.all_timezones:
        return False, f'Invalid timezone: {timezone}'

    return True, 'Valid'

def validate_and_get_intervals(request, project_object, is_starting_node='0', schedule_type='none'):
    ##Intervals and Crontabs
    is_starting_node = bool(int(request.POST.get('is_starting_node', is_starting_node)))
    run_after_nodes_csv = request.POST.get('run_after_nodes_csv', '') ##Only needed if not starting node
    schedule_type = request.POST.get('schedule_type', schedule_type).lower()
    interval_object = None
    crontab_object = None
    run_after_nodes_array = []

    if is_starting_node:
        ##Validate all below params are available in request
        required_params = []
        if schedule_type == 'interval':
            required_params = ['interval_every', 'interval_type']
        if schedule_type == 'crontab':
            required_params = ['crontab_minutes', 'crontab_hours', 'crontab_days_of_month',
                                       'crontab_months_of_year', 'crontab_days_of_week', 'crontab_timezone']
        missing_params = [param for param in required_params if not request.POST.get(param, '')]
        if missing_params:
            return False, 'All schedule params are required: ' + str(required_params), None, None, None

        ##Schedule Params:


        if schedule_type not in dict(SCHEDULE_TYPE_CHOICES):
            return False, 'Schedule type not valid, choose from: ' + str(list(dict(SCHEDULE_TYPE_CHOICES).keys())), None, None, None

        if schedule_type == 'interval':
            interval_every = int(request.POST.get('interval_every', '1'))
            interval_type = request.POST.get('interval_type', 'seconds').lower()

            ##Create django celery beat interval object
            ##Check if interval_type in celery_models.PERIOD_CHOICES
            if interval_type not in dict(celery_models.PERIOD_CHOICES):
                return False, 'Interval type not valid, choose from: ' + str(list(dict(celery_models.PERIOD_CHOICES).keys())), None, None, None

            if interval_every < 1:
                return False, 'Interval should be greater than 0', None, None, None
            try:
                interval_object,created = celery_models.IntervalSchedule.objects.get_or_create(every=interval_every, period=interval_type)
                interval_object.save()
            except Exception as e:
                return False, 'Something went wrong while creating/fetching interval object: ' + str(e), None, None, None

        elif schedule_type == 'crontab':
            crontab_minutes = request.POST.get('crontab_minutes', '*')
            crontab_hours = request.POST.get('crontab_hours', '*')
            crontab_days_of_month = request.POST.get('crontab_days_of_month', '*')
            crontab_months_of_year = request.POST.get('crontab_months_of_year', '*')
            crontab_days_of_week = request.POST.get('crontab_days_of_week', '*')
            crontab_timezone = request.POST.get('crontab_timezone', 'UTC')

            ##Create django celery beat crontab object
            is_valid, message = validate_crontab_fields(crontab_minutes, crontab_hours, crontab_days_of_month, crontab_months_of_year, crontab_days_of_week, crontab_timezone)
            if not is_valid:
                return False, message, None, None, None
            try:
                crontab_object,created = celery_models.CrontabSchedule.objects.get_or_create(
                    minute=crontab_minutes,
                    hour=crontab_hours,
                    day_of_month=crontab_days_of_month,
                    month_of_year=crontab_months_of_year,
                    day_of_week=crontab_days_of_week,
                    timezone=crontab_timezone
                )
                crontab_object.save()
            except:
                return False, 'Something went wrong while creating crontab object', None, None, None

    else:
        run_after_nodes_keys = run_after_nodes_csv.split(',')
        for run_after_node_key in run_after_nodes_keys:
            try:
                run_after_node_object = Nodes.objects.get(node_key=run_after_node_key, project_object=project_object)
                run_after_nodes_array.append(run_after_node_object)
            except:
                return False, 'Invalid/Not found run after nodes. Please provide valid run after nodes as this is not a starting node', None, None, None
        if len(run_after_nodes_array) == 0:
            return False, 'Invalid/Not found run after nodes. Please provide valid run after nodes as this is not a starting node', None, None, None

    return True, '', interval_object, crontab_object, run_after_nodes_array



def validate_user_and_data_run(request, access_level_gte=1):
    uid = utils.get_param(request, 'uid')
    try:
        user_object = User.objects.get(uid=uid)
    except:
        return False, 'User not found', None, None

    data_run_key = utils.get_param(request, 'data_run_key') or utils.get_param(request, 'environment_key')
    try:
        data_run_object = DataRuns.objects.get(data_run_key=data_run_key, is_enabled=True)
    except:
        return False, 'Environment/DataRun not found', None, None

    if not utils.does_user_have_access_to_data_run(user_object, data_run_object, access_type=access_level_gte):
        return False, 'You do not have access to this Environment/DataRun', None, None

    return True, '', user_object, data_run_object




def validate_user_and_deployment(request, access_level_gte=1):
    uid = request.POST.get('uid', '')
    try:
        user_object = User.objects.get(uid=uid)
    except:
        return False, 'User not found', None, None


    deployment_key = request.POST.get('deployment_key', '')
    try:
        deployment_object = Deployments.objects.get(key=deployment_key)
    except:
        return False, 'Deployment not found', None, None

    data_run_object = deployment_object.data_run_object

    if not utils.does_user_have_access_to_data_run(user_object, data_run_object, access_type=access_level_gte):
        return False, 'You do not have access to this deployment as you do not have access to the data run', None, None

    return True, '', user_object, deployment_object



def does_user_have_access_to_data_run_key(user_object, data_run_key, access_level_gte=1):
    if data_run_key == "":
        return False, 'Data Run Key not found', None
    try:
        data_run_object = DataRuns.objects.get(id=data_run_key)
    except:
        return False, 'Data Run not found', None

    success = utils.does_user_have_access_to_data_run(user_object, data_run_object, access_gte=access_level_gte)
    if success:
        return success, '', data_run_object
    else:
        return success, 'You do not have access to this data run', None


def does_user_have_access_to_project_key(user_object, project_key):
    project_object = Project.objects.get(project_key=project_key)
    return utils.does_user_have_access_to_project(user_object, project_object)


def validate_keys_csv(keys_csv, project_object):
    keys_array = keys_csv.split(",")
    key_object_array = []
    for key in keys_array:
        key = key.strip()
        if key == "":
            continue
        try:
            data_key_object = DataKey.objects.get(key=key, project_object=project_object)
            key_object_array.append(data_key_object)
        except:
            return False, f'Data Key {key} not found in project', None
    return True, '', key_object_array