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

- LOGGING_LEVEL (default: INFO)
- SMTP_HOST (default: localhost)
- SMTP_PORT (default: 25)
- SMTP_USE_TLS (default: true)
- SMTP_USER
- SMTP_PASS
- CLUSTER_CONTEXTS (default: current)
- INTERNAL_CLUSTER (default: false)
- REMEDIATION (default: false)
- KUBE_CONFIG_FILE (Required with INTERNAL_CLUSTER=false)
- DEBUG (default: false)
- SCHEDULE_DELAY (default: 30) - Seconds to sleep before checking for new jobs

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