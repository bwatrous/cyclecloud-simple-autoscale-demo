"""Cyclecloud API demo"""
from subprocess import check_call
import json
from cyclecloud.client import Client, Record
import logging
import sys
from retry import retry

from uuid import uuid4

from hpc.autoscale.example.readmeutil import clone_dcalc, example, withcontext
from hpc.autoscale.hpctypes import Memory
from hpc.autoscale.node.constraints import BaseNodeConstraint
from hpc.autoscale.node.node import Node, UnmanagedNode
from hpc.autoscale.node.nodemanager import new_node_manager
from hpc.autoscale.results import DefaultContextHandler, SatisfiedResult



CC_CONFIG = {
    "url": "https://localhost:8443",  # Or your CC URL
    "username": "USER",
    "password": "PASS",
    "verify_certificates": False
}

logging.basicConfig(
    format="%(asctime)-15s: %(levelname)s %(message)s",
    stream=sys.stderr,
    level=logging.DEBUG,
)        


BASE_CLUSTER_PARAMS = {
    "Credentials" : "azure",  # Or your CC account name
    "AzccMachineTypes" : ["Standard_F72S_v2", "Standard_D2_v3"],
    "SubnetId" : "SUBNET_ID",
    "ImageName" : "cycle.image.centos7",
    "UseLowPrio" : False,
    "Region" : "REGION",
    "TargetCount" : 500
}



class ClusterTimeoutError(Exception):
    pass


def create_params_file(cluster_name, params):
    params_filename =  "./{}.json".format(cluster_name)
    with open(params_filename, 'w') as f:
        json.dump(params, f)
    return params_filename

def get_node_arrays(client, cluster_name):
    cluster = client.clusters.get(cluster_name)
    s = cluster.get_status()
    return [Record(nodearray.nodearray) for nodearray in s.nodearrays]

def print_node_arrays(client, cluster_name):
    for n in get_node_arrays(client, cluster_name):
        print ("{}".format(str(n)))



def generate_import_params(template_file, cluster_parameters, template_cluster_name):
    params = {"source": "standard"}

    with open(template_file) as f:
        body = f.read()

    # Cluster INI text
    params["cluster"] = body
    # Allow updating existing clusters (vs only creating new clusters)
    params["force"] = "true"
    # The cluster name in the cluster ini text
    params["template"] = template_cluster_name
    # Import as a cluster template (vs creating a cluster instantiation)
    #params["as_template"] = false
    params["parameters"] = json.dumps(cluster_parameters)
    params["parameters_format"] = "json"

    return params


def import_cluster(client, cluster_name, template_file, cluster_parameters, template_cluster_name = None):
    # cluster_name should be url quoted
    import urllib
    quoted_name = urllib.parse.quote(cluster_name, safe="")

    # Quoted Name is the desired new cluster name
    api_path = "/cloud/api/import_cluster/{}".format(quoted_name)
    base_url = client.session._config["url"]
    base_url = base_url.rstrip("/")
    full_url = base_url + api_path        

    verb="POST"
    params = {}
    headers = {}
    if not template_cluster_name:
        template_cluster_name = cluster_name
    body = generate_import_params(template_file, cluster_parameters, template_cluster_name)
    responses = []

    return client.session._request(verb, full_url, params, headers, body)

def show_cluster(client, cluster_name=None, summary=True, include_templates=False):
    # This method replicates the CLI show_cluster method
    # NOTE: It is better to use client.clusters and client.nodes to iterate over clusters
    #       and nodes.
    import urllib
    quoted_name = None
    api_path = "/cloud/clusters"
    if cluster_name:
        quoted_name = urllib.parse.quote(cluster_name, safe="")
        api_path = "/cloud/clusters/{}".format(quoted_name)

    base_url = client.session._config["url"]
    base_url = base_url.rstrip("/")
    full_url = base_url + api_path        

    verb="GET"
    params = {}
    # Use new Cloud.Instance records not legacy types
    params['cloud_instances'] = "true"
    if summary:
        # Return only most critical node attributes
        params['summary'] = "true"
    if include_templates:
        # Show cluster "templates" as well as cluster "instances" 
        params['templates'] = "true"

    headers = {}
    body = None

    return client.session._request(verb, full_url, params, headers, body)
    
