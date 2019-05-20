import collections
from os import environ
from logging import getLogger
from typing import Optional, Dict

from kubernetes import config, client
from openshift.dynamic import DynamicClient
from openshift.dynamic.client import ResourceList
from openshift.dynamic.exceptions import ForbiddenError


def deep_update(source, overrides):
    """
    Update a nested dictionary or similar mapping.
    Modify ``source`` in place.
    """
    for key, value in overrides.items():
        if isinstance(value, collections.Mapping) and value:
            returned = deep_update(source.get(key, {}), value)
            source[key] = returned
        else:
            source[key] = overrides[key]
    return source


class OpenShift:
    def __init__(self, context: str = 'current', use_internal: bool = False):
        if use_internal:
            config.load_incluster_config()
            k8s_client = client.ApiClient()
        else:
            k8s_client = config.new_client_from_config(
                context=None if context == 'current' else context,
                config_file=environ.get('KUBE_CONFIG_FILE'),
                persist_config=False
            )
        self.context = context
        self.client = DynamicClient(k8s_client)
        self.log = getLogger(__name__)

    def list_projects(self) -> Optional[ResourceList]:
        project_list = self.client.resources.get(kind='ProjectList', api_version='project.openshift.io/v1')
        try:
            all_projects = project_list.get()
        except ForbiddenError as e:
            # Ignore clusters that don't have any projects
            self.log.debug(e)
            self.log.info(f'403 Forbidden: LIST Projects')
            return None
        return all_projects

    def list_routes(self, namespace: str = None) -> Optional[ResourceList]:
        route_list = self.client.resources.get(kind='RouteList', api_version='route.openshift.io/v1')
        try:
            routes_for_namespace = route_list.get(namespace=namespace)
        except ForbiddenError as e:
            # Ignore namespaces that are not accessible
            self.log.debug(e)
            self.log.info(f'403 Forbidden: LIST Routes {namespace}')
            return None
        return routes_for_namespace

    def update_route(self, object_name: str, namespace: str, definition: Dict):
        routes = self.client.resources.get(kind='Route', api_version='route.openshift.io/v1')
        body = {
            'kind': 'Route',
            'apiVersion': 'route.openshift.io/v1',
            'metadata': {'name': object_name}
        }
        deep_update(body, definition)
        try:
            updated_route = routes.patch(body=body, namespace=namespace)
        except ForbiddenError as e:
            self.log.debug(e)
            self.log.info(f'403 Forbidden: PATCH {object_name}:{namespace}')
            return None
        return updated_route
