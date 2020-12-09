"""
module for creating lambda widgets

"""
import boto3
from .lookups import (dashboard_lambdas, custom_lambda_widgets)
from .constants import positioning


def create_lambda_widgets(region, deploy_stage, iow_functions):
    """
    Iterate over an account's list of lambdas and create generic widgets for those with
    wma:organization = 'IOW' tags.  It also creates some custom widgets.

    :param iow_functions: filtered list of iow lambda functions
    :param region: The region, for us that's usually us-west-2
    :param deploy_stage: The specified deployment environment (DEV, TEST, QA, PROD-EXTERNAL)
    :return: List of lambda widgets
    :rtype: list
    """

    lambda_widgets = []

    # set dimensions for custom lambda widgets
    positioning['width'] = 24
    positioning['height'] = 1

    custom_lambda_section_title_widget = {
        'type': 'text',
        'height': positioning['height'],
        'width': positioning['width'],
        'properties': {
            "markdown": "# Lambda Status"
        }
    }

    lambda_widgets.append(custom_lambda_section_title_widget)

    # set dimensions for custom lambda widgets
    positioning['width'] = 12
    positioning['height'] = 6

    # Custom widget for monitoring error handler invocation counts over time
    error_handler_activity = {
        'type': 'metric',
        'height': positioning['height'],
        'width': positioning['width'],
        'properties': {
            "metrics": [
                ["AWS/Lambda", "ConcurrentExecutions", "FunctionName",
                    lambda_properties('error_handler', deploy_stage)['name'], "Resource",
                    lambda_properties('error_handler', deploy_stage)['name']],
                [".", "Invocations", ".", ".", {"stat": "Sum"}]
            ],
            "view": "timeSeries",
            "stacked": False,
            "region": region,
            "title": "Error Handler Activity",
            "period": 60,
            "stat": "Average"
        }
    }

    lambda_widgets.append(error_handler_activity)

    # Custom widget for monitoring concurrency of lambdas specifically involved in the ETL
    concurrent_lambdas = {
        'type': 'metric',
        'height': positioning['height'],
        'width': positioning['width'],
        'properties': {
            "metrics": generate_custom_lambda_metrics(deploy_stage, 'ConcurrentExecutions', 'concurrent_lambdas'),
            "view": "timeSeries",
            "stacked": True,
            "region": region,
            "period": 60,
            "stat": "Average",
            "title": "Concurrent Lambdas (Average per minute)",
        }
    }

    lambda_widgets.append(concurrent_lambdas)

    # Custom widget for monitoring average duration of transform db lambdas
    duration_of_transform_db_lambdas_average = {
        'type': 'metric',
        'height': positioning['height'],
        'width': positioning['width'],
        'properties': {
            "metrics": generate_custom_lambda_metrics(deploy_stage, 'Duration', 'duration_of_transform_db_lambdas'),
            "view": "timeSeries",
            "stacked": False,
            "region": region,
            "period": 300,
            "stat": "Average",
            "title": "Duration of Transformation DB Lambdas (Average)"
        }
    }

    lambda_widgets.append(duration_of_transform_db_lambdas_average)

    # Custom widget for monitoring max duration of transform db lambdas
    duration_of_transform_db_lambdas_max = {
        'type': 'metric',
        'height': positioning['height'],
        'width': positioning['width'],
        'properties': {
            "metrics": generate_custom_lambda_metrics(deploy_stage, 'Duration', 'duration_of_transform_db_lambdas'),
            "view": "timeSeries",
            "stacked": False,
            "region": region,
            "period": 300,
            "stat": "Maximum",
            "title": "Duration of Transformation DB Lambdas (Maximum)"
        }
    }

    lambda_widgets.append(duration_of_transform_db_lambdas_max)

    # set dimensions for title text widget
    positioning['width'] = 24
    positioning['height'] = 1

    autogenerated_lambdas_title_widget = {
        'type': 'text',
        'height': positioning['height'],
        'width': positioning['width'],
        'properties': {
            "markdown": "# Status of each 'IOW' tagged lambda in the account"
        }
    }

    lambda_widgets.append(autogenerated_lambdas_title_widget)

    dv_widgets = []
    sv_widgets = []
    data_in_widgets = []
    data_purge_widgets = []
    error_widgets = []
    environment_management_widgets = []
    nwis_web_widgets = []
    misc_widgets = []

    # iterate over the list of iow functions create widgets for the assets we care about based on filters
    for function in iow_functions:

        function_name = function['function_name']
        title = function['title']
        branch = function['etl_branch']

        # set dimensions for generic lambda widgets
        positioning['width'] = 8
        positioning['height'] = 6

        # create 4 widgets per lambda in the account
        # 1 for numeric metrics, 2 for charting those same metrics graphically, and 1 for memory usage
        numeric_stats_widget = {
            'type': 'metric',
            'height': positioning['height'],
            'width': positioning['width'],
            'properties': {
                "metrics": [
                    ["AWS/Lambda", "Invocations", "FunctionName", function_name, {"stat": "Sum"}],
                    [".", "Errors", ".", ".", {"stat": "Sum"}],
                    [".", "Duration", ".", "."],
                    [".", "ConcurrentExecutions", ".", "."],
                    [".", "Throttles", ".", "."]
                ],
                "view": "singleValue",
                "region": region,
                "title": title,
                "period": 300,
                "stacked": False,
                "stat": "Average"
            }
        }

        concurrent_executions_widget = {
            'type': 'metric',
            'height': positioning['height'],
            'width': positioning['width'],
            'properties': {
                "metrics": [
                    ["AWS/Lambda", "ConcurrentExecutions", "FunctionName", function_name, {"stat": "Maximum", "label": "ConcurrentExecutions (max)"}],
                    [".", "Invocations", ".", "."],
                    [".", "Errors", ".", "."],
                    [".", "Throttles", ".", ".", {"stat": "Average"}]
                ],
                "view": "timeSeries",
                "region": region,
                "title": f"{title} Concurrent Executions",
                "period": 300,
                "stat": "Sum",
                "stacked": False
            }
        }

        duration_widget = {
            'type': 'metric',
            'height': positioning['height'],
            'width': positioning['width'],
            'properties': {
                "metrics": [
                    ["AWS/Lambda", "Duration", "FunctionName", function_name, {"yAxis": "left"}],
                    ["...", {"yAxis": "right", "stat": "Maximum"}]
                ],
                "view": "timeSeries",
                "region": region,
                "title": f"{title} Duration",
                "period": 300,
                "stat": "Average",
                "stacked": False
            }
        }

        widgets = [numeric_stats_widget, concurrent_executions_widget, duration_widget]

        # inner function to sort the autogenerated widgets into etl-branch-specific lists for grouped display
        def sort_widgets_by_etl_branch(widget_list):
            for w in widget_list:
                if 'dv' == branch:
                    dv_widgets.append(w)
                elif 'sv' == branch:
                    sv_widgets.append(w)
                elif 'environment_management' == branch:
                    environment_management_widgets.append(w)
                elif 'error_handling' == branch:
                    error_widgets.append(w)
                elif 'data_ingest' == branch:
                    data_in_widgets.append(w)
                elif 'data_purging' == branch:
                    data_purge_widgets.append(w)
                elif 'nwis_web' == branch:
                    nwis_web_widgets.append(w)
                else:
                    misc_widgets.append(w)

        sort_widgets_by_etl_branch(widgets)

    # add the generic widget groups so they appear together in the dashboard
    lambda_widgets.extend(error_widgets)
    lambda_widgets.extend(data_in_widgets)
    lambda_widgets.extend(dv_widgets)
    lambda_widgets.extend(sv_widgets)
    lambda_widgets.extend(nwis_web_widgets)
    lambda_widgets.extend(data_purge_widgets)
    lambda_widgets.extend(environment_management_widgets)
    # When we don't have a lookup defined for the lambda yet, it will appear at the bottom of the list
    lambda_widgets.extend(misc_widgets)

    return lambda_widgets


