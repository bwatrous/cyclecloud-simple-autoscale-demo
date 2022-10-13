"""Cyclecloud API demo"""
import argparse
import getpass
import logging
import sys

from hpc.autoscale.node.nodemanager import new_node_manager

CC_CONFIG = {
    "url": "http://localhost:8080",  # Or your CC URL
    "username": "USER",
    "password": "PASS",
    "verify_certificates": False,
    "cluster_name": ""
}

logging.basicConfig(
    format="%(asctime)-15s: %(levelname)s %(message)s",
    stream=sys.stderr,
    level=logging.DEBUG,
)


def deallocate_nodes(node_mgr, cluster_name, nodearray_name):
    print("Deallocating nodes : {}".format(nodearray_name))

    node_mgr.deallocate_nodes(
        [x for x in node_mgr.get_nodes() if x.nodearray == nodearray_name]
    )


def add_nodes(node_mgr, cluster_name, nodearray_name, count=1, sku=""):
    print("Adding nodes to cluster: {} nodearray: {}".format(cluster_name, nodearray_name))

    # Show available capacity before:
    print("Capacity BEFORE scale up")
    buckets = node_mgr.get_buckets()
    for bucket in buckets:
        print(bucket)

    # allocate by  node (vs slot)
    selector = {"node.nodearray": nodearray_name}
    print("sku")
    print(sku)
    if sku:
        selector["node.vm_size"] = sku
    r = node_mgr.allocate(selector, node_count=count)
    print("About to START nodes")
    node_mgr.bootup()

    # Show capacity after
    print("Capacity AFTER scale up")
    buckets = node_mgr.get_buckets()
    for bucket in buckets:
        print(bucket)


def main():
    parser = argparse.ArgumentParser(description="usage: %prog [options]")

    parser.add_argument("--action", dest="action", default="start", help="[Start | Stop]")
    parser.add_argument("--clustername", dest="cluster_name", default=CC_CONFIG["cluster_name"], help="Cluster name")
    parser.add_argument("--nodearray", dest="nodearray", default="persistent-execute", help="Node array name")
    parser.add_argument("--sku", dest="sku", default="", help="Force specific SKU selection")
    parser.add_argument("--count", dest="count", default=1, help="Node count")
    parser.add_argument("--url", dest="url", default=CC_CONFIG["url"], help="CC URL")
    parser.add_argument("--username", dest="username", default=CC_CONFIG["username"], help="CC Username")
    parser.add_argument("--password", dest="password", default=None, help="CC Password")

    args = parser.parse_args()
    
    if not args.password:
        print("Enter CycleCloud password.")
        args.password = getpass.getpass("password: ")

    CC_CONFIG["url"] = args.url
    CC_CONFIG["username"] = args.username
    CC_CONFIG["password"] = args.password
    CC_CONFIG["cluster_name"] = args.cluster_name
    node_mgr = new_node_manager(CC_CONFIG)

    if args.action.lower() == "stop":
        deallocate_nodes(node_mgr, args.cluster_name, args.nodearray)
    else:
        add_nodes(node_mgr, args.cluster_name, args.nodearray, count=int(args.count),sku=args.sku)


if __name__ == "__main__":
    main()
