from abc import ABC, abstractmethod
from logging import getLogger, Logger
from os import environ
from typing import List, Dict, Union

import emails
from openshift.dynamic.client import ResourceField

from openshift_client import OpenShift


class BaseAlert(ABC):
    def __init__(self, client: OpenShift):
        self.client: OpenShift = client
        self.cluster: str = self.client.client.configuration.host
        self.log: Logger = getLogger(self.__class__.__name__)
        self.failed_alerts: List[Dict[str, Union[str, bool, ResourceField]]] = []
        super().__init__()

    def email_results(self) -> None:
        subject = f'{self.__class__.__name__} - {self.cluster}'
        message = 'Alert(s) found:\n\n\t'
        for alert in self.failed_alerts:
            message += alert['message']
            if alert.get('remediated') is True:
                message += ' - Successfully remediated'
            elif alert.get('remediated') is False:
                message += ' - Failed remediation'
            message += '\n\t'
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
            self.log.error(f'{"="*80}\n\tUnable to send email alert {subject} (ERR: {resp.error}):\n\n\t{message}\n\t{"="*80}')

    @abstractmethod
    def process_alerts(self) -> None:
        pass

    @abstractmethod
    def process_remediations(self) -> None:
        pass
