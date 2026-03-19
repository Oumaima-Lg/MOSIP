# MOSIP Pre-Registration Docker Setup - Full Context for Next Conversation

## HOW TO USE THIS DOCUMENT
Paste this entire document at the start of the next conversation with Claude, followed by your new question/issue.

---

## PROJECT OVERVIEW
Setting up MOSIP Pre-Registration stack on Docker Desktop (Windows, MINGW64 Git Bash + PowerShell).
**STATUS: Full end-to-end pre-registration flow is WORKING.**

**IMPORTANT WINDOWS NOTES:**
- Use `py` instead of `python3` in Windows commands
- Use `sh -c "..."` with docker exec to avoid Git Bash path mangling
- Commands with `!` must be run in PowerShell not Git Bash
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

### MinIO
- Image: `minio/minio`
- Ports: 9000 (API), 9001 (console)
- Credentials: minioadmin / minioadmin123
- Bucket: `prereg`
- Run command:
```bash
docker run -d --name minio --network mosip-network \
  -p 9000:9000 -p 9001:9001 \
  -e MINIO_ROOT_USER=minioadmin \
  -e MINIO_ROOT_PASSWORD=minioadmin123 \
  -v minio-data:/data \
  minio/minio server /data --console-address ":9001"
```

---

## RUNNING CONTAINERS & PORTS

| Container | Image/JAR | Port | Status |
|---|---|---|---|
| postgres | postgres:10 | 5432 | ✅ |
| keycloak | mosipid/mosip-keycloak:1.2.0 | 8080 | ✅ |
| softhsm | mosipid/softhsm:v2 | 5666 | ✅ |
| minio | minio/minio | 9000,9001 | ✅ |
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

## KEY CONFIGURATION FILES

### application-default.properties (key overrides)
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
# MinIO object store
mosip.kernel.objectstore.account-name=prereg
object.store.s3.url=http://minio:9000
object.store.s3.accesskey=minioadmin
object.store.s3.secretkey=minioadmin123
object.store.s3.region=us-east-1
object.store.s3.readlimit=10000000
# Notification
mosip.notificationtype=EMAIL
preregistration.contact.email=contact@dev.mosip.net
preregistration.contact.phone=+212600000000
```

---

## MASTER DATA - FULLY POPULATED

All master data has been inserted using official MOSIP release-1.2.0 xlsx files from:
`https://github.com/mosip/mosip-data/tree/release-1.2.0/mosip_master`

### Import Scripts Location
All scripts at `C:\Users\olaghjibi\MOSIP\`:
- `import_01_documents.py` — doc_category, doc_type, valid_document, applicant_valid_document
- `import_02_location.py` — loc_hierarchy_list, location, loc_holiday
- `import_03_id_schema.py` — identity_schema, dynamic_field, id_type, ui_spec
- `import_04_registration_center.py` — zone, reg_center_type, registration_center, registration_center_h, reg_exceptional_holiday, reg_working_nonworking
- `import_05_others.py` — status_type, status_list, daysofweek_list, module_detail, process_list, blocklisted_words, title, zone, zone_user, zone_user_h
- `import_06_templates.py` — template_file_format, template_type, template

### xlsx files location
`C:\Users\olaghjibi\MOSIP\mosip-data-release-1.2.0\mosip_master\xlsx\`

### Key master data values
- **Country code**: MOR
- **Location hierarchy**: MOR → RSK (Rabat Sale Kenitra) → RBT/KTA → RAB/KNT → HARD/ASSM/... → 10104/14000/...
- **Registration center used for testing**: 10013 (Center Hay Riad, location_code=10104)
- **Applicant type for adult foreigner**: 002
- **Document categories**: POI (Identity), POA (Address), POR (Relationship), POB (Birth), POE (Exception)
- **Document types used**: CIN (POI), RNC (POA)

---

## UI SPEC
The official pre-registration ui_spec (id=619e3392...) is loaded with:
- All identity fields: fullName, dateOfBirth, gender, residenceStatus, addressLine1, region, province, city, zone, postalCode, phone, email, referenceIdentityNumber
- Document fields: proofOfIdentity (POI, required), proofOfAddress (POA), proofOfRelationship (POR), proofOfDateOfBirth (POB), proofOfException (POE)
- Location hierarchy: region → province → city → zone → postalCode

**IMPORTANT**: The ui_spec in DB must be the official one (from ui_spec.xlsx), NOT the manually created one.
The manually created one was missing fileupload fields — it was replaced by import_03_id_schema.py.

---

## SLOT GENERATION
Slots are generated by pre-registration-batchjob. To force regeneration:
```bash
docker restart pre-registration-batchjob
```
Verify slots exist:
```bash
docker exec -i postgres psql -U prereguser -d mosip_prereg -c "
SELECT regcntr_id, availability_date, COUNT(*) 
FROM prereg.reg_available_slot 
GROUP BY regcntr_id, availability_date 
ORDER BY availability_date LIMIT 10;"
```
If no slots for upcoming dates, insert manually:
```bash
docker exec -i postgres psql -U prereguser -d mosip_prereg << 'PSQL'
INSERT INTO prereg.reg_available_slot 
  (regcntr_id, availability_date, slot_from_time, slot_to_time, available_kiosks, cr_by, cr_dtimes)
