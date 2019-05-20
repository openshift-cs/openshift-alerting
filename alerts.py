from logging import getLogger
from typing import List, Dict, Union

from openshift.dynamic.client import ResourceField
from openshift_client import OpenShift


class Alerts:
    def __init__(self):
        self.log = getLogger(__name__)

    def lets_encrypt_routes(self, client: OpenShift) -> List[Dict[str, Union[str, ResourceField]]]:
        failed = []
        projects = client.list_projects()
        if projects:
            for project in projects.items:
                routes = client.list_routes(namespace=project.metadata.name)
                if routes:
                    for route in routes.items:
                        if route.metadata.annotations and 'kubernetes.io/tls-acme-paused' in route.metadata.annotations.keys():
                            msg = f'Route {route.metadata.name} is paused; Namespace: {route.metadata.namespace}'
                            failed.append({
                                'object': route,
                                'message': msg
                            })
                            self.log.info(msg)
        return failed
