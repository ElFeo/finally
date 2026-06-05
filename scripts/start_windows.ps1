param([switch]$Build)

$ContainerName = "finally"
$ImageName = "finally"
$Port = 8000
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir

if ($Build -or -not (docker image inspect $ImageName 2>$null)) {
    Write-Host "Building FinAlly Docker image..."
    docker build -t $ImageName $ProjectRoot
}

$running = docker ps -q --filter "name=$ContainerName"
if ($running) {
    Write-Host "Stopping existing container..."
    docker stop $ContainerName | Out-Null
    docker rm $ContainerName | Out-Null
}

Write-Host "Starting FinAlly..."
docker run -d `
    --name $ContainerName `
    -p "${Port}:8000" `
    -v "finally-data:/app/db" `
    --env-file "$ProjectRoot\.env" `
    $ImageName

Write-Host ""
Write-Host "FinAlly is running at http://localhost:$Port"
Write-Host "  Stop with: .\scripts\stop_windows.ps1"

Start-Sleep 2
Start-Process "http://localhost:$Port"
