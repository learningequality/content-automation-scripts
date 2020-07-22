import datetime
# from dateutil.parser import parse
# from github import Github
from io import BytesIO
from itertools import groupby
import json
import os
import pipes
import re
import sys
import time

from fabric.api import env, task, local, sudo, run, prompt, settings
from fabric.api import get, put, require
from fabric.colors import red, green, blue, yellow
from fabric.context_managers import cd, prefix, show, hide, shell_env, quiet, lcd
from fabric.contrib.files import exists, sed, upload_template
from fabric.utils import puts

from fabfiles.github import test_utility_function


@task
def test_task():
    puts(blue('print blue...'))
    puts(red('print red'))
    puts(green('print green'))
    print('calling module:', test_utility_function())
    print('DONE')

