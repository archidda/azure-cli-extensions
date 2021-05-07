# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for license information.
# --------------------------------------------------------------------------------------------

# pylint: disable=line-too-long, protected-access

import time
import json

from binascii import hexlify
from os import urandom

from knack.util import CLIError
from knack.log import get_logger

from msrestazure.tools import is_valid_resource_id, parse_resource_id

from azure.cli.core.commands import LongRunningOperation
from azure.cli.core.util import get_az_user_agent
from azure.cli.command_modules.appservice.custom import (
    start_webapp,
    stop_webapp,
    restart_webapp,
    parse_docker_image_name,
    delete_function_app,
    _load_runtime_stacks_json_functionapp,
    _get_matching_runtime_json_functionapp,
    _get_matching_runtime_version_json_functionapp,
    _get_supported_runtime_versions_functionapp,
    _validate_and_get_connection_string,
    _format_fx_version,
    _convert_camel_to_snake_case,
    _get_extension_version_functionapp,
    is_plan_elastic_premium,
    get_app_insights_key,
    list_consumption_locations,
    _set_remote_or_local_git,
    try_create_application_insights,
    update_app_settings,
    update_container_settings_functionapp,
    assign_identity,
    perform_onedeploy,
    set_functionapp,
    update_functionapp,
    _rename_server_farm_props,
    is_plan_consumption,
    upload_zip_to_storage,
    _get_site_credential,
    get_app_settings,
    _build_app_settings_output,
    _generic_settings_operation,
    _configure_default_logging)
from azure.cli.command_modules.appservice.utils import retryable_method

from ._constants import (FUNCTIONS_STACKS_API_KEYS, FUNCTIONS_NO_V2_REGIONS, KUBE_APP_KIND)
from ._client_factory import web_client_factory
from ._util import _generic_site_operation

logger = get_logger(__name__)

