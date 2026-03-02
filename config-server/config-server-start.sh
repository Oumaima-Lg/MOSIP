#!/bin/bash
# Charger les variables d'environnement
source .env

java -jar \
  -Ddb.dbuser.password="${DB_DBUSER_PASSWORD}" \
  -Dpreregistration.mosip.prereg.client.secret="${PREREGISTRATION_CLIENT_SECRET}" \
  -Dkeycloak.host="${KEYCLOAK_HOST}" \
  -Dprereg.captcha.site.key="${PREREG_CAPTCHA_SITE_KEY}" \
  -Dprereg.captcha.secret.key="${PREREG_CAPTCHA_SECRET_KEY}" \
  -Dspring.profiles.active=native \
  -Dspring.cloud.config.server.native.search-locations=file:///C:/Users/olaghjibi/MOSIP/mosip-config/sandbox-local/ \
  -Dspring.cloud.config.server.accept-empty=true \
  -Dspring.cloud.config.server.git.force-pull=false \
  -Dspring.cloud.config.server.git.cloneOnStart=false \
  -Dspring.cloud.config.server.git.refreshRate=0 \
  kernel-config-server-1.2.0-20201016.134941-57.jar
