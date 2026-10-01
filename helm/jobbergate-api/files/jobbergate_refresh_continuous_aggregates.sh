#!/bin/bash

export PGPASSWORD=$DB_PASSWORD

if [[ "$MULTI_TENANCY_ENABLED" == "true" ]]; then
    # Multi-tenancy: one database per organization, named after the organization id (UUID).
    echo "Fetching the list of databases"
    DB_LIST=$(psql -h $DB_HOST \
    -p $DB_PORT \
    -U $DB_USER \
    -w \
    -d $INIT_DB \
    -c "SELECT datname FROM pg_database WHERE datname ~ '^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$';" -t -A)
else
    # Single tenant: refresh the only database.
    DB_LIST=$INIT_DB
fi
echo ""

for DB in $DB_LIST
do
    (
        echo "Refreshing the view $VIEW_NAME in $DB"
        psql -h $DB_HOST \
        -p $DB_PORT \
        -U $DB_USER \
        -w \
        -d $DB -c "CALL refresh_continuous_aggregate('$VIEW_NAME', NULL, NULL);" -t -A
        echo "View $VIEW_NAME in $DB refreshed"
        echo ""
    ) &
done
wait
