# Azure CycleCloud REST API and Autoscaling with Scalelib

This demo shows some minimal examples of how the Azure CycleCloud REST API and cyclecloud-scalelib library can
be used to implement custom autoscaling and automated cluster operations in Azure CycleCloud clusters.

See the [cyclecloud-scalelib project](https://github.com/Azure/cyclecloud-scalelib) for detailed usage and 
examples on building your own autoscaler with Azure CycleCloud

## Pre-Requisites

This demo expects that you have a working [CycleCloud Installation](https://docs.microsoft.com/en-us/azure/cyclecloud/how-to/install-manual?view=cyclecloud-8) and understand the [basics of CycleCloud](https://docs.microsoft.com/en-us/azure/cyclecloud/overview?view=cyclecloud-8)
and the [core concepts](https://docs.microsoft.com/en-us/azure/cyclecloud/concepts/core?view=cyclecloud-8) of CycleCloud Clusters.

It also requires python 3.8 or later.
## Packaging

1. Clone the Repository
2. Run the python packaging script to create a redistributable demo tarball

    ```bash
    python3 ./package.py
    ```

3. Extract the dist tarball

    ```bash
    tar xzf ./dist/cyclecloud-demo-*.tar.gz
    ```

4. Create a python virtual environment for the demo

    ```bash
    cd cyclecloud-demo
    ./install.sh
    ```

5. Activate the virtual environment:

    ```bash
    . ~/.virtualenvs/autoscale_demo/bin/activate
    ```

6. Edit `demo.py` to set your local CycleCloud configuration

    ```python
    CC_CONFIG = {
        "url": "https://localhost:8443",  # Or your CC URL
        "username": "USER",
        "password": "PASS",
        "verify_certificates": False
    }
    ```

7. Optionally, change the cluster configuration parameters:

   ```python
   BASE_CLUSTER_PARAMS = {
        "Credentials" : "azure",  # Or your CC account name
        "AzccMachineTypes" : ["Standard_F72S_v2", "Standard_D2_v3"],
        "SubnetId" : "SUBNET_ID",
        "ImageName" : "cycle.image.centos7",
        "UseLowPrio" : False,
        "Region" : "REGION"
    }
    ```

8. Start the demo:

    ```bash
    python3 ./demo.py
    ```

The demo should create a cluster named "apiTest" and begin scaling it up.  
In the console, the demo should show your subscription's current quotas modified by limits imposed
by the NodeArrays in the cluster.   That information is used to provide the autoscaler the current 
`AvailableCoreCount` and `AvailableCount` (VM instances) in your subscription for each VM SKU.

The autoscaler uses that information to decide which SKU to scale up.

