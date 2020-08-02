# Content Automation Scripts

Content pipeline automation scripts -- everything is *fab*ulous when you've got Python on your side.

1. Semi-automated steps provided for the following tasks:
  - Setup a kolibri demo server from any pex and any content channel.
  - Use cases:
    - Kolibri preview for content developers
    - Channel Q/A process
    - Support partnerships by providing place to preview content channels
  - Out of scope:
    - Public demo servers (see https://github.com/learningequality/infrastructure)

2. Automatic github repo management and checks

3. Utilities for setting up and running chefs on a remote integration server (`vader`)



Install
-------

    virtualenv -p python3 venv
    source venv/bin/activate
    pip install -r requirements.txt


TODOs
-----
  - Figure out if KOLIBRI_LANGUAGE is necessary for cmd line or a Facility setting.
  - Start using an inventory.json to store the info from gcp.inventory
    - Automatically read when fab runs
    - Automatically append to when new demoservers created
    - Automatically remove when demoserver deleted
  - Make sure swap space persists after reboot (see TODO in install_base)




GCP Authentication and Authorization
------------------------------------
1. The SushOps engineer who will be running these scripts must be part of the GCP project
[`kolibri-demo-servers`](https://console.cloud.google.com/compute/instances?project=kolibri-demo-servers).
As a first step, try logging in via the web interface and check what can you see.

2. The SushOps engineer must be one of the default sudo accounts specified on the
"compute metadata" tab in the GCP console. The metadata field for ssh-keys must
contain the SushOps engineer's username and their public ssh key. To confirm, see
[here](https://console.cloud.google.com/compute/metadata?project=kolibri-demo-servers).
Note: The scripts assume the SushOps engineer's username on GCP metadata is the
same as on their laptop (Laptop username taken from `echo $USER`).

3. On the command line, you'll have to install `gcloud` command line tools, then
run this to do the complete GCP login song and dance via OAuth login etc:

    gcloud init

To test if you're logged in and authorized to access the GCP project run

    gcloud compute instances list --project=kolibri-demo-servers

You should see all VM instances in the GCP project `kolibri-demo-servers`.





Create instance
---------------
Suppose you want to setup a demo server called `mitblossoms-demo`. First you must
create the demo server instance:

    fab create:mitblossoms-demo

Note it's also possible to provision a virtual machine using web interface.
See [docs/gcp_instance.md](docs/gcp_instance.md) for more info.


Using
-----

  1. Update the `env.roledefs` info in `fabfile.py` inserting appropriate info:
      - Use the instance name as the key for this role, e.g., `mitblossoms-demo`
      - The IP address of the new cloud host (obtained when created)
      - The channel ids to load into Kolibri (optional)

  2. To provision the demo server, run the command:

         fab -R mitblossoms-demo   demoserver

  3. Setup a DNS record for the demoserver hostname pointing to the host IP address



Updating
--------
To update the `mitblossoms-demo` server that currently runs an old version of Kolibri,
change `KOLIBRI_PEX_URL` in `fabfile.py` to the URL of the latest release and then run:

    fab -R mitblossoms-demo   update_kolibri

This will download the new pex, overwrite the startup script, and restart Kolibri.

**NOTE**: currently this command fails sporadically, so you may need to run twice for it to work.



Delete instance
---------------

    fab delete:mitblossoms-demo

