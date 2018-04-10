import boto3
from botocore.exceptions import ClientError
from fabric.api import env, local

env.app_name = 'testdemo'


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


def _create_repository(instance_name):
    """
    Create a new Docker repository on ECR using the app_name/instance_name as
    the name of the repo

    returns the repository URL
    """
    repo_name = '{}/{}'.format(env.app_name, instance_name)
    existing_repo = _repository_exists(repo_name)
    if not existing_repo:
        ecr = boto3.client('ecr')
        try:
            response = ecr.create_repository(repositoryName=repo_name)
            return response['repository']['repositoryUri']
        except ClientError as e:
            raise e
    else:
        return existing_repo['repositoryUri']


def _build(instance_name):
    """
    Build the container
    """
    local('docker image prune -f')
    local('./bin/docker-build -a {} -i {}'.format(env.app_name, instance_name))


def _upload_to_repository(repository_url, instance_name):
    """
    Tag the docker image, upload to repository
    """
    kwargs = {
        'project_name': '{}/{}'.format(env.app_name, instance_name),
        'repository': repository_url,
    }
    docker_cmd = "docker tag {project_name} {repository}:latest".format(**kwargs)
    local(docker_cmd)

    print "Pushing to {repository}".format(**kwargs)
    docker_cmd = "eval $(aws ecr get-login --no-include-email --region us-east-1) && " \
                "docker push {repository}:latest".format(**kwargs)
    local(docker_cmd)


def create_test_instance(branch_name, instance_name=''):
    """
    @brief      Create a new test instance

    @param      branch_name    The branch name
    @param      instance_name  The instance name

    """
    # 1. Create docker repository
    # 2. Build
    # 3. Upload to docker repository
    # 4. Connect to test server
    # 5. Create test instance path
    # 6. Pull down image
    # 7. Create environment config with VIRTUAL_HOST
    # 8. docker run
    # 6. Create systemd config from template
    if instance_name == '':
        instance_name = branch_name
    repository_url = _create_repository(instance_name)
    # _build(instance_name)
    _upload_to_repository(repository_url, instance_name)