def create_logicapp(cmd, resource_group_name, name, storage_account, plan=None,
                    os_type=None, functions_version=None, runtime=None, runtime_version=None,
                    consumption_plan_location=None, app_insights=None, app_insights_key=None,
                    disable_app_insights=None, deployment_source_url=None,
                    deployment_source_branch='master', deployment_local_git=None,
                    docker_registry_server_password=None, docker_registry_server_user=None,
                    deployment_container_image_name=None, tags=None, assign_identities=None,
                    role='Contributor', scope=None):
    # pylint: disable=too-many-statements, too-many-branches
    # if functions_version is None:
    #     logger.warning("No functions version specified so defaulting to 2. In the future, specifying a version will "
    #                    "be required. To create a 2.x function you would pass in the flag `--functions-version 2`")
    functions_version = '3'
    if deployment_source_url and deployment_local_git:
        raise CLIError('usage error: --deployment-source-url <url> | --deployment-local-git')
    if bool(plan) == bool(consumption_plan_location):
        raise CLIError("usage error: --plan NAME_OR_ID | --consumption-plan-location LOCATION")
    SiteConfig, Site, NameValuePair = cmd.get_models('SiteConfig', 'Site', 'NameValuePair')
    docker_registry_server_url = parse_docker_image_name(deployment_container_image_name)
    disable_app_insights = (disable_app_insights == "true")
    site_config = SiteConfig(app_settings=[])
    functionapp_def = Site(location=None, site_config=site_config, tags=tags)
    KEYS = FUNCTIONS_STACKS_API_KEYS()
    client = web_client_factory(cmd.cli_ctx)
    plan_info = None
    if runtime is not None:
        runtime = runtime.lower()
    if consumption_plan_location:
        locations = list_consumption_locations(cmd)
        location = next((loc for loc in locations if loc['name'].lower() == consumption_plan_location.lower()), None)
        if location is None:
            raise CLIError("Location is invalid. Use: az logicapp list-consumption-locations")
        functionapp_def.location = consumption_plan_location
        functionapp_def.kind = 'functionapp,workflowapp'
        # if os_type is None, the os type is windows
        is_linux = os_type and os_type.lower() == 'linux'
    else:  # apps with SKU based plan
        if is_valid_resource_id(plan):
            parse_result = parse_resource_id(plan)
            plan_info = client.app_service_plans.get(parse_result['resource_group'], parse_result['name'])
        else:
            plan_info = client.app_service_plans.get(resource_group_name, plan)
        if not plan_info:
            raise CLIError("The plan '{}' doesn't exist".format(plan))
        location = plan_info.location
        is_linux = plan_info.reserved
        functionapp_def.server_farm_id = plan
        functionapp_def.location = location
    if functions_version == '2' and functionapp_def.location in FUNCTIONS_NO_V2_REGIONS:
        raise CLIError("2.x functions are not supported in this region. To create a 3.x function, "
                       "pass in the flag '--functions-version 3'")

    if is_linux and not runtime and (consumption_plan_location or not deployment_container_image_name):
        raise CLIError(
            "usage error: --runtime RUNTIME required for linux functions apps without custom image.")

    runtime_stacks_json = _load_runtime_stacks_json_functionapp(is_linux)

    if runtime is None and runtime_version is not None:
        raise CLIError('Must specify --runtime to use --runtime-version')

    # get the matching runtime stack object
    runtime_json = _get_matching_runtime_json_functionapp(runtime_stacks_json, runtime if runtime else 'dotnet')
    if not runtime_json:
        # no matching runtime for os
        os_string = "linux" if is_linux else "windows"
        supported_runtimes = list(map(lambda x: x[KEYS.NAME], runtime_stacks_json))
        raise CLIError("usage error: Currently supported runtimes (--runtime) in {} function apps are: {}."
                       .format(os_string, ', '.join(supported_runtimes)))

    runtime_version_json = _get_matching_runtime_version_json_functionapp(runtime_json,
                                                                          functions_version,
                                                                          runtime_version,
                                                                          is_linux)
    if not runtime_version_json:
        supported_runtime_versions = list(map(lambda x: x[KEYS.DISPLAY_VERSION],
                                              _get_supported_runtime_versions_functionapp(runtime_json,
                                                                                          functions_version)))
        if runtime_version:
            if runtime == 'dotnet':
                raise CLIError('--runtime-version is not supported for --runtime dotnet. Dotnet version is determined '
                               'by --functions-version. Dotnet version {} is not supported by Functions version {}.'
                               .format(runtime_version, functions_version))
            raise CLIError('--runtime-version {} is not supported for the selected --runtime {} and '
                           '--functions-version {}. Supported versions are: {}.'
                           .format(runtime_version,
                                   runtime,
                                   functions_version,
                                   ', '.join(supported_runtime_versions)))

        # if runtime_version was not specified, then that runtime is not supported for that functions version
        raise CLIError('no supported --runtime-version found for the selected --runtime {} and '
                       '--functions-version {}'
                       .format(runtime, functions_version))

    if runtime == 'dotnet':
        logger.warning('--runtime-version is not supported for --runtime dotnet. Dotnet version is determined by '
                       '--functions-version. Dotnet version will be %s for this function app.',
                       runtime_version_json[KEYS.DISPLAY_VERSION])

    if runtime_version_json[KEYS.IS_DEPRECATED]:
        logger.warning('%s version %s has been deprecated. In the future, this version will be unavailable. '
                       'Please update your command to use a more recent version. For a list of supported '
                       '--runtime-versions, run \"az functionapp create -h\"',
                       runtime_json[KEYS.PROPERTIES][KEYS.DISPLAY], runtime_version_json[KEYS.DISPLAY_VERSION])

    site_config_json = runtime_version_json[KEYS.SITE_CONFIG_DICT]
    app_settings_json = runtime_version_json[KEYS.APP_SETTINGS_DICT]

    con_string = _validate_and_get_connection_string(cmd.cli_ctx, resource_group_name, storage_account)

    if is_linux:
        functionapp_def.kind = 'functionapp,workflowapp,linux,kubernetes' # kubernetes is needed for Lima
        functionapp_def.reserved = True
        is_consumption = consumption_plan_location is not None
        if not is_consumption:
            site_config.app_settings.append(NameValuePair(name='MACHINEKEY_DecryptionKey',
                                                          value=str(hexlify(urandom(32)).decode()).upper()))
            if deployment_container_image_name:
                functionapp_def.kind = 'functionapp,workflowapp,linux,container,kubernetes' # kubernetes is needed for Lima
                site_config.app_settings.append(NameValuePair(name='DOCKER_CUSTOM_IMAGE_NAME',
                                                              value=deployment_container_image_name))
                site_config.app_settings.append(NameValuePair(name='FUNCTION_APP_EDIT_MODE', value='readOnly'))
                site_config.app_settings.append(NameValuePair(name='WEBSITES_ENABLE_APP_SERVICE_STORAGE', value='false'))
                site_config.linux_fx_version = _format_fx_version(deployment_container_image_name)

                # clear all runtime specific configs and settings
                site_config_json = {KEYS.USE_32_BIT_WORKER_PROC: False}
                app_settings_json = {}

                # ensure that app insights is created if not disabled
                runtime_version_json[KEYS.APPLICATION_INSIGHTS] = True
            else:
                site_config.app_settings.append(NameValuePair(name='WEBSITES_ENABLE_APP_SERVICE_STORAGE',
                                                              value='true'))
    else:
        functionapp_def.kind = 'functionapp,workflowapp'

    # set site configs
    for prop, value in site_config_json.items():
        snake_case_prop = _convert_camel_to_snake_case(prop)
        setattr(site_config, snake_case_prop, value)

    # temporary workaround for dotnet-isolated linux consumption apps
    if is_linux and consumption_plan_location is not None and runtime == 'dotnet-isolated':
        site_config.linux_fx_version = ''

    # adding app settings
    for app_setting, value in app_settings_json.items():
        site_config.app_settings.append(NameValuePair(name=app_setting, value=value))

    site_config.app_settings.append(NameValuePair(name='FUNCTIONS_EXTENSION_VERSION',
                                                  value=_get_extension_version_functionapp(functions_version)))
    site_config.app_settings.append(NameValuePair(name='AzureWebJobsStorage', value=con_string))

    site_config.app_settings.append(NameValuePair(name='AzureFunctionsJobHost__extensionBundle__id',
                                                  value="Microsoft.Azure.Functions.ExtensionBundle.Workflows"))
    site_config.app_settings.append(NameValuePair(name='AzureFunctionsJobHost__extensionBundle__version', value="[1.*, 2.0.0)"))
    site_config.app_settings.append(NameValuePair(name='APP_KIND', value="workflowApp"))
    site_config.app_settings.append(NameValuePair(name='FUNCTIONS_V2_COMPATIBILITY_MODE', value="true"))

    # If plan is not consumption or elastic premium, we need to set always on
    if consumption_plan_location is None and not is_plan_elastic_premium(cmd, plan_info):
        site_config.always_on = True

    # If plan is elastic premium or windows consumption, we need these app settings
    is_windows_consumption = consumption_plan_location is not None and not is_linux
    if is_plan_elastic_premium(cmd, plan_info) or is_windows_consumption:
        site_config.app_settings.append(NameValuePair(name='WEBSITE_CONTENTAZUREFILECONNECTIONSTRING',
                                                      value=con_string))
        site_config.app_settings.append(NameValuePair(name='WEBSITE_CONTENTSHARE', value=name.lower()))

    create_app_insights = False

    if app_insights_key is not None:
        site_config.app_settings.append(NameValuePair(name='APPINSIGHTS_INSTRUMENTATIONKEY',
                                                      value=app_insights_key))
    elif app_insights is not None:
        instrumentation_key = get_app_insights_key(cmd.cli_ctx, resource_group_name, app_insights)
        site_config.app_settings.append(NameValuePair(name='APPINSIGHTS_INSTRUMENTATIONKEY',
                                                      value=instrumentation_key))
    elif disable_app_insights or not runtime_version_json[KEYS.APPLICATION_INSIGHTS]:
        # set up dashboard if no app insights
        site_config.app_settings.append(NameValuePair(name='AzureWebJobsDashboard', value=con_string))
    elif not disable_app_insights and runtime_version_json[KEYS.APPLICATION_INSIGHTS]:
        create_app_insights = True

    poller = client.web_apps.create_or_update(resource_group_name, name, functionapp_def)
    functionapp = LongRunningOperation(cmd.cli_ctx)(poller)

    if consumption_plan_location and is_linux:
        logger.warning("Your Linux function app '%s', that uses a consumption plan has been successfully "
                       "created but is not active until content is published using "
                       "Azure Portal or the Functions Core Tools.", name)
    else:
        _set_remote_or_local_git(cmd, functionapp, resource_group_name, name, deployment_source_url,
                                 deployment_source_branch, deployment_local_git)

    if create_app_insights:
        try:
            try_create_application_insights(cmd, functionapp)
        except Exception:  # pylint: disable=broad-except
            logger.warning('Error while trying to create and configure an Application Insights for the Function App. '
                           'Please use the Azure Portal to create and configure the Application Insights, if needed.')
            update_app_settings(cmd, functionapp.resource_group, functionapp.name,
                                ['AzureWebJobsDashboard={}'.format(con_string)])

    if deployment_container_image_name:
        update_container_settings_functionapp(cmd, resource_group_name, name, docker_registry_server_url,
                                              deployment_container_image_name, docker_registry_server_user,
                                              docker_registry_server_password)

    if assign_identities is not None:
        identity = assign_identity(cmd, resource_group_name, name, assign_identities,
                                   role, None, scope)
        functionapp.identity = identity

    return functionapp


