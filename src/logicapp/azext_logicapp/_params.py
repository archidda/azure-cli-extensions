# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for license information.
# --------------------------------------------------------------------------------------------

# pylint: disable=line-too-long, too-many-statements
from knack.arguments import CLIArgumentType

from azure.cli.core.commands.parameters import get_datetime_type, tags_type, get_three_state_flag, get_enum_type
from azure.cli.command_modules.monitor.actions import get_period_type
from ._validators import validate_applications, validate_storage_account_name_or_id, validate_log_analytic_workspace_name_or_id, validate_app_service


def load_arguments(self, _):

    with self.argument_context('logicapp update') as c:
        c.argument('name', options_list=['--name', '-n'], help='Name of the logicapp to update.')

    with self.argument_context('monitor app-insights component update-tags') as c:
        c.argument('tags', tags_type)

    with self.argument_context('monitor app-insights component connect-webapp') as c:
        c.argument('app_service', options_list=['--web-app'], help="Name or resource id of the web app.", validator=validate_app_service, id_part=None)
        c.argument('enable_profiler', help='Enable collecting profiling traces that help you see where time is spent in code. Currently it is only supported for .NET/.NET Core Web Apps.', arg_type=get_three_state_flag())
        c.argument('enable_snapshot_debugger', options_list=['--enable-snapshot-debugger', '--enable-debugger'], help='Enable snapshot debugger when an exception is thrown. Currently it is only supported for .NET/.NET Core Web Apps.', arg_type=get_three_state_flag())

    with self.argument_context('monitor app-insights component connect-function') as c:
        c.argument('app_service', options_list=['--function'], help="Name or resource id of the Azure function.", validator=validate_app_service)

    with self.argument_context('monitor app-insights component billing') as c:
        c.argument('stop_sending_notification_when_hitting_cap', options_list=['-s', '--stop'], arg_type=get_three_state_flag(),
                   help='Do not send a notification email when the daily data volume cap is met.')
        c.argument('cap', type=float, help='Daily data volume cap in GB.')

    with self.argument_context('monitor app-insights api-key create') as c:
        c.argument('api_key', help='The name of the API key to create.')
        c.argument('read_properties', nargs='+', options_list=['--read-properties'])
        c.argument('write_properties', nargs='+')

    with self.argument_context('monitor app-insights api-key show') as c:
        c.argument('api_key', help='The name of the API key to fetch.')

    with self.argument_context('monitor app-insights query') as c:
        c.argument('application', validator=validate_applications, options_list=['--apps', '-a'], nargs='+', id_part='name', help='GUID, app name, or fully-qualified Azure resource name of Application Insights component. The application GUID may be acquired from the API Access menu item on any Application Insights resource in the Azure portal. If using an application name, please specify resource group.')
        c.argument('analytics_query', help='Query to execute over Application Insights data.')
        c.argument('start_time', arg_type=get_datetime_type(help='Start-time of time range for which to retrieve data.'))
        c.argument('end_time', arg_type=get_datetime_type(help='End of time range for current operation. Defaults to the current time.'))
        c.argument('offset', help='Filter results based on UTC hour offset.', type=get_period_type(as_timedelta=True))

    with self.argument_context('monitor app-insights component linked-storage') as c:
        c.argument('storage_account_id', options_list=['--storage-account', '-s'], validator=validate_storage_account_name_or_id,
                   help='Name or ID of a linked storage account.')

    with self.argument_context('monitor app-insights component continues-export list') as c:
        c.argument('application', id_part=None)

    with self.argument_context('monitor app-insights component continues-export') as c:
        c.argument('record_types', nargs='+',
                   arg_type=get_enum_type(
                       ['Requests', 'Event', 'Exceptions', 'Metrics', 'PageViews', 'PageViewPerformance', 'Rdd',
                        'PerformanceCounters', 'Availability', 'Messages']),
                   help='The document types to be exported, as comma separated values. Allowed values include \'Requests\', \'Event\', \'Exceptions\', \'Metrics\', \'PageViews\', \'PageViewPerformance\', \'Rdd\', \'PerformanceCounters\', \'Availability\', \'Messages\'.')

    for scope in ['update', 'show', 'delete']:
        with self.argument_context('monitor app-insights component continues-export {}'.format(scope)) as c:
            c.argument('export_id', options_list=['--id'],
                       help='The Continuous Export configuration ID. This is unique within a Application Insights component.')