def create_lambda_memory_usage_widgets(region, iow_functions):
    memory_usage_widgets = []

    # set dimensions for memory usage title widget
    positioning['width'] = 24
    positioning['height'] = 1

    memory_usage_lambdas_title_widget = {
        'type': 'text',
        'height': positioning['height'],
        'width': positioning['width'],
        'properties': {
            "markdown": "# Memory usage of each 'IOW' tagged lambda in the account"
        }
    }

    memory_usage_widgets.append(memory_usage_lambdas_title_widget)

    # iterate over the list of iow functions and create memory usage widgets
    for function in iow_functions:

        function_name = function['function_name']
        title = function['title']
        branch = function['etl_branch']

        # set dimensions for memory usage widgets
        positioning['width'] = 24
        positioning['height'] = 6

        memory_usage_widget = {
            "type": "log",
            'height': positioning['height'],
            'width': positioning['width'],
            "properties": {
                "query": f"SOURCE '/aws/lambda/{function_name}' | filter @type=\"REPORT\" | max(@memorySize) as allocatedMemory, avg(@maxMemoryUsed) as mean_MemoryUsed, max(@maxMemoryUsed) as max_MemoryUsed by bin(5min)",
                "region": region,
                "title": f"{title} Memory Usage",
                "view": "timeSeries",
                "stacked": False
            }
        }

        memory_usage_widgets.append(memory_usage_widget)

    return memory_usage_widgets


