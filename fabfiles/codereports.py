import functools
import json
import os
import requirements
import tempfile
import xmlrpc.client

from fabric.api import env, task, local
from fabric.colors import red, green, blue, yellow
from fabric.context_managers import hide, lcd
from fabric.utils import puts

from .github import get_chef_repos


class FabricException(Exception):    # Generic Exception for using Fabric Errors
    pass
env.abort_exception = FabricException



# LOCAL CHEF REPOS CHECKOUT
################################################################################
CHEF_REPOS_DIR = 'chefrepos'
if not os.path.exists(CHEF_REPOS_DIR):
    os.mkdir(CHEF_REPOS_DIR)

# A dict of header --> attrpath associations to use when printing the report
REPORT_FIELDS_TO_PRINT = {
    'repo_name': 'repo_name',
    'branch': 'branch',
    'requirements.txt': 'requirements_check.verdict',
    'sushichef.py': 'sushichef_check.verdict',
    'pyfiles': 'cloc_data.Python.nFiles',
    'pyLOC': 'cloc_data.Python.code',
    'md': 'cloc_data.Markdown.code',
    'Bash': 'cloc_data.Bourne Shell.code',
    'js': 'cloc_data.JavaScript.code',
    'JSON': 'cloc_data.JSON.code',
    'HTML': 'cloc_data.HTML.code',
    'CSS': 'cloc_data.CSS.code',
    # 'Comments': manually added containing combined comments from all reports
}



# CODE REPORTS
################################################################################

@task
def analyze_chef_repo(nickname, repo_name=None, organization='learningequality', branch='master', printing=True):
    """
    Ruch chef repo convention checks and count LOC for a given chef repo.
    """
    if repo_name is None:
        repo_name = 'sushi-chef-' + nickname
    chef_repo_dir = os.path.join(CHEF_REPOS_DIR, repo_name)
    if not os.path.exists(chef_repo_dir):
        local_setup_chef(None, repo_name=repo_name, organization=organization, branch=branch)
    else:
        local_update_chef(None, repo_name=repo_name, branch=branch)

    # The "report" for the chef repo is a dict of checks and data
    report = {
        'repo_name': repo_name,
        'branch': branch,
    }

    # requirements.txt report
    requirements_check = check_requirements_txt(repo_name, branch=branch)
    report['requirements_check'] = requirements_check

    # sushichef.py report
    sushichef_check = check_sushichef_py(repo_name, branch=branch)
    report['sushichef_check'] = sushichef_check

    # cloc
    cloc_data = run_cloc_in_repo(repo_name)
    report['cloc_data'] = cloc_data

    if printing:
        print_code_reports([report])

    return report


@task
def analyze_chef_repos():
    """
    Ruch chef repo convention checks on all repos (based on local code checkout).
    """
    chef_repos = get_chef_repos()
    reports = []
    for i, chef_repo in enumerate(chef_repos):
        organization = chef_repo.owner.login
        repo_name = chef_repo.name
        report = analyze_chef_repo(None, repo_name=repo_name, organization=organization, branch='master', printing=False)
        reports.append(report)
    print_code_reports(reports)



# CHEF REPO CONVENTION CHECKS
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
            found = False
            for req in requirements.parse(reqsf):
                if req.name.lower() == 'ricecooker':
                    found = True
                    if not req.specs:
                        return {'verdict':'✅ *'} # not pinned so will be latest
                    else:
                        reln, version = req.specs[0]   # we assume only one spec
                        if reln == '==':
                            if version == latest_ricecooker_version:
                                return {'verdict': '✅'}   # latest and greatest
                            if version != latest_ricecooker_version:
                                return {        
                                    'verdict': version + ' ⬆️',  # needs upgrade
                                    'comment': 'Ricecooker needs to be updated',
                                }    
                        else:
                            return {'verdict':'✅ >='}      # >= means is latest
            if not found:
                return {'verdict':'❌'}


def check_sushichef_py(repo_name, branch='master'):
    """
    Check if the chef repo contains a file called `sushichef.py` and also report
    on other python files found in the repo.
    """
    chef_repo_dir = os.path.join(CHEF_REPOS_DIR, repo_name)
    all_files = os.listdir(chef_repo_dir)
    py_files = [f for f in all_files if f.endswith('.py')]

    subreport = {}
    if 'sushichef.py' in py_files:
        subreport['verdict'] = '✅'
        py_files.remove('sushichef.py')
    else:
        subreport['verdict'] = '❌'
    if py_files:
        subreport['comment'] = 'Python files: ' + ', '.join(py_files)
    return subreport



# REPORT HELPERS
################################################################################

def rget(dict_obj, attrpath):
    """
    A fancy version of `get` that allows getting dot-separated nested attributes
    like `license.license_name` for use in tree comparisons attribute mappings.
    This code is inspired by solution in https://stackoverflow.com/a/31174427.
    """
    def _getnoerrors(dict_obj, attr):
        """
        Like regular get but will no raise if `dict_obj` is None.
        """
        if dict_obj is None:
            return None
        return dict_obj.get(attr)
    return functools.reduce(_getnoerrors, [dict_obj] + attrpath.split('.'))


def print_code_reports(reports):
    """
    Print a table with the attributes REPORT_FIELDS_TO_PRINT from the `report`s.
    """
    # 0. compute max length of each column so that the table will look nice
    max_lens = {}
    for header, attrpath in REPORT_FIELDS_TO_PRINT.items():
        lens = [len(header)]
        for report in reports:
            val = rget(report, attrpath)
            val_str = str(val) if val else ''
            lens.append(len(val_str))
        max_lens[header] = max(lens)

    # 1. print header line
    header_strs = []
    for header in REPORT_FIELDS_TO_PRINT.keys():
        max_len = max_lens[header]
        header_str = header.ljust(max_len)
        header_strs.append(header_str)
    header_strs.append('Comments')
    print('\t'.join(header_strs))

    # 2. print report lines
    for report in reports:

        # extract comments from any subreports
        comments = []
        for subreport in report.values():
            if 'comment' in subreport:
                comments.append(subreport['comment'])
        combined_comments = '; '.join(comments)

        report_strs = []
        for header, attrpath in REPORT_FIELDS_TO_PRINT.items():
            max_len = max_lens[header]
            val = rget(report, attrpath)
            val_str = str(val) if val else ''
            report_str = val_str.ljust(max_len)
            if '⬆️' in report_str:
                report_str += ' '
            report_strs.append(report_str)
        report_strs.append(combined_comments)
        print('\t'.join(report_strs))



# CODE ANALYSIS
################################################################################

def run_cloc_in_repo(repo_name):
    try:
        with hide('running', 'stdout', 'stderr'):
            local('which cloc')
    except FabricException:
        puts(red('command line tool  cloc  not found. Please install cloc.'))
        return
    chef_repo_dir = os.path.join(CHEF_REPOS_DIR, repo_name)
    # json tempfile file to store cloc output
    with tempfile.NamedTemporaryFile(suffix='.json') as tmpf:
        with lcd(chef_repo_dir), hide('running', 'stdout', 'stderr'):
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
    puts(green('Updating ' + chef_repo_dir + ' to branch ' + branch))
    with lcd(chef_repo_dir), hide('running', 'stdout', 'stderr'):
        local('git fetch origin  ' + branch)
        local('git checkout ' + branch)
        local('git reset --hard origin/' + branch)
