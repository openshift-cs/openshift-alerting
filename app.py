from logging import getLogger, Formatter, StreamHandler, Logger
from os import environ
import sys
import inspect
import time

import emails
import schedule

from alerts import Alerts
from remediations import Remediations
from openshift_client import OpenShift

LOG_FORMAT = '{message:<80} | {asctime}:{levelname:<9} | {module}:{funcName}:{lineno}'


def setup_logging() -> Logger:
    log = getLogger()
    log.setLevel(environ.get('LOGGING_LEVEL', 'INFO'))
    log.addHandler(get_normal_formatter())

    return log


def get_normal_formatter():
    formatter = Formatter(LOG_FORMAT, "%Y-%m-%d %H:%M:%S", '{')
    stdout_handler = StreamHandler(sys.stdout)
    stdout_handler.setFormatter(formatter)
    return stdout_handler


def get_tabbed_formatter():
    formatter = Formatter(f'\t{LOG_FORMAT}', "%Y-%m-%d %H:%M:%S", '{')
    stdout_handler = StreamHandler(sys.stdout)
    stdout_handler.setFormatter(formatter)
    return stdout_handler


def send_email(subject: str, message: str) -> None:
    msg = emails.html(
        subject=subject,
        text=message,
        mail_from='alerts@openshift.com',
        mail_to='openshift-website-requests@redhat.com'
    )
    resp = msg.send(
        smtp={
            'host': environ.get('SMTP_HOST', 'localhost'),
            'port': environ.get('SMTP_PORT', '25'),
            'tls': environ.get('SMTP_USE_TLS', 'true') == 'true',
            'user': environ.get('SMTP_USER'),
            'password': environ.get('SMTP_PASS'),
        }
    )

    if resp.status_code not in [250, 251, 252]:
        logger.error(f'{"="*80}\n\tUnable to send email alert {subject} (ERR: {resp.error}):\n\n\t{message}\n\t{"="*80}')


def process_alerts_and_remediations(clusters, alerts, remediations):
    for context in clusters:
        client = OpenShift(context=context, use_internal=environ.get('INTERNAL_CLUSTER', 'false') == 'true')
        cluster = client.client.configuration.host
        logger.info(f'Processing alerts for Cluster: {cluster} ...')
        logger.handlers = [get_tabbed_formatter()]
        # Iterate over all alerts
        for alert, alert_method in alerts.items():
            # Alerts are considered failed if they produce output
            alert_failed = alert_method(client)
            if alert_failed:
                # Alert has an automated remediation process and REMEDIATION is enabled
                if alert in remediations.keys() and environ.get('REMEDIATION', 'false') == 'true':
                    # Remediation attempt was not successful
                    remediation_attempt = remediation_methods[alert](client, alert_failed)
                    successful = remediation_attempt['successful']
                    failed = remediation_attempt['failed']
                    if failed:
                        fail_messages = '\n\t'.join([fail_item for fail_item in failed])
                        # Email remediation attempt output
                        send_email(
                            subject=f'{alert} - {cluster}',
                            message=f'Remediation(s) failed:\n\n\t{fail_messages}'
                        )
                    # Remediation was successful
                    if successful:
                        success_messages = '\n\t'.join([success_item for success_item in successful])
                        logger.info(f'Alert(s) successfully remediated:\n\n\t{success_messages}')
                # Alert cannot be automatically remediated
                else:
                    alert_messages = '\n\t'.join([failed_item['message'] for failed_item in alert_failed])
                    # Email alert output
                    send_email(
                        subject=f'{alert} - {cluster}',
                        message=f'Alert(s) found:\n\n\t{alert_messages}'
                    )
        logger.handlers = [get_normal_formatter()]
        logger.info(f'Finished processing alerts for Cluster: {cluster}.')


if __name__ == '__main__':
    logger = setup_logging()
    cluster_contexts = environ.get('CLUSTER_CONTEXTS', 'current').split(',')
    alert_class = Alerts()
    remediation_class = Remediations()
    alert_methods = {method_name: method for method_name, method in inspect.getmembers(alert_class, predicate=inspect.ismethod) if not method_name.startswith('_')}
    remediation_methods = {method_name: method for method_name, method in inspect.getmembers(remediation_class, predicate=inspect.ismethod) if not method_name.startswith('_')}

    schedule.every(1).hour.do(process_alerts_and_remediations, cluster_contexts, alert_methods, remediation_methods)

    # Perform initial run of all scheduled jobs
    schedule_delay = int(environ.get('SCHEDULE_DELAY', '30'))
    schedule.run_all(schedule_delay)

    while True:
        schedule.run_pending()
        time.sleep(int(environ.get('SCHEDULE_DELAY', '30')))
