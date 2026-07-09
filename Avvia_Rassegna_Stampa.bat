@echo off
title Rassegna Stampa Mattutina
cls
echo ====================================================
echo                 RASSEGNA STAMPA
echo ====================================================
echo.
echo [1] CONTROLLO PROGRAMMI.

:: Controlla e crea le cartelle principali se mancano
if not exist "Rassegne" mkdir "Rassegne"
if not exist "data" mkdir "data"

:: Esegue lo script PowerShell bypassando le restrizioni di blocco di Windows
powershell -ExecutionPolicy Bypass -File data\setup.ps1

echo.
echo [2] ANALISI FEED RSS.
if exist data\.venv (
        data\.venv\Scripts\python data\app.py
) else (
        echo Errore critico: Impossibile trovare l'ambiente Python locale.
)

echo.
echo [3] RASSEGNA CREATA.
pause