import sys
from cyclecloud.client import Client
from cyclecloud.api import clusters

CC_CONFIG = {
    "url": "https://localhost:8443",  # Or your CC URL
    "username": "USER",
    "password": "PASS",
    "verify_certificates": False
}

cluster_name = sys.argv[1]
array_name = sys.argv[2]
target_cores = sys.argv[3]

cl1 = Client(CC_CONFIG)

# gets a Cluster object for the cluster
cluster_obj = cl1.clusters[cluster_name]

# prints the current state of the cluster
print(cluster_obj.get_status().state)

# start up to N new cores
cluster_obj.scale_by_cores(array_name, target_cores)
