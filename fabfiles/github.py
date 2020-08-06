from github import Github
import json
import re

from fabric.api import task
from fabric.colors import red, green, blue, yellow
from fabric.utils import puts


# GITHUB CREDS
################################################################################
GITHUB_API_TOKEN_FILE = 'credentials/github_api.json'
GITHUB_API_TOKEN_NAME = 'cloud-chef-token'
GITHUB_SUSHI_CHEFS_TEAM_ID = 2590528  # "Sushi Chefs" team = all sushi chef devs



def get_github_client(token=None):
    """
    Returns a token-authenticated github client (to avoid code duplication).
    """
    if token is None:
        with open(GITHUB_API_TOKEN_FILE, 'r') as tokenf:
            token = json.load(tokenf)[GITHUB_API_TOKEN_NAME]
    return Github(token)


@task
def create_github_repo(nickname, source_url=None, init=True, private=False):
    """
    Create a github repo for chef given its `nickname` and `source_url`.
    """
    init = False if init=='False' or init=='false' else True
    private = True if private=='True' or private=='true' else False
    description = 'Sushi Chef script for importing {} content'.format(nickname)
    if source_url:
        description += ' from ' + str(source_url)
    repo_name = 'sushi-chef-' + nickname

    github = get_github_client()
    le_org = github.get_organization('learningequality')

    # 1. create repo
    create_repo_kwargs = dict(
        description=description,
        private=private,
        has_issues=True,
        has_wiki=False,
        auto_init=init
    )
    if init:
        create_repo_kwargs['license_template'] = 'mit'
        create_repo_kwargs['gitignore_template'] = 'Python'
    repo = le_org.create_repo(repo_name, **create_repo_kwargs)

    # 3. Give "Sushi Chefs" team read/write persmissions
    team = le_org.get_team(GITHUB_SUSHI_CHEFS_TEAM_ID)
    team.add_to_repos(repo)
    team.set_repo_permission(repo, 'admin')
    puts(green('Chef repo succesfully created: {}'.format(repo.html_url)))



@task
def list_chef_repos(organization='learningequality', printing=True, detailed=False):
    """
    List of all learningequality github repos that match the `sushi-chef-*`.
    """
    detailed = (detailed and detailed.lower() == 'true')
    CHEF_REPO_PATTERN = re.compile('.*sushi-chef-.*')
    github = get_github_client() 
    le_org = github.get_organization(organization)
    repos = le_org.get_repos()
    chef_repos = []
    for repo in repos:
        if CHEF_REPO_PATTERN.search(repo.name):
            chef_repos.append(repo)
    for repo in chef_repos:
        forks = list(repo.get_forks())
        branches = list(repo.get_branches())
        pulls = list(repo.get_pulls())
        issues = list(repo.get_issues(state='open'))
        if printing:
            if detailed:
                print()  # extra newline between repos
            print('-', blue(repo.html_url),
                '\t', len(forks), 'forks',
                '\t', len(branches), 'branches',
                '\t', len(pulls), 'PRs',
                '\t', len(issues), 'Issues')
            if detailed:
                for fork in forks:
                    fork_branches = list(fork.get_branches())
                    branch_names = [yellow(fb.name) for fb in fork_branches if fb.name != 'master']
                    fork_branches_str = 'branches: ' + ', '.join(branch_names) if branch_names else ''
                    print(blue('   - fork: ' + fork.owner.login + '/' + fork.name), fork_branches_str)
                for branch in branches:
                    commit_msg_lines = branch.commit.commit.message.split('\n')
                    commit_msg_str = commit_msg_lines[0] 
                    print(yellow('   - branch: ' + branch.name),
                           '('+ branch.commit.sha[0:7]+')', 
                            'by', branch.commit.author.login if branch.commit.author else '?',
                            commit_msg_str, '\t', branch.commit.commit.last_modified)
                for pr in pulls:
                    print(green('   - PR' + str(pr.number) + ': ' + pr.title),
                          pr.state, 
                          'by', pr.user.login,
                          '\t', pr.last_modified,
                          pr.commits, 'commits',
                          pr.comments, 'comments',
                          pr.labels if pr.labels else '')
                for issue in issues:
                    print(red('   - I' + str(issue.number) + ': ' + issue.title),
                          issue.state, issue.comments, 'comments', issue.labels if issue.labels else '')
    return chef_repos


@task
def list_repo_issues(reponame, organization='learningequality'):
    """
    List github issues associated with a given suchi chef repository.
    """
    if reponame is None:
        return
    github = get_github_client() 
    repo = github.get_repo("{}/{}".format(organization, reponame))
    open_issues = repo.get_issues(state='open')
    for issue in open_issues:
        print(issue.number, issue.state, issue.title, issue.comments, 'comments', issue.labels)
    return open_issues