SELECT '10013', CURRENT_DATE + s.day,
  (TIME '09:00:00' + (slot.num * INTERVAL '15 minutes')),
  (TIME '09:15:00' + (slot.num * INTERVAL '15 minutes')),
  3, 'superadmin', NOW()
FROM generate_series(0, 6) AS s(day)
CROSS JOIN generate_series(0, 23) AS slot(num)
ON CONFLICT DO NOTHING;
PSQL
```

---

## COMPLETED PRE-REGISTRATION (TEST)
- **Application ID**: 73429783021879
- **Status**: Booked / SUBMITTED
- **Center**: 10013 (Center Hay Riad)
- **Appointment**: 2026-03-23 at 09:30
- **Location used**: RSK → RBT → RAB → HARD → 10104

---

## DEMOGRAPHIC FORM - WORKING VALUES
Use these values to fill the demographic form successfully:
- **Region**: Rabat Sale Kenitra (RSK)
- **Province**: Rabat (RBT)
- **City**: Rabat (RAB)
- **Zone**: Hay Riad (HARD)
- **Postal Code**: 10104
- **Phone**: must start with 6-9, e.g. `6629733212` (regex: `^([6-9]{1})([0-9]{9})$`)

---

## AUTHENTICATION PATTERN
- Services use `Cookie: Authorization=<token>` NOT `Authorization: Bearer <token>`
- Token from:
```bash
TOKEN=$(docker exec kernel-auth-service curl -s -X POST \
  "http://keycloak:8080/auth/realms/mosip/protocol/openid-connect/token" \
  -d "client_id=mosip-admin-client&client_secret=mosip123&grant_type=client_credentials" \
  | py -c "import sys,json; print(json.load(sys.stdin)['access_token'])")
```

---

## KNOWN ISSUES / WORKAROUNDS

| Issue | Status | Fix |
|---|---|---|
| `email id:undefined` in error messages | ✅ Fixed | Added `preregistration.contact.email` and `preregistration.contact.phone` to config |
| Postal code spinner never loads | ✅ Fixed | Restart kernel-masterdata-service after location data changes |
| Phone validation fails with `06...` | ✅ Known | Use `6629733212` format (no leading 0) |

---

## ERRORS SOLVED (full history)

| Error | Root Cause | Fix |
|---|---|---|
| `PRG_PAM_APP_020` prid failed | kernel-pridgenerator not running | Deploy pridgenerator container |
| `KER-IOV-002` URI not absolute | `"id"` fields in schema properties | Remove all `"id"` from schema properties |
| `KER-IOV-002` NullPointerException | Reference validator NPE | Disable: `mosip.kernel.idobjectvalidator.referenceValidator=` |
| `KER-KMS-002` ApplicationId not found | Key policy missing | Insert from official MOSIP CSV |
| `KER-KMS-012` Key generation not complete | Master keys not generated | Call `generateMasterKey/certificate` API |
| `KER-ATH-401` Auth failed | Using Bearer instead of Cookie | Use `Cookie: Authorization=<token>` |
| `KER-MSD-150` Document Category-Type not found | Empty doc tables | Run import_01_documents.py |
| `KER-MSD-016` Valid document not found | Wrong column order in insert | Fixed in import_01_documents.py |
| `KER-MSD-215` Registration Center not found | Empty registration_center table | Run import_04_registration_center.py |
| `KER-MSD-046` Template not found | Empty template tables | Run import_06_templates.py |
| Document upload page empty (no dropdowns) | ui_spec missing fileupload fields | Replace with official ui_spec via import_03_id_schema.py |
| No slots available | batchjob ran before centers existed | Restart batchjob or insert slots manually |
| File upload fails (minio.default) | MinIO not running / wrong hostname | Deploy MinIO container, add S3 config to pre-reg properties |

---

## CURRENT FLOW STATUS
- ✅ OTP Login
- ✅ Demographic form renders with all fields
- ✅ Gender/ResidenceStatus dropdowns work
- ✅ Location dropdowns work (Region/Province/City/Zone/PostalCode)
- ✅ Demographic form save (Continue button)
- ✅ Document Upload (POI + POA)
- ✅ Book Appointment (Center Hay Riad, slot confirmed)
- ✅ Confirmation notification (UI payload bug — non-blocking, booking is saved)

