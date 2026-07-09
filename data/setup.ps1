# Configurazione per mostrare correttamente i testi in italiano
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

Write-Host "=== VERIFICA PREREQUISITI DI SISTEMA ===" -ForegroundColor Cyan

# ----------------------------------------------------
# 1. CONTROLLO E INSTALLAZIONE PYTHON
# ----------------------------------------------------
$pythonInstalled = $false
$localPythonPath = "$env:USERPROFILE\AppData\Local\Programs\Python\Python312\python.exe"

if (Get-Command python -ErrorAction SilentlyContinue) {
        $pythonInstalled = $true
        $pythonCmd = "python"
} elseif (Test-Path $localPythonPath) {
        $pythonInstalled = $true
        $pythonCmd = $localPythonPath
}

if (-not $pythonInstalled) {
        Write-Host "-> Python NON trovato. Download dell'installatore ufficiale..." -ForegroundColor Yellow
        $urlPython = "https://www.python.org/ftp/python/3.12.3/python-3.12.3-amd64.exe"
        $installerPython = "$env:TEMP\python_installer.exe"

        Invoke-WebRequest -Uri $urlPython -OutFile $installerPython

        Write-Host "-> Installazione silenziosa di Python in corso (Directory Utente)..." -ForegroundColor Yellow
        Start-Process -FilePath $installerPython -ArgumentList "/quiet InstallAllUsers=0 PrependPath=1" -Wait

        Remove-Item $installerPython
        $pythonCmd = $localPythonPath
        Write-Host "[OK] Python installato con successo!" -ForegroundColor Green
} else {
        Write-Host "[OK] Python e' gia' presente sul PC." -ForegroundColor Green
}

# ----------------------------------------------------
# 2. CONTROLLO E INSTALLAZIONE OLLAMA
# ----------------------------------------------------
$ollamaInstalled = $false
if (Get-Command ollama -ErrorAction SilentlyContinue) {
        $ollamaInstalled = $true
}

if (-not $ollamaInstalled) {
        Write-Host "-> Ollama NON trovato. Download in corso..." -ForegroundColor Yellow
        $urlOllama = "https://ollama.com/download/OllamaSetup.exe"
        $installerOllama = "$env:TEMP\OllamaSetup.exe"

        Invoke-WebRequest -Uri $urlOllama -OutFile $installerOllama

        Write-Host "-> Installazione silenziosa di Ollama in corso (Senza cliccare nulla)..." -ForegroundColor Yellow
        # I parametri /SP- /VERYSILENT /NORESTART installano Ollama senza chiedere conferme visive e sbloccano il terminale
        Start-Process -FilePath $installerOllama -ArgumentList "/SP- /VERYSILENT /NORESTART" -Wait

        # Aspettiamo 5 secondi che Windows registri l'installazione
        Start-Sleep -Seconds 5
        Remove-Item $installerOllama
        Write-Host "[OK] Ollama installato in background!" -ForegroundColor Green
} else {
        Write-Host "[OK] Ollama e' gia' presente sul PC." -ForegroundColor Green
}

# ----------------------------------------------------
# 3. CREAZIONE AMBIENTE VIRTUALE E LIBRERIE (.venv)
# ----------------------------------------------------
if (-not (Test-Path "$PSScriptRoot\.venv")) {
        Write-Host "-> Creazione dell'ambiente isolato (.venv) nella cartella data..." -ForegroundColor Yellow
        Start-Process -FilePath $pythonCmd -ArgumentList "-m venv $PSScriptRoot\.venv" -Wait

        Write-Host "-> Installazione delle librerie necessarie nella cartella locale..." -ForegroundColor Yellow
        Start-Process -FilePath "$PSScriptRoot\.venv\Scripts\pip.exe" -ArgumentList "install feedparser ollama requests" -Wait -NoNewWindow
        Write-Host "[OK] Ambiente locale configurato e pronto!" -ForegroundColor Green
} else {
        Write-Host "[OK] Ambiente locale (.venv) gia' configurato." -ForegroundColor Green
}