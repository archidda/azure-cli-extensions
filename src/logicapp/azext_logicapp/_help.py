# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for license information.
# --------------------------------------------------------------------------------------------

from knack.help_files import helps

# pylint: disable=line-too-long


helps['monitor app-insights metrics get-metadata'] = """
    type: command
    short-summary: Get the metadata for metrics on a particular application.
    examples:
      - name: Views the metadata for the provided app.
        text: |
          az monitor app-insights metrics get-metadata --app e292531c-eb03-4079-9bb0-fe6b56b99f8b
"""

helps['monitor app-insights events show'] = """
    type: command
    short-summary: List events by type or view a single event from an application, specified by type and ID.
    parameters:
      - name: --offset
        short-summary: >
          Time offset of the query range, in ##d##h format.
        long-summary: >
          Can be used with either --start-time or --end-time. If used with --start-time, then
          the end time will be calculated by adding the offset. If used with --end-time (default), then
          the start time will be calculated by subtracting the offset. If --start-time and --end-time are
          provided, then --offset will be ignored.
    examples:
      - name: Get an availability result by ID.
        text: |
          az monitor app-insights events show --app 578f0e27-12e9-4631-bc02-50b965da2633 --type availabilityResults --event b2cf08df-bf42-4278-8d2c-5b55f85901fe
      - name: List availability results from the last 24 hours.
        text: |
          az monitor app-insights events show --app 578f0e27-12e9-4631-bc02-50b965da2633 --type availabilityResults --offset 24h
"""

helps['monitor app-insights component continues-export list'] = """
    type: command
    short-summary: List Continuous Export configurations for an Application Insights component.
    examples:
      - name: ExportConfigurationsList
        text: |
            az monitor app-insights component continues-export list -g rg \\
            --app 578f0e27-12e9-4631-bc02-50b965da2633
"""

helps['monitor app-insights component continues-export create'] = """
    type: command
    short-summary: Create a Continuous Export configuration for an Application Insights component.
    examples:
      - name: Create a Continuous Export configuration.
        text: |
            az monitor app-insights component continues-export create -g rg \\
            --app 578f0e27-12e9-4631-bc02-50b965da2633 \\
            --record-types Requests Event Exceptions Metrics PageViews \\
            --dest-account account --dest-container container --dest-sub-id sub-id \\
            --dest-sas se=2020-10-27&sp=w&sv=2018-11-09&sr=c
"""

helps['monitor app-insights component continues-export update'] = """
    type: command
    short-summary: Update a Continuous Export configuration for an Application Insights component.
    examples:
      - name: Update a Continuous Export configuration record-types.
        text: |
            az monitor app-insights component continues-export update -g rg \\
            --app 578f0e27-12e9-4631-bc02-50b965da2633 \\
            --id exportid \\
            --record-types Requests Event Exceptions Metrics PageViews
      - name: Update a Continuous Export configuration storage destination.
        text: |
            az monitor app-insights component continues-export update -g rg \\
            --app 578f0e27-12e9-4631-bc02-50b965da2633 \\
            --id exportid \\
            --dest-account account --dest-container container --dest-sub-id sub-id \\
            --dest-sas se=2020-10-27&sp=w&sv=2018-11-09&sr=c
"""
