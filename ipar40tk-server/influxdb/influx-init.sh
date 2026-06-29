#!/bin/sh

until influx ping --host http://influxdb:8086
do
    echo "Waiting for InfluxDB..."
    sleep 2
done

echo "InfluxDB ready"

if ! influx user list --host $INFLUX_URL --token "$INFLUX_TOKEN_OPENMAPS"  | grep "lathe"; then

    influx user create --host $INFLUX_URL --token "$INFLUX_TOKEN_OPENMAPS" --name lathe --password lathe-E3N01

fi

BUCKET_ID=$(influx bucket list --host $INFLUX_URL --token "$INFLUX_TOKEN_OPENMAPS" | awk '$2=="openmaps"{print $1}')

if ! influx auth list --host $INFLUX_URL --token "$INFLUX_TOKEN_OPENMAPS" | grep -qw lathe; then

    influx auth create --host $INFLUX_URL --token "$INFLUX_TOKEN_OPENMAPS" --org bmetk --user lathe --read-bucket "$BUCKET_ID"

fi
echo "Done"