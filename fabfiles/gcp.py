import dns.resolver
import json

from fabric.api import env, task, local, run
from fabric.colors import red, green, blue, yellow
from fabric.utils import puts


# GCP SETTINGS
################################################################################
GCP_PROJECT = 'kolibri-demo-servers'
GCP_REGION = 'us-east1'
GCP_ZONE = 'us-east1-d'

# VM SETTINGS
################################################################################
GCP_IMAGE_PROJECT = 'debian-cloud'  # run `gcloud compute images list` available
GCP_IMAGE_NAME = 'debian-10-buster-v20200714'
GCP_BOOT_DISK_SIZE = '30GB'






# QA DEMOSERVERS INVENTORY
################################################################################

inventory = {
    'test3': {
        'hosts':['35.185.77.25'],
        'channels_to_import': [
            '95a52b386f2c485cb97dd60901674a98',
        ],
        'facility_name': 'test3',
        'hostname': 'test3.learningequality.org',
    },
    'pradigi-demo': {  # 60GB = used by the Pratham for testing PraDigi channel
        'hosts':['35.196.179.152'],
        'channels_to_import': [], # 'f9da12749d995fa197f8b4c0192e7b2c'],  # PraDigi
        'facility_name': 'PraDigi Demo Server',
        'hostname': 'pradigi-demo.learningequality.org',
    },
    #
    # QA DEMO SERVERS
    'pradigi-demo-backup': {    # 30GB = contains 3-4 channels undergoing Q/A
        'hosts':['35.196.115.213'],
        'channels_to_import': [],
        'facility_name': 'pradigi demo backup',
        'hostname': '35.196.115.213',
    },
    'davemckee-demo': {         # 100GB = contains 5-10 channels undergoing Q/A
        'hosts':['35.231.153.103'],
        'channels_to_import': [],
        'facility_name': 'Dave McKee Demo',
        'hostname': 'davemckee-demo.learningequality.org',
    },
    'alejandro-demo': {         # 300GB = contains 10-20 channels undergoing Q/A
        'hosts':['35.227.71.104'],
        'channels_to_import': [
            'da53f90b1be25752a04682bbc353659f',  # Ciencia NASA
            '2748b6a3569a55f5bd6e35a70e2be7ee',  # EDSITEment
            'e66cd89375845ebf864ea00005be902d',  # ELD Teacher Professional Course
            '1d13b59b62b85470b61483fa63c530a2',  # Libretext OER Library
            'd6a3e8b17e8a5ac9b021f378a15afbb4',  # ReadWriteThink
            # '668a1d198f2e5269939df31dd8c36efb',  # TED Talks Arabic Subtitles
        ],
        'facility_name': 'alejandro demo',
        'hostname': 'alejandro-demo.learningequality.org',
    },
    'demo-ar': {                # Madrasati Excel sheets link to this server
        'hosts':['35.246.148.139'],
        'channels_to_import': [],
        'facility_name': 'New Arabic Demo',
        'hostname': 'kolibridemo-ar.learningequality.org',
    },
    'openupresources-demo': {   # Used for Profuturo channels testing
        'hosts':['104.196.183.152'],
        'channels_to_import': [],
        'facility_name': 'OLD OpenUp Resources (Illustrative Mathematics) demo',
        'hostname': 'openupresources-demo.learningequality.org',
    },
}


# PROVISIONING
################################################################################

