import collections
from json import loads
from os import environ
from logging import getLogger
from typing import Optional, Dict, Union

from kubernetes import config, client
from openshift.dynamic import DynamicClient
from openshift.dynamic.client import ResourceList, ResourceField
from openshift.dynamic.exceptions import ForbiddenError, ApiException


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
        all_projects = self._make_call(project_list, 'get')
        return all_projects

    def list_routes(self, namespace: str = None) -> Optional[ResourceList]:
        route_list = self.client.resources.get(kind='RouteList', api_version='route.openshift.io/v1')
        routes_for_namespace = self._make_call(route_list, 'get', namespace=namespace)
        return routes_for_namespace

    def update_route(self, object_name: str, namespace: str, definition: Dict) -> Optional[ResourceField]:
        routes = self.client.resources.get(kind='Route', api_version='route.openshift.io/v1')
        body = {
            'kind': 'Route',
            'apiVersion': 'route.openshift.io/v1',
            'metadata': {'name': object_name}
        }
        deep_update(body, definition)
        updated_route = self._make_call(routes, 'patch', body=body, namespace=namespace)
        return updated_route

    def _make_call(self, resource: Union[ResourceList, ResourceField], method: str, *args, **kwargs) -> Optional[Union[ResourceList, ResourceField]]:
        try:
            result = getattr(resource, method)(*args, **kwargs)
        except ForbiddenError as e:
            self.log.debug(e)
            msg = f'403 Forbidden: {method.upper()} {getattr(resource, "kind", "")}'
            if 'object_name' in kwargs:
                msg += f' - {kwargs["object_name"]}'
            if 'namespace' in kwargs:
                msg += f' - {kwargs["namespace"]}'
            self.log.info(msg)
        except ApiException as e:
            self.log.debug(e)
            self.log.warning(f'Unable to {method.upper()} {getattr(resource, "kind", "")}: {loads(e.body)["message"]}')
        except AttributeError as e:
            self.log.debug(e)
            self.log.error(f'Unable to {method.upper()} {getattr(resource, "kind", "")}: {e}')
        else:
            return result
