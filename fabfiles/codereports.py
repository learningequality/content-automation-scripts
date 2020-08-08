import json
import os
import re
import requirements
import tempfile
import xmlrpc.client

from fabric.api import env, task, local, prompt
from fabric.colors import red, green, blue, yellow
from fabric.context_managers import cd, prefix, lcd
from fabric.contrib.files import exists
from fabric.utils import puts

from .github import get_chef_repos, get_pipeline_repos

class FabricException(Exception):    # Generic Exception for using Fabric Errors
    pass
env.abort_exception = FabricException



# LOCAL CHEF REPOS CHECKOUT
################################################################################
CHEF_REPOS_DIR = 'chefrepos'
if not os.path.exists(CHEF_REPOS_DIR):
    os.mkdir(CHEF_REPOS_DIR)

MAX_REPO_NAME_LEN = 46  # len('sushi-chef-internet-archive-universal-library')+1

CODE_KINDS = [
    'Python',
    'JavaScript',
    'Markdown',
    'JSON',
    'HTML',
    'CSS',
]

COUNT_KEYS = ['nFiles', 'blank', 'comment', 'code']



# CODE REPORTS
################################################################################

@task
def analyze_chef_repo(nickname, repo_name=None, organization='learningequality', branch='master', printheader=True):
    if repo_name is None:
        repo_name = 'sushi-chef-' + nickname
    chef_repo_dir = os.path.join(CHEF_REPOS_DIR, repo_name)
    if not os.path.exists(chef_repo_dir):
        local_setup_chef(None, repo_name=repo_name, organization=organization, branch=branch)
    else:
        local_update_chef(None, repo_name=repo_name, branch=branch)

    # requirements.txt
    reqs_check = check_requirements_txt(repo_name, branch=branch)

    # cloc
    cloc_data = run_cloc_in_repo(repo_name)
    cloc_data.pop('SUM')
    cloc_data.pop('header')

    if printheader:
        print(
            'repo_name'.ljust(MAX_REPO_NAME_LEN), '\t',
            'requirements.txt', '\t',
            'sushichef.py', '\t',
            'Python files', '\t',
            'Python lines', '\t',
            'JavaScript', '\t',
            'Markdown', '\t',
            'JSON', '\t',
            'HTML', '\t',
            'CSS',
        )
    print(
        repo_name.ljust(MAX_REPO_NAME_LEN), '\t',
        reqs_check['verdict'].ljust(17), '\t',
        '⬆️', '\t',
        cloc_data.get('Python', {}).get('nFiles', ''), '\t',
        cloc_data.get('Python', {}).get('code', ''), '\t',
        cloc_data.get('JavaScript', {}).get('code', ''), '\t',
        cloc_data.get('Markdown', {}).get('code', ''), '\t',
        cloc_data.get('JSON', {}).get('code', ''), '\t',
        cloc_data.get('HTML', {}).get('code', ''), '\t',
        cloc_data.get('HTML', {}).get('code', '')
    )
    interesting_keys = [key for key in cloc_data.keys() if key not in CODE_KINDS]
    if interesting_keys:
        print(blue('interesting_keys=' + str(interesting_keys)))


@task
def analyze_chef_repos(fast=False):
    """
    Print report about all sushi chef repos (forks, branches, PRs, issues).
    """
    chef_repos = get_chef_repos()
    for i, chef_repo in enumerate(chef_repos):
        organization = chef_repo.owner.login
        repo_name = chef_repo.name
        printheader = True if i == 0 else False
        analyze_chef_repo(None, repo_name=repo_name, organization=organization, branch='master', printheader=printheader)
        # check_requirements_txt(repo_name)

    # print_report_for_github_repos(chef_repos, fast=fast)


@task
def analyze_pipeline_repos(fast=False):
    """
    Print report about all the github repos related to the Content Pipeline.
    """
    pipeline_repos = get_pipeline_repos()



# CHEF REPO CONVENTION CHECKERS
################################################################################

