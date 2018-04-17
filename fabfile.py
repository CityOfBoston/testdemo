import codecs
import os
import io
import boto3
from botocore.exceptions import ClientError
from fabric.api import env, local, sudo, run
from fabric.contrib.files import upload_template, exists

# TODO:
# Add update method
#   - Figure out why update screws up the running container
# Add start, stop, restart, list methods
# Make sure steps to implement are documented
# Create user account with RSA keys for github
# Do creation on the test server
# Do a shallow git clone into the test directory that can be updated
# Decide what to do with existing "<name>.test.boston.gov" apps
# Get wildcard domain for test.boston.gov
# Database and supplimental services


escape_decoder = codecs.getdecoder('unicode_escape')

if os.path.exists('.env'):
    for line in io.open('.env'):
        line.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        k, v = line.split('=', 1)
        k, v = k.strip(), v.strip()
        if v:
            v = v.encode('unicode-escape').decode('ascii')
            quoted = v[0] == v[-1] in ['"', "'"]
            if quoted:
                v = escape_decoder(v[1:-1])[0]
        os.environ[k] = v

env.app_name = 'testdemo'
env.use_ssh_config = True
env.hosts = ['test']


def _authenticate_to_registry():
    """
    Authenticate to the ECR registry for docker
    """
    run('eval $(aws ecr get-login --no-include-email --region us-east-1)')


def _repository_exists(repo_name):
    """
    Return True if the specified repository exists
    """
    ecr = boto3.client('ecr')
    try:
        response = ecr.describe_repositories(repositoryNames=[repo_name])
        if len(response['repositories']) == 1:
            return response['repositories'][0]
        else:
            raise Exception('Multiple repositories named "{}"'.format(repo_name))
    except ClientError as e:
        if e.response['Error']['Code'] == 'RepositoryNotFoundException':
            return False
        else:
            raise e


def _get_or_create_repository():
    """
    Create a new Docker repository on ECR using the app_name/instance_name as
    the name of the repo

    returns the repository URL
    """
    import json

    lifecycle_policy = {
        "rules": [
            {
                "rulePriority": 1,
                "description": "Keep only one untagged image, expire all others",
                "selection": {
                    "tagStatus": "untagged",
                    "countType": "imageCountMoreThan",
                    "countNumber": 1
                },
                "action": {
                    "type": "expire"
                }
            }
        ]
    }
    repo_name = '{app_name}/{instance_name}'.format(**env)
    existing_repo = _repository_exists(repo_name)
    if not existing_repo:
        ecr = boto3.client('ecr')
        try:
            response = ecr.create_repository(repositoryName=repo_name)
            url = response['repository']['repositoryUri']
            ecr.put_lifecycle_policy(
                repositoryName=repo_name,
                lifecyclePolicyText=json.dumps(lifecycle_policy))
            return url
        except ClientError as e:
            raise e
    else:
        return existing_repo['repositoryUri']


def _delete_repository():
    """
    Delete an existing Docker repository on ECR using the app_name/instance_name as
    the name of the repo
    """
    repo_name = '{app_name}/{instance_name}'.format(**env)
    existing_repo = _repository_exists(repo_name)
    if existing_repo:
        ecr = boto3.client('ecr')
        try:
            ecr.delete_repository(repositoryName=repo_name, force=True)
        except ClientError as e:
            raise e


def _build():
    """
    Build the container
    """
    local('docker image prune -f')
    local('./bin/docker-build -a {} -i {}'.format(env.app_name, env.instance_name))


def _upload_to_repository():
    """
    Tag the docker image, upload to repository
    """
    kwargs = {
        'project_name': '{}/{}'.format(env.app_name, env.instance_name),
        'repository': env.repository_url,
    }
    docker_cmd = "docker tag {project_name} {repository}:latest".format(**kwargs)
    local(docker_cmd)

    print "Pushing to {repository}".format(**kwargs)
    docker_cmd = "eval $(aws ecr get-login --no-include-email --region us-east-1) && " \
                "docker push {repository}:latest".format(**kwargs)
    local(docker_cmd)


