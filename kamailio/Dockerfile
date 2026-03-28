FROM ghcr.io/kamailio/kamailio-ci:6.1.1-alpine
RUN apk add sngrep vim python3    
WORKDIR /etc/kamailio
ENTRYPOINT ["sh","/etc/kamailio/init.sh"]