def get_iow_functions(region, deploy_stage):
    """
    Returns a list of iow tagged lambda properties used for creating lambda widgets.

    :param region: The region, for us that's usually us-west-2
    :param deploy_stage: The specified deployment environment (DEV, TEST, QA, PROD-EXTERNAL)
    :return: A list of iow function property dicts
    :rtype: list
    """
    api_calls = LambdaAPICalls(region, deploy_stage)
    # grab all the lambdas in the account/region
    all_lambda_metadata_response = api_calls.get_all_lambda_metadata()

    iow_functions = []

    # iterate over the list of lambda metadata and return a dict of iow tagged function properties
    for function in all_lambda_metadata_response['Functions']:

        if api_calls.is_iow_lambda_filter(function):
            function_name = function['FunctionName']
            widget_properties = get_widget_properties(function_name, deploy_stage)
            title = widget_properties['title']
            branch = widget_properties['etl_branch']

            iow_function = {
                'function_name': function_name,
                'title': title,
                'etl_branch': branch
            }

            iow_functions.append(iow_function)

    return iow_functions


def get_widget_properties(function_name, deploy_stage):

    # default values for the etl branch and function name
    etl_branch = 'not defined'
    title = function_name
    es_logs_plugin = 'es-logs-plugin'

    # hack apart the function name to get the repo name and the descriptor
    if es_logs_plugin in function_name:
        descriptor = es_logs_plugin
        repo_name = function_name.replace(f"-{deploy_stage}-{descriptor}", '')
    else:
        function_name_without_tier = function_name.replace(f"-{deploy_stage}", '')
        function_name_parts = function_name_without_tier.split('-')
        descriptor = function_name_parts[-1]
        function_name_parts_without_tier_or_descriptor = function_name_parts[:-1]
        repo_name = '-'.join(function_name_parts_without_tier_or_descriptor)

    # set the widget title based on the label in our lookups, defaults to the original function name
    # set the etl branch so we can group the generic lambdas together by their purpose in the etl.
    for lookup in dashboard_lambdas:

        lookup_repo_name = dashboard_lambdas[lookup]['repo_name']

        # the descriptors are sometimes the same, so we have to assign values to the etl_branch and title as a package.
        if repo_name == lookup_repo_name and descriptor == dashboard_lambdas[lookup]['descriptor']:
            etl_branch = dashboard_lambdas[lookup]['etl_branch']
            title = dashboard_lambdas[lookup]['label']
        if repo_name == lookup_repo_name and descriptor == es_logs_plugin:
            etl_branch = dashboard_lambdas[lookup]['etl_branch']
            title = f"{dashboard_lambdas[lookup]['label']} ES logger"

    return {'title': title, 'etl_branch': etl_branch}