def show_webapp(cmd, resource_group_name, name, slot=None, app_instance=None):
    webapp = app_instance
    if not app_instance:  # when the routine is invoked as a help method, not through commands
        webapp = _generic_site_operation(cmd.cli_ctx, resource_group_name, name, 'get', slot)
    if not webapp:
        raise CLIError("'{}' app doesn't exist".format(name))
    webapp.site_config = _generic_site_operation(cmd.cli_ctx, resource_group_name, name, 'get_configuration', slot)
    _rename_server_farm_props(webapp)

    # TODO: get rid of this conditional once the api's are implemented for kubapps
    if KUBE_APP_KIND.lower() not in webapp.kind.lower():
        _fill_ftp_publishing_url(cmd, webapp, resource_group_name, name, slot)

    return webapp


def _fill_ftp_publishing_url(cmd, webapp, resource_group_name, name, slot=None):
    profiles = list_publish_profiles(cmd, resource_group_name, name, slot)
    try:
        url = next((p['publishUrl'] for p in profiles if p['publishMethod'] == 'FTP'), None)
        setattr(webapp, 'ftpPublishingUrl', url)
    except StopIteration as e:
        pass

    return webapp


def list_publish_profiles(cmd, resource_group_name, name, slot=None, xml=False):
    import xmltodict

    content = _generic_site_operation(cmd.cli_ctx, resource_group_name, name,
                                      'list_publishing_profile_xml_with_secrets', slot)
    full_xml = ''
    for f in content:
        full_xml += f.decode()

    if not xml:
        profiles = xmltodict.parse(full_xml, xml_attribs=True)['publishData']['publishProfile']
        converted = []

        if not isinstance(profiles, list):
            profiles = [profiles]

        for profile in profiles:
            new = {}
            for key in profile:
                # strip the leading '@' xmltodict put in for attributes
                new[key.lstrip('@')] = profile[key]
            converted.append(new)
        return converted
    cmd.cli_ctx.invocation.data['output'] = 'tsv'
    return full_xml


