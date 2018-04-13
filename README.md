# City of Boston Test Infrastructure Demo

This project was started using [Gatsby Docs Starter](https://github.com/ericwindmill/gatsby-starter-docs)

The Docker configuration was borrowed from [Gatsby-Docker](https://github.com/gatsbyjs/gatsby-docker) and extended for educational purposes.

If you have multiple AWS credentials configured on your local machine, you will need to add `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` with the appropriate values to a `.env` file.

## bin directory

To run these commands from the project directory, prefix them with `./bin/` like `./bin/foo` to run the `foo` command.

**`docker-build`**

This builds the Gatsby site and then builds the Docker container.

It includes three build arguments in the command: `RELEASE`, `APP_NAME`, `BRANCH_NAME`, and `INSTANCE_NAME`. These are included in the container's environment as variables and also written to a text file named `RELEASE.txt`.

By default `RELEASE` is the git hash, `APP_NAME` is name of the current directory, `BRANCH_NAME` and `INSTANCE_NAME` are both the name of the current branch.

**`docker-run`**

This runs the Docker container.

You can also run commands within the Docker container by adding them at the end of the command. For example `./bin/docker-run bash` will launch the container and put you into the bash shell. You can use `ctrl-d` to exit.

## deploy directory

At least two templates are required for each test instance: one for the environment variable configurations and one for the system service.

**`env-test.template`**

This **must** include the entry `VIRTUAL_HOST=%(INSTANCE_NAME)s.test.boston.gov`. That gives the DNS name that the test instance listens on, and the nGinx proxy routes to.

Anything else is up to you.

**`systemd-test.conf.template`**

This is the systemd service configuration that is installed.

You can manage the service with `sudo systemctl [start|stop|restart|reload] <instance_name>`. You can check the status with `systemctl status <instance_name>`.