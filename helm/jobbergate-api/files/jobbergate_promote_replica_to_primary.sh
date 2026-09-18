#!/bin/bash
set -e

dt=$(date '+%d/%m/%Y %H:%M:%S');
echo "$dt - Attempting to promote a Replica PostgreSql to Primary..." > /usr/share/promotion.log

standbyFilePath="$PGDATA/standby.signal"

if [[ ! -f "$standbyFilePath" ]]; then
  echo "$dt - Skipping as this PostgreSql is already a Primary since the file '$standbyFilePath' does not exist." >> /usr/share/promotion.log

else

  counter=1
  until pg_isready -U postgres || [[ $counter -gt 10 ]]
  do
    echo "$dt - Attempt $counter - Postgres is not ready yet. Waiting..." > /usr/share/promotion.log
    ((counter++))
    sleep 5
  done

  if pg_isready -U postgres; then
    echo "$dt - Running: su -c '/usr/local/bin/pg_ctl promote -D $PGDATA' postgres" >> /usr/share/promotion.log
    su -c '/usr/local/bin/pg_ctl promote -D $PGDATA' postgres >> /usr/share/promotion.log
  else
    echo "$dt - Postgres is still not ready. We tried $counter times. Stopping attempts." > /usr/share/promotion.log
  fi

fi