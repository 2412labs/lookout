#!/bin/bash
usage() { echo "Usage: $0 [-l logfilePath] [-p installPath] [-s serviceName] [-r]"; echo "-r runs the service after install" 1>&2; exit 1; }

while getopts l::rhs::p option
do
 case "${option}"
 in
 l) LOG=${OPTARG};;
 r) RUN=1;;
 s) SERVICE=${OPTARG};;
 p) INSTALL_DIR=$OPTARG;;
 h) HELP=1;;
 esac
done

if [ $HELP ]; then
  usage
  exit 1
fi

: ${LOG=/var/log/notifything}
: ${SERVICE=notifything.service}
: ${INSTALL_DIR=/usr/local/notifything}

echo checking if $INSTALL_DIR exists ...

if [ ! -e $INSTALL_DIR/conf.json ]; then
    echo "you must place AWS iot thing certs in $INSTALL_DIR/certs"
    mkdir -p $INSTALL_DIR
fi

echo "copying files to $INSTALL_DIR"

cp -rf * $INSTALL_DIR/
chmod +x $INSTALL_DIR/run.sh

if [ ! -e $INSTALL_DIR/conf.json ]; then
    echo "Creating conf.json.  You must edit the file prior to starting the service."
    cp $INSTALL_DIR/conf_example.json $INSTALL_DIR/conf.json
fi

systemctl stop $SERVICE

cat > /lib/systemd/system/$SERVICE <<ENDSERVICE
[Unit]
Description=Notifier service
After=multi-user.target

[Service]
Type=simple
ExecStart=$INSTALL_DIR/run.sh $LOG
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target

ENDSERVICE

systemctl daemon-reload
systemctl enable $SERVICE

echo "service $SERVICE updated"

if [ -z "$RUN" ]; then
    echo "service has NOT been started automatically.  to start service run this command:"
    echo "systemctl start $SERVICE"
else
    echo "starting $SERVICE ..."
    systemctl start $SERVICE
    echo "$SERVICE is started"
    systemctl status $SERVICE
fi

echo "to view app log files run this command:"
echo "cat $LOG/current"
