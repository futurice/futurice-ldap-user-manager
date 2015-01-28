import os, subprocess, locale, sys

cwd = os.getcwd()
try:
    encoding = locale.getdefaultlocale()[1]
except:
    encoding = 'UTF-8'

def cmd(execute):
    return subprocess.call(execute.format(cwd).split(), shell=False)

if not os.path.isdir('./env'):
    cmd('virtualenv -p python env')

def shell_source(script):
    """ Emulate 'source' -command """
    import subprocess, os
    pipe = subprocess.Popen("source {}; env".format(script), stdout=subprocess.PIPE, shell=True)
    output = pipe.communicate()[0]
    env = dict((line.decode(encoding).split("=", 1) for line in output.splitlines()))
    os.environ.update(env)

# prepare virtualenv; without, sys.executable points to /usr/bin/python in subsequent calls
shell_source('{}/env/bin/activate'.format(cwd))

def virtualenv_site_packages_directory():
    return 'env/lib/python{}.{}/site-packages/'.format(sys.version_info.major, sys.version_info.minor)

def virtualenv_site_packages(**kw):
    return '{cwd}/{pkg_dir}'.format(pkg_dir=virtualenv_site_packages_directory(), **kw)

# PYTHONPATH, PATH to use virtualenv, for subsequent calls
sys.path.insert(0, virtualenv_site_packages(cwd=cwd))
sys.path.insert(0, '{}/env/bin'.format(cwd))
os.environ.setdefault('PYTHONPATH', '')
os.environ['PYTHONPATH'] += ':{}'.format(virtualenv_site_packages(cwd=cwd))

cmd('pip install -r requirements.txt')

# Project paths from .env
from procboy.boy import InifilePrepend, Inifile, get_procfile, get_procfile_env
inip = InifilePrepend('./{}'.format(get_procfile_env()))
inip.run()
ini = Inifile('./{}'.format(get_procfile_env()))
ini.run()

from procboy.utils.runner import main
main()
