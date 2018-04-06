FROM alpine:edge

RUN apk add \
        --no-cache \
        --repository http://dl-3.alpinelinux.org/alpine/edge/testing/ \
        gosu && \
    apk add nginx bash

ADD nginx-boot.sh /sbin/nginx-boot
ADD docker-entrypoint.sh /sbin/docker-entrypoint.sh

ADD public/ /pub

ARG RELEASE
ARG APP_NAME
ARG INSTANCE_NAME
ARG BRANCH_NAME
ENV RELEASE=${RELEASE:-FORGOT_BUILD_ARG_RELEASE} \
    APP_NAME=${APP_NAME:-FORGOT_BUILD_ARG_APP_NAME} \
    INSTANCE_NAME=${INSTANCE_NAME:-FORGOT_BUILD_ARG_INSTANCE_NAME} \
    BRANCH_NAME=${BRANCH_NAME:-FORGOT_BUILD_ARG_BRANCH_NAME}
RUN echo "{\"APP_NAME\": \"$APP_NAME\", \"INSTANCE_NAME\": \"$INSTANCE_NAME\", \"RELEASE\": \"$RELEASE\"}" > /pub/RELEASE.txt

ENTRYPOINT [ "/sbin/docker-entrypoint.sh" ]
EXPOSE 3000
