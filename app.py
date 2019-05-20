from importlib import import_module
from inspect import getmembers, isclass
from logging import Logger
from os import environ
from pathlib import Path
import time
from typing import List, Callable, Tuple

import schedule

import logging_config
from alerts import BaseAlert
from openshift_client import OpenShift


def process_alerts_and_remediations(log: Logger, clusters, alerts: List[Tuple[str, Callable[..., BaseAlert]]]):
    for context in clusters:
        client: OpenShift = OpenShift(context=context, use_internal=environ.get('INTERNAL_CLUSTER', 'false') == 'true')
        cluster: str = client.client.configuration.host
        log.info(f'Processing alerts for Cluster: {cluster} ...')
        log.handlers = [logging_config.get_tabbed_formatter()]
        # Iterate over all alerts
        for _, alert_class in alerts:
            alert = alert_class(client)
            alert.process_alerts()
            if environ.get('REMEDIATION', 'false') == 'true':
                alert.process_remediations()
            if alert.failed_alerts:
                if environ.get('SKIP_EMAIL_FOR_SUCCESSFUL_REMEDIATION', 'false') == 'true':
                    if not all(failure.get('remediated', False) for failure in alert.failed_alerts):
                        alert.email_results()
                else:
                    alert.email_results()

        log.handlers = [logging_config.get_normal_formatter()]
        log.info(f'Finished processing alerts for Cluster: {cluster}.')


if __name__ == '__main__':
    logger: Logger = logging_config.setup_logging()
    cluster_contexts: List[str] = environ.get('CLUSTER_CONTEXTS', 'current').split(',')

    # Import all modules below the `alerts/` directory
    alert_plugins = (import_module(f'alerts.{alert_module.stem}') for alert_module in Path('./alerts').glob('*.py'))
    # Load all classes from each module that inherits from the BaseAlert abstract class
    alert_classes = (cls for plugin in alert_plugins for cls in getmembers(plugin, predicate=lambda curr_class: isclass(curr_class) and BaseAlert in curr_class.__bases__) if cls)

    schedule.every(1).hour.do(process_alerts_and_remediations, logger, cluster_contexts, alert_classes)

    # Perform initial run of all scheduled jobs
    schedule_delay = int(environ.get('SCHEDULE_DELAY', '30'))
    schedule.run_all(schedule_delay)

    while True:
        schedule.run_pending()
        time.sleep(int(environ.get('SCHEDULE_DELAY', '30')))
