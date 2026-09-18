$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Push-Location $root
try {
    New-Item -ItemType Directory -Path verify_tmp -Force | Out-Null
    python -m pytest -q tests/backend --basetemp verify_tmp/pytest
    if ($LASTEXITCODE -ne 0) { throw "Backend tests failed" }

    Push-Location frontend
    try {
        npm.cmd run typecheck
        if ($LASTEXITCODE -ne 0) { throw "Frontend typecheck failed" }
        npm.cmd run build
        if ($LASTEXITCODE -ne 0) { throw "Frontend build failed" }
    }
    finally {
        Pop-Location
    }

    python scripts/generate_demo_evidence.py
    if ($LASTEXITCODE -ne 0) { throw "Demo evidence generation failed" }
}
finally {
    Pop-Location
}
