# ============================================================
# THRIVE-Belize Deck Builder v2
# Extracts audio, transcribes, summarizes, and updates deck
# ============================================================
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$scriptDir   = Split-Path -Parent $MyInvocation.MyCommand.Path
$parentDir   = Split-Path -Parent $scriptDir
$genDir      = Join-Path $scriptDir "assets\generated"
$audioDir    = Join-Path $genDir "audio"
$transcriptDir = Join-Path $genDir "transcripts"
$summaryDir  = Join-Path $genDir "summaries"

# Create directories
foreach ($d in @($genDir, $audioDir, $transcriptDir, $summaryDir)) {
    New-Item -ItemType Directory -Force -Path $d | Out-Null
}

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  THRIVE-Belize Deck Builder v2" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Project:    $scriptDir"
Write-Host "Videos in:  $parentDir"
Write-Host "Output:     $genDir"
Write-Host ""

# --- Verify video files ---
$videos = @{
    v1 = @{ pattern = "Jewkes2021ElemOf_Video"; ext = ".mp4" }
    v2 = @{ pattern = "Morales2026THRIVE-Belize"; ext = ".mp4" }
    v3 = @{ pattern = "Morales2026TheManBox"; ext = ".mp4" }
}

$videoPaths = @{}
foreach ($key in $videos.Keys) {
    $pat = $videos[$key].pattern
    $found = Get-ChildItem -Path $parentDir -Filter "*$pat*" -File -ErrorAction SilentlyContinue |
             Select-Object -First 1
    if ($found) {
        $videoPaths[$key] = $found.FullName
        Write-Host "[OK] $key -> $($found.Name)" -ForegroundColor Green
    } else {
        Write-Warning "$key video not found (pattern: *$pat*)"
        $videoPaths[$key] = $null
    }
}
Write-Host ""

# --- Check tools ---
$hasFfmpeg  = [bool](Get-Command ffmpeg -ErrorAction SilentlyContinue)
$hasPython  = [bool](Get-Command python -ErrorAction SilentlyContinue)

if (-not $hasFfmpeg) {
    Write-Warning "ffmpeg not found. Audio extraction will be skipped."
    Write-Warning "Install: winget install Gyan.FFmpeg"
}
if (-not $hasPython) {
    Write-Warning "Python not found. Transcription pipeline requires Python."
    Write-Warning "The deck will still work with fallback summaries."
}

# --- Step 1: Extract audio ---
Write-Host "--- Step 1: Audio extraction ---" -ForegroundColor Yellow
foreach ($key in $videoPaths.Keys) {
    $vp = $videoPaths[$key]
    if (-not $vp) { continue }
    $audioOut = Join-Path $audioDir "$key.wav"
    if (Test-Path $audioOut) {
        Write-Host "  $key audio already exists, skipping."
        continue
    }
    if (-not $hasFfmpeg) {
        Write-Host "  Skipping $key (no ffmpeg)."
        continue
    }
    Write-Host "  Extracting audio for $key..."
    & ffmpeg -y -i $vp -ar 16000 -ac 1 -c:a pcm_s16le $audioOut 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  [OK] $audioOut" -ForegroundColor Green
    } else {
        Write-Warning "  ffmpeg failed for $key."
    }
}
Write-Host ""

# --- Step 2: Transcribe ---
Write-Host "--- Step 2: Transcription ---" -ForegroundColor Yellow
if ($hasPython) {
    $builder = Join-Path $scriptDir "scripts\build_deck.py"
    if (Test-Path $builder) {
        Write-Host "  Running Python build script..."
        python $builder --project-root $scriptDir --parent-dir $parentDir
        if ($LASTEXITCODE -ne 0) {
            Write-Warning "  Python script returned non-zero. Check output above."
        }
    } else {
        Write-Warning "  scripts\build_deck.py not found."
    }
} else {
    Write-Host "  Skipping (no Python). Fallback summaries will be used."
}
Write-Host ""

# --- Step 3: Detect video durations ---
Write-Host "--- Step 3: Detect durations ---" -ForegroundColor Yellow
$durations = @{}
if ($hasFfmpeg) {
    foreach ($key in $videoPaths.Keys) {
        $vp = $videoPaths[$key]
        if (-not $vp) { continue }
        try {
            $probe = & ffprobe -v quiet -show_entries format=duration -of csv="p=0" $vp 2>$null
            if ($probe) {
                $secs = [math]::Round([double]$probe)
                $mins = [math]::Floor($secs / 60)
                $rem  = $secs % 60
                $durations[$key] = "${mins}m ${rem}s"
                Write-Host "  $key duration: $($durations[$key])" -ForegroundColor Green
            }
        } catch {
            Write-Host "  Could not detect duration for $key."
        }
    }
}
Write-Host ""

# --- Step 4: Update deck_data.json ---
Write-Host "--- Step 4: Update deck data ---" -ForegroundColor Yellow
$deckData = @{
    videos = @{
        v1 = @{
            filename = "../Jewkes2021ElemOf_Video.mp4"
            duration = if ($durations.ContainsKey("v1")) { $durations["v1"] } else { "Unknown" }
        }
        v2 = @{
            filename = "../Morales2026THRIVE-Belize.mp4"
            duration = if ($durations.ContainsKey("v2")) { $durations["v2"] } else { "Unknown" }
        }
        v3 = @{
            filename = "../Morales2026TheManBox.mp4"
            duration = if ($durations.ContainsKey("v3")) { $durations["v3"] } else { "Unknown" }
        }
    }
}
$jsonOut = Join-Path $genDir "deck_data.json"
$deckData | ConvertTo-Json -Depth 5 | Set-Content -Path $jsonOut -Encoding UTF8
Write-Host "  [OK] $jsonOut" -ForegroundColor Green
Write-Host ""

# --- Done ---
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  Build complete." -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Open: $scriptDir\index.html"
Write-Host "Generated: $genDir"
Write-Host ""
