# MOSIP Pre-Registration Docker Setup - Full Context for Next Conversation

## HOW TO USE THIS DOCUMENT
Paste this entire document at the start of the next conversation with Claude, followed by your new question/issue.

---

## PROJECT OVERVIEW
Setting up MOSIP Pre-Registration stack on Docker Desktop (Windows, MINGW64 Git Bash + PowerShell).
Goal: Complete end-to-end pre-registration flow (Demographics → Documents → Booking).

**IMPORTANT WINDOWS NOTES:**
- Use `py` instead of `python3` in Windows commands
- Use `sh -c "..."` with docker exec to avoid Git Bash path mangling (e.g. `/home/mosip` becoming `C:/Program Files/Git/home/mosip`)
- Commands with `!` must be run in PowerShell not Git Bash (bash history expansion issue)
- File-writing scripts that use `$VAR` must be created in PowerShell to avoid variable expansion

---

## INFRASTRUCTURE

### Docker Network
```
mosip-network (bridge)
```

### Config Server
- JAR: `C:\Users\olaghjibi\MOSIP\jars\kernel-config-server-1.2.0-20201016.134941-57.jar`
- Port: 51000
- Config dir: `C:\Users\olaghjibi\MOSIP\mosip-config\sandbox-local\`
- Run from: `C:\Users\olaghjibi\MOSIP\`

### Postgres
- Image: `postgres:10`
- Port: 5432
- Databases: mosip_master, mosip_prereg, mosip_kernel, mosip_keymgr, mosip_audit, mosip_regprc, mosip_keycloak
- Users: kerneluser/mosip123, keymgruser/mosip123, prereguser/mosip123, masteruser/mosip123

### Keycloak
- Image: `mosipid/mosip-keycloak:1.2.0`
- Port: 8080
- Admin: admin/mosip123
- Realm `mosip`: clients mosip-admin-client, mosip-auth-client (secret: mosip123)
- Realm `preregistration`: client mosip-prereg-client (secret: prereg_client_secret_123456)

---

## RUNNING CONTAINERS & PORTS

| Container | Image/JAR | Port | Status |
|---|---|---|---|
| postgres | postgres:10 | 5432 | ✅ |
| keycloak | mosipid/mosip-keycloak:1.2.0 | 8080 | ✅ |
| softhsm | mosipid/softhsm:v2 | 5666 | ✅ |
| kernel-auth-service | JAR | 8091 | ✅ |
| kernel-auditmanager-service | JAR | 8082 | ✅ |
| kernel-masterdata-service | JAR | 8086 | ✅ |
| kernel-otpmanager-service | kernel-otpmanager-custom:1.2.0 | 8085 | ✅ |
| kernel-pridgenerator-service | mosipid/kernel-pridgenerator-service:1.2.0 | 8100 | ✅ |
| kernel-keymanager-service | kernel-keymanager-custom:1.2.0 | 8088 | ✅ |
| pre-registration-application-service | pre-reg-custom:1.2.0 | 9090 | ✅ |
| pre-registration-booking-service | pre-reg-booking-custom:1.2.0 | 9095 | ✅ |
| pre-registration-batchjob | pre-reg-batchjob-custom:1.2.0 | 9097 | ✅ |
| file-server | nginx | 8083 | ✅ |
| mosip-proxy | nginx | 80 | ✅ |
| pre-reg-ui | mosipid/pre-registration-ui:1.2.0 | 8081 | ✅ |
| mock-notifier | nginx | internal | ✅ |

---

## CUSTOM DOCKERFILES

All located at `C:\Users\olaghjibi\MOSIP\`

### Dockerfile (pre-reg-custom:1.2.0)
```dockerfile
FROM mosipid/pre-registration-application-service:1.2.0
USER root
RUN mkdir -p /home/mosip/additional_jars
COPY jars/kernel-auth-adapter-1.2.0.jar /home/mosip/additional_jars/kernel-auth-adapter.jar
RUN chmod 644 /home/mosip/additional_jars/kernel-auth-adapter.jar
USER 1001:1001
```

### Dockerfile.booking (pre-reg-booking-custom:1.2.0)
```dockerfile
FROM mosipid/pre-registration-booking-service:1.2.0
USER root
RUN mkdir -p /home/mosip/additional_jars
COPY jars/kernel-auth-adapter-1.2.0.jar /home/mosip/additional_jars/kernel-auth-adapter.jar
RUN chmod 644 /home/mosip/additional_jars/kernel-auth-adapter.jar
USER 1001:1001
```

### Dockerfile.batchjob (pre-reg-batchjob-custom:1.2.0)
```dockerfile
FROM mosipid/pre-registration-batchjob:1.2.0
USER root
RUN mkdir -p /home/mosip/additional_jars
COPY jars/kernel-auth-adapter-1.2.0.jar /home/mosip/additional_jars/kernel-auth-adapter.jar
RUN chmod 644 /home/mosip/additional_jars/kernel-auth-adapter.jar
USER 1001:1001
```

### Dockerfile.otpmanager (kernel-otpmanager-custom:1.2.0)
```dockerfile
FROM mosipid/kernel-otpmanager-service:1.2.0
USER root
RUN mkdir -p /home/mosip/additional_jars
COPY jars/kernel-auth-adapter-1.2.0.jar /home/mosip/additional_jars/kernel-auth-adapter.jar
RUN chmod 644 /home/mosip/additional_jars/kernel-auth-adapter.jar
USER 1001:1001
```

### Dockerfile.keymanager (kernel-keymanager-custom:1.2.0)
```dockerfile
FROM mosipid/kernel-keymanager-service:1.2.0
USER root
RUN apt-get update && apt-get install -y softhsm2 && \
    mkdir -p /var/lib/softhsm/tokens && \
    mkdir -p /config /home/mosip/additional_jars /home/mosip/hsm-lib && \
    mkdir -p /home/mosip/.config/softhsm2 && \
    echo 'directories.tokendir = /var/lib/softhsm/tokens' > /home/mosip/.config/softhsm2/softhsm2.conf && \
    echo 'objectstore.backend = file' >> /home/mosip/.config/softhsm2/softhsm2.conf && \
    chown -R 1001:1001 /home/mosip /var/lib/softhsm /config
