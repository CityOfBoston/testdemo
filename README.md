# City of Boston Test Infrastructure Demo

This project was started using [Gatsby Docs Starter](https://github.com/ericwindmill/gatsby-starter-docs)

The Docker configuration was borrowed from [Gatsby-Docker](https://github.com/gatsbyjs/gatsby-docker) and extended for educational purposes.

## bin directory

To run these commands from the project directory, prefix them with `./bin/` like `./bin/foo` to run the `foo` command.

**`docker-build`**

This builds the Gatsby site and then builds the Docker container.

It includes three build arguments in the command: `RELEASE`, `APP_NAME`, `BRANCH_NAME`, and `INSTANCE_NAME`. These are included in the container's environment as variables and also written to a text file named `RELEASE.txt`.

By default `RELEASE` is the git hash, `APP_NAME` is name of the current directory, `BRANCH_NAME` and `INSTANCE_NAME` are both the name of the current branch.

**`docker-run`**

This runs the Docker container.

You can also run commands within the Docker container by adding them at the end of the command. For example `./bin/docker-run bash` will launch the container and put you into the bash shell. You can use `ctrl-d` to exit.