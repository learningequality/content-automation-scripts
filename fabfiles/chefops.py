import os
import re

from fabric.api import env, task, local, sudo, run, prompt
from fabric.colors import red, green, blue, yellow
from fabric.context_managers import cd, prefix
from fabric.contrib.files import exists
from fabric.utils import puts


# Studio
STUDIO_TOKEN = os.environ.get('STUDIO_TOKEN', None)


# GLOBAL CHEF SETTINGS
################################################################################
CHEF_USER = 'chef'
DATA_DIR = '/data'
VIRTUALENV_PYTHON = 'python3.5'


# INTEGRATIONS SERVERS (UNIX hosts with good internet and lots of storage space)
################################################################################
integrationservers = {
    'vader': {
        'hosts':['eslgenie.com:1'],           # because vader runs ssh on port 1
    },
}



# RUN CHEF
################################################################################

@task
def run_chef(nickname, repo_name=None, nohup=False, prfx=None, args='', cwd=None):
    """
    Run the command: `cd cwd; prfx && ./sushichef.py --thumbnails --token={}`
    where {} will be replaced by the value of the env variable STUDIO_TOKEN.
    All keyword arguments are optional and used only for special cases.
    """
    nohup = (nohup and nohup.lower() == 'true')  # defaults to False
    if STUDIO_TOKEN is None:
        raise ValueError('Must define STUDIO_TOKEN env var to run chefs.')

    if repo_name is None:
        repo_name = 'sushi-chef-' + nickname
    chef_repo_dir = os.path.join(DATA_DIR, repo_name)
    chef_root_dir = os.path.join(chef_repo_dir, cwd) if cwd else chef_repo_dir

    # TODO rm chef_root_dir/.webcache if needed...
    cmd = './sushichef.py --token={} --thumbnails '.format(STUDIO_TOKEN)
    if args:
        cmd += args

    with cd(chef_root_dir):
        full_prfx = prfx + ' && ' if prfx else ''
        full_prfx += 'source ' + os.path.join(chef_root_dir, 'venv/bin/activate')
        with prefix(full_prfx):
            if nohup == False:
                # Normal operation (blocking)
                sudo(cmd, user=CHEF_USER)
            else:
                # Run in background
                cmd_nohup = wrap_in_nohup(cmd)
                sudo(cmd_nohup, user=CHEF_USER)
                nohup_out_file = os.path.join(chef_root_dir, 'nohup.out')
                puts(green('Script stdout is sent to   ' + nohup_out_file))


# CHEF SETUP
################################################################################

@task
def setup_chef(nickname, repo_name=None, cwd=None, organization='learningequality', branch='master'):
    """
    Git-clone, setup virtualenv, and pip-install the the chef `nickname`.
    The source code for the chef is assumed to be taken from the github repo
    `https://github.com/learningequality/sushi-chef-{nickname}`.
    """
    if repo_name is None:
        repo_name = 'sushi-chef-' + nickname
    chef_repo_dir = os.path.join(DATA_DIR, repo_name)
    chef_root_dir = os.path.join(chef_repo_dir, cwd) if cwd else chef_repo_dir

    github_http_url = 'https://github.com/{}/{}'.format(organization, repo_name)

    with cd(DATA_DIR):
        if exists(chef_repo_dir):
            puts(yellow('Chef repo dir ' + chef_repo_dir + ' already exists.'))
            puts(yellow('You can use `update_chef` task to update existing code.'))
            return

        # clone and chown that repo
        sudo('git clone  --quiet  ' + github_http_url)
        sudo('chown -R {}:{}  {}'.format(CHEF_USER, CHEF_USER, chef_repo_dir))

        # checkout the desired branch
        with cd(chef_repo_dir):
            sudo('git checkout ' + branch, user=CHEF_USER)
        puts(green('Setup code from ' + github_http_url + ' in ' + chef_repo_dir))

        # setup python virtualenv
        with cd(chef_root_dir):
            sudo('virtualenv -p ' + VIRTUALENV_PYTHON + ' venv', user=CHEF_USER)

        # install requirements
        activate_sh = os.path.join(chef_root_dir, 'venv/bin/activate')
        reqs_filepath = os.path.join(chef_root_dir, 'requirements.txt')
        with prefix('export HOME=/data && source ' + activate_sh):
            sudo('pip install --no-input --quiet -r ' + reqs_filepath, user=CHEF_USER)
        puts(green('Python env setup in ' + os.path.join(chef_root_dir, 'venv')))


@task
def unsetup_chef(nickname, repo_name=None):
    """
    Remove the repo `sushi-chef-{nickname}` form the content integration server.
    """
    if repo_name is None:
        repo_name = 'sushi-chef-' + nickname
    chef_repo_dir = os.path.join(DATA_DIR, repo_name)
    sudo('rm -rf  ' + chef_repo_dir)
    puts(green('Removed chef directory ' + chef_repo_dir))


@task
def update_chef(nickname, repo_name=None, cwd=None, branch='master'):
    """
    Run pull -f in the chef repo to update the chef code to the lastest version.
    """
    if repo_name is None:
        repo_name = 'sushi-chef-' + nickname
    chef_repo_dir = os.path.join(DATA_DIR, repo_name)
    chef_root_dir = os.path.join(chef_repo_dir, cwd) if cwd else chef_repo_dir
    with cd(chef_repo_dir):
        sudo('git fetch origin  ' + branch, user=CHEF_USER)
        sudo('git checkout ' + branch, user=CHEF_USER)
        sudo('git reset --hard origin/' + branch, user=CHEF_USER)

    # setup python virtualenv
    if not exists(os.path.join(chef_root_dir, 'venv')):
        with cd(chef_root_dir):
            sudo('virtualenv -p ' + VIRTUALENV_PYTHON + ' venv', user=CHEF_USER)

    # update requirements
    activate_sh = os.path.join(chef_root_dir, 'venv/bin/activate')
    reqs_filepath = os.path.join(chef_root_dir, 'requirements.txt')
    with prefix('export HOME=/data && source ' + activate_sh):
        sudo('pip install -U --no-input --quiet -r ' + reqs_filepath, user=CHEF_USER)




# HELPER METHODS
################################################################################

def wrap_in_nohup(cmd):
    """
    This wraps the chef command `cmd` appropriately for it to run in background
    using `nohup` to avoid being terminated when the HANGUP signal is received
    when shell exists. This function is necessary to support some edge cases:
      - supports composite commands, e.g. `source ./c/keys.env && ./chef.py`
      - add extra sleep 1 call so commands doesn't exit fast and confuse fabric
    """
    # prefixes
    cmd_prefix = ' ('            # wrapping needed for sleep suffix
    cmd_prefix += ' nohup '      # call cmd using nohup
    cmd_prefix += ' bash -c " '  # spawn subshell in case cmd has multiple parts
    # suffixes
    cmd_suffix = ' " '           # /subshell
    cmd_suffix += ' & '          # put nohup command in background
    cmd_suffix += ') && sleep 1' # via https://stackoverflow.com/a/43152236
    # wrap it yo!
    return cmd_prefix + cmd + cmd_suffix


# TODO: support git:// URLs
# TODO: support .git suffix in HTTTPs urls
# TODO: handle all special cases https://github.com/tj/node-github-url-from-git
GITHUB_REPO_NAME_PAT = re.compile(r'https://github.com/(?P<organization>\w*?)/(?P<repo_name>[A-Za-z0-9_-]*)')

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
