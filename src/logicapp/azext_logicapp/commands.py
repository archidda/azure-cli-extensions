# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for license information.
# --------------------------------------------------------------------------------------------

# pylint: disable=line-too-long

from azure.cli.core.commands import CliCommandType

from azure.cli.command_modules.appservice.commands import (
    transform_web_output,
    ex_handler_factory,
    update_function_ex_handler_factory
)

from ._validators import validate_onedeploy_params, rebrand_validate_update_params

from ._client_factory import cf_webapps


def load_command_table(self, _):

    appservice_custom = CliCommandType(operations_tmpl='azure.cli.command_modules.appservice.custom#{}')
    webapp_sdk = CliCommandType(
        operations_tmpl='azure.mgmt.web.operations#WebAppsOperations.{}',
        client_factory=cf_webapps
    )

    with self.command_group('logicapp') as g:
        g.custom_command('create', 'create_logicapp', exception_handler=ex_handler_factory())
        g.custom_show_command('show', 'show_webapp', table_transformer=transform_web_output)
        g.custom_command('delete', 'delete_function_app')
        g.custom_command('stop', 'stop_webapp')
        g.custom_command('start', 'start_webapp')
        g.custom_command('restart', 'restart_webapp')
        g.custom_command('list-consumption-locations', 'list_consumption_locations')
        # g.custom_command('identity assign', 'assign_identity')
        # g.custom_show_command('identity show', 'show_identity')
        # g.custom_command('identity remove', 'remove_identity')
        g.custom_command('deploy', 'perform_onedeploy', validator=validate_onedeploy_params, is_preview=True)
        g.generic_update_command('update', setter_name='set_functionapp', exception_handler=update_function_ex_handler_factory( ),
                                  custom_func_name='update_functionapp', setter_type=appservice_custom, command_type=webapp_sdk,
                                  validator=rebrand_validate_update_params)

    with self.command_group('logicapp deployment source') as g:
        g.custom_command('config-zip', 'enable_zip_deploy_functionapp')
        
