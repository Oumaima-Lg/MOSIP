#!/bin/bash

# Properties file
set -e
properties_file="$1"
echo `date "+%m/%d/%Y %H:%M:%S"` ": $properties_file"
if [ -f "$properties_file" ]
then
     echo `date "+%m/%d/%Y %H:%M:%S"` ": Property file \"$properties_file\" found."
    while IFS='=' read -r key value
    do
        key=$(echo $key | tr '.' '_')
         eval ${key}=\${value}
    done < "$properties_file"
else
     echo `date "+%m/%d/%Y %H:%M:%S"` ": Property file not found, Pass property file name as argument."
fi

# ============================================
# ÉTAPE 1 : Copier tous les fichiers SQL dans le conteneur
# ============================================
echo `date "+%m/%d/%Y %H:%M:%S"` ": Copying SQL files to container..."

# Créer les dossiers nécessaires dans le conteneur
docker exec postgres mkdir -p /tmp/ddl /tmp/dml

# Copier les fichiers SQL à la racine
for file in db.sql ddl.sql drop_db.sql drop_role.sql role_dbuser.sql grants.sql dml.sql; do
    if [ -f "$file" ]; then
        docker cp "$file" postgres:/tmp/
        echo "  ✅ Copied $file"
    fi
done

# Copier tout le contenu des dossiers ddl et dml
if [ -d "ddl" ]; then
    docker cp ddl/. postgres:/tmp/ddl/
    echo "  ✅ Copied all files from ddl/ folder"
fi

if [ -d "dml" ]; then
    docker cp dml/. postgres:/tmp/dml/
    echo "  ✅ Copied all files from dml/ folder"
fi

echo `date "+%m/%d/%Y %H:%M:%S"` ": Files copied successfully"
echo "============================================"

# ============================================
# ÉTAPE 2 : Vérification que les fichiers sont bien dans le conteneur
# ============================================
echo "Vérification du contenu de /tmp/ dans le conteneur :"
docker exec postgres ls -la /tmp/
echo "============================================"

# ============================================
# ÉTAPE 3 : Exécution des scripts SQL
# ============================================

# Définir la commande psql avec PGPASSWORD
PSQL_CMD="docker exec -i -e PGPASSWORD=$SU_USER_PWD postgres psql"

## Terminate existing connections
echo "Terminating active connections" 
$PSQL_CMD --username=$SU_USER --dbname=$DEFAULT_DB_NAME -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '$MOSIP_DB_NAME' AND pid <> pg_backend_pid();"
echo "Terminated connections"

## Drop db and role - AVEC LE CHEMIN ABSOLU /tmp/
echo `date "+%m/%d/%Y %H:%M:%S"` ": Dropping database and role..."
$PSQL_CMD --username=$SU_USER --dbname=$DEFAULT_DB_NAME -f /tmp/drop_db.sql
$PSQL_CMD --username=$SU_USER --dbname=$DEFAULT_DB_NAME -f /tmp/drop_role.sql

## Create users
echo `date "+%m/%d/%Y %H:%M:%S"` ": Creating database users..."
$PSQL_CMD --username=$SU_USER --dbname=$DEFAULT_DB_NAME -f /tmp/role_dbuser.sql -v dbuserpwd=\'$DBUSER_PWD\'

## Create DB
echo `date "+%m/%d/%Y %H:%M:%S"` ": Creating database and tables..."
$PSQL_CMD --username=$SU_USER --dbname=$DEFAULT_DB_NAME -f /tmp/db.sql 
$PSQL_CMD --username=$SU_USER --dbname=$DEFAULT_DB_NAME -f /tmp/ddl.sql

## Grants
echo `date "+%m/%d/%Y %H:%M:%S"` ": Applying grants..."
$PSQL_CMD --username=$SU_USER --dbname=$DEFAULT_DB_NAME -f /tmp/grants.sql

## Populate tables
if [ ${DML_FLAG} == 1 ]
then
    echo `date "+%m/%d/%Y %H:%M:%S"` ": Deploying DML for ${MOSIP_DB_NAME} database..." 
    $PSQL_CMD --username=$SU_USER --dbname=$DEFAULT_DB_NAME -a -b -f /tmp/dml.sql
fi

echo `date "+%m/%d/%Y %H:%M:%S"` ": ✅ Script completed successfully!"