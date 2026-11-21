# Windows host audit only. Does not install packages, start services or query data.
# PowerShell 5.1+, no Python dependency. Outputs UTF-8 without BOM.
[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$taskRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $taskRoot
$taskStart = [DateTimeOffset]::UtcNow
$taskId = 'phase0-' + $taskStart.ToString('yyyyMMddTHHmmssfffffffZ')
$taskUtf8 = [Text.UTF8Encoding]::new($false)

function Invoke-Probe {
    param([string]$Executable, [string]$Arguments, [int]$TimeoutSeconds = 15)
    $probe = [ordered]@{
        command = ($Executable + ' ' + $Arguments).Trim()
        observed_at_utc = [DateTimeOffset]::UtcNow.ToString('o')
        executable = $null; status = 'not_found'; exit_code = $null
        stdout = ''; stderr = ''
    }
    $resolved = Get-Command $Executable -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1
    if (-not $resolved) { return $probe }
    $probe.executable = $resolved.Source
    $proc = [Diagnostics.Process]::new()
    try {
        $info = [Diagnostics.ProcessStartInfo]::new()
        $info.FileName = $resolved.Source
        $info.Arguments = $Arguments
        if ([IO.Path]::GetExtension($resolved.Source) -in @('.bat', '.cmd')) {
            if ($resolved.Source -match '[&|<>^%!"\r\n]') { throw 'Unsupported shell metacharacter in executable path' }
            $info.FileName = $env:ComSpec
            $info.Arguments = '/d /s /c ""' + $resolved.Source + '" ' + $Arguments + '"'
        }
        $info.UseShellExecute = $false
        $info.CreateNoWindow = $true
        $info.RedirectStandardOutput = $true
        $info.RedirectStandardError = $true
        if ($Executable -eq 'wsl') {
            $info.StandardOutputEncoding = [Text.Encoding]::Unicode
            $info.StandardErrorEncoding = [Text.Encoding]::Unicode
        }
        $proc.StartInfo = $info
        [void]$proc.Start()
        $outTask = $proc.StandardOutput.ReadToEndAsync()
        $errTask = $proc.StandardError.ReadToEndAsync()
        if ($proc.WaitForExit($TimeoutSeconds * 1000)) {
            $probe.exit_code = $proc.ExitCode
            $probe.status = if ($proc.ExitCode -eq 0) { 'executed' } else { 'failed' }
        } else {
            $proc.Kill()
            $proc.WaitForExit()
            $probe.status = 'timeout'
        }
        $probe.stdout = $outTask.GetAwaiter().GetResult().Trim()
        $probe.stderr = $errTask.GetAwaiter().GetResult().Trim()
    } catch {
        $probe.status = 'error'
        $probe.stderr = $_.Exception.Message
    } finally { $proc.Dispose() }
    return $probe
}

$taskProbes = [ordered]@{}
$taskProbes.git = Invoke-Probe 'git' '--version'
$taskProbes.commit = Invoke-Probe 'git' 'rev-parse HEAD'
$taskProbes.worktree = Invoke-Probe 'git' 'status --porcelain'
$taskProbes.java = Invoke-Probe 'java' '-version'
$taskProbes.javac = Invoke-Probe 'javac' '-version'
$taskProbes.python = Invoke-Probe 'python' '--version'
$taskProbes.python3 = Invoke-Probe 'python3' '--version'
$taskProbes.python_launcher = Invoke-Probe 'py' '-0p'
$taskProbes.docker_client = Invoke-Probe 'docker' '--version'
$taskProbes.docker_compose = Invoke-Probe 'docker' 'compose version'
$taskProbes.docker_engine = Invoke-Probe 'docker' 'version --format "{{json .}}"'
$taskProbes.wsl = Invoke-Probe 'wsl' '--list --verbose'
$taskProbes.postgres_binary = Invoke-Probe 'postgres' '--version'
$taskProbes.psql = Invoke-Probe 'psql' '--version'
$taskProbes.ontop = Invoke-Probe 'ontop' '--version'
$taskProbes.pandoc = Invoke-Probe 'pandoc' '--version'

# Import metadata only; never dump environment variables or connection strings.
$taskPython = @($taskProbes.python, $taskProbes.python3) | Where-Object { $_.status -eq 'executed' } | Select-Object -First 1
$taskPackages = [ordered]@{status = 'not_executed'; reason = 'No Python executable available on PATH'; versions = $null}
if ($taskPython) {
    $taskCode = 'import importlib.metadata as m,json; installed={d.metadata[''Name''].lower():d.version for d in m.distributions() if d.metadata[''Name'']}; print(json.dumps({n:installed.get(n) for n in [''psycopg'',''rdflib'']}))'
    $taskProbes.python_packages = Invoke-Probe $taskPython.executable ('-c "' + $taskCode + '"')
    $taskPackages.status = $taskProbes.python_packages.status
    $taskPackages.reason = $null
    if ($taskPackages.status -eq 'executed') { $taskPackages.versions = $taskProbes.python_packages.stdout | ConvertFrom-Json }
}

$taskResources = [ordered]@{
    os_version = [Environment]::OSVersion.VersionString
    os_64_bit = [Environment]::Is64BitOperatingSystem
    process_64_bit = [Environment]::Is64BitProcess
    logical_processors_visible_to_process = [Environment]::ProcessorCount
    process_working_set_bytes = [Diagnostics.Process]::GetCurrentProcess().WorkingSet64
    powershell_version = $PSVersionTable.PSVersion.ToString()
    windows_cim = $null; windows_cim_error = $null
}
try {
    $taskOs = Get-CimInstance Win32_OperatingSystem
    $taskCpu = @(Get-CimInstance Win32_Processor | Select-Object Name, NumberOfCores, NumberOfLogicalProcessors)
    $taskResources.windows_cim = [ordered]@{
        caption = $taskOs.Caption; version = $taskOs.Version; architecture = $taskOs.OSArchitecture
        visible_memory_kib = [long]$taskOs.TotalVisibleMemorySize
        free_memory_kib = [long]$taskOs.FreePhysicalMemory
        processors = $taskCpu
    }
} catch { $taskResources.windows_cim_error = $_.Exception.Message }

$taskDiscovery = @()
foreach ($taskDirectory in @(
    'C:\Program Files\Eclipse Adoptium', 'C:\Program Files\Java',
    'C:\Program Files\PostgreSQL', 'C:\Program Files\Python312',
    'C:\Program Files\Ontop', 'C:\ontop',
    (Join-Path $env:LOCALAPPDATA 'Programs\Python'),
    (Join-Path $taskRoot '.local\tools')
)) {
    try {
        $taskFound = Get-Item -LiteralPath $taskDirectory -ErrorAction Stop
        $taskEntries = @(Get-ChildItem -LiteralPath $taskFound.FullName -Force | Select-Object -ExpandProperty Name)
        $taskDiscovery += [ordered]@{path = $taskDirectory; status = 'listed'; entries = $taskEntries}
    } catch {
        $taskDiscovery += [ordered]@{path = $taskDirectory; status = 'unavailable'; error = $_.Exception.Message}
    }
}

# Search only inside this repository, not unrelated application directories.
$taskJars = @(Get-ChildItem -LiteralPath $taskRoot -Filter 'postgresql-*.jar' -File -Recurse -ErrorAction SilentlyContinue | ForEach-Object {
    [ordered]@{path = $_.FullName; sha256 = (Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash.ToLowerInvariant(); version_verified = $false}
})
$taskJavaVersion = $null
if (($taskProbes.java.stdout + $taskProbes.java.stderr) -match 'version "([^"]+)"') { $taskJavaVersion = $Matches[1] }
$taskDoc = Join-Path $taskRoot 'docs\TCC 1 - Gabriel Venerusso.docx'
$taskRecord = [ordered]@{
    schema_version = 1
    inspection_id = $taskId
    collected_at_utc = $taskStart.ToString('o')
    user_timezone = 'America/Sao_Paulo'
    phase = 0
    purpose = 'Host inventory; not an MVP evaluation or proof of runtime compatibility'
    git_commit_at_collection = $taskProbes.commit.stdout
    collector_sha256 = (Get-FileHash -LiteralPath $PSCommandPath -Algorithm SHA256).Hash.ToLowerInvariant()
    source_document = [ordered]@{
        path = 'docs/TCC 1 - Gabriel Venerusso.docx'
        sha256 = (Get-FileHash -LiteralPath $taskDoc -Algorithm SHA256).Hash.ToLowerInvariant()
    }
    requested_versions = [ordered]@{
        postgresql = '17.11'; ontop = '5.5.0'; postgresql_jdbc = '42.7.8'
        openjdk_major = '21'; python_minor = '3.12'; psycopg = '3.2.10'
        rdflib = '7.1.4'; protege_optional = '5.6.9'
    }
    document_claimed_versions = [ordered]@{openjdk = '21.0.13'; python = '3.12.14'}
    resources = $taskResources
    probes = $taskProbes
    python_packages = $taskPackages
    local_directory_discovery = $taskDiscovery
    jdbc = [ordered]@{search_scope = 'Repository only'; artifacts = $taskJars; runtime_version = $null}
    findings = [ordered]@{
        java_observed_version = $taskJavaVersion
        java_matches_requested_major = ($null -ne $taskJavaVersion -and $taskJavaVersion.StartsWith('21.'))
        docker_engine_accessible = ($taskProbes.docker_engine.status -eq 'executed')
        database_server_version = $null
        database_connection_test = 'not_executed'
        ontop_validation = 'not_executed'
        compose_application_execution = 'not_executed'
        configurations_executed = @()
    }
    limitations = @(
        'Missing on PATH or in listed locations does not establish global absence.'
        'PostgreSQL client/binary versions do not establish running server version.'
        'No packages installed, no services started, no schema or data created.'
        'No credentials, complete environment dump or Docker configuration contents collected.'
        'A/B/C results claimed in the thesis remain unverified by this inventory.'
        'This collector inventories a Windows host; Linux/container runtime collection remains to be implemented.'
    )
}
$taskJson = ($taskRecord | ConvertTo-Json -Depth 20) + "`n"
$taskSnapshotDirectory = Join-Path $taskRoot ('results\environment\' + $taskId)
[void](New-Item -ItemType Directory -Path $taskSnapshotDirectory)
[IO.File]::WriteAllText((Join-Path $taskSnapshotDirectory 'environment.json'), $taskJson, $taskUtf8)
[IO.File]::WriteAllText((Join-Path $taskRoot 'environment.json'), $taskJson, $taskUtf8)
Write-Output ('Inventory saved: results/environment/' + $taskId + '/environment.json')
Write-Output ('Java matches requested major: ' + $taskRecord.findings.java_matches_requested_major)
Write-Output ('Docker Engine accessible: ' + $taskRecord.findings.docker_engine_accessible)
