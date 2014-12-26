import os
from fabric.api import *
from fabric.contrib.files import exists
from fabric.contrib.project import rsync_project

# application settings
config = type(env)()
app_user = 'app_user'
app_name = 'app_name'
app_dir = '/home/%s/%s' % (app_user, app_name)

local_supervisor_conf = './etc/supervisor.conf'
system_supervisor_conf = '/etc/supervisor/conf.d/%s.conf' % app_name
local_ngix_conf = './etc/nginx.conf'
system_nginx_conf = '/etc/nginx/sites-enabled/%s' % app_name

# fabric settings
env.hosts = ['dev.elifiner.com']
env.use_ssh_config = True

nginx_conf_template = '''
server {
    location / {
        proxy_pass http://127.0.0.1:8000;
    }
    location /static {
        alias /home/%(app_user)s/%(app_name)s/static/;
    }
}
''' % dict(app_user=app_user, app_name=app_name)

supervisor_conf_template = '''
[program:%(app_name)s]
command = /home/%(app_user)s/%(app_name)s/venv/bin/gunicorn app:app -b localhost:8000
directory = /home/%(app_user)s/%(app_name)s
user = %(app_user)s
''' % dict(app_user=app_user, app_name=app_name)

def _install_requirements():
    with hide('stdout'):
        sudo('apt-get install -y python')
        sudo('apt-get install -y python-pip')
        sudo('apt-get install -y python-virtualenv')
        sudo('apt-get install -y nginx')
        sudo('apt-get install -y supervisor')
        sudo('apt-get install -y git')

def _configure_supervisor():
    sudo('ln -s %s/%s %s' % (app_path, local_ngix_conf, system_supervisor_conf))
    sudo('supervisorctl reread')
    sudo('supervisorctl update')

def _configure_nginx():
    sudo('ln -s %s/%s %s' % (app_path, source_nginx_conf, system_nginx_conf))
    sudo('/etc/init.d/nginx restart')

def _sync_code():
    if not exists(app_dir):
        run('mkdir -p %s' % app_dir)
    rsync_project(local_dir='./', remote_dir=app_dir, exclude=['venv'])

def _update_venv():
    with cd(app_dir):
        if not exists('venv/'):
            run('virtualenv venv --prompt="(%s)"' % app_name)
        with prefix('source venv/bin/activate'):
            run('pip install -r requirements.txt')

def make_conf():
    '''Generate nginx and supervisor configuration files'''
    if not os.path.exists('etc'):
        os.makedirs('etc')
    with open(local_supervisor_conf, 'w') as f:
        f.write(supervisor_conf_template)
    with open(local_ngix_conf, 'w') as f:
        f.write(nginx_conf_template)

def install():
    _install_requirements()
    _sync_code()
    _update_venv()
    _configure_supervisor()
    _configure_nginx()

def uninstall():
    if exists(app_dir):
        run('rm -rf %s' % app_dir)
    if exists(system_nginx_conf):
        sudo('rm %s' % system_nginx_conf)
    if exists(system_supervisor_conf):
        sudo('rm %s' % system_supervisor_conf)

def update():
    _sync_code()
    restart()

def start():
    sudo('supervisorctl start %s' % app_name)

def stop():
    sudo('supervisorctl stop %s' % app_name)

def restart():
    sudo('supervisorctl restart %s' % app_name)