def start_cluster(client, cluster_name):
    # cluster_name should be url quoted
    import urllib
    quoted_name = urllib.parse.quote(cluster_name, safe="")

    api_path = "/cloud/actions/startcluster/{}".format(quoted_name)
    base_url = client.session._config["url"]
    base_url = base_url.rstrip("/")
    full_url = base_url + api_path
    
    verb = "POST"
    params = {}
    # Optional, insert a sleep to wait for cluster state to update for more user friendly output
    # params['wait_time'] = 30
    # Start dependent clusters for hierarchical clusters
    # params['recursive'] = false
    # Run cluster-init tests on boot
    # params['test_mode'] = false
    headers = {}
    body = None
    
    return client.session._request(verb, full_url, params, headers, body)

def retry_cluster(client, cluster_name):
    import urllib
    quoted_name = urllib.parse.quote(cluster_name, safe="")

    api_path = "/cloud/actions/retry/{}".format(quoted_name)
    base_url = client.session._config["url"]
    base_url = base_url.rstrip("/")
    full_url = base_url + api_path
    
    verb = "POST"
    params = {}
    # Retry dependent clusters for hierarchical clusters
    # params['recursive'] = false
    headers = {}
    body = None
    
    return client.session._request(verb, full_url, params, headers, body)
    


def terminate_cluster(client, cluster_name):
    # cluster_name should be url quoted
    import urllib
    quoted_name = urllib.parse.quote(cluster_name, safe="")

    api_path = "/cloud/actions/terminatecluster/{}".format(quoted_name)
    base_url = client.session._config["url"]
    base_url = base_url.rstrip("/")
    full_url = base_url + api_path
    
    verb = "POST"
    params = {}
    # Optional, insert a sleep to wait for cluster state to update for more user friendly output
    params['wait_time'] = 30
    # Terminate dependent clusters for hierarchical clusters
    # params['recursive'] = false    
    headers = {}
    body = None
    
    return client.session._request(verb, full_url, params, headers, body)



def delete_cluster(client, cluster_name):
    # cluster_name should be url quoted
    import urllib
    quoted_name = urllib.parse.quote(cluster_name, safe="")

    api_path = "/cloud/actions/removecluster/{}".format(quoted_name)
    base_url = client.session._config["url"]
    base_url = base_url.rstrip("/")
    full_url = base_url + api_path
    
    verb = "POST"
    params = {}
    # Optional, insert a sleep to wait for cluster state to update for more user friendly output
    # params['wait_time'] = 30
    # Force delete cluster even if there were issues deleting some cluster resources
    # params['force'] = false
    # Delete dependent clusters for hierarchical clusters
    # params['recursive'] = false        
    # If set delete the named Cluster Template rather than a specific cluster instantiation
    # params['template'] = false
    params['wait_time'] = 30
    headers = {}
    body = None
    
    return client.session._request(verb, full_url, params, headers, body)


def add_nodes(cluster_name, sku="Standard_F72S_v2", count=1):
    config = dict(CC_CONFIG)
    config["cluster_name"] = "apiTest"
    node_mgr=new_node_manager(config)
    # Optional: add consumable resources for autoscale packing
    node_mgr.add_default_resource({}, "ncpus", "node.vcpu_count")

    # Show available capacity before:
    print("Capacity BEFORE scale up")
    buckets=node_mgr.get_buckets()
    for bucket in buckets:
        print(bucket)
    
    # allocate by  node (vs slot)
    r=node_mgr.allocate({"node.vm_size": sku}, node_count=count)
    print("About to START nodes")
    node_mgr.bootup()

    # Show capacity after
    print("Capacity AFTER scale up")
    buckets=node_mgr.get_buckets()
    for bucket in buckets:
        print(bucket)


