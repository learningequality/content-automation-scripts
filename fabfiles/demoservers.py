from collections import defaultdict
import dns.resolver
import json
import os
import time
import requests
import socket
from urllib.parse import urlparse

from fabric.api import env, task, local, sudo, run, settings
from fabric.api import get, put, require
from fabric.colors import red, green, blue, yellow
from fabric.context_managers import cd, prefix, show, hide, shell_env
from fabric.contrib.files import exists, sed, upload_template
from fabric.utils import puts


# LOCAL SETTINGS
################################################################################
CONFIG_DIR = './config'


# KOLIBRI SETTINGS
################################################################################
KOLIBRI_LANG_DEFAULT = 'en'
KOLIBRI_HOME = '/kolibrihome'
KOLIBRI_PORT = 9090
KOLIBRI_PEX_URL = 'https://github.com/learningequality/kolibri/releases/download/v0.13.3/kolibri-0.13.3.pex'
KOLIBRI_PEX_FILE = os.path.basename(KOLIBRI_PEX_URL.split("?")[0])  # in case ?querystr...
KOLIBRI_USER = 'kolibri'
KOLIBRI_RUN_MODE="demoserver"


KOLIBRI_PROVISIONDEVICE_PRESET = "formal"  # other options "nonformal" "informal"
KOLIBRI_PROVISIONDEVICE_SUPERUSER_USERNAME = "devowner"
KOLIBRI_PROVISIONDEVICE_SUPERUSER_PASSWORD = "admin123"




# HIGH LEVEL API
################################################################################

@task
def demoserver():
    """
    Main setup command that does all the steps.
    """
    install_base()
    download_kolibri()
    configure_nginx()
    configure_kolibri()
    restart_kolibri(post_restart_sleep=30)  # wait for DB migration to happen...
    provisiondevice()
    import_channels()
    restart_kolibri()
    puts(green('Kolibri demo server setup complete.'))


@task
def update_kolibri(kolibri_lang=KOLIBRI_LANG_DEFAULT):
    """
    Use this task to re-install kolibri:
      - (re)download the Kolibri pex from KOLIBRI_PEX_URL
      - overwrite the startup script /kolibrihome/startkolibri.sh
      - overwrite the supervisor script /etc/supervisor/conf.d/kolibri.conf.
    NOTE: this command fails sporadically; try two times and it will work.
    """
    # install_base()  # Mar 4: disabled because Debian 8 repos no longer avail.
    stop_kolibri()
    download_kolibri()
    # no nginx, because already confured
    configure_kolibri(kolibri_lang=kolibri_lang)
    restart_kolibri(post_restart_sleep=30)  # wait for DB migration to happen...
    # no need to provision_kolibri; se assume facily has already been created
    import_channels()
    restart_kolibri()
    puts(green('Kolibri server update complete.'))



# SYSADMIN TASKS
################################################################################

@task
def install_base():
    """
    Install base system pacakges, add swap, and create application user.
    """
    # 1. Apt-get the system requirements
    puts('Installing base system packages (this might take a few minutes).')
    with hide('running', 'stdout', 'stderr'):
        sudo('curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | apt-key add -')
        sudo('apt-get update -qq')
        # sudo('apt-get upgrade -y')  # no need + slows down process for nothing
        sudo('apt-get install -y --force-yes software-properties-common')
        sudo('apt-get install -y curl wget vim git sqlite3 tree zip unzip jq')
        sudo('apt-get install -y python3 python-pip')
        sudo('apt-get install -y nginx')
        sudo('apt-get install -y supervisor')

    # 2. Add swap space
    if not exists('/var/swap.1'):
        puts('Adding 1G of swap file /var/swap.1')
        sudo('/bin/dd if=/dev/zero of=/var/swap.1 bs=1M count=1024')
        sudo('/sbin/mkswap /var/swap.1')
        sudo('chmod 600 /var/swap.1')
        sudo('/sbin/swapon /var/swap.1')
        sudo('echo "/var/swap.1  none  swap  sw  0  0" >> /etc/fstab')

    # 3. Add the user `kolibri` who will be running Kolibri app
    if not exists('/home/kolibri'):
        puts('Creating UNIX user ' + KOLIBRI_USER)
        sudo('useradd  --create-home ' + KOLIBRI_USER)

    puts(green('Base install steps finished.'))