def check_requirements_txt(repo_name, branch='master'):
    """
    Check if repo contains a file `requirements.txt` and if ricecooker version
    in it is up to date.
    """
    chef_repo_dir = os.path.join(CHEF_REPOS_DIR, repo_name)
    requirements_txt = os.path.join(chef_repo_dir, 'requirements.txt')
    if not os.path.exists(requirements_txt):
        return {'verdict':'❌'}
    else:
        # get the latest version of ricecooker from PyPI
        pypi = xmlrpc.client.ServerProxy('https://pypi.python.org/pypi')
        latest_ricecooker_version = pypi.package_releases('ricecooker')[0]

        # compare with version in requirements.txt
        with open(requirements_txt, 'r') as reqsf:
            for req in requirements.parse(reqsf):
                if req.name.lower() == 'ricecooker':
                    if not req.specs:
                        return {'verdict':'✅ *'} # not pinned so will be latest
                    else:
                        reln, version = req.specs[0]   # we assume only one spec
                        if reln == '==':
                            if version == latest_ricecooker_version:
                                return {'verdict': '✅'}   # latest and greatest
                            if version != latest_ricecooker_version:
                                return {'verdict': version + ' ⬆️'}    # upgrade
                        else:
                            return {'verdict':'✅ >='}      # >= means is latest


def check_sushichef_py(repo_name, branch='master'):
    chef_repo_dir = os.path.join(CHEF_REPOS_DIR, repo_name)
    pass




# CODE ANALYSIS
################################################################################

def run_cloc_in_repo(repo_name):
    try:
        local('which cloc')
    except FabricException:
        puts(red('command line tool  cloc  not found. Please install cloc.'))
        return
    chef_repo_dir = os.path.join(CHEF_REPOS_DIR, repo_name)
    # json tempfile file to store cloc output
    with tempfile.NamedTemporaryFile(suffix='.json') as tmpf:
        with lcd(chef_repo_dir):
            local('cloc --exclude-dir=venv . --json > ' + tmpf.name)
        with open(tmpf.name) as jsonf:
            cloc_data = json.load(jsonf)
    return cloc_data



# LOCAL CHEF SETUP
################################################################################

@task
def local_setup_chef(nickname, repo_name=None, cwd=None, organization='learningequality', branch='master'):
    """
    Locally git-clone the repo `sushi-chef-{nickname}` to the dir `chefrepos/`.
    """
    if repo_name is None:
        repo_name = 'sushi-chef-' + nickname
    chef_repo_dir = os.path.join(CHEF_REPOS_DIR, repo_name)
    github_ssh_url = 'git@github.com:{}/{}.git'.format(organization, repo_name)

    if os.path.exists(chef_repo_dir):
        puts(yellow('Chef repo dir ' + chef_repo_dir + ' already exists.'))
        puts(yellow('You can use `local_update_chef` task to update code.'))
        return

    # clone the repo
    with lcd(CHEF_REPOS_DIR):
        local('git clone  --quiet  ' + github_ssh_url)

    # checkout the desired branch
    with lcd(chef_repo_dir):
        local('git checkout ' + branch)
    puts(green('Setup code from ' + github_ssh_url + ' in ' + chef_repo_dir))


@task
def local_unsetup_chef(nickname, repo_name=None):
    """
    Remove the local repo `chefrepos/sushi-chef-{nickname}`.
    """
    if repo_name is None:
        repo_name = 'sushi-chef-' + nickname
    chef_repo_dir = os.path.join(CHEF_REPOS_DIR, repo_name)
    if os.path.exists(chef_repo_dir):
        local('rm -rf  ' + chef_repo_dir)
        puts(green('Removed chef directory ' + chef_repo_dir))
    else:
        puts(yellow('Directory ' + chef_repo_dir + ' does not exist.'))


@task
def local_update_chef(nickname, repo_name=None, cwd=None, branch='master'):
    """
    Run pull -f in the local chef repo to update the code to the lastest version.
    """
    if repo_name is None:
        repo_name = 'sushi-chef-' + nickname
    chef_repo_dir = os.path.join(CHEF_REPOS_DIR, repo_name)
    with lcd(chef_repo_dir):
        local('git fetch origin  ' + branch)
        local('git checkout ' + branch)
        local('git reset --hard origin/' + branch)

