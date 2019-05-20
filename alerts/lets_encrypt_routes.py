from . import BaseAlert


class LetsEncryptRoutes(BaseAlert):
    def process_alerts(self):
        projects = self.client.list_projects()
        if projects:
            for project in projects.items:
                routes = self.client.list_routes(namespace=project.metadata.name)
                if routes:
                    for route in routes.items:
                        if route.metadata.annotations and 'kubernetes.io/tls-acme-paused' in route.metadata.annotations.keys():
                            msg = f'Route {route.metadata.name} is paused; Namespace: {route.metadata.namespace}'
                            self.failed_alerts.append({
                                'object': route,
                                'message': msg
                            })
                            self.log.info(msg)

    def process_remediations(self):
        for alert in self.failed_alerts:
            route = alert['object']
            updated_route = self.client.update_route(
                object_name=route.metadata.name,
                namespace=route.metadata.namespace,
                definition={'metadata': {'annotations': {'kubernetes.io/tls-acme-paused': None}}}
            )
            if updated_route and 'kubernetes.io/tls-acme-paused' not in updated_route.metadata.annotations.keys():
                alert['remediated'] = True
                msg = f'Route {route.metadata.name} remediation successful; Namespace: {route.metadata.namespace}'
            else:
                alert['remediated'] = False
                msg = f'Route {route.metadata.name} remediation failed; Namespace: {route.metadata.namespace}'

            self.log.info(msg)