def show_nodes(client, cluster_name=None, node_name=None, filter_expr=None, attrs_select=None,
               output_format_str=None, output_format='text'):
    # This method replicates the CLI show_nodes method
    # NOTE: It is generally better to use client.clusters and client.nodes to iterate over clusters
    #       and nodes.
    import urllib
    quoted_name = None
    api_path = "/cloud/api/nodes"
    if node_name:
        quoted_name = urllib.parse.quote(node_name, safe="")
        api_path = "/cloud/api/nodes/{}".format(quoted_name)

    base_url = client.session._config["url"]
    base_url = base_url.rstrip("/")
    full_url = base_url + api_path        

    verb="GET"
    headers = {}
    body = None
    params = {}
    
    # If cluster_name not specified, then a filter is required
    if cluster_name:
        params['cluster'] = cluster_name
    params['summary'] = False
    params['long'] = True

    if output_format:
        # Output text format: text, json, xml, csv, tabular
        params['format'] = output_format

    if attrs_select:
        params['attrs'] = attrs_select

    if output_format_str:
        params['output'] = output_format_str
        if attrs_select:
            print >> sys.stderr, "Both --attrs and --output are specified.  The --attrs option will be dropped."

    params['filter'] = filter_expr

    print("Requesting: {}\nParams: {}".format(full_url, params))
    return client.session._request(verb, full_url, params, headers, body)


def get_node_status(client, cluster_name):
    cluster = client.clusters.get(cluster_name)
    print("Cluster {}".format(cluster_name))
    node_status = []
    for node in cluster.nodes:
        print(node)
        node_status.append(node['Status'])
    return node_status

@retry(ClusterTimeoutError, tries=600)
def wait_for_cluster_termination(client, cluster_name):
    import time
    time.sleep(10)
    node_status = get_node_status(client, cluster_name)
    if all(map(lambda s: s == "Off", node_status)):
        return
    if any(map(lambda s: s == "Failed", node_status)):
        raise Exception("One or more nodes failed unexpectedly in cluster {}".format(cluster_name))
    raise ClusterTimeoutError("Timer expired waiting for nodes in cluster {} to terminate.")
    

def test_cli_cluster_management(cluster_name="cliTest"):

    client = Client(CC_CONFIG)

    cluster_template = "./simple.txt"
    simple_cluster_params = dict(BASE_CLUSTER_PARAMS)
    
    print("Importing cluster : {}".format(cluster_name))
    params_filename = create_params_file(cluster_name, simple_cluster_params)
    check_call(["cyclecloud", "import_cluster", cluster_name, "-c", "simple", "-f", cluster_template, "-p", params_filename, "--force"])

    print_node_arrays(client, cluster_name)

    print("Starting cluster : {}".format(cluster_name))
    check_call(["cyclecloud", "start_cluster", cluster_name])

    print("Modifying configuration for cluster: {}".format(cluster_name))
    simple_cluster_params["AzccMachineTypes"] = [ "Standard_D2_v3", "Standard_D64S_v3", "Standard_F64S_v2", "Standard_F72S_v2" ]
    params_filename = create_params_file(cluster_name, simple_cluster_params)
    check_call(["cyclecloud", "import_cluster", cluster_name, "-c", "simple", "-f", cluster_template, "-p", params_filename, "--force"])

    # IMPORTANT: after adding a new node array,  it needs to  be "Activated" by calling start_cluster again
    check_call(["cyclecloud", "start_cluster", cluster_name])
    

    print("Adding nodearray to cluster: {}".format(cluster_name))
    cluster_template = "./simple_3nodearrays.txt"
    simple_cluster_params["SubnetId2"] = "bewatrouGenomicsDemo/renderdemo/render"
    # simple_cluster_params["Region2"] = "eastus2"
    simple_cluster_params["Region2"] = "westus2"
    params_filename = create_params_file(cluster_name, simple_cluster_params)
    check_call(["cyclecloud", "import_cluster", cluster_name, "-c", "simple", "-f", cluster_template, "-p", params_filename, "--force"])

    print_node_arrays(client, cluster_name)