COPY softhsm-application.conf /config/softhsm-application.conf
COPY patch_configure.py /tmp/patch_configure.py
RUN python3 /tmp/patch_configure.py
USER 1001:1001
RUN softhsm2-util --init-token --slot 0 --label "keymanager" --pin 1234 --so-pin 1234
```

### patch_configure.py (used by Dockerfile.keymanager)
```python
import sys
content = open('/home/mosip/configure_start.sh').read()
content = content.replace('sudo ./install.sh', './install.sh')
content = content.replace('mkdir "$DIR_NAME"', 'rm -rf "$DIR_NAME"; mkdir "$DIR_NAME"')
open('/home/mosip/configure_start.sh', 'w').write(content)
print("Done")
```
**IMPORTANT:** Create this file in PowerShell using `@"..."@ | Set-Content` to avoid `$DIR_NAME` variable expansion.

### softhsm-application.conf
```
name=SoftHSM
library=/usr/lib/softhsm/libsofthsm2.so
slotListIndex=0
```

---

## KEY RUN COMMANDS

### softhsm
```bash
docker run -d --name softhsm --network mosip-network \
  -e SECURITY_OFFICER_PIN=1234 \
  -e PKCS11_DAEMON_SOCKET=tcp://0.0.0.0:5666 \
  -v softhsm-data:/softhsm \
  mosipid/softhsm:v2
```

### kernel-pridgenerator-service
```bash
# First copy auth adapter to file-server:
docker cp /c/Users/olaghjibi/MOSIP/jars/kernel-auth-adapter-1.2.0.jar file-server:/usr/share/nginx/html/kernel-auth-adapter.jar

docker run -d --name kernel-pridgenerator-service --network mosip-network -p 8100:8100 \
  -e active_profile_env=default \
  -e spring_config_label_env=master \
  -e spring_config_url_env=http://host.docker.internal:51000/config \
  -e iam_adapter_url_env=http://file-server/kernel-auth-adapter.jar \
  -e artifactory_url_env="http://localhost/skip" \
  -e is_glowroot_env=notpresent \
  mosipid/kernel-pridgenerator-service:1.2.0
