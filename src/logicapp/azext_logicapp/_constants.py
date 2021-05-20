# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for license information.
# --------------------------------------------------------------------------------------------
import os

FUNCTIONS_NO_V2_REGIONS = {
    "USNat West",
    "USNat East",
    "USSec West",
    "USSec East"
}

KUBE_APP_KIND = "linux,kubernetes,app"
KUBE_DEFAULT_SKU = "K1"
KUBE_ASP_KIND = "linux,kubernetes"
KUBE_APP_KIND = "linux,kubernetes,app"
KUBE_CONTAINER_APP_KIND = 'linux,kubernetes,app,container'
KUBE_FUNCTION_APP_KIND = 'functionapp,workflowapp,linux,kubernetes'
KUBE_FUNCTION_CONTAINER_APP_KIND = 'linux,kubernetes,functionapp,workflowapp,container'
KUBE_LOGIC_APP_KIND = 'functionapp,workflowapp,linux,kubernetes'
KUBE_LOGIC_CONTAINER_APP_KIND = 'linux,kubernetes,functionapp,workflowapp,container'
LINUX_RUNTIMES = ['dotnet', 'node', 'python', 'java']
WINDOWS_RUNTIMES = ['dotnet', 'node', 'java', 'powershell']

NODE_VERSION_DEFAULT = "10.14"
NODE_VERSION_NEWER = "12-lts"
NODE_EXACT_VERSION_DEFAULT = "10.14.1"
NETCORE_VERSION_DEFAULT = "2.2"
DOTNET_VERSION_DEFAULT = "4.7"
PYTHON_VERSION_DEFAULT = "3.7"
NETCORE_RUNTIME_NAME = "dotnetcore"
DOTNET_RUNTIME_NAME = "aspnet"
NODE_RUNTIME_NAME = "node"
PYTHON_RUNTIME_NAME = "python"
OS_DEFAULT = "Windows"
STATIC_RUNTIME_NAME = "static"  # not an official supported runtime but used for CLI logic
NODE_VERSIONS = ['4.4', '4.5', '6.2', '6.6', '6.9', '6.11', '8.0', '8.1', '8.9', '8.11', '10.1', '10.10', '10.14']
PYTHON_VERSIONS = ['3.7', '3.6', '2.7']
NETCORE_VERSIONS = ['1.0', '1.1', '2.1', '2.2']
DOTNET_VERSIONS = ['3.5', '4.7']

LINUX_SKU_DEFAULT = "P1V2"
FUNCTIONS_VERSIONS = ['2', '3']

# functions version : default node version
FUNCTIONS_VERSION_TO_DEFAULT_NODE_VERSION = {
    '2': '~10',
    '3': '~12'
}
# functions version -> runtime : default runtime version
FUNCTIONS_VERSION_TO_DEFAULT_RUNTIME_VERSION = {
    '2': {
        'node': '8',
        'dotnet': '2',
        'python': '3.7',
        'java': '8'
    },
    '3': {
        'node': '12',
        'dotnet': '3',
        'python': '3.7',
        'java': '8'
    }
}
# functions version -> runtime : runtime versions
FUNCTIONS_VERSION_TO_SUPPORTED_RUNTIME_VERSIONS = {
    '2': {
        'node': ['8', '10'],
        'python': ['3.6', '3.7'],
        'dotnet': ['2'],
        'java': ['8']
    },
    '3': {
        'node': ['10', '12'],
        'python': ['3.6', '3.7', '3.8'],
        'dotnet': ['3'],
        'java': ['8']
    }
}
# dotnet runtime version : dotnet linuxFxVersion
DOTNET_RUNTIME_VERSION_TO_DOTNET_LINUX_FX_VERSION = {
    '2': '2.2',
    '3': '3.1'
}

MULTI_CONTAINER_TYPES = ['COMPOSE', 'KUBE']

OS_TYPES = ['Windows', 'Linux']

CONTAINER_APPSETTING_NAMES = ['DOCKER_REGISTRY_SERVER_URL', 'DOCKER_REGISTRY_SERVER_USERNAME',
                              'DOCKER_REGISTRY_SERVER_PASSWORD', "WEBSITES_ENABLE_APP_SERVICE_STORAGE"]
APPSETTINGS_TO_MASK = ['DOCKER_REGISTRY_SERVER_PASSWORD']

SCALE_VALID_PARAMS = {
    "runtimeScaleMonitoringEnabled": "siteConfig.functionsRuntimeScaleMonitoringEnabled",
    "logicAppScaleLimit": "siteConfig.functionAppScaleLimit",
    "minimumElasticInstanceCount": "siteConfig.minimumElasticInstanceCount"
}

class FUNCTIONS_STACKS_API_KEYS():
    # pylint:disable=too-few-public-methods,too-many-instance-attributes
    def __init__(self):
        self.NAME = 'name'
        self.VALUE = 'value'
        self.DISPLAY = 'display'
        self.PROPERTIES = 'properties'
        self.MAJOR_VERSIONS = 'majorVersions'
        self.DISPLAY_VERSION = 'displayVersion'
        self.RUNTIME_VERSION = 'runtimeVersion'
        self.IS_HIDDEN = 'isHidden'
        self.IS_PREVIEW = 'isPreview'
        self.IS_DEPRECATED = 'isDeprecated'
        self.IS_DEFAULT = 'isDefault'
        self.SITE_CONFIG_DICT = 'siteConfigPropertiesDictionary'
        self.APP_SETTINGS_DICT = 'appSettingsDictionary'
        self.LINUX_FX_VERSION = 'linuxFxVersion'
        self.APPLICATION_INSIGHTS = 'applicationInsights'
        self.SUPPORTED_EXTENSION_VERSIONS = 'supportedFunctionsExtensionVersions'
        self.USE_32_BIT_WORKER_PROC = 'use32BitWorkerProcess'
        self.FUNCTIONS_WORKER_RUNTIME = 'FUNCTIONS_WORKER_RUNTIME'


RUNTIME_STACKS = os.path.abspath(os.path.join(os.path.abspath(__file__),
                                              '../resources/WebappRuntimeStacks.json'))

GENERATE_RANDOM_APP_NAMES = os.path.abspath(os.path.join(os.path.abspath(__file__),
                                                         '../resources/GenerateRandomAppNames.json'))

PUBLIC_CLOUD = "AzureCloud"
