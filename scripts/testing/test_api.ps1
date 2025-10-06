$body = @{
    text = "Le soleil est jaune car sa température de surface est d'environ 5 500 degrés Celsius, ce qui le fait apparaître principalement blanc, mais l'atmosphère terrestre diffuse la lumière bleue et violette, laissant les longueurs d'onde plus jaunes et rouges atteindre nos yeux."
} | ConvertTo-Json -Compress

try {
    $response = Invoke-RestMethod -Uri http://localhost:8095/api/analyze -Method Post -ContentType 'application/json' -Body $body
    $response | ConvertTo-Json
} catch {
    Write-Error "API call failed: $_"
    exit 1
}