def _setup_path():
    """
    Set up the path on the remote server
    """
    path = '/testing/{}/{}'.format(env.app_name, env.instance_name)
    sudo('mkdir -p {}'.format(path))

    # Set up the permissions on all the paths
    sudo('chgrp -R docker /testing')
    sudo('chmod -R g+w /testing')


def _remove_path():
    """
    Remove the path o the remote server
    """
    path = '/testing/{}/{}'.format(env.app_name, env.instance_name)
    if exists(path):
        sudo('rm -Rf {}'.format(path))


def _setup_service():
    """
    Set up the service
    """
    systemd_template = 'deploy/systemd-test.conf.template'
    systemd_tmp_dest = '/tmp/{instance_name}.service'.format(**env)
    systemd_dest = '/etc/systemd/system/{instance_name}.service'.format(**env)
    if not exists(systemd_dest):
        upload_template(systemd_template, systemd_tmp_dest, env.context)
        sudo('mv {} {}'.format(systemd_tmp_dest, systemd_dest))
        sudo('systemctl enable {instance_name}.service'.format(**env))
        sudo('systemctl start {instance_name}.service'.format(**env))


def _remove_service():
    """
    Stop the service, and remove its configuration
    """
    systemd_dest = '/etc/systemd/system/{instance_name}.service'.format(**env)
    if exists(systemd_dest):
        sudo('systemctl disable {instance_name}.service'.format(**env))
        sudo('systemctl stop {instance_name}.service'.format(**env))
        sudo('rm {}'.format(systemd_dest))


def _setup_templates():
    """
    Write the templates to the appropriate places
    """
    env_template = 'deploy/env-test.template'
    env_dest = '/testing/{app_name}/{instance_name}/test.env'.format(**env)
    if not exists(env_dest):
        upload_template(env_template, env_dest, env.context)


def _update_image():
    """
    Pull down the latest version of the image from the repository
    """
    run("eval $(aws ecr get-login --no-include-email --region us-east-1) && "
        "docker pull {repository_url}:latest".format(**env))

    # Delete the container if it exists
    containers = run('docker ps -a --filter name={app_name}-{instance_name} --format "{{{{.ID}}}}"'.format(**env))
    if len(containers) > 0:
        run('docker stop -t2 {app_name}-{instance_name}'.format(**env))
        run('docker rm {app_name}-{instance_name}'.format(**env))

    run('docker create --env-file /testing/{app_name}/{instance_name}/test.env --name {app_name}-{instance_name} {repository_url}:latest'.format(**env))

    # If the container existed before, we need to start it again
    if len(containers) > 0:
        run('docker start -a {app_name}-{instance_name}'.format(**env))


def _prune_docker():
    """
    Tell docker to get rid of unused images
    """
    run('docker container prune -f')
    run('docker image prune -f')


def create_test_instance(branch_name, instance_name=''):
    """
    @brief      Create a new test instance

    @param      branch_name    The branch name
    @param      instance_name  The instance name, if different than the branch name
    """
    if instance_name == '':
        instance_name = branch_name
    env.instance_name = instance_name
    env.branch_name = branch_name
    env.release = local('git rev-parse --verify HEAD')
    env.context = {
        'APP_NAME': env.app_name,
        'INSTANCE_NAME': instance_name,
        'BRANCH_NAME': env.branch_name,
        'RELEASE': env.release,
    }
    env.repository_url = _get_or_create_repository()
    _build()
    _upload_to_repository()
    _setup_path()
    _setup_templates()
    _update_image()
    _setup_service()


def update_test_instance(instance_name):
    """
    Update a test instance with a new image
    """
    env.instance_name = instance_name
    env.branch_name = local('git rev-parse --abbrev-ref HEAD')
    env.release = local('git rev-parse --verify HEAD')
    env.context = {
        'APP_NAME': env.app_name,
        'INSTANCE_NAME': instance_name,
        'BRANCH_NAME': env.branch_name,
        'RELEASE': env.release,
    }
    env.repository_url = _get_or_create_repository()
    _build()
    _upload_to_repository()
    _update_image()
    sudo('systemctl start {instance_name}.service'.format(**env))


def remove_test_instance(instance_name):
    """
    @brief      Removes a test instance.

    @param      instance_name  The instance name
    """
    env.instance_name = instance_name
    _delete_repository()
    _remove_service()
    _remove_path()
    _prune_docker()