```

### kernel-keymanager-service
```bash
# Build client.zip from softhsm container (Step 1 - Git Bash):
docker exec softhsm sh -c "mkdir -p /tmp/hsm-client && cp /usr/local/lib/libpkcs11-proxy.so.0 /tmp/hsm-client/ && cp /usr/local/lib/libpkcs11-proxy.so.0.1 /tmp/hsm-client/ && cp /usr/local/lib/libpkcs11-proxy.so /tmp/hsm-client/"

# Step 2 - PowerShell ONLY:
$script = "#!/bin/sh`nmkdir -p /home/mosip/hsm-lib`ncp libpkcs11-proxy.so.0 /home/mosip/hsm-lib/`ncp libpkcs11-proxy.so.0.1 /home/mosip/hsm-lib/`ncp libpkcs11-proxy.so /home/mosip/hsm-lib/`n"
$script | docker exec -i softhsm sh -c "cat > /tmp/hsm-client/install.sh && chmod +x /tmp/hsm-client/install.sh"

# Step 3 - PowerShell:
docker exec -u root softhsm sh -c "apt-get update -qq && apt-get install -y -qq zip && cd /tmp && zip -j client.zip hsm-client/*"
docker cp softhsm:/tmp/client.zip C:\Users\olaghjibi\MOSIP\client.zip
docker cp C:\Users\olaghjibi\MOSIP\client.zip file-server:/usr/share/nginx/html/client.zip

# Build image:
cd /c/Users/olaghjibi/MOSIP && docker build -f Dockerfile.keymanager -t kernel-keymanager-custom:1.2.0 .

# Run:
docker run -d --name kernel-keymanager-service --network mosip-network -p 8088:8088 \
  -e active_profile_env=default \
  -e spring_config_label_env=master \
  -e spring_config_url_env=http://host.docker.internal:51000/config \
  -e iam_adapter_url_env=http://file-server/kernel-auth-adapter.jar \
  -e artifactory_url_env=http://file-server \
  -e hsm_zip_file_path=client.zip \
  -e is_glowroot_env=notpresent \
  kernel-keymanager-custom:1.2.0