def enable_zip_deploy_functionapp(cmd, resource_group_name, name, src, build_remote=False, timeout=None, slot=None):
    client = web_client_factory(cmd.cli_ctx)
    app = client.web_apps.get(resource_group_name, name)
    if app is None:
        raise CLIError('The function app \'{}\' was not found in resource group \'{}\'. '
                       'Please make sure these values are correct.'.format(name, resource_group_name))
    parse_plan_id = parse_resource_id(app.server_farm_id)
    plan_info = None
    retry_delay = 10  # seconds
    # We need to retry getting the plan because sometimes if the plan is created as part of function app,
    # it can take a couple of tries before it gets the plan
    for _ in range(5):
        plan_info = client.app_service_plans.get(parse_plan_id['resource_group'],
                                                 parse_plan_id['name'])
        if plan_info is not None:
            break
        time.sleep(retry_delay)

    if build_remote and not app.reserved:
        raise CLIError('Remote build is only available on Linux function apps')

    is_consumption = is_plan_consumption(cmd, plan_info)
    if (not build_remote) and is_consumption and app.reserved:
        return upload_zip_to_storage(cmd, resource_group_name, name, src, slot)
    if build_remote:
        add_remote_build_app_settings(cmd, resource_group_name, name, slot)
    else:
        remove_remote_build_app_settings(cmd, resource_group_name, name, slot)

    return enable_zip_deploy(cmd, resource_group_name, name, src, timeout, slot)


