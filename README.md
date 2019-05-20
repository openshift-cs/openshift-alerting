# Deployment

1. (Optional) If monitoring multiple clusters, create ServiceAccount

    - If `REMEDIATION` is enabled, create a SA with `dedicated-admin` 
    or `cluster-admin` access

    - If `REMEDIATION` is disabled, create SA with `dedicated-reader`
    or `cluster-reader` access
    
    ```bash 
    $ oc create sa <sa-name>
    ```
          
2. Deploy application

    ```bash
    $ oc new-app https://github.com/openshift-cs/openshift-alerting
    ```
       
3. Provide credentials to deployment

    - For single-cluster alerting only, you can rely on the _in cluster_ 
    configuration. You also _must_ deploy the application in either `dedicated-reader`
    or `dedicated-admin` projects in order to inherit the proper rolebindings
    
        ```bash
        # Configure the application to rely on the pod's SA's credentials
        $ oc set env dc/openshift-alerting INTERNAL_CLUSTER=true
        ```
        
    - For multi-cluster alerting, you can generate a _kubeconfig_ for 
    the SA. 
    
        ```bash
        # Do this for each cluster, and manually combine them into one kubeconfig file
        $ oc sa create-kubeconfig <sa-name> > <file>
        # Create a Secret with the kubeconfig file
        $ oc create secret generic kubeconfig --from-file=kube.config=<file>
        # Add the secret to the deployment
        $ oc set volume dc/openshift-alerting --add --mount-path=/kube --secret-name=kubeconfig
        # Configure the application to use the context(s)
        $ oc set env dc/opepnshift-alerting KUBE_CONFIG_FILE=/kube/kube.config CLUSTER_CONTEXTS=context_1,context_2,context_N
        ```

# Configuration

The configuration of this application is controlled by environment variables.
These can either be set initially with `oc new-app -e`, or adjusted later
with `oc set env`.

- SMTP Configuration options:
    - SMTP_HOST (default: localhost)
    - SMTP_PORT (default: 25)
    - SMTP_USE_TLS (default: true)
    - SMTP_USER
    - SMTP_PASS
- INTERNAL_CLUSTER (default: false) - Use the pod's assigned ServiceAccount credentials
- KUBE_CONFIG_FILE (Required if INTERNAL_CLUSTER=false)
- CLUSTER_CONTEXTS (default: current) - A comma separated list of contexts from the KUBE_CONFIG_FILE, ignored if `INTERNAL_CLUSTER`=true
- REMEDIATION (default: false) - Whether or not to perform automatic remediation
- SCHEDULE_DELAY (default: 30) - Seconds to sleep before checking for new jobs
- SKIP_EMAIL_FOR_SUCCESSFUL_REMEDIATION (default: false) - Prevents alert emails if *all* alerts were successfully remediated
- LOGGING_LEVEL (default: INFO) - The level of logging output to produce

# Examples

## Deploy remediation with in-cluster configuration

```bash
$ oc project dedicated-admin
$ oc new-app https://github.com/openshift-cs/openshift-alerting \
    -e REMEDIATION=true \
    -e INTERNAL_CLUSTER=true \
    -e SMTP_HOST=smtp.mandrillapp.com \
    -e SMTP_PORT=587
```

## Deploy alerting only with in-cluster configuration

```bash
$ oc project dedicated-reader
$ oc new-app https://github.com/openshift-cs/openshift-alerting \
    -e INTERNAL_CLUSTER=true \
    -e SMTP_HOST=smtp.mandrillapp.com \
    -e SMTP_PORT=587
```

## Deploy remediation for several clusters

```bash
# Get cluster1 credentials
$ oc login https://api.cluster1.openshift.com
$ oc project dedicated-admin
$ oc create sa cluster1-alerting-and-remediation
$ oc sa create-kubeconfig cluster1-alerting-and-remediation > cluster1-kube.config
# Get cluster2 credentials
$ oc login https://api.cluster2.openshift.com
$ oc project dedicated-admin
$ oc create sa cluster2-alerting-and-remediation
$ oc sa create-kubeconfig cluster2-alerting-and-remediation > cluster2-kube.config
# STOP: Manually merge cluster1-kube.config and cluster2-kube.config into 1 coherent combined-kube.config
#   YAML merging can be assisted by the `yq` tool: https://github.com/mikefarah/yq
#       yq merge --append --inplace cluster1-kube.config cluster2-kube.config]
# Deploy application into its own project
$ oc new-project my-openshift-alerting
$ oc create secret generic kubeconfig --from-file=kube.config=combined-kube.config
$ oc new-app https://github.com/openshift-cs/openshift-alerting \
    -e REMEDIATION=true \
    -e KUBE_CONFIG_FILE=/kube/kube.config \
    -e CLUSTER_CONTEXTS=cluster1-alerting-and-remediation,cluster2-alerting-and-remediation \
    -e SMTP_HOST=smtp.mandrillapp.com \
    -e SMTP_PORT=587
$ oc set volume dc/openshift-alerting --add --mount-path=/kube --secret-name=kubeconfig
```

# Contributing

## Adding alert plugins

1. Create a python module within the `alerts/` directory

2. Create a class within the new module that _must_ inherit the `BaseAlert` abstract class

    ```python
    from . import BaseAlert

    class MyNewAlert(BaseAlert):
        pass
    ```

3. Implement the required methods, `process_alerts` and `process_remediations`

    ```python
    def process_alerts(self):
        pass
        
    def process_remediations(self):
        pass
    ```

    - `process_alerts` should rely on the `self.failed_alerts` list by appending a dictionary for every object that fails the desired test
    
        ```python
        # Dictionary definition that should be added to `self.failed_alerts`
        self.failed_alerts.append({
            'object': ResourceField,  # Object to perform remediation on
            'message': 'Alert message'  # Message that is sent within the alert email
        })
        
        # It is also generally a good idea to log out the alert message to stdout
        self.log.info('Alert message')
        ```
        
    - `process_remediations` should iterate over `self.failed_alerts` to attempt remediations. If the remediation succeeds or fails, you should update the dictionary as follows
    
        ```python
        for alert in self.failed_alerts:
            if remediation_succeeds:
                alert['remediated'] = True
            else:
                alert['remediated'] = False
        ```
        
    - If it is not possible or desired to remediate automatically, then leave the method definition empty
    
        ```python
        def process_remediations(self):
            pass
        ```
