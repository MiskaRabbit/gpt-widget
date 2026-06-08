$ErrorActionPreference = "Stop"

function Invoke-Step {
    param(
        [Parameter(Mandatory=$true)]
        [string] $Label,
        [Parameter(Mandatory=$true)]
        [scriptblock] $Command
    )

    Write-Host $Label
    & $Command
    if ($LASTEXITCODE -ne 0) {
        throw "$Label failed with exit code $LASTEXITCODE"
    }
}

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

# Avoid mixing stdlib files from another Python installation.
Remove-Item Env:PYTHONHOME -ErrorAction SilentlyContinue
Remove-Item Env:PYTHONPATH -ErrorAction SilentlyContinue

$Candidates = @(
    "$env:LOCALAPPDATA\Programs\Python\Python39\python.exe",
    "$env:LOCALAPPDATA\Programs\Python\Python314\python.exe"
)

$Python = $Candidates | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $Python) {
    throw "Python not found. Expected one of: $($Candidates -join ', ')"
}

$Version = & $Python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
Write-Host "Using Python $Version at $Python"

if ($Version -eq "3.14") {
    Write-Warning "Python 3.14 alpha may not have compatible PyQt6 wheels. Install Python 3.11 or use Python 3.9 if dependency installation fails."
}

$VenvDir = if ($Version -eq "3.9") { ".venv-py39" } else { ".venv-py$($Version.Replace('.', ''))" }
$VenvPython = Join-Path $Root "$VenvDir\Scripts\python.exe"

if (-not (Test-Path $VenvPython)) {
    Write-Host "Creating virtual environment: $VenvDir"
    & $Python -m venv $VenvDir
    if ($LASTEXITCODE -ne 0) {
        throw "Virtual environment creation failed with exit code $LASTEXITCODE"
    }
}

Invoke-Step "Upgrading pip..." {
    & $VenvPython -m pip install --upgrade pip
}

Invoke-Step "Installing dependencies..." {
    & $VenvPython -m pip install -r requirements.txt
}

Invoke-Step "Verifying PyQt6..." {
    & $VenvPython -c "import PyQt6; print('PyQt6 OK')"
}

Write-Host "Starting GPT Usage Widget..."
& $VenvPython main.py
