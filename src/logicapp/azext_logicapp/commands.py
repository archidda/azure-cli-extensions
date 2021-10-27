# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for license information.
# --------------------------------------------------------------------------------------------

# pylint: disable=line-too-long

from azure.cli.core.commands import CliCommandType
from azure.cli.core.util import empty_on_404

from azure.cli.command_modules.appservice.commands import (
    transform_web_output,
    ex_handler_factory,
    update_function_ex_handler_factory
)

from ._validators import validate_onedeploy_params

from ._client_factory import cf_webapps

def load_command_table(self, _):
    appservice_custom = CliCommandType(operations_tmpl='azure.cli.command_modules.appservice.custom#{}')
    webapp_sdk = CliCommandType(
        operations_tmpl='azure.mgmt.web.operations#WebAppsOperations.{}',
        client_factory=cf_webapps
    )


    with self.command_group('logicapp config appsettings') as g:
        g.custom_command('list', 'get_app_settings_new', exception_handler=empty_on_404)
        g.custom_command('set', 'update_logicapp_app_settings', exception_handler=ex_handler_factory())
        g.custom_command('delete', 'delete_logicapp_app_settings', exception_handler=ex_handler_factory())

    with self.command_group('logicapp') as g:
        g.custom_command('create', 'create_logicapp', exception_handler=ex_handler_factory())
        g.custom_show_command('show', 'show_logicapp', table_transformer=transform_web_output)
        g.custom_command('delete', 'delete_logicapp')
        g.custom_command('stop', 'stop_logicapp')
        g.custom_command('start', 'start_logicapp')
        g.custom_command('restart', 'restart_logicapp')
        g.custom_command('scale', 'scale_webapp')
        g.custom_command('list-consumption-locations', 'list_consumption_locations_logicapp')
        g.custom_command('upgrade', 'upgrade_logicapp')

    with self.command_group('logicapp deployment source') as g:
        g.custom_command('config-zip', 'enable_zip_deploy_functionapp')
