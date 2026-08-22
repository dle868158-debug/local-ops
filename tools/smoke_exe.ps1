param(
    [Parameter(Mandatory = $true)]
    [string]$ExePath,
    [ValidateRange(9600, 9609)]
    [int]$Port = 9609,
    [switch]$KeepArtifacts
)

$ErrorActionPreference = 'Stop'
$exe = (Resolve-Path -LiteralPath $ExePath).Path
$projectRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$distRoot = (Resolve-Path -LiteralPath (Join-Path $projectRoot 'dist')).Path
$smokeRoot = Join-Path $distRoot ('.exe-smoke-' + $Port)
$resolvedParent = [System.IO.Path]::GetFullPath($smokeRoot)
if (-not $resolvedParent.StartsWith($distRoot + [System.IO.Path]::DirectorySeparatorChar,
        [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "Smoke 目录越出 dist：$resolvedParent"
}

New-Item -ItemType Directory -Force -Path $resolvedParent | Out-Null
$env:CONSOLE_DATA_DIR = Join-Path $resolvedParent 'data'
$env:CONSOLE_LOG_DIR = Join-Path $resolvedParent 'logs'
$env:QT_QPA_PLATFORM = 'offscreen'
$env:QTWEBENGINE_CHROMIUM_FLAGS = '--disable-gpu'
$process = $null
$baseUrl = "http://127.0.0.1:$Port"
$existingPids = @(
    Get-CimInstance Win32_Process | Where-Object {
        $_.ExecutablePath -and $_.ExecutablePath.Equals(
            $exe, [System.StringComparison]::OrdinalIgnoreCase)
    } | ForEach-Object { [int]$_.ProcessId }
)

try {
    $process = Start-Process -FilePath $exe -ArgumentList @('--preferred-port', "$Port") `
        -WindowStyle Hidden -PassThru
    Write-Output "EXE started: pid=$($process.Id), expectedPort=$Port"
    $session = New-Object Microsoft.PowerShell.Commands.WebRequestSession
    $health = $null
    $deadline = [DateTime]::UtcNow.AddSeconds(75)
    while ([DateTime]::UtcNow -lt $deadline) {
        if ($process.HasExited) {
            throw "EXE 在健康检查前退出，exit $($process.ExitCode)"
        }
        try {
            $health = Invoke-RestMethod -Uri "$baseUrl/api/health" -WebSession $session `
                -TimeoutSec 3
            if ($health.status -eq 'ok') {
                Write-Output "Health passed: version=$($health.version), port=$Port"
                break
            }
        } catch {
            Start-Sleep -Milliseconds 500
        }
    }
    if (-not $health -or $health.status -ne 'ok') {
        throw 'EXE 未在 75 秒内通过 /api/health'
    }
    $null = Invoke-RestMethod -Uri "$baseUrl/api/console/stop" -Method Post `
        -ContentType 'application/json' -Body '{}' -Headers @{ Origin = $baseUrl } `
        -WebSession $session -TimeoutSec 5
    Write-Output 'Stop request accepted'
    $stopDeadline = [DateTime]::UtcNow.AddSeconds(15)
    $closed = $false
    while ([DateTime]::UtcNow -lt $stopDeadline) {
        try {
            $null = Invoke-RestMethod -Uri "$baseUrl/api/health" -TimeoutSec 1
            Start-Sleep -Milliseconds 250
        } catch {
            $closed = $true
            break
        }
    }
    if (-not $closed) {
        throw 'EXE 接受停止请求后 HTTP 端口仍未关闭'
    }
    $null = $process.WaitForExit(5000)
    Write-Output "EXE smoke passed: version=$($health.version), port=$Port"
} finally {
    if ($process -and -not $process.HasExited) {
        Stop-Process -Id $process.Id -Force
        $process.WaitForExit()
    }
    # PyInstaller one-file 可能让 Start-Process 返回的父 bootloader 先退出；
    # 测试失败时还要精确清理由本次命令行产生的解压子进程。
    Get-CimInstance Win32_Process | Where-Object {
        $_.ExecutablePath -and $_.ExecutablePath.Equals(
            $exe, [System.StringComparison]::OrdinalIgnoreCase) -and
        [int]$_.ProcessId -notin $existingPids -and
        $_.CommandLine -like "*--preferred-port $Port*"
    } | ForEach-Object {
        Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
    }
    if (-not $KeepArtifacts -and (Test-Path -LiteralPath $resolvedParent)) {
        for ($attempt = 0; $attempt -lt 20; $attempt++) {
            try {
                Remove-Item -LiteralPath $resolvedParent -Recurse -Force
                break
            } catch {
                if ($attempt -eq 19) {
                    Write-Warning "Smoke 目录暂未释放，可稍后删除：$resolvedParent"
                    break
                }
                Start-Sleep -Milliseconds 500
            }
        }
    }
}