```

### Generate Master Keys (run after keymanager starts)
```bash
TOKEN=$(docker exec kernel-keymanager-service curl -s -X POST "http://keycloak:8080/auth/realms/mosip/protocol/openid-connect/token" \
  -d "client_id=mosip-admin-client&client_secret=mosip123&grant_type=client_credentials" | py -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

# Generate ROOT key:
docker exec kernel-keymanager-service curl -s -X POST "http://localhost:8088/v1/keymanager/generateMasterKey/certificate" \
  -H "Cookie: Authorization=$TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"id":"io.mosip.kernel.generateMasterKey","version":"1.0","requesttime":"2026-03-14T00:00:00.000Z","request":{"applicationId":"ROOT","referenceId":"","force":false}}'

# Generate PRE_REGISTRATION key:
docker exec kernel-keymanager-service curl -s -X POST "http://localhost:8088/v1/keymanager/generateMasterKey/certificate" \
  -H "Cookie: Authorization=$TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"id":"io.mosip.kernel.generateMasterKey","version":"1.0","requesttime":"2026-03-14T00:00:00.000Z","request":{"applicationId":"PRE_REGISTRATION","referenceId":"","force":false}}'
```

---

## KEY CONFIGURATION FILES

### application-default.properties (key overrides added)
```properties
mosip.country.code=MOR
mosip.mandatory-languages=eng
mosip.optional-languages=ara,fra
mosip.kernel-pridgenerator-service.url=http://kernel-pridgenerator-service:8100
mosip.kernel-keymanager-service.url=http://kernel-keymanager-service:8088
softhsm.kernel.pin=1234
```

### pre-registration-default.properties (key overrides)
```properties
mosip.iam.adapter.clientid=mosip-admin-client
mosip.iam.adapter.clientsecret=mosip123
mosip.iam.adapter.appid=admin
mosip.iam.adapter.issuerURL=http://keycloak:8080/auth/realms/mosip
mosip.preregistration.id-schema=http://kernel-masterdata-service:8086/v1/masterdata/idschema/latest
mosip.kernel.idobjectvalidator.referenceValidator=
logging.level.io.mosip.kernel.idobjectvalidator=DEBUG
```

### kernel-keymanager-service-default.properties
```properties
mosip.auth.adapter.impl.basepackage=io.mosip.kernel.auth.defaultadapter
mosip.kernel.auth.adapter.ssl-bypass=true
mosip.iam.adapter.appid=admin
mosip.iam.adapter.clientid=mosip-admin-client
mosip.iam.adapter.clientsecret=mosip123
mosip.iam.adapter.issuerURL=http://keycloak:8080/auth/realms/mosip
auth.server.admin.issuer.uri=http://keycloak:8080/auth/realms/
mosip.kernel.auth.appids.realm.map={prereg:'preregistration',ida:'mosip',registrationclient:'mosip',regproc:'mosip',partner:'mosip',resident:'mosip',admin:'mosip'}
javax.persistence.jdbc.url=jdbc:postgresql://postgres:5432/mosip_keymgr
javax.persistence.jdbc.user=keymgruser
javax.persistence.jdbc.password=mosip123
mosip.kernel.keymanager.softhsm.config-path=/etc/softhsm/softhsm2.conf
mosip.kernel.keymanager.softhsm.keystore-type=PKCS11
mosip.kernel.keymanager.softhsm.keystore-pass=1234
keycloak.use-resource-role-mappings=false
```

---

## DATABASE DATA INSERTED

### mosip_master database
```sql
-- Languages
INSERT INTO master.language(code, name, native_name, is_active, cr_by, cr_dtimes, is_deleted)
VALUES ('eng','English','English',TRUE,'superadmin',NOW(),FALSE),
       ('ara','Arabic','عربى',TRUE,'superadmin',NOW(),FALSE),
       ('fra','French','Français',TRUE,'superadmin',NOW(),FALSE);

-- Gender dynamic fields (one row per code per language)
INSERT INTO master.dynamic_field(id, name, description, data_type, value_json, lang_code, is_active, cr_by, cr_dtimes, is_deleted)
VALUES
('1','gender','Gender','string','{"code":"MLE","value":"Male"}','eng',TRUE,'superadmin',NOW(),FALSE),
('2','gender','Gender','string','{"code":"FLE","value":"Female"}','eng',TRUE,'superadmin',NOW(),FALSE),
('3','gender','Gender','string','{"code":"OTH","value":"Others"}','eng',TRUE,'superadmin',NOW(),FALSE),
-- ara and fra versions similarly...

-- ResidenceStatus dynamic fields
-- ('x','residenceStatus',...) FR=Foreigner, NFR=Non-Foreigner per lang

-- Location hierarchy (MOR as root)
-- loc_hierarchy_list for eng/ara/fra
-- location table: MOR→REG01→PROV01→CITY01→ZONE01 for all 3 languages

-- Consent template
INSERT INTO master.template_type(code, descr, lang_code, is_active, cr_by, cr_dtimes, is_deleted)
VALUES ('consent', 'Consent Template', 'eng', TRUE, 'superadmin', NOW(), FALSE);
INSERT INTO master.template(id, name, descr, file_format_code, file_txt, module_id, module_name, template_typ_code, lang_code, is_active, cr_by, cr_dtimes, is_deleted)
VALUES ('4','Consent Template','Consent Template','txt','I hereby consent...','PREREG','Pre-Registration','consent','eng',TRUE,'superadmin',NOW(),FALSE);
```

### mosip_master - identity_schema
```sql
-- schema_json must NOT have "id" fields inside properties (causes URI resolution bug)
-- Must have "$schema":"http://json-schema.org/draft-07/schema#" at root
-- Fields use "$ref":"#/definitions/simpleType" for array fields
UPDATE master.identity_schema SET schema_json = '...' WHERE id = '1';
```

### mosip_master - ui_spec
```sql
-- jsonSpec format: {"identity": {"identity": [...fields...], "locationHierarchy": [["region","province","city","zone","postalCode"]]}}
-- labelName must be object: {"eng":"..","ara":"..","fra":".."}
-- fieldType:"dynamic" + subType:"gender"|"residenceStatus" for dropdowns
```

### mosip_keymgr - key_policy_def
```sql
-- Inserted from official MOSIP CSV (keymanager repo release-1.2.0)
-- Key app_ids: PRE_REGISTRATION, REGISTRATION, REGISTRATION_PROCESSOR, IDA, 
--              ID_REPO, KERNEL, ROOT, BASE, PMS, DATASHARE, CREDENTIAL_SERVICE,
--              RESIDENT, ADMIN_SERVICES
```

---

## IMPORTANT TECHNICAL NOTES

### Authentication Pattern
- Services use `Cookie: Authorization=<token>` NOT `Authorization: Bearer <token>`
- Token from: `curl -X POST http://keycloak:8080/auth/realms/mosip/protocol/openid-connect/token -d 'client_id=mosip-admin-client&client_secret=mosip123&grant_type=client_credentials'`
- Pre-registration user tokens: from `preregistration` realm, validated by pre-reg service internally

### ID Schema Validation
- `KER-IOV-002`: ID object validation failed
  - Fixed by: removing `"id"` fields from schema properties (they interfere with `$ref` URI resolution)
  - Disabled reference validator: `mosip.kernel.idobjectvalidator.referenceValidator=`
- Schema must NOT have field-level `id` properties alongside `$ref`

### Keymanager Auth
- Endpoints require `Cookie: Authorization=<token>` 
- `generateMasterKey` endpoint path: `/v1/keymanager/generateMasterKey/certificate` (not `/ROOT`)
- ROOT key must be generated before any app-specific key
- Key policies must exist in `keymgr.key_policy_def` before key generation

### Location Data
- `mosip.country.code=MOR` → used as root location code
- Location hierarchy: MOR (country) → REG01 (region) → PROV01 (province) → CITY01 (city) → ZONE01 (zone)
- Must exist for all 3 languages (eng, ara, fra)

### Dynamic Fields
- `value_json` = single object `{"code":"X","value":"Y"}` NOT an array
- One DB row per code per language
- API auth uses `Cookie: Authorization=<token>`

### File Server
- Serves files at `http://file-server/<filename>`
- Used to serve: `kernel-auth-adapter.jar`, `client.zip`, `pre-registration-i18n-bundle.zip`
- Copy files: `docker cp <file> file-server:/usr/share/nginx/html/<filename>`

---

## CURRENT FLOW STATUS
- ✅ OTP Login
- ✅ Demographic form renders with all fields
- ✅ Gender/ResidenceStatus dropdowns work
- ✅ Location dropdowns work (Region/Province/City/Zone)
- ✅ Demographic form save (Continue button) — JUST FIXED
- 🔄 Document Upload — NEXT ISSUE TO SOLVE
- ⏳ Booking/Appointment
- ⏳ Full end-to-end completion

---

## ERRORS SOLVED (for reference)

| Error | Root Cause | Fix |
|---|---|---|
| `PRG_PAM_APP_020` Rest call to get prid failed | `kernel-pridgenerator-service` not running | Deploy pridgenerator container |
| `PRG_PAM_APP_020` Id schema fetch failed | Service calling syncdata (not running) | Override URL to masterdata |
| `KER-IOV-002` URI not absolute | `"id"` fields in schema properties conflict with `$ref` | Remove all `"id"` fields from schema properties |
| `KER-IOV-002` NullPointerException | Reference validator NPE on masterdata call | Disable: `mosip.kernel.idobjectvalidator.referenceValidator=` |
| `KER-KMS-002` ApplicationId not found | Key policy missing | Insert from official MOSIP CSV |
| `KER-KMS-012` Key generation not complete | Master keys not generated | Call `generateMasterKey/certificate` API |
| `KER-ATH-401` Auth failed on keymanager | Using Bearer token instead of Cookie | Use `Cookie: Authorization=<token>` |
| `mkdir: cannot create directory 'hsm-client': File exists` | configure_start.sh doesn't clean up on restart | Patch script: replace `mkdir` with `rm -rf && mkdir` |
| `CKR_FUNCTION_NOT_SUPPORTED` | libpkcs11-proxy can't init via SunPKCS11 | Use softhsm2 directly in container instead |
| `sudo: a terminal is required` | configure_start.sh uses sudo | Patch: replace `sudo ./install.sh` with `./install.sh` |
| `Realm does not exist` | Pre-reg token issuer mismatch | Use mosip realm credentials in pre-registration config |
| Gender/location dropdowns empty | Data not in DB, wrong format | Insert dynamic_field with single JSON object per row |
