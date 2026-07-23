$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)

function Write-HookResult {
    param(
        [Parameter(Mandatory)]
        [bool]$DriftDetected,

        [Parameter(Mandatory)]
        [AllowEmptyCollection()]
        [string[]]$ChangedPaths,

        [Parameter(Mandatory)]
        [string]$Message,

        [bool]$Warn = $false
    )

    $result = [ordered]@{
        continue      = $true
        driftDetected = $DriftDetected
        changedPaths  = @($ChangedPaths)
        message       = $Message
    }

    if ($Warn) {
        $result.systemMessage = if ($ChangedPaths.Count -gt 0) {
            "$Message`n- " + ($ChangedPaths -join "`n- ")
        } else {
            $Message
        }
    }

    $result | ConvertTo-Json -Depth 4 -Compress
}

function Find-ProjectRoot {
    $current = (Get-Item -LiteralPath (Get-Location).Path).FullName

    while ($true) {
        $agentsPath = Join-Path $current 'AGENTS.md'
        $sotPath = Join-Path $current 'SOT/SourceOfTruth.md'

        if (
            (Test-Path -LiteralPath $agentsPath -PathType Leaf) -and
            (Test-Path -LiteralPath $sotPath -PathType Leaf)
        ) {
            return $current
        }

        $parent = Split-Path -Parent $current
        if ([string]::IsNullOrEmpty($parent) -or $parent -eq $current) {
            return $null
        }

        $current = $parent
    }
}

function Test-CandidateChangedAfter {
    param(
        [Parameter(Mandatory)]
        [System.IO.DirectoryInfo]$Candidate,

        [Parameter(Mandatory)]
        [datetime]$BaselineUtc
    )

    if ($Candidate.LastWriteTimeUtc -gt $BaselineUtc) {
        return $true
    }

    $changedItem = Get-ChildItem -LiteralPath $Candidate.FullName -Force -Recurse -ErrorAction SilentlyContinue |
        Where-Object { $_.LastWriteTimeUtc -gt $BaselineUtc } |
        Select-Object -First 1

    return $null -ne $changedItem
}

$projectRoot = Find-ProjectRoot

if ($null -eq $projectRoot) {
    Write-HookResult `
        -DriftDetected $false `
        -ChangedPaths @() `
        -Message 'SOT와 AGENTS.md가 함께 있는 프로젝트 루트를 찾지 못했습니다.' `
        -Warn $true
    exit 0
}

$sotPath = Join-Path $projectRoot 'SOT/SourceOfTruth.md'
$sotLastWriteUtc = (Get-Item -LiteralPath $sotPath).LastWriteTimeUtc
$changedPaths = [System.Collections.Generic.List[string]]::new()

$candidateSpecs = @(
    @{ Root = '03_WORK'; Pattern = '^W[0-9]{2}_[0-9]{4}-[0-9]{2}-[0-9]{2}_.+$' },
    @{ Root = '03_WORKS'; Pattern = '^W[0-9]{2}_[0-9]{4}-[0-9]{2}-[0-9]{2}_.+$' },
    @{ Root = '04_OUTPUT'; Pattern = '^OUT[0-9]{2}_[0-9]{4}-[0-9]{2}-[0-9]{2}_.+$' }
)

foreach ($spec in $candidateSpecs) {
    $candidateRoot = Join-Path $projectRoot $spec.Root
    if (-not (Test-Path -LiteralPath $candidateRoot -PathType Container)) {
        continue
    }

    foreach ($candidate in Get-ChildItem -LiteralPath $candidateRoot -Directory -Force -ErrorAction SilentlyContinue) {
        if ($candidate.Name -notmatch $spec.Pattern) {
            continue
        }

        if (Test-CandidateChangedAfter -Candidate $candidate -BaselineUtc $sotLastWriteUtc) {
            $relativePath = [System.IO.Path]::GetRelativePath($projectRoot, $candidate.FullName).Replace('\', '/')
            $changedPaths.Add($relativePath)
        }
    }
}

$fileCandidateSpecs = @(
    @{ Root = '02_SOURCE/COMMUNICATION_LOG'; Filter = '*_summary.md' },
    @{ Root = '05_MEETING'; Filter = '*.md' }
)

foreach ($spec in $fileCandidateSpecs) {
    $candidateRoot = Join-Path $projectRoot $spec.Root
    if (-not (Test-Path -LiteralPath $candidateRoot -PathType Container)) {
        continue
    }

    foreach ($candidate in Get-ChildItem -LiteralPath $candidateRoot -File -Force -Recurse -Filter $spec.Filter -ErrorAction SilentlyContinue) {
        if ($candidate.LastWriteTimeUtc -gt $sotLastWriteUtc) {
            $relativePath = [System.IO.Path]::GetRelativePath($projectRoot, $candidate.FullName).Replace('\', '/')
            $changedPaths.Add($relativePath)
        }
    }
}

$sortedPaths = @($changedPaths | Sort-Object -Unique)
$driftDetected = $sortedPaths.Count -gt 0
$message = if ($driftDetected) {
    'SOT 이후 변경된 작업·발행·소통 요약·회의 기록 후보가 있습니다.'
} else {
    'SOT 이후 변경된 WNN·OUTNN·소통 요약·회의 기록 후보가 없습니다.'
}

Write-HookResult `
    -DriftDetected $driftDetected `
    -ChangedPaths $sortedPaths `
    -Message $message `
    -Warn $driftDetected
