$ErrorActionPreference = "Stop"

cd C:\Users\LENOVO\.openclaw-autoclaw\workspace\project-prometheus\web

Write-Host "Copying static assets..."
Copy-Item -Path .next\static -Destination .next\standalone\.next\static -Recurse -Force
if (Test-Path public) {
    Copy-Item -Path public -Destination .next\standalone\public -Recurse -Force
}

Write-Host "Creating run.sh..."
python -c "open('.next/standalone/run.sh', 'wb').write(b'#!/bin/bash\nexec node server.js\n')"

Write-Host "Zipping payload..."
python zip_it.py

Write-Host "Deploying to Lambda..."
aws lambda update-function-code --function-name prometheus-web --zip-file fileb://prometheus-web.zip --profile prometheus --region ap-south-1 | Out-Null

Write-Host "Deployment complete."
