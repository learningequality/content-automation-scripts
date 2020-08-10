Content Automation Scripts
==========================

Content pipeline automation scripts -- everything is *fab*ulous when you've got Python on your side.

1. Semi-automated steps provided for the following tasks:
   - Setup a kolibri demo server from any pex and any content channel.
   - Use cases:
     - Kolibri preview for content developers
     - Channel Q/A process
     - Support partnerships by providing place to preview content channels

2. Utilities for setting up and running chefs on a remote integration server (`vader`)

3. Automatic github repo management and checks



Install
-------

    virtualenv -p python3 venv
    source venv/bin/activate
    pip install -r requirements.txt



Required credentials
--------------------
 1. To create temporary demo servers for content QA, you must:
   - be part of the GCP project `kolibri-demo-servers` (ask Aron)
   - your ssh public key must be added [here](https://console.cloud.google.com/compute/metadata?project=kolibri-demo-servers)
     and it must correspond to the same username as you use on your local machine.
 2. To run chefs on `vader`, you must:
    - have a sudo-enabled account on `vader`
    - have set the env variable `SUDO_PASSWORD` to your vader password
    - have set the env variable `STUDIO_TOKEN` to a Studio API token with `edit` rights for the channel
 3. To run the github automation scripts
    - You must have a GitHub API token placed in `credentials/github_api.json`,
      see `credentials/github_api.template.json` for example structure.



# Cloud Kolibri demo servers


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



TODOs
-----
  - Start using an inventory.json to store the info from gcp.inventory
    - Automatically read when fab runs
    - Automatically append to when new demoservers created
    - Automatically remove when demoserver is deleted



Remote host utils
-----------------
### Information
To show all sushi chefs (python processes) running on `vader`, use:

    fab -R vader pypsaux 


### Commands
You can run any command on the remote host `vader` as follows:

    fab -R vader exec:'ls -l /data'

certain commands require running as root:

    fab -R vader exec:'ls -l /data',usesudo=true

which requires that the env var `SUDO_PASSWORD` is set.

Good luck figuring out the appropriate quote escape sequence that will satisfy
your local shell, Fabric command escaping, and the remote shell ;) For anything
non-trivial, just connect to the host via ssh. This command will tell you the
appropriate host string to connect to a given host `fab -R vader  shell`.




# 2. Remote chef execution

General chef repo conventions:
  - Git repo names follow the convention `sushi-chef-{nickname}`,
    where `{nickname}` is a hyphen-separated unique name.
  - The content integration script is called `sushichef.py`.
  - Every content integration script repo contains a `requirements.txt`.



Basic usage
-----------

### 1. Setup chef script

    fab -R vader  setup_chef:<nickname>

This command will clone `https://github.com/learningequality/sushi-chef-{nickname}`,
to `/data/sushi-chef-{nickname}`, create a virtual environment called `venv`,
and install the python packages in the `requirements.txt` for the project.

Run `update_chef` task to update chef code to latest version (`fetch` and `checkout --hard`).

To remove chef code completely from the integration server, use `unsetup_chef`.


### 2. Run it

    export STUDIO_TOKEN=<YOURSTUDIOTOKENGOESGHERE>
    fab -R vader  run_chef:<nickname>

This will result in the call `./sushichef.py --thumbnails --token=$STUDIO_TOKEN`
on the host `vader`, inside the directory `/data/sushi-chef-{nickname}` after the
virtualenv `/data/sushi-chef-{nickname}/venv` has been activated.


You can also run chef in background using

    fab -R vader run_chef:<nickname>,nohup=true

which starts the chef command wrapped in `nohup` so that it persists after the ssh
connection is closed. Output logs will be in `/data/sushi-chef-{nickname}/nohup.out`.





# 3. Github repo management


Creating a github repo for a new chef
-------------------------------------
The code for each chef script lives in its own github repo in the `learnignequality` org.
Run the following command to create an empty github repo for a new chef:

    fab create_github_repo:nickname,source_url="https://nickname.org"

This will create the repository https://github.com/learningequality/sushi-chef-nickname
and enable read/write access to this repo for the "Sushi Chefs" team.
The `source_url` argument is optional, but it's nice to have.
This command requires a github API key to be present in the `credentials/` dir.



GitHub repository checks
------------------------
Print report about all sushi chef repos (forks, branches, PRs, issues):

    fab list_chef_repos


The same repo report can be performed for the non-chef repos related to the Content Pipeline using:

    fab list_pipeline_repos



Chef code reports
-----------------
Use the following commands to check the general chef repo conventions:

    fab analyze_chef_repo:<nickname>

This command will do a local clone of the chef repo to the directory `chefrepos`
and perform some basic checks (is requirements.txt defined? is chef script called sushichef.py?)
and count the lines of code in the repo.

To run the code analysis on all chef repos, use

    fab analyze_chef_repos

or to check all branches in the chef repos use this command:

    fab analyze_chef_repos:allbranches=true

The output of all these commands are tab-separated so they can be pasted into
a spreadsheet for further processing.