def lambda_properties(lookup_name, deploy_stage):
    """
    Uses the supplied lookup name to generate lambda name and label key values.

    :param lookup_name: the name of the lookup object containing lambda properties
    :param deploy_stage: the deploy stage (DEV, TEST, QA, PROD-EXTERNAL)
    :return: the lambda name and label
    :rtype: dict
    """
    properties = dashboard_lambdas[lookup_name]
    name = f"{properties['repo_name']}-{deploy_stage}-{properties['descriptor']}"
    label = properties['label']

    return {'name': name, 'label': label}


def generate_custom_lambda_metrics(deploy_stage, metric_name, lookup_list_name):
    """
    Generates custom lambda widget metrics.

    :param deploy_stage: The deployment tier
    :param metric_name: The name of the metric, like "Duration" or "ConcurrentExecutions"
    :param lookup_list_name: the lookup list containing the lambdas we wish to monitor
    :return: The list of generated metrics
    :rtype: list
    """

    metrics_list = []
    count = 0

    for name in custom_lambda_widgets[lookup_list_name]:
        lambda_attributes = lambda_properties(name, deploy_stage)

        if count < 1:
            # the first metric in the list has some additional stuff
            first_metric = [
                "AWS/Lambda",
                metric_name,
                "FunctionName",
                lambda_attributes['name'],
                {"label": lambda_attributes['label']}
            ]
            metrics_list.append(first_metric)
        else:
            metric = [
                "...",
                lambda_attributes['name'],
                {"label": lambda_attributes['label']}
            ]
            metrics_list.append(metric)

        count += 1

    return metrics_list


class LambdaAPICalls:
    def __init__(self, region, deploy_stage):
        """
        Constructor for the LambdaAPICalls class.

        :param region: usually 'us-west-2'
        :param deploy_stage: The deployment tier (DEV, TEST, QA, PROD-EXTERNAL)
        """
        self.region = region
        self.lambda_client = boto3.client('lambda', region_name=region)
        self.deploy_stage = deploy_stage

    def get_all_lambda_metadata(self):
        """
        Using the AWS python sdk (boto3), grab all the lambda functions for the specified account for a given region.

        :return: response: metadata about each lambda in the account.
        :rtype: dict
        """
        # TODO maybe get a paginator to work instead of 'manual' iteration
        # https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/lambda.html#Lambda.Client.list_functions
        response = {}
        marker = None
        while True:
            if marker:
                response_iterator = self.lambda_client.list_functions(
                    MaxItems=10,
                    Marker=marker)
                response['Functions'].extend(response_iterator['Functions'])
            else:
                response_iterator = self.lambda_client.list_functions(
                    MaxItems=10
                )
                response.update(response_iterator)
            try:
                marker = response_iterator['NextMarker']
            except KeyError:
                # no more pages, move on
                break

        # The order in which we receive lambda metadata isn't guaranteed
        # sort alphabetically by function name to group each lambda function with its elasticsearch logger function
        response['Functions'] = sorted(response['Functions'], key=lambda i: i['FunctionName'])
        return response

    def is_iow_lambda_filter(self, function):
        """
        Apply filters to determine if the function is a tagged IOW asset in the correct tier.

        :param function: A single lambda function's metadata
        :return: is_iow_lambda: is this an IOW asset or not
        :rtype: bool
        """
        function_name = function['FunctionName']

        is_iow_lambda = False

        # filtering on deploy tier
        if self.deploy_stage.upper() in function_name:

            # launch API call to grab metadata for a specific function, we are interested in the tags
            # https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/lambda.html#Lambda.Client.get_function
            function_metadata = self.lambda_client.get_function(FunctionName=function_name)

            # we only want lambdas that are tagged as 'IOW'
            if 'Tags' in function_metadata:
                if 'wma:organization' in function_metadata['Tags']:
                    if 'IOW' == function_metadata['Tags']['wma:organization']:
                        if 'CleanupFunction' not in function_name:
                            is_iow_lambda = True

        return is_iow_lambda
