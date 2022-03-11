"""Cyclecloud API cleanup_failed_nodes"""
from subprocess import check_call
import json
from cyclecloud.client import Client, Record
import logging
import sys
from retry import retry
from urllib.parse import urlencode

from uuid import uuid4


CC_CONFIG = {
    "url": "http://localhost:8080",  # Or your CC URL
    "username": "your-username",
    "password": "your-password",
    "verify_certificates": False,
    "cluster_name" : "your-cluster-name"
}

logging.basicConfig(
    format="%(asctime)-15s: %(levelname)s %(message)s",
    stream=sys.stderr,
    level=logging.DEBUG,
)        



class ClusterTimeoutError(Exception):
    pass



class Cluster:
    
    def __init__(self, cluster_name, config, logger=None):
        self.cluster_name = cluster_name
        
        self.config = config
        self.logger = logger or logging.getLogger()

        self.client = Client(config)
    
    def status(self):
        '''pprint.pprint(json.dumps(json.loads(dougs_example)))'''
        return self.get("/clusters/%s/status" % self.cluster_name)

    def retry(self):
        response_raw = self.post("/cloud/actions/retry/%s" % self.cluster_name)
        try:
            return json.loads(response_raw)
        except:
            raise RuntimeError("Could not parse response as json to retry! '%s'" % response_raw)
    

    def all_nodes(self):
        return self.get("/clusters/%s/nodes" % self.cluster_name)

    def nodes(self, request_ids):
        responses = {}
        for request_id in request_ids:
            params = {'request_id': request_id}
            responses[request_id] = self.get(f"/clusters/{self.cluster_name}/nodes", params=params)
        return responses
    
    def nodes_by_operation_id(self, operation_id):
        if not operation_id:
            raise RuntimeError("You must specify operation id!")
        params = { 'operation': operation_id }
        return self.get(f"/clusters/{self.cluster_name}/nodes", params=params)

    
    def terminate(self, node_ids=[]):
        '''Terminate by NodeId
        Terminating by NodeId is STRONGLY preferred because hostname may be reused
        (in the case of Spot this can cause termination of valid nodes)'''

        self.logger.warning("Terminating the following nodes by id: %s", node_ids)
        
        
        response_raw = None
        try:
            response_raw = self.post(f"/clusters/{self.cluster_name}/nodes/terminate", body=json.dumps({"ids": node_ids}))
        except Exception as e:
            if "No instances were found matching your query" in str(e):
                return
            raise
        
        self.logger.warning(json.loads(response_raw))
        return json.loads(response_raw)


    def terminate_by_hostname(self, hostnames=[]):
        '''Terminate by Hostname
        Prefer terminating by NodeId if possible.'''

        self.logger.warning("Terminating the following nodes by hostnames: %s", hostnames)
        f = urlencode('HostName in {%s}' % ",".join('"%s"' % x for x in hostnames))
        
        response_raw = None
        try:
            params = { 'instance-filter': f }
            response_raw = self.post(f"/cloud/actions/terminate_node/{self.cluster_name}", params=params)
        except Exception as e:
            if "No instances were found matching your query" in str(e):
                return
            raise
        self.logger.warning(json.loads(response_raw))
        return json.loads(response_raw)
            
    def post(self, url, body=None, params={}, headers={}):
        root_url = self.config['url']
        full_url = root_url + url
        self.logger.info("POST %s params %s headers %s body %s", full_url, params, headers, body)
        
        response = self.client.session._request("POST", full_url, params, headers, body)
        response_content = response.text
        if response_content is not None and isinstance(response_content, bytes):
            response_content = response_content.decode()
        if response.status_code < 200 or response.status_code > 299:
            raise ValueError(response_content)
        return response_content
        
    def get(self, url, body=None, params={}, headers={}):
        root_url = self.config['url']
        full_url = root_url + url        
        self.logger.info("GET %s params %s headers %s body %s", full_url, params, headers, body)

        response = self.client.session._request("GET", full_url, params, headers, body)
        response_content = response.text
        if response_content is not None and isinstance(response_content, bytes):
            response_content = response_content.decode()

        if response.status_code < 200 or response.status_code > 299:
            raise ValueError(response_content)
        return json.loads(response_content)

    
def terminate_failed_nodes(cluster_name):

    print(f"Terminating Failed Nodes for cluster : {cluster_name}")

    cluster = Cluster(cluster_name, CC_CONFIG)


    try:
        all_nodes = cluster.all_nodes()
    except:
        logger.exception("Azure CycleCloud experienced an error and the get return request failed. %s", e)

    failed_nodes=[]
    for node in all_nodes['nodes']:
        node_name = node.get("Name")
        hostname = node.get("Hostname")
        node_status = node.get("Status")

        print(f"Cluster Node: {node_name}   Host: {hostname}  Status: {node_status}")

        report_failure_states = ["Unavailable", "Failed"]
        if node_status in report_failure_states:
            failed_nodes.append(node)

    if failed_nodes:
        print(f"The following nodes are unhealthy: {failed_nodes}")
        input("Press a enter to terminate...") 

        failed_node_ids = [n['NodeId'] for n in failed_nodes]
        print(f"Terminating nodes : {failed_node_ids}")
        try:
            cluster.terminate(failed_node_ids)
        except:
            logger.exception("Azure CycleCloud experienced an error and the get return request failed. %s", e)

    
if __name__ == "__main__":

    import getpass

    print('Enter CycleCloud url, username and password.')
    url = input('CycleCloud URL: ({})'.format(CC_CONFIG['url'])) or CC_CONFIG['url']
    username = input('username: ({})'.format(CC_CONFIG['username'])) or CC_CONFIG['username']
    passwd = getpass.getpass('password: ')
    cluster_name = input('cluster_name: ({})'.format(CC_CONFIG['cluster_name'])) or CC_CONFIG['cluster_name']    
    CC_CONFIG['url'] = url
    CC_CONFIG['username'] = username
    CC_CONFIG['password'] = passwd
    CC_CONFIG['cluster_name'] = cluster_name

                      
    print("***************************")
    terminate_failed_nodes(cluster_name)

