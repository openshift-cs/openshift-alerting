from logging import getLogger
from typing import List, Dict, Union

from openshift.dynamic.client import ResourceField
from openshift_client import OpenShift


class Remediations:
    def __init__(self):
        self.log = getLogger(__name__)

    def lets_encrypt_routes(self, client: OpenShift, failed_alerts: List[Dict[str, Union[str, ResourceField]]]) -> Dict[str, List[str]]:
        result: Dict[str, List[str]] = {'successful': [], 'failed': []}
        for alert in failed_alerts:
            route = alert['object']
            updated_route = client.update_route(
                object_name=route.metadata.name,
                namespace=route.metadata.namespace,
                definition={'metadata': {'annotations': {'kubernetes.io/tls-acme-paused': None}}}
            )
            if updated_route and 'kubernetes.io/tls-acme-paused' not in updated_route.metadata.annotations.keys():
                msg = f'Route {route.metadata.name} remediation successful; Namespace: {route.metadata.namespace}'
                result['successful'].append(msg)
            else:
                msg = f'Route {route.metadata.name} remediation failed; Namespace: {route.metadata.namespace}'
                result['failed'].append(msg)

            self.log.info(msg)
        return result