def enable_zip_deploy(cmd, resource_group_name, name, src, timeout=None, slot=None, is_kube=False):
    logger.warning("Getting scm site credentials for zip deployment")
    user_name, password = _get_site_credential(cmd.cli_ctx, resource_group_name, name, slot)
    # Wait for a few seconds for envoy changes to propogate, for a kube app
    if is_kube:
        time.sleep(7)
    try:
        scm_url = _get_scm_url(cmd, resource_group_name, name, slot)
    except ValueError:
        raise CLIError('Failed to fetch scm url for function app')

    zip_url = scm_url + '/api/zipdeploy?isAsync=true'
    deployment_status_url = scm_url + '/api/deployments/latest'

    import urllib3
    authorization = urllib3.util.make_headers(basic_auth='{0}:{1}'.format(user_name, password))
    headers = authorization
    headers['Content-Type'] = 'application/octet-stream'
    headers['Cache-Control'] = 'no-cache'
    headers['User-Agent'] = get_az_user_agent()

    import requests
    import os
    from azure.cli.core.util import should_disable_connection_verify
    # Read file content
    with open(os.path.realpath(os.path.expanduser(src)), 'rb') as fs:
        zip_content = fs.read()
        logger.warning("Starting zip deployment. This operation can take a while to complete ...")
        res = requests.post(zip_url, data=zip_content, headers=headers, verify=not should_disable_connection_verify())
        logger.warning("Deployment endpoint responded with status code %d", res.status_code)

        if is_kube and res.status_code != 202 and res.status_code != 409:
            logger.warning('Something went wrong. It may take a few seconds for a new deployment to reflect on kube cluster. Retrying deployment...')
            time.sleep(10)   # retry in a moment
            res = requests.post(zip_url, data=zip_content, headers=headers, verify=not should_disable_connection_verify())
            logger.warning("Deployment endpoint responded with status code %d", res.status_code)

    # check if there's an ongoing process
    if res.status_code == 409:
        raise CLIError("There may be an ongoing deployment or your app setting has WEBSITE_RUN_FROM_PACKAGE. "
                       "Please track your deployment in {} and ensure the WEBSITE_RUN_FROM_PACKAGE app setting "
                       "is removed.".format(deployment_status_url))


    # check the status of async deployment
    response = _check_zip_deployment_status(cmd, resource_group_name, name, deployment_status_url,
                                            authorization, timeout)
    return response


