param([string]$Version = '1.0.0')
$ErrorActionPreference = 'Stop'
$repoRoot = $PSScriptRoot
$taskCache = Join-Path $repoRoot 'cache'
New-Item -ItemType Directory -Force -Path $taskCache | Out-Null
$env:TEMP = $taskCache
$env:TMP = $taskCache
$env:PYTHONDONTWRITEBYTECODE = '1'
$env:PIP_CACHE_DIR = Join-Path $taskCache 'pip'
$env:PYINSTALLER_CONFIG_DIR = Join-Path $taskCache 'pyinstaller-config'
$taskPython = Join-Path $repoRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $taskPython)) {
    & py -3.11 -m venv (Join-Path $repoRoot '.venv')
    if ($LASTEXITCODE) { throw 'venv 创建失败' }
}
& $taskPython -m pip install -r (Join-Path $repoRoot 'requirements-build.txt')
if ($LASTEXITCODE) { throw '构建依赖安装失败' }
Push-Location $repoRoot
try {
    & $taskPython -m PyInstaller --noconfirm --onedir --windowed --name AC8-MRP-Editor --distpath (Join-Path $repoRoot 'dist') --workpath (Join-Path $taskCache 'pyinstaller') --specpath $taskCache (Join-Path $repoRoot 'AC8_MRP_Editor.py')
    if ($LASTEXITCODE) { throw '打包失败' }
    $appFolder = Join-Path $repoRoot 'dist\AC8-MRP-Editor'
    Copy-Item -LiteralPath (Join-Path $repoRoot 'README.md'),(Join-Path $repoRoot 'LICENSE') -Destination $appFolder -Force
    $releaseFolder = Join-Path $repoRoot 'release'
    New-Item -ItemType Directory -Force -Path $releaseFolder | Out-Null
    $assetName = "AC8-MRP-Editor-v$Version-windows-x64.zip"
    $archive = Join-Path $releaseFolder $assetName
    Compress-Archive -LiteralPath $appFolder -DestinationPath $archive -Force
    $assetHash = (Get-FileHash -LiteralPath $archive -Algorithm SHA256).Hash.ToLowerInvariant()
    [IO.File]::WriteAllText((Join-Path $releaseFolder 'SHA256SUMS.txt'), "$assetHash  $assetName`n", [Text.UTF8Encoding]::new($false))
    Write-Output $archive
} finally { Pop-Location }
