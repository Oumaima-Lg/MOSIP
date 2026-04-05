# MOSIP Device Certificate Signing Script
# This script creates a proper certificate chain: Root CA -> Intermediate CA -> Device Certs

$keytoolPath = "C:\Users\olaghjibi\MOSIP\reg-client\jre\bin\keytool.exe"
$basePath = "C:\Users\olaghjibi\MOSIP\mock-mds\collab-mock-mds-reg\target\Biometric Devices"
$tmpDir = "$basePath\tmp"

# Create temp directory
if (-Not (Test-Path $tmpDir)) {
    New-Item -ItemType Directory -Path $tmpDir -Force | Out-Null
}

Write-Host "========================================" -ForegroundColor Green
Write-Host "MOSIP Certificate Chain Setup" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green

# Step 1: Generate Intermediate CA
Write-Host "`n[Step 1] Generating Intermediate CA..." -ForegroundColor Cyan

& $keytoolPath -genkeypair `
  -alias mosipisca `
  -keyalg RSA -keysize 2048 `
  -validity 3650 `
  -keystore "$basePath\mosipisca.p12" `
  -storetype PKCS12 `
  -storepass mosipftm `
  -keypass mosipftm `
  -ext "BasicConstraints:critical=ca:true" `
  -dname "CN=MOSIP Intermediate CA, OU=mosip, O=mosip, L=Bangalore, ST=Karnataka, C=IN"

Write-Host "OK Intermediate CA keystore created" -ForegroundColor Green

# Step 2: Create CSR for Intermediate CA
Write-Host "`n[Step 2] Creating CSR for Intermediate CA..." -ForegroundColor Cyan

& $keytoolPath -certreq `
  -alias mosipisca `
  -keystore "$basePath\mosipisca.p12" `
  -storetype PKCS12 `
  -storepass mosipftm `
  -file "$tmpDir\mosipisca.csr"

Write-Host "OK CSR created" -ForegroundColor Green

# Step 3: Sign Intermediate CA with Root CA
Write-Host "`n[Step 3] Signing Intermediate CA with Root CA..." -ForegroundColor Cyan

& $keytoolPath -gencert `
  -alias mosipftm `
  -keystore "$basePath\mosiprootcaftm.p12" `
  -storetype PKCS12 `
  -storepass mosipftm `
  -infile "$tmpDir\mosipisca.csr" `
  -outfile "$tmpDir\mosipisca_signed.cer" `
  -validity 3650 `
  -ext "BasicConstraints:critical=ca:true" `
  -rfc

Write-Host "OK Intermediate CA signed" -ForegroundColor Green

# Step 4: Import Root CA into Intermediate keystore (for chain)
Write-Host "`n[Step 4] Importing Root CA into Intermediate keystore..." -ForegroundColor Cyan

& $keytoolPath -import `
  -alias mosipftm `
  -keystore "$basePath\mosipisca.p12" `
  -storetype PKCS12 `
  -storepass mosipftm `
  -file "$basePath\rootcaftm.cer" `
  -noprompt

Write-Host "OK Root CA imported" -ForegroundColor Green

# Step 5: Import signed Intermediate cert
Write-Host "`n[Step 5] Importing signed Intermediate certificate..." -ForegroundColor Cyan

& $keytoolPath -import `
  -alias mosipisca `
  -keystore "$basePath\mosipisca.p12" `
  -storetype PKCS12 `
  -storepass mosipftm `
  -file "$tmpDir\mosipisca_signed.cer" `
  -noprompt

Write-Host "OK Intermediate certificate imported" -ForegroundColor Green

# Export Intermediate CA certificate
Write-Host "`n[Step 6] Exporting Intermediate CA certificate..." -ForegroundColor Cyan

& $keytoolPath -export `
  -alias mosipisca `
  -keystore "$basePath\mosipisca.p12" `
  -storetype PKCS12 `
  -storepass mosipftm `
  -file "$basePath\mosipisca.cer" `
  -rfc

Write-Host "OK Intermediate CA certificate exported" -ForegroundColor Green

# Array of device types
$devices = @(
    @{ name = "Iris Double"; path = "Iris\Double"; modality = "IRIS_DOUBLE" },
    @{ name = "Iris Single"; path = "Iris\Single"; modality = "IRIS_SINGLE" },
    @{ name = "Finger Slap"; path = "Finger\Slap"; modality = "FINGER_SLAP" },
    @{ name = "Finger Single"; path = "Finger\Single"; modality = "FINGER_SINGLE" },
    @{ name = "Face"; path = "Face"; modality = "FACE" }
)

# Step 7: Sign each device certificate
Write-Host "`n[Step 7] Signing Device Certificates..." -ForegroundColor Cyan

foreach ($device in $devices) {
    $devicePath = "$basePath\$($device.path)\Keys"
    $deviceName = $device.name
    
    Write-Host "`n  Processing: $deviceName" -ForegroundColor Yellow
    
    # Create CSR
    & $keytoolPath -certreq `
      -alias Device `
      -keystore "$devicePath\Device.p12" `
      -storetype PKCS12 `
      -storepass mosipface `
      -file "$tmpDir\Device_$($device.modality).csr"
    
    Write-Host "    OK CSR created" -ForegroundColor Green
    
    # Sign with Intermediate CA
    & $keytoolPath -gencert `
      -alias mosipisca `
      -keystore "$basePath\mosipisca.p12" `
      -storetype PKCS12 `
      -storepass mosipftm `
      -infile "$tmpDir\Device_$($device.modality).csr" `
      -outfile "$tmpDir\Device_$($device.modality)_signed.cer" `
      -validity 3650 `
      -rfc
    
    Write-Host "    OK Certificate signed" -ForegroundColor Green
    
    # Import Root CA into device keystore
    & $keytoolPath -import `
      -alias mosipftm `
      -keystore "$devicePath\Device.p12" `
      -storetype PKCS12 `
      -storepass mosipface `
      -file "$basePath\rootcaftm.cer" `
      -noprompt
    
    # Import Intermediate CA
    & $keytoolPath -import `
      -alias mosipisca `
      -keystore "$devicePath\Device.p12" `
      -storetype PKCS12 `
      -storepass mosipface `
      -file "$basePath\mosipisca.cer" `
      -noprompt
    
    Write-Host "    OK CA chain imported" -ForegroundColor Green
    
    # Import signed device cert
    & $keytoolPath -import `
      -alias Device `
      -keystore "$devicePath\Device.p12" `
      -storetype PKCS12 `
      -storepass mosipface `
      -file "$tmpDir\Device_$($device.modality)_signed.cer" `
      -noprompt
    
    Write-Host "    OK Device certificate imported" -ForegroundColor Green
}

# Verify all certificates
Write-Host "`n[Step 8] Verifying Certificate Chains..." -ForegroundColor Cyan

foreach ($device in $devices) {
    $devicePath = "$basePath\$($device.path)\Keys"
    $deviceName = $device.name
    
    Write-Host "`n  Verifying: $deviceName" -ForegroundColor Yellow
    
    & $keytoolPath -list `
      -keystore "$devicePath\Device.p12" `
      -storetype PKCS12 `
      -storepass mosipface
}

# Cleanup temp files
Write-Host "`n[Step 9] Cleaning up temporary files..." -ForegroundColor Cyan
Remove-Item -Path $tmpDir -Recurse -Force -ErrorAction SilentlyContinue
Write-Host "OK Cleanup complete" -ForegroundColor Green

Write-Host "`n========================================" -ForegroundColor Green
Write-Host "Certificate chain setup COMPLETE!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green