@task
def download_kolibri():
    """
    Downloads and installs Kolibri `.pex` file to KOLIBRI_HOME.
    """
    if not exists(KOLIBRI_HOME):
        sudo('mkdir -p ' + KOLIBRI_HOME)
        sudo('chmod 777 ' + KOLIBRI_HOME)
    with cd(KOLIBRI_HOME):
        sudo('wget --no-verbose "{}" -O {}'.format(KOLIBRI_PEX_URL, KOLIBRI_PEX_FILE))
    sudo('chown -R {}:{}  {}'.format(KOLIBRI_USER, KOLIBRI_USER, KOLIBRI_HOME))
    puts(green('Kolibri pex downloaded.'))


@task
def configure_nginx():
    """
    Perform necessary NGINX configurations to forward HTTP traffic to kolibri.
    """
    current_role = env.effective_roles[0]
    demo_server_hostname = env.roledefs[current_role]['hostname']

    if exists('/etc/nginx/sites-enabled/default'):
        sudo('rm /etc/nginx/sites-enabled/default')
    context = {
        'INSTANCE_PUBLIC_IP': env.host,
        'DEMO_SERVER_HOSTNAME': demo_server_hostname,
        'KOLIBRI_HOME': KOLIBRI_HOME,
        'KOLIBRI_PORT': KOLIBRI_PORT,
    }
    if exists('/etc/nginx/sites-enabled/kolibri.conf'):
        sudo('rm /etc/nginx/sites-enabled/kolibri.conf')
    upload_template(os.path.join(CONFIG_DIR,'nginx_site.template.conf'),
                    '/etc/nginx/sites-available/kolibri.conf',
                    context=context, use_jinja=True, use_sudo=True, backup=False)
    sudo('chown root:root /etc/nginx/sites-available/kolibri.conf')
    sudo('ln -s /etc/nginx/sites-available/kolibri.conf /etc/nginx/sites-enabled/kolibri.conf')
    sudo('chown root:root /etc/nginx/sites-enabled/kolibri.conf')
    sudo('service nginx reload')
    puts(green('NGINX site kolibri.conf configured.'))


@task
def configure_kolibri(kolibri_lang=KOLIBRI_LANG_DEFAULT):
    """
    Upload kolibri startup script and configure supervisor
    Args:
      - `kolibri_lang` in ['en','sw-tz','es-es','es-mx','fr-fr','pt-pt','hi-in']
    """
    # startup script
    context = {
        'KOLIBRI_LANG': kolibri_lang,
        'KOLIBRI_HOME': KOLIBRI_HOME,
        'KOLIBRI_PORT': KOLIBRI_PORT,
        'KOLIBRI_PEX_FILE': KOLIBRI_PEX_FILE,
    }

    startscript_path = os.path.join(KOLIBRI_HOME, 'startkolibri.sh')
    upload_template(os.path.join(CONFIG_DIR, 'startkolibri.template.sh'),
                    startscript_path,
                    context=context,
                    mode='0755', use_jinja=True, use_sudo=True, backup=False)
    sudo('chown {}:{} {}'.format(KOLIBRI_USER, KOLIBRI_USER, startscript_path))

    # supervisor config
    context = {
        'KOLIBRI_HOME': KOLIBRI_HOME,
        'KOLIBRI_USER': KOLIBRI_USER,
    }
    upload_template(os.path.join(CONFIG_DIR, 'supervisor_kolibri.template.conf'),
                    '/etc/supervisor/conf.d/kolibri.conf',
                    context=context, use_jinja=True, use_sudo=True, backup=False)
    sudo('chown root:root /etc/supervisor/conf.d/kolibri.conf')
    sudo('service supervisor restart')
    time.sleep(1)
    puts(green('Kolibri start script and supervisor config done.'))


