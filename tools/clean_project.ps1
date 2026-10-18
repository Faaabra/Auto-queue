[CmdletBinding(SupportsShouldProcess)]
param()
$ErrorActionPreference = 'Stop'
$projectRoot = [IO.Path]::GetFullPath((Split-Path $PSScriptRoot -Parent))
$archiveRoot = Join-Path $projectRoot ('_archive\' + (Get-Date -Format 'yyyyMMdd-HHmmss'))
$candidates = [Collections.Generic.List[object]]::new()
foreach ($item in Get-ChildItem -LiteralPath $projectRoot -File) {
    if (($item.Extension -eq '.spec' -and $item.Name -ne 'RustAutoQueue.spec') -or
        $item.Name -match '^test.*\.(exe|png|xml|py)$' -or
        $item.Name -in @('mask_test.png', 'verify_features.py', 'PLAN_SMOOTH.md')) {
        $candidates.Add(@{ Item = $item; Relative = $item.Name })
    }
}
foreach ($name in @('build', 'dist10', '__pycache__')) {
    $candidate = Join-Path $projectRoot $name
    if (Test-Path -LiteralPath $candidate) {
        $candidates.Add(@{ Item = Get-Item -LiteralPath $candidate; Relative = $name })
    }
}
$releasesPath = Join-Path $projectRoot 'releases'
if (Test-Path -LiteralPath $releasesPath) {
    foreach ($item in Get-ChildItem -LiteralPath $releasesPath -File -Filter '*.exe') {
        if ($item.Name -notin @('RustAutoQueue.exe', 'RustAutoQueue_v122.exe')) {
            $candidates.Add(@{ Item = $item; Relative = 'releases\' + $item.Name })
        }
    }
}
$manifest = [Collections.Generic.List[object]]::new()
foreach ($candidate in $candidates) {
    $sourcePath = [IO.Path]::GetFullPath($candidate.Item.FullName)
    $destinationPath = [IO.Path]::GetFullPath((Join-Path $archiveRoot $candidate.Relative))
    if (-not $sourcePath.StartsWith($projectRoot + '\', [StringComparison]::OrdinalIgnoreCase) -or
        -not $destinationPath.StartsWith($archiveRoot + '\', [StringComparison]::OrdinalIgnoreCase)) {
        throw 'La ruta calculada esta fuera del proyecto. No se ha movido.'
    }
    if ($candidate.Item.Attributes -band [IO.FileAttributes]::ReparsePoint) {
        throw "No se archivan enlaces: $sourcePath"
    }
    if ($PSCmdlet.ShouldProcess($sourcePath, "Archivar en $destinationPath")) {
        New-Item -ItemType Directory -Path (Split-Path $destinationPath -Parent) -Force | Out-Null
        Move-Item -LiteralPath $sourcePath -Destination $destinationPath
        $manifest.Add([pscustomobject]@{ Original = $sourcePath; Archived = $destinationPath })
        $manifest | ConvertTo-Json -Depth 3 | Set-Content -LiteralPath (Join-Path $archiveRoot 'manifest.json') -Encoding utf8
    }
}
Write-Output "Archivados $($manifest.Count) elementos. Archivo recuperable: $archiveRoot"
