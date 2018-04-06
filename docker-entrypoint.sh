#!/bin/bash

if [ $# -gt 0 ]; then
    USER_ID=${LOCAL_USER_ID:-9001}
    GROUP_ID=${LOCAL_GROUP_ID:-9001}

    addgroup -S -g $GROUP_ID user
    adduser -S -D -s /bin/bash -G user -u $USER_ID user
    export HOME=/home/user

    echo "Running overridden command $@ as UID $USER_ID."
    exec gosu user "$@"
else
    exec /sbin/nginx-boot
fi