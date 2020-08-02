import os
import re

from fabric.api import env, task, local, sudo, run, prompt
from fabric.colors import red, green, blue, yellow
from fabric.context_managers import cd, prefix
from fabric.contrib.files import exists
from fabric.utils import puts


# Studio
STUDIO_TOKEN = os.environ.get('STUDIO_TOKEN')


# GLOBAL CHEF SETTINGS
################################################################################
CHEF_USER = 'chef'
DEFAULT_GIT_BRANCH = 'master'
CHEFS_DATA_DIR = '/data'


integrationservers = {
    'vader': {
        'hosts':['eslgenie.com:1'],           # because vader runs ssh on port 1
    },
}






# CHEF SETUP
################################################################################

@task
def setup_chef(nickname, organization='learningequality', repo_name=None, branch_name=DEFAULT_GIT_BRANCH):
    """
    Git-clone, setup virtualenv, and pip-install the Python packages for the chef
    `nickname` chef. Code is assumed to be in `https://github.com/learningequality/sushi-chef-{nickname}`.
    """
    if repo_name is None:
        repo_name = 'sushi-chef-' + nickname
    chef_root_dir = os.path.join(CHEFS_DATA_DIR, repo_name)

    # github_git_url = 'git@github.com:{}/{}.git'.format(organization, repo_name)
    github_http_url = 'https://github.com/{}/{}'.format(organization, repo_name)

    with cd(CHEFS_DATA_DIR):
        if exists(chef_root_dir):
            puts(yellow('Chef repo dir ' + chef_root_dir + ' already exists.'))
            puts(yellow('You can use `update_chef` task to update existing code.'))
            return

        # clone and chown that repo
        sudo('git clone  --quiet  ' + github_http_url)
        sudo('chown -R {}:{}  {}'.format(CHEF_USER, CHEF_USER, chef_root_dir))

        # checkout the desired branch
        with cd(chef_root_dir):
            sudo('git checkout ' + branch_name, user=CHEF_USER)

        # setup python virtualenv
        with cd(chef_root_dir):
            sudo('virtualenv -p python3.5  venv', user=CHEF_USER)

        with cd(chef_root_dir):
            activate_sh = os.path.join(chef_root_dir, 'venv/bin/activate')
            reqs_filepath = os.path.join(chef_root_dir, 'requirements.txt')
            # Nov 23: workaround____ necessary to avoid HOME env var being set wrong
            with prefix('export HOME=/data && source ' + activate_sh):
                # install requirements
                sudo('pip install --no-input --quiet -r ' + reqs_filepath, user=CHEF_USER)
        puts(green('Setup chef code from ' + github_http_url + ' in ' + chef_root_dir))


@task
def unsetup_chef(nickname, repo_name=None):
    """
    Remove the repo `sushi-chef-{nickname}` form the content integration server.
    """
    if repo_name is None:
        repo_name = 'sushi-chef-' + nickname
    chef_root_dir = os.path.join(CHEFS_DATA_DIR, repo_name)
    sudo('rm -rf  ' + chef_root_dir)
    puts(green('Removed chef directory ' + chef_root_dir))


@task
def update_chef(nickname, repo_name=None, branch_name=DEFAULT_GIT_BRANCH):
    """
    Run pull -f in the chef repo to update the chef code to the lastest version.
    """
    if repo_name is None:
        repo_name = 'sushi-chef-' + nickname
    chef_root_dir = os.path.join(CHEFS_DATA_DIR, repo_name)    
    with cd(chef_root_dir):
        sudo('git fetch origin  ' + branch_name, user=CHEF_USER)
        sudo('git checkout ' + branch_name, user=CHEF_USER)
        sudo('git reset --hard origin/' + branch_name, user=CHEF_USER)

    # update requirements
    activate_sh = os.path.join(chef_root_dir, 'venv/bin/activate')
    reqs_filepath = os.path.join(chef_root_dir, 'requirements.txt')
    with prefix('export HOME=/data && source ' + activate_sh):
        sudo('pip install -U --no-input --quiet -r ' + reqs_filepath, user=CHEF_USER)






# HELPER METHODS
################################################################################

def wrap_in_nohup(cmd, redirects=None, pid_file=None):
    """
    This wraps the chef command `cmd` appropriately for it to run in background
    using the nohup to avoid being terminated when the HANGUP signal is received
    when shell exists. This function is necessary to support some edge cases:
      - composite commands, e.g. ``source ./c/keys.env && ./chef.py``
      - adds an extra sleep 1 call so commands doesn't exit too fast and confuse fabric
    Args:
      redirects (str):  options for redirecting command's stdout and stderr
      pid_file (str): path to pid file where to save pid of backgrdoun process (needed for stop command)
    """
    # prefixes
    cmd_prefix = ' ('            # wrapping needed for sleep suffix
    cmd_prefix += ' nohup '      # call cmd using nohup
    cmd_prefix += ' bash -c " '  # spawn subshell in case cmd has multiple parts
    # suffixes
    cmd_suffix = ' " '           # /subshell
    if redirects is not None:    # optional stdout/stderr redirects (e.g. send output to a log file)
        cmd_suffix += redirects
    cmd_suffix += ' & '          # put nohup command in background
    if pid_file is not None:     # optionally save nohup pid in  `pid_file`
         cmd_suffix += ' echo $! >{pid_file} '.format(pid_file=pid_file)
    cmd_suffix += ') && sleep 1' # via https://stackoverflow.com/a/43152236
    # wrap it yo!
    return cmd_prefix + cmd + cmd_suffix


def add_args(cmd, args_dict):
    """
    Insert the command line arguments from `args_dict` into a chef run command.
    Assumes `cmd` contains the substring `--token` and inserts args right before
    instead of appending to handle the case where cmd contains extra options. 
    """
    args_str = ''
    for argk, argv in args_dict.items():
        if argv is not None:
            args_str += ' ' + argk + '=' + argv + ' '
        else:
            args_str += ' ' + argk + ' '
    return cmd.replace('--token', args_str + ' --token')


# TODO: support git:// URLs
# TODO: support .git suffix in HTTTPs urls
# TODO: handle all special cases https://github.com/tj/node-github-url-from-git
GITHUB_REPO_NAME_PAT = re.compile(r'https://github.com/(?P<repo_account>\w*?)/(?P<repo_name>[A-Za-z0-9_-]*)')

def github_repo_to_chefdir(github_url):
    """
    Extracts the `chefdir` (repo name) from a github URL.
    """
    if github_url.endswith('/'):
        github_url = github_url[0:-1]
    match = GITHUB_REPO_NAME_PAT.search(github_url)
    if match:
        return match.groupdict()['repo_name']
    else:
        raise ValueError('chefdir cannot be inferred from github repo name...')