@task
def provisiondevice():
    """
    Provision Kolibri facility. Works for Kolibri versions 0.9 and later.
    """
    current_role = env.effective_roles[0]
    role = env.roledefs[current_role]
    facility_name = role.get('facility_name', current_role.replace('-', ' '))
    prfx = 'export KOLIBRI_RUN_MODE="{}"'.format(KOLIBRI_RUN_MODE)
    prfx += ' && export KOLIBRI_HOME="{}"'.format(KOLIBRI_HOME)
    with prefix(prfx):
        cmd = 'python ' + os.path.join(KOLIBRI_HOME, KOLIBRI_PEX_FILE)
        cmd += " manage provisiondevice"
        cmd += ' --facility "{}"'.format(facility_name)
        cmd += " --preset {}".format(KOLIBRI_PROVISIONDEVICE_PRESET)
        cmd += " --superusername {}".format(KOLIBRI_PROVISIONDEVICE_SUPERUSER_USERNAME)
        cmd += " --superuserpassword {}".format(KOLIBRI_PROVISIONDEVICE_SUPERUSER_PASSWORD)
        cmd += " --language_id {}".format(KOLIBRI_LANG_DEFAULT)
        cmd += " --verbosity 0"
        cmd += " --noinput"
        puts("Provision command = " + cmd)
        sudo(cmd, user=KOLIBRI_USER)
        puts(green('Kolibri facility provisoin done.'))


@task
def import_channels():
    """
    Import the channels in `channels_to_import` using the command line interface.
    """
    current_role = env.effective_roles[0]
    channels_to_import = env.roledefs[current_role]['channels_to_import']
    for channel_id in channels_to_import:
        import_channel(channel_id)
    puts(green('Channels ' + str(channels_to_import) + ' imported.'))


@task
def import_channel(channel_id):
    """
    Import the channels in `channels_to_import` using the command line interface.
    """
    base_cmd = 'python ' + os.path.join(KOLIBRI_HOME, KOLIBRI_PEX_FILE) + ' manage'
    with hide('stdout'):
        with shell_env(KOLIBRI_HOME=KOLIBRI_HOME):
            sudo(base_cmd + ' importchannel network ' + channel_id, user=KOLIBRI_USER)
            sudo(base_cmd + ' importcontent network ' + channel_id, user=KOLIBRI_USER)
    puts(green('Channel ' + channel_id + ' imported.'))


@task
def generateuserdata():
    """
    Generates student usage data to demonstrate more of Kolibri's functionality.
    """
    base_cmd = 'python ' + os.path.join(KOLIBRI_HOME, KOLIBRI_PEX_FILE) + ' manage'
    with shell_env(KOLIBRI_HOME=KOLIBRI_HOME):
        sudo(base_cmd + ' generateuserdata', user=KOLIBRI_USER)
    puts(green('User data generation finished.'))


@task
def restart_kolibri(post_restart_sleep=0):
    sudo('supervisorctl restart kolibri')
    if post_restart_sleep > 0:
        puts(green('Taking a pause for ' + str(post_restart_sleep) + 'sec to let migrations run...'))
        time.sleep(post_restart_sleep)


@task
def stop_kolibri():
    sudo('supervisorctl stop kolibri')


@task
def delete_kolibri():
    stop_kolibri()
    sudo('rm -rf ' + KOLIBRI_HOME)
    sudo('rm /etc/nginx/sites-available/kolibri.conf /etc/nginx/sites-enabled/kolibri.conf')
    sudo('rm /etc/supervisor/conf.d/kolibri.conf')