def test_api_cluster_management(cluster_name="apiTest"):

    client = Client(CC_CONFIG)

    cluster_template = "./simple.txt"
    simple_cluster_params = dict(BASE_CLUSTER_PARAMS)
    
    print("Importing cluster : {}".format(cluster_name))
    r = import_cluster(client, cluster_name, cluster_template, simple_cluster_params, template_cluster_name="simple")
    print("{} : {}".format(r.status_code, r.text))
    
    print_node_arrays(client, cluster_name)

    print("Starting cluster : {}".format(cluster_name))
    r = start_cluster(client, cluster_name)
    print("{} : {}".format(r.status_code, r.text))

    print("Modifying configuration for cluster: {}".format(cluster_name))
    simple_cluster_params["AzccMachineTypes"] = [ "Standard_D2_v3", "Standard_D64S_v3", "Standard_F64S_v2", "Standard_F72S_v2" ]
    r = import_cluster(client, cluster_name, cluster_template, simple_cluster_params, template_cluster_name="simple")
    print("{} : {}".format(r.status_code, r.text))

    print_node_arrays(client, cluster_name)


    print("Adding nodearray to cluster: {}".format(cluster_name))
    cluster_template = "./simple_3nodearrays.txt"
    simple_cluster_params["SubnetId2"] = "bewatrouGenomicsDemo/renderdemo/render"
    # simple_cluster_params["Region2"] = "eastus2"
    simple_cluster_params["Region2"] = "westus2"
    r = import_cluster(client, cluster_name, cluster_template, simple_cluster_params, template_cluster_name="simple")
    print("{} : {}".format(r.status_code, r.text))

    print_node_arrays(client, cluster_name)

    # IMPORTANT: after adding a new node array,  it needs to  be "Activated" by calling start_cluster again
    r = start_cluster(client, cluster_name)
    print("{} : {}".format(r.status_code, r.text))

    print("Adding nodes to cluster: {}".format(cluster_name))
    add_nodes(cluster_name, sku="Standard_D2_v3", count=int(BASE_CLUSTER_PARAMS['TargetCount']))
    get_node_status(client, cluster_name)


    input("Press a enter to terminate...") 

    print("Terminating cluster : {}".format(cluster_name))
    r = terminate_cluster(client, cluster_name)
    print("{} : {}".format(r.status_code, r.text))

    print("Waiting for termination...")
    wait_for_cluster_termination(client, cluster_name)    
    print("All nodes terminated.")

    print("Deleting cluster : {}".format(cluster_name))
    r = delete_cluster(client, cluster_name)
    print("{} : {}".format(r.status_code, r.text))

    



    
if __name__ == "__main__":

    import getpass

    print('Enter CycleCloud url, username and password.')
    url = input('CycleCloud URL: ({})'.format(CC_CONFIG['url'])) or CC_CONFIG['url']
    username = input('username: ({})'.format(CC_CONFIG['username'])) or CC_CONFIG['username']
    passwd = getpass.getpass('password: ')
    CC_CONFIG['url'] = url
    CC_CONFIG['username'] = username
    CC_CONFIG['password'] = passwd

    creds = input('CycleCloud Account Name: ({})'.format(BASE_CLUSTER_PARAMS['Credentials'])) or BASE_CLUSTER_PARAMS['Credentials']
    region = input('Cluster Region: ({})'.format(BASE_CLUSTER_PARAMS['Region'])) or BASE_CLUSTER_PARAMS['Region']
    subnet = input('Cluster Subnet: ({})'.format(BASE_CLUSTER_PARAMS['SubnetId'])) or BASE_CLUSTER_PARAMS['SubnetId']
    target_count = int(input('Target Node Count: ({})'.format(BASE_CLUSTER_PARAMS['TargetCount'])) or BASE_CLUSTER_PARAMS['TargetCount'])

    BASE_CLUSTER_PARAMS['Credentials'] = creds
    BASE_CLUSTER_PARAMS['Region'] = region
    BASE_CLUSTER_PARAMS['SubnetId'] = subnet
    BASE_CLUSTER_PARAMS['TargetCount'] = target_count

    print("***************************")
    print("CLI Demo")
    print("***************************")
    
    # test_cli_cluster_management()
    
    print("***************************")
    print("API Demo")
    print("***************************")
    
    test_api_cluster_management()
