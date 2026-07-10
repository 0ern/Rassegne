# Configurazione per mostrare correttamente i testi in italiano
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

# ----------------------------------------------------
# 1. CONTROLLO E INSTALLAZIONE PYTHON
# ----------------------------------------------------
$pythonInstalled = $false
$localPythonPath = "$env:USERPROFILE\AppData\Local\Programs\Python\Python314\python.exe"

if (Get-Command python -ErrorAction SilentlyContinue) {
        $pythonInstalled = $true
        $pythonCmd = "python"
} elseif (Test-Path $localPythonPath) {
        $pythonInstalled = $true
        $pythonCmd = $localPythonPath
}

if (-not $pythonInstalled) {
        Write-Host "Python NON trovato. Download..."
        $urlPython = "https://www.python.org/ftp/python/3.14.6/python-3.14.6-amd64.exe"
        $installerPython = "$env:TEMP\python_installer.exe"

        Invoke-WebRequest -Uri $urlPython -OutFile $installerPython

        Write-Host "Installazione di Python in corso (Directory Utente)..."
        Start-Process -FilePath $installerPython -ArgumentList "/quiet InstallAllUsers=0 PrependPath=1" -Wait

        Remove-Item $installerPython
        $pythonCmd = $localPythonPath
        Write-Host "Python installato con successo." -ForegroundColor Green
} else {
        Write-Host "Python presente sul PC." -ForegroundColor Green
}

# ----------------------------------------------------
# 2. CONTROLLO E INSTALLAZIONE OLLAMA
# ----------------------------------------------------
$ollamaInstalled = $false
if (Get-Command ollama -ErrorAction SilentlyContinue) {
        $ollamaInstalled = $true
}

if (-not $ollamaInstalled) {
        Write-Host "Ollama NON trovato. Download in corso..."
        $urlOllama = "https://ollama.com/download/OllamaSetup.exe"
        $installerOllama = "$env:TEMP\OllamaSetup.exe"

        Invoke-WebRequest -Uri $urlOllama -OutFile $installerOllama

        Write-Host "Installazione di Ollama in corso..."
        # I parametri /SP- /VERYSILENT /NORESTART installano Ollama senza chiedere conferme visive e sbloccano il terminale
        Start-Process -FilePath $installerOllama -ArgumentList "/SP- /VERYSILENT /NORESTART" -Wait

        # Aspettiamo 5 secondi che Windows registri l'installazione
        Start-Sleep -Seconds 5
        Remove-Item $installerOllama
        Write-Host "Ollama installato in background." -ForegroundColor Green
} else {
        Write-Host "Ollama presente sul PC." -ForegroundColor Green
}

# ----------------------------------------------------
# 3. CREAZIONE AMBIENTE VIRTUALE E LIBRERIE (.venv)
# ----------------------------------------------------
if (-not (Test-Path "$PSScriptRoot\.venv")) {
        Write-Host "Creazione dell'ambiente isolato (.venv) nella cartella \data..."
        Start-Process -FilePath $pythonCmd -ArgumentList "-m venv $PSScriptRoot\.venv" -Wait

        Write-Host "Installazione delle librerie necessarie nella cartella locale..."
        Start-Process -FilePath "$PSScriptRoot\.venv\Scripts\pip.exe" -ArgumentList "install feedparser ollama requests" -Wait -NoNewWindow -RedirectStandardOutput "$env:TEMP\nul"
        Write-Host "Ambiente locale configurato." -ForegroundColor Green
} else {
        Write-Host "Ambiente locale (.venv) configurato." -ForegroundColor Green
}

# --- AUTOMAZIONE DOWNLOAD MODELLO IA ---
# Avvia il download mostrando la barra di avanzamento in una finestra dedicata
Start-Process -FilePath "ollama" -ArgumentList "pull llama3.1:8b" -Wait

Write-Host "Modello llama3.1:8b pronto." -ForegroundColor Green