def _check_zip_deployment_status(cmd, rg_name, name, deployment_status_url, authorization, timeout=None):
    import requests
    from azure.cli.core.util import should_disable_connection_verify
    total_trials = (int(timeout) // 2) if timeout else 450
    num_trials = 0
    while num_trials < total_trials:
        time.sleep(2)
        response = requests.get(deployment_status_url, headers=authorization,
                                verify=not should_disable_connection_verify())
        try:
            res_dict = response.json()
        except json.decoder.JSONDecodeError:
            logger.warning("Deployment status endpoint %s returns malformed data. Retrying...", deployment_status_url)
            res_dict = {}
        finally:
            num_trials = num_trials + 1

        if res_dict.get('status', 0) == 3:
            _configure_default_logging(cmd, rg_name, name)
            raise CLIError("""Zip deployment failed. {}. Please run the command az webapp log tail
                           -n {} -g {}""".format(res_dict, name, rg_name))
        if res_dict.get('status', 0) == 4:
            break
        if 'progress' in res_dict:
            logger.info(res_dict['progress'])  # show only in debug mode, customers seem to find this confusing
    # if the deployment is taking longer than expected
    if res_dict.get('status', 0) != 4:
        _configure_default_logging(cmd, rg_name, name)
        raise CLIError("""Timeout reached by the command, however, the deployment operation
                       is still on-going. Navigate to your scm site to check the deployment status""")
    return res_dict


def add_remote_build_app_settings(cmd, resource_group_name, name, slot):
    settings = get_app_settings(cmd, resource_group_name, name, slot)
    scm_do_build_during_deployment = None
    website_run_from_package = None
    enable_oryx_build = None

    app_settings_should_not_have = []
    app_settings_should_contain = {}

    for keyval in settings:
        value = keyval['value'].lower()
        if keyval['name'] == 'SCM_DO_BUILD_DURING_DEPLOYMENT':
            scm_do_build_during_deployment = value in ('true', '1')
        if keyval['name'] == 'WEBSITE_RUN_FROM_PACKAGE':
            website_run_from_package = value
        if keyval['name'] == 'ENABLE_ORYX_BUILD':
            enable_oryx_build = value

    if scm_do_build_during_deployment is not True:
        logger.warning("Setting SCM_DO_BUILD_DURING_DEPLOYMENT to true")
        update_app_settings(cmd, resource_group_name, name, [
            "SCM_DO_BUILD_DURING_DEPLOYMENT=true"
        ], slot)
        app_settings_should_contain['SCM_DO_BUILD_DURING_DEPLOYMENT'] = 'true'

    if website_run_from_package:
        logger.warning("Removing WEBSITE_RUN_FROM_PACKAGE app setting")
        delete_app_settings(cmd, resource_group_name, name, [
            "WEBSITE_RUN_FROM_PACKAGE"
        ], slot)
        app_settings_should_not_have.append('WEBSITE_RUN_FROM_PACKAGE')

    if enable_oryx_build:
        logger.warning("Removing ENABLE_ORYX_BUILD app setting")
        delete_app_settings(cmd, resource_group_name, name, [
            "ENABLE_ORYX_BUILD"
        ], slot)
        app_settings_should_not_have.append('ENABLE_ORYX_BUILD')

    # Wait for scm site to get the latest app settings
    if app_settings_should_not_have or app_settings_should_contain:
        logger.warning("Waiting SCM site to be updated with the latest app settings")
        scm_is_up_to_date = False
        retries = 10
        while not scm_is_up_to_date and retries >= 0:
            scm_is_up_to_date = validate_app_settings_in_scm(
                cmd, resource_group_name, name, slot,
                should_contain=app_settings_should_contain,
                should_not_have=app_settings_should_not_have)
            retries -= 1
            time.sleep(5)

        if retries < 0:
            logger.warning("App settings may not be propagated to the SCM site.")


def remove_remote_build_app_settings(cmd, resource_group_name, name, slot):
    settings = get_app_settings(cmd, resource_group_name, name, slot)
    scm_do_build_during_deployment = None

    app_settings_should_contain = {}

    for keyval in settings:
        value = keyval['value'].lower()
        if keyval['name'] == 'SCM_DO_BUILD_DURING_DEPLOYMENT':
            scm_do_build_during_deployment = value in ('true', '1')

    if scm_do_build_during_deployment is not False:
        logger.warning("Setting SCM_DO_BUILD_DURING_DEPLOYMENT to false")
        update_app_settings(cmd, resource_group_name, name, [
            "SCM_DO_BUILD_DURING_DEPLOYMENT=false"
        ], slot)
        app_settings_should_contain['SCM_DO_BUILD_DURING_DEPLOYMENT'] = 'false'

    # Wait for scm site to get the latest app settings
    if app_settings_should_contain:
        logger.warning("Waiting SCM site to be updated with the latest app settings")
        scm_is_up_to_date = False
        retries = 10
        while not scm_is_up_to_date and retries >= 0:
            scm_is_up_to_date = validate_app_settings_in_scm(
                cmd, resource_group_name, name, slot,
                should_contain=app_settings_should_contain)
            retries -= 1
            time.sleep(5)

        if retries < 0:
            logger.warning("App settings may not be propagated to the SCM site")


def _get_scm_url(cmd, resource_group_name, name, slot=None):
    from azure.mgmt.web.models import HostType
    webapp = show_webapp(cmd, resource_group_name, name, slot=slot)
    for host in webapp.host_name_ssl_states or []:
        if host.host_type == HostType.repository:
            return "https://{}".format(host.name)

    # this should not happen, but throw anyway
    raise ValueError('Failed to retrieve Scm Uri')


# Check if the app setting is propagated to the Kudu site correctly by calling api/settings endpoint
# should_have [] is a list of app settings which are expected to be set
# should_not_have [] is a list of app settings which are expected to be absent
# should_contain {} is a dictionary of app settings which are expected to be set with precise values
# Return True if validation succeeded
def validate_app_settings_in_scm(cmd, resource_group_name, name, slot=None,
                                 should_have=None, should_not_have=None, should_contain=None):
    scm_settings = _get_app_settings_from_scm(cmd, resource_group_name, name, slot)
    scm_setting_keys = set(scm_settings.keys())

    if should_have and not set(should_have).issubset(scm_setting_keys):
        return False

    if should_not_have and set(should_not_have).intersection(scm_setting_keys):
        return False

    temp_setting = scm_settings.copy()
    temp_setting.update(should_contain or {})
    if temp_setting != scm_settings:
        return False

    return True


@retryable_method(3, 5)
def _get_app_settings_from_scm(cmd, resource_group_name, name, slot=None):
    scm_url = _get_scm_url(cmd, resource_group_name, name, slot)
    settings_url = '{}/api/settings'.format(scm_url)
    username, password = _get_site_credential(cmd.cli_ctx, resource_group_name, name, slot)
    headers = {
        'Content-Type': 'application/octet-stream',
        'Cache-Control': 'no-cache',
        'User-Agent': get_az_user_agent()
    }

    import requests
    response = requests.get(settings_url, headers=headers, auth=(username, password), timeout=3)

    return response.json() or {}


def delete_app_settings(cmd, resource_group_name, name, setting_names, slot=None):
    app_settings = _generic_site_operation(cmd.cli_ctx, resource_group_name, name, 'list_application_settings', slot)
    client = web_client_factory(cmd.cli_ctx)

    slot_cfg_names = client.web_apps.list_slot_configuration_names(resource_group_name, name)
    is_slot_settings = False
    for setting_name in setting_names:
        app_settings.properties.pop(setting_name, None)
        if slot_cfg_names.app_setting_names and setting_name in slot_cfg_names.app_setting_names:
            slot_cfg_names.app_setting_names.remove(setting_name)
            is_slot_settings = True

    if is_slot_settings:
        client.web_apps.update_slot_configuration_names(resource_group_name, name, slot_cfg_names)

    result = _generic_settings_operation(cmd.cli_ctx, resource_group_name, name,
                                         'update_application_settings',
                                         app_settings.properties, slot, client)

    return _build_app_settings_output(result.properties, slot_cfg_names.app_setting_names)
