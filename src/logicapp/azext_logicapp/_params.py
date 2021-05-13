# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for license information.
# --------------------------------------------------------------------------------------------

# pylint: disable=line-too-long, too-many-statements
from knack.arguments import CLIArgumentType
from azure.cli.core.commands.parameters import (tags_type, get_three_state_flag, get_resource_name_completion_list, get_enum_type)

from ._constants import (FUNCTIONS_VERSIONS, FUNCTIONS_VERSION_TO_SUPPORTED_RUNTIME_VERSIONS,
                         LINUX_RUNTIMES, WINDOWS_RUNTIMES, OS_TYPES)

def load_arguments(self, _):
    # pylint: disable=too-many-statements
    # pylint: disable=line-too-long
    name_arg_type = CLIArgumentType(
        options_list=['--name', '-n'], metavar='NAME')

    # combine all runtime versions for all functions versions
    functionapp_runtime_to_version = {}
    for functions_version in FUNCTIONS_VERSION_TO_SUPPORTED_RUNTIME_VERSIONS.values():
        for runtime, val in functions_version.items():
            # dotnet version is not configurable, so leave out of help menu
            if runtime != 'dotnet':
                functionapp_runtime_to_version[runtime] = functionapp_runtime_to_version.get(
                    runtime, set()).union(val)

    functionapp_runtime_to_version_texts = []
    for runtime, runtime_versions in functionapp_runtime_to_version.items():
        runtime_versions_list = list(runtime_versions)
        runtime_versions_list.sort(key=float)
        functionapp_runtime_to_version_texts.append(
            runtime + ' -> [' + ', '.join(runtime_versions_list) + ']')

    with self.argument_context('logicapp') as c:
        c.ignore('app_instance')
        c.argument('name', arg_type=name_arg_type, id_part='name',
                   help='name of the function app')
        c.argument('slot', options_list=['--slot', '-s'],
                   help="the name of the slot. Default to the productions slot if not specified")

    with self.argument_context('logicapp create') as c:
        c.argument('plan', options_list=['--plan', '-p'], configured_default='appserviceplan',
                   completer=get_resource_name_completion_list(
                       'Microsoft.Web/serverFarms'),
                   help="name or resource id of the function app service plan. Use 'appservice plan create' to get one")
        c.argument('new_app_name', options_list=['--name', '-n'], help='name of the new logic app')
        c.argument('custom_location', options_list=['--custom-location'], help="Name or ID of the custom location")
        c.argument('storage_account', options_list=['--storage-account', '-s'],
                   help='Provide a string value of a Storage Account in the provided Resource Group. Or Resource ID of a Storage Account in a different Resource Group')
        c.argument('consumption_plan_location', options_list=['--consumption-plan-location', '-c'],
                   help="Geographic location where logic App will be hosted. Use `az logicapp list-consumption-locations` to view available locations.")
        # c.argument('functions_version', help='The functions app version.',
        #            arg_type=get_enum_type(FUNCTIONS_VERSIONS))
        # c.argument('runtime', help='The runtime stack.', arg_type=get_enum_type(
        #     set(LINUX_RUNTIMES).union(set(WINDOWS_RUNTIMES))))
        # c.argument('runtime_version', help='The version of the functions runtime stack. '
        #                                    'Allowed values for each --runtime are: ' + ', '.join(functionapp_runtime_to_version_texts))
        c.argument('os_type', arg_type=get_enum_type(OS_TYPES),
                   help="Set the OS type for the app to be created.")
        c.argument('app_insights_key',
                   help="Instrumentation key of App Insights to be added.")
        c.argument('app_insights', help="Name of the existing App Insights project to be added to the Logic app. Must be in the same resource group.")
        c.argument('disable_app_insights', arg_type=get_three_state_flag(return_label=True),
                   help="Disable creating application insights resource during functionapp create. No logs will be available.")
        c.argument('docker_registry_server_user',
                   help='The container registry server username.')
        c.argument('docker_registry_server_password',
                   help='The container registry server password. Required for private registries.')

    for scope in ['webapp', 'logicapp']:
        with self.argument_context(scope + ' create') as c:
            c.argument('deployment_container_image_name', options_list=[
                       '--deployment-container-image-name', '-i'], help='Linux only. Container image name from Docker Hub, e.g. publisher/image-name:tag')
            c.argument('deployment_local_git', action='store_true', options_list=[
                       '--deployment-local-git', '-l'], help='enable local git')
            c.argument('deployment_zip', options_list=[
                       '--deployment-zip', '-z'], help='perform deployment using zip file')
            c.argument('deployment_source_url', options_list=[
                       '--deployment-source-url', '-u'], help='Git repository URL to link with manual integration')
            c.argument('deployment_source_branch', options_list=[
                       '--deployment-source-branch', '-b'], help='the branch to deploy')
            c.argument('min_worker_count', help='Minimum number of workers to be allocated.',
                       type=int, default=None, is_preview=True)
            c.argument('max_worker_count', help='Maximum number of workers to be allocated.',
                       type=int, default=None, is_preview=True)
            c.argument('tags', arg_type=tags_type)

    with self.argument_context('logicapp update') as c:
        c.argument('name', options_list=['--name', '-n'], help='Name of the logicapp to update.')
