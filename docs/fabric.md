Using fabric
============
The `fab` command allows us to run various configuration scripts over `ssh`.
Using the fabric commend `run` allows us to run commands on remote machines,
just as easily as you would run them on your local machine.


Install
-------

    pip install fab-classic


Purpose
-------
  - Command line interface to call provisioning scripts
  - Connect to remote machines securely
  - Execute system administration tasks (provisioning, setup, deploy)
  - Execute system checks, e.g., `fab checkdns`


Minimum viable fabfile
----------------------
Create the file `fabfile.py` in new directory with contents:

    from fabric.api import *

    env.hosts = ['myserver.com']
    env.user = 'admin'
    env.key_filename = '/path/to/admin/keyfile'

    def check_uname():
        run('uname -a')

You can then check what type of UNIX runs on `myserver.com` using:

    fab check_uname

Fabric will then do the following things:
  - open an ssh connection to `myserver.com`
  - login as `admin` using the specified ssh private key
  - run the command `uname -a` on `myserver.com`
  - print the result to your screen



Basic usage
-----------
By default, the `fab` command will search for a file called `fabfile.py` in
the current directory which contains the settings and tasks.

To run this command on a particular host, use the `-H` flag, which will override
the `env.hosts` setting:

    fab -H user@server.com check_uname

Alternatively, we can assign one or more hosts to a particular "role" and then
run a task on all hosts in a given role using the `-R` switch. For example:

    fab -R something-demo check_uname

The above command runs `check_uname` on all hosts in the role `something-demo`.


Getting help
------------
Fab uses introspection to recognize all functions decorated with `@task`, and
can print a full menu of these functions. To see all tasks defined type:

    fab help

To see the documentation for any task use the `-d` flag (shows the docstring):

    fab -d info

If you don't know what is going on, the best approach would be to read the source
code of the `fabfile.py` script—it's very easy to read and self-explantory.


Tasks and env
-------------
The main thing you need to know about Fabric is that `tasks` can access a global
dictionary of settings and parameters called `env`. A lot of interesting data is
passed to scripts and functions in this manner:
   - `env.roledefs`: is a global dictionary that defines the parameters for the demo servers
      - `hosts`: list of hosts in this role (usually one)
      - `channels_to_import`: channel ids for channels to import when setting up server
      - `facility_name`: what should the Kolibri facility be called
      - `hostname`: a DNS name (needs to be setup manually; ask in #sysops)


Debugging
---------
If you ever get the error:

    Fatal error: Host key for 192.168.59.13 did not match pre-existing key!
    Server's key was changed recently, or possible man-in-the-middle attack.
    ('192.168.59.13', <paramiko.rsakey.RSAKey object at 0x1054808d0>,
    <paramiko.rsakey.RSAKey object at 0x105452650>)

Erase all `192.168.59.13` entries in your `~/.ssh/known_hosts`.


