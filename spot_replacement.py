"""Cyclecloud API demo"""
from subprocess import check_call
import json
import typing
from cyclecloud.client import Client, Record
import logging
import sys
from hpc.autoscale.util import json_dump
from retry import retry

from uuid import uuid4

from hpc.autoscale.job.demandcalculator import new_demand_calculator
from hpc.autoscale.job.demandprinter import print_demand
from hpc.autoscale.job.job import Job
from hpc.autoscale.node.nodemanager import NodeManager, new_node_manager


CC_CONFIG: typing.Dict[str, typing.Any] = {
    "url": "https://localhost:8443",  # Or your CC URL
    "username": "USER",
    "password": "PASS",
    "verify_certificates": False,
    "cluster_name": "CLUSTER_NANE"
}

logging.basicConfig(
    format="%(asctime)-15s: %(levelname)s %(message)s",
    stream=sys.stderr,
    level=logging.DEBUG,
)        


BASE_CLUSTER_PARAMS: typing.Dict[str, typing.Any] = {
    "TargetCount" : 5,
    "NodeArray" : "execute-spot"
}




def scale_nodearray_to_target_demand(cluster_name, nodearray, target_count, shuffle=True, dry_run=False) -> None:

    client = Client(CC_CONFIG)

    print("Scaling nodearray {} in cluster {} to {} nodes".format(nodearray, cluster_name, target_count))

    """
    We're simply doing a "Target Count" style allocation, so we could simply use the NodeMgr API here.
    But we're using the DemandCalculator API to provide a basis for a more advanced autoscaler later.
    """
    dcalc = new_demand_calculator(CC_CONFIG)
    node_mgr = dcalc.node_mgr
    vm_sizes = [bucket.vm_size for bucket in node_mgr.get_buckets()]

    # Simple means to spread the demand across machine types to avoid spot capacity issues
    # Sample Constraint (showing how it could be extended to add preference for spot over non-spot as
    # well as vm_sizes preference)
    #     {"or": [{"node.vm_size": "Standard_NC6", "node.spot": true},
    #             {"node.vm_size": "Standard_F16", "node.spot": false}]}

    machine_type_selection_order = [{"node.vm_size": vm_size} for vm_size in vm_sizes]
    if shuffle:
        # Spread the requests across machine types to avoid spot capacity issues
        import random
        random.shuffle(machine_type_selection_order)
    constraint_set = {"node.nodearray": nodearray, "exclusive": True, "ncpus": 1, "or": machine_type_selection_order}
    job = Job(
            name="placeholder_job",
            constraints=constraint_set,
            # node_count=target_count,
            iterations=target_count,
            packing_strategy="scatter"
        )
    dcalc.add_job(job)
    demand_result = dcalc.finish()

    if not dry_run:
        dcalc.bootup()

    # note that /ncpus will display available/total. ncpus will display the total, and
    # *ncpus will display available.
    print("Constraints:")
    print(constraint_set)
    print_demand(["name", "job_ids", "nodearray", "/ncpus", "vm_size", "pcpu_count"], demand_result)


def scale_nodearray_to_target_count(cluster_name, nodearray, target_count, shuffle=True, dry_run=False) -> None:

    client = Client(CC_CONFIG)

    print("Scaling nodearray {} in cluster {} to {} nodes".format(nodearray, cluster_name, target_count))

    """
    We're simply doing a "Target Count" style allocation, so we can simply use the NodeMgr API here.
    Using the DemandCalculator API would provide a basis for a more advanced autoscaler later.
    """
    node_mgr:NodeManager = new_node_manager(CC_CONFIG)
    vm_sizes = [bucket.vm_size for bucket in node_mgr.get_buckets()]

    # Simple means to spread the demand across machine types to avoid spot capacity issues
    # Sample Constraint (showing how it could be extended to add preference for spot over non-spot as
    # well as vm_sizes preference)
    #     {"or": [{"node.vm_size": "Standard_NC6", "node.spot": true},
    #             {"node.vm_size": "Standard_F16", "node.spot": false}]}

    machine_type_selection_order = [{"node.vm_size": vm_size} for vm_size in vm_sizes]
    if shuffle:
        # Spread the requests across machine types to avoid spot capacity issues
        import random
        random.shuffle(machine_type_selection_order)
    constraint_set = {"node.nodearray": nodearray, "exclusive": True, "ncpus": 1, "or": machine_type_selection_order}

    node_mgr.allocate(constraints=constraint_set, node_count=target_count,
                      allow_existing=True, all_or_nothing=False)

    allocation_results = None
    if not dry_run:
        allocation_results = node_mgr.bootup()
        if allocation_results.nodes:
            print("Auto-starting:")
            for node in allocation_results.nodes:
                print("Name {}   NodeArray {}   Machine Type {}   CPUs {}".format(node.name, node.nodearray, node.vm_size, node.vcpu_count))
        elif allocation_results.status == "success":
            print("No additional nodes required.")
        else:
            print("Result: {}".format(allocation_results))

    
if __name__ == "__main__":

    import getpass

    print('Enter CycleCloud url, username and password.')
    url = input('CycleCloud URL: ({})'.format(CC_CONFIG['url'])) or CC_CONFIG['url']
    username = input('username: ({})'.format(CC_CONFIG['username'])) or CC_CONFIG['username']
    passwd = getpass.getpass('password: ')
    cluster_name = input('Cluster Name: ({})'.format(CC_CONFIG['cluster_name'])) or CC_CONFIG['cluster_name']
    CC_CONFIG['url'] = url
    CC_CONFIG['username'] = username
    CC_CONFIG['password'] = passwd
    CC_CONFIG['cluster_name'] = cluster_name


    print("***************************")
    print("Maintain Target Scale Demo")
    print("***************************")

    nodearray = input('NodeArray Name: ({})'.format(BASE_CLUSTER_PARAMS['NodeArray'])) or BASE_CLUSTER_PARAMS['NodeArray']
    target_count = int(input('Target Node Count: ({})'.format(BASE_CLUSTER_PARAMS['TargetCount'])) or BASE_CLUSTER_PARAMS['TargetCount'])

    shuffle = input('Shuffle Spot? (true)').lower() in {'', 'y', 'yes', 'true'} or False
    dry_run = input('Dry Run? (false)').lower() in {'y', 'yes', 'true'} or False

    scale_nodearray_to_target_count(cluster_name, nodearray, target_count, shuffle=shuffle, dry_run=False)
