import socket

from fabric.api import env, task, sudo, run, settings
from fabric.api import get, put, require
from fabric.colors import red, green, blue, yellow
from fabric.context_managers import hide
from fabric.utils import puts


# PROXY SERVERS
################################################################################

@task
def checkproxies():
    """
    Check which demoservers have port 3128 open and is running a proxy service.
    """
    puts(green('Checking proxy service available on all demo servers.'))
    demo_servers = list(env.roledefs.items())
    proxy_hosts = []
    for role_name, role in demo_servers:
        assert len(role['hosts'])==1, 'Multiple hosts found for role'
        host = role['hosts'][0]
        print('Checking role_name=', role_name, 'host=', host)
        # check if we proxy port is open on host
        proxy_port_open = False
        port = 3128  # squid3 default proxy port
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(3)

        result = sock.connect_ex((host, port))
        proxy_port_open = True if result == 0 else False
        sock.close()
        if proxy_port_open:
            puts('    - proxy port open on {} demoserver'.format(role_name))
            proxy_hosts.append(host)
    PROXY_LIST_value = ';'.join(host+':3128' for host in proxy_hosts)
    puts(blue('Use the following command to set the PROXY_LIST env var:\n'))
    puts(blue('  export PROXY_LIST="' + PROXY_LIST_value + '"'))
    return proxy_hosts

@task
def update_proxy_servers():
    """
    Update the /etc/squid/squid.conf on all proxy hosts.
    Use this command to add new IP addresses to the lecheffers ACL group:
     1. First update ACL info in config/etc_squid_squid.conf
     2. Run `fab update_proxy_servers`
    """
    proxy_hosts = checkproxies()
    puts(green('Updating the proxy service config file on all proxy hosts:'))
    puts(green('proxy_hosts = ' + str(proxy_hosts)))
    for host in proxy_hosts:
        puts(green('Updating the proxy config on ' + host))
        with settings(host_string=host):
            update_squid_proxy()



# PROXY SERVICE
################################################################################

@task
def install_squid_proxy():
    """
    Install squid3 package and starts it so demoserver can be used as HTTP proxy.
    Note this rquires opening port 3128 on from the GCP console for this server,
    which can be done by applying the "Network tag" `allow-http-proxy-3128`.
    """

    with settings(warn_only=True), hide('stdout'):
        sudo('apt-get update')
        sudo('apt-get -y install squid3')
    put('config/etc_squid_squid.conf', '/etc/squid/squid.conf', use_sudo=True)
    sudo('chown root:root /etc/squid/squid.conf')
    sudo('service squid restart')
    puts('\n')
    puts(green('Proxy service started on ' + str(env.host)))
    puts(blue('Next steps:'))
    puts(blue('  1. Visit https://console.cloud.google.com/compute/instances?project=kolibri-demo-servers&organizationId=845500209641&instancessize=50'))
    puts(blue('  2. Add the Network Tag  "allow-http-proxy-3128" to the server ' + env.effective_roles[0]))
    puts(blue('  3. Append {}:{} to the PROXY_LIST used for cheffing.'.format(env.host, '3128')))


@task
def update_squid_proxy():
    """
    Update /etc/squid/squid.conf based on file in config/etc_squid_squid.conf.
    """
    puts(green('Updating the proxy service config file /etc/squid/squid.conf.'))
    with hide('running', 'stdout', 'stderr'):
        hostname = run('hostname')
    puts(green('Updting proxy config on ' + hostname))
    sudo('service squid stop')
    put('config/etc_squid_squid.conf', '/etc/squid/squid.conf', use_sudo=True)
    sudo('chown root:root /etc/squid/squid.conf')
    sudo('service squid start')
    puts(green('Proxy server updated successfully.'))


@task
def uninstall_squid_proxy():
    """
    Stop and uninstall squid3 proxy on the demoserver.
    """
    sudo('service squid stop')
    with settings(warn_only=True):
         sudo('apt-get -y purge squid3')
    puts(green('Proxy service removed from ' + str(env.host)))
    puts(blue('**Please remove {}:{} from the PROXY_LIST used for cheffing.**'.format(env.host, '3128')))