@task
def create(instance_name, region=GCP_REGION, zone=GCP_ZONE, disk_size=GCP_BOOT_DISK_SIZE, address_name=None):
    """
    Create a GCP instance `instance_name` and associate a new static IP with it.
    If `address_name` is given (an existing static IP) it will be used.
    """
    # puts(green('You may need to run `gcloud init` before running this command.'))
    # STEP 1: reserve a static IP address
    if address_name is None:
        address_name = instance_name
        reserve_ip_cmd =  'gcloud compute addresses create ' + address_name
        reserve_ip_cmd += ' --project ' + GCP_PROJECT
        reserve_ip_cmd += ' --region ' + region
        local(reserve_ip_cmd)
    # STEP 2: provision instance
    create_cmd =  'gcloud compute instances create ' + instance_name
    create_cmd += ' --project ' + GCP_PROJECT
    create_cmd += ' --zone ' + zone
    create_cmd += ' --machine-type f1-micro'
    create_cmd += ' --boot-disk-size ' + disk_size
    create_cmd += ' --image-project ' + GCP_IMAGE_PROJECT
    create_cmd += ' --image ' + GCP_IMAGE_NAME
    create_cmd += ' --address ' + address_name
    create_cmd += ' --tags http-server,https-server'
    create_cmd += ' --format json'
    cmd_out = local(create_cmd, capture=True)
    cmd_result = json.loads(cmd_out)
    new_ip = cmd_result[0]['networkInterfaces'][0]['accessConfigs'][0]['natIP']
    puts(green('Created demo instance ' + instance_name + ' with IP ' + new_ip))
    puts(green('Add this paragraph to the dict `inventory` in `fabfiles/gcp.py`:'))
    puts(blue("    '%s': {"                                     % instance_name    ))
    puts(blue("        'hosts':['%s'],"                         % new_ip           ))
    puts(blue("        'channels_to_import': [],"                                  ))
    puts(blue("        'facility_name': '" + instance_name.replace('-', ' ') + "',"))
    puts(blue("        'hostname': '%s.learningequality.org',"  % instance_name    ))
    puts(blue("    },"                                                             ))


@task
def delete(instance_name, region=GCP_REGION, zone=GCP_ZONE, address_name=None):
    """
    Delete the GCP instance `instance_name` and it's associated IP address.
    """
    delete_cmd = 'gcloud compute instances delete ' + instance_name + ' --quiet'
    delete_cmd += ' --project ' + GCP_PROJECT
    delete_cmd += ' --zone ' + zone
    local(delete_cmd)
    if address_name is None:
        address_name = instance_name
    delete_ip_cmd = 'gcloud compute addresses delete ' + address_name + ' --quiet'
    delete_ip_cmd += ' --project ' + GCP_PROJECT
    delete_ip_cmd += ' --region ' + region
    local(delete_ip_cmd)
    puts(green('Deleted instance ' + instance_name + ' and its static IP.'))



# INVENTORY UTILS
################################################################################

@task
def list_instances(tsv=None):
    """
    Show list of all currently running demo instances.
    Optional tsv argument for easy copy-pasting into spreadsheets.
    """
    cmd = 'gcloud compute instances list'
    cmd += ' --project=kolibri-demo-servers'
    # cmd += ' --format=yaml'
    if tsv is not None:
        cmd += ' --format="csv[separator=\'\t\']('
        cmd += '''name,
                  zone.basename(),
                  networkInterfaces[0].accessConfigs[0].natIP:label=EXTERNAL_IP,
                  creationTimestamp.date(tz=LOCAL)
                  )"'''
    local(cmd)


@task
def checkdiskspace():
    """
    Check available disk space on all demo servers.
    """
    puts(blue('Checking available disk space on all demo servers.'))
    demo_servers = list(env.roledefs.items())
    for role_name, role in demo_servers:
        assert len(role['hosts'])==1, 'Multiple hosts found for role'
        print('role_name', role_name)
        env.host_string = role['hosts'][0]
        run('df -h | grep /dev/sda1')


@task
def checkdns():
    """
    Checks if DNS lookup matches hosts IP.
    """
    puts(blue('Checking DNS records for all demo servers.'))
    for role_name, role in env.roledefs.items():
        assert len(role['hosts'])==1, 'Multiple hosts found for role'
        host_ip = role['hosts'][0]
        hostname = role.get('hostname')
        if hostname:
            results = []
            try:
                for rdata in dns.resolver.query(hostname, 'A'):
                    results.append(rdata)
                results_text = [r.to_text().rstrip('.') for r in results]
                if host_ip in results_text:
                    print('DNS for', role_name, 'OK')
                else:
                    print('WRONG DNS for', role_name, 'Hostname:', hostname, 'Expected:', host_ip, 'Got:', results_text)
            except dns.resolver.NoAnswer:
                print('MISSING DNS for', role_name, 'Hostname:', hostname, 'Expected:', host_ip)



# HOST UTILS
################################################################################

@task
def info():
    puts(green('Python version:'))
    run('python --version')
    puts(green('/kolibrihome contains:'))
    run('ls -ltr /kolibrihome')
    puts(green('Running processes:'))
    run('ps -aux')

@task
def shell():
    puts(green('TO connect to the server run:'))
    puts(blue('ssh ' + env.user + '@' + env.host_string))
