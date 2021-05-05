# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for license information.
# --------------------------------------------------------------------------------------------

# pylint: disable=line-too-long, protected-access

from binascii import hexlify
from os import urandom
from knack.util import CLIError
from knack.log import get_logger
from msrestazure.tools import is_valid_resource_id, parse_resource_id
from azure.cli.core.commands import LongRunningOperation
from azure.cli.command_modules.appservice.custom import (
    show_webapp,
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
    list_consumption_locations,
    set_functionapp,
    update_functionapp,
    enable_zip_deploy_functionapp
)
from ._constants import (FUNCTIONS_STACKS_API_KEYS, FUNCTIONS_NO_V2_REGIONS)
from ._client_factory import web_client_factory

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
