# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for license information.
# --------------------------------------------------------------------------------------------

from azure.cli.core import AzCommandsLoader
from azure.cli.core.profiles import register_resource_type

from azext_logicapp._help import helps  # pylint: disable=unused-import
from azext_logicapp._client_factory import CUSTOM_MGMT_APPSERVICE


class LogicappCommandsLoader(AzCommandsLoader):

    def __init__(self, cli_ctx=None):
        from azure.cli.core.commands import CliCommandType
        register_resource_type('latest', CUSTOM_MGMT_APPSERVICE, '2020-12-01')

        logicapp_custom = CliCommandType(
            operations_tmpl='azext_logicapp.custom#{}')
        super(LogicappCommandsLoader, self).__init__(cli_ctx=cli_ctx,
                                            custom_command_type=logicapp_custom,
                                            resource_type=CUSTOM_MGMT_APPSERVICE)

    def load_command_table(self, args):
        from azext_logicapp.commands import load_command_table
        load_command_table(self, args)
        return self.command_table

    def load_arguments(self, command):
        from azext_logicapp._params import load_arguments
        load_arguments(self, command)


COMMAND_LOADER_CLS = LogicappCommandsLoader
