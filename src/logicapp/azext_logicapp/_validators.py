# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for license information.
# --------------------------------------------------------------------------------------------

# pylint: disable=len-as-condition
from knack.util import CLIError
from azure.mgmt.core.tools import parse_resource_id, is_valid_resource_id

from ._constants import (SCALE_VALID_PARAMS)


def validate_onedeploy_params(namespace):
    if namespace.src_path and namespace.src_url:
        raise CLIError('Only one of --src-path and --src-url can be specified')

    if not namespace.src_path and not namespace.src_url:
        raise CLIError('Either of --src-path or --src-url must be specified')

    if namespace.src_url and not namespace.artifact_type:
        raise CLIError(
            'Deployment type is mandatory when deploying from URLs. Use --type')


def validate_app_service(namespace):
    if namespace.app_service and is_valid_resource_id(namespace.app_service):
        namespace.app_service = parse_resource_id(
            namespace.app_service)['name']


def rebrand_validate_update_params(namespace):
    (set, nameValuePairs) = namespace.ordered_arguments[0]
    params = {}
    for index, item in enumerate(nameValuePairs):
        parameterName, parameterValue = item.split('=')[0], item.split('=')[1]
        params[parameterName] = parameterValue
        if parameterName in SCALE_VALID_PARAMS:
            nameValuePairs[index] = SCALE_VALID_PARAMS[parameterName] + \
                '=' + parameterValue
    namespace.ordered_arguments[0] = (set, nameValuePairs)

    # 'minimumElasticInstanceCount' should not be more than 'logicAppScaleLimit'
    if 'minimumElasticInstanceCount' in params and 'logicAppScaleLimit' in params and \
            params['minimumElasticInstanceCount'] > params['logicAppScaleLimit']:
        raise CLIError('The parameter \'minimumElasticInstanceCount\' has an invalid value. Details: The desired \
minimumElasticInstanceCount ({0}) for the logicapp \'{1}\' must be less than or equal to the site\'s configured \
logicappScaleLimit ({2}).'.format(params['minimumElasticInstanceCount'], namespace.name, params['logicAppScaleLimit']))


def validate_applications(namespace):
    if namespace.resource_group_name:
        if isinstance(namespace.application, list):
            if len(namespace.application) == 1:
                if is_valid_resource_id(namespace.application[0]):
                    raise CLIError(
                        "Specify either a full resource id or an application name and resource group.")
            else:
                raise CLIError(
                    "Resource group only allowed with a single application name.")


def validate_storage_account_name_or_id(cmd, namespace):
    if namespace.storage_account_id:
        from msrestazure.tools import resource_id
        from azure.cli.core.commands.client_factory import get_subscription_id
        if not is_valid_resource_id(namespace.storage_account_id):
            namespace.storage_account_id = resource_id(
                subscription=get_subscription_id(cmd.cli_ctx),
                resource_group=namespace.resource_group_name,
                namespace='Microsoft.Storage',
                type='storageAccounts',
                name=namespace.storage_account_id
            )


def validate_log_analytic_workspace_name_or_id(cmd, namespace):
    if namespace.workspace_resource_id:
        from msrestazure.tools import resource_id
        from azure.cli.core.commands.client_factory import get_subscription_id
        if not is_valid_resource_id(namespace.workspace_resource_id):
            namespace.workspace_resource_id = resource_id(
                subscription=get_subscription_id(cmd.cli_ctx),
                resource_group=namespace.resource_group_name,
                namespace='microsoft.OperationalInsights',
                type='workspaces',
                name=namespace.workspace_resource_id
            )
