import os

from fabric.api import env



# FAB SETTTINGS
################################################################################
env.user = os.environ.get('USER')  # assume ur local username == remote username
env.roledefs = {}  # combined roles from inventory and integrationservers
env.password = os.environ.get('SUDO_PASSWORD')


# PREREQUISITES
################################################################################
# 1. SusOps engineer be part of the GCP project kolibri-demo-servers
# 2. The username $USER must be one of the default accounts created on instances
# see https://console.cloud.google.com/compute/metadata?project=kolibri-demo-servers


# PROVISIONING
################################################################################
from fabfiles.gcp import inventory
from fabfiles.gcp import create, delete
from fabfiles.gcp import list_instances, check_dns, check_diskspace
from fabfiles.gcp import exec, shell, pypsaux

env.roledefs.update(inventory)  # QA demoservers inventory (GCP VMs)


# DEMOSERVERS
################################################################################
from fabfiles.demoservers import demoserver, update_kolibri
from fabfiles.demoservers import import_channel, import_channels
from fabfiles.demoservers import restart_kolibri, stop_kolibri


# PROXY SERVICE
################################################################################
from fabfiles.proxyservice import check_proxies, update_proxy_servers
from fabfiles.proxyservice import install_squid_proxy, update_squid_proxy
from fabfiles.proxyservice import uninstall_squid_proxy


# CHEFOPS
################################################################################
from fabfiles.chefops import integrationservers
from fabfiles.chefops import run_chef, setup_chef, unsetup_chef, update_chef

env.roledefs.update(integrationservers)  # content integration servers (vader)


# CATALOG SERVER CHECKS
################################################################################
from fabfiles.catalogservers import check_catalog_channels


# GITHUB
################################################################################
from fabfiles.github import create_github_repo, list_chef_repos, list_pipeline_repos


# CODE REPORTS
################################################################################
from fabfiles.codereports import local_setup_chef, local_update_chef, local_unsetup_chef
from fabfiles.codereports import analyze_chef_repo, analyze_chef_repos

