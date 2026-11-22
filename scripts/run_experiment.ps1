# Reproduce the experiment through Docker Compose on Windows (PowerShell 5.1+).
# No host Python is required. Intermediate logs stay ignored until evaluation ends.
[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$taskRoot = Split-Path -Parent $PSScriptRoot
$taskOriginalLocation = Get-Location
$taskUtf8 = [Text.UTF8Encoding]::new($false)
$taskStarted = [DateTimeOffset]::UtcNow
$taskRunId = $taskStarted.ToString('yyyyMMddTHHmmssZ') + '-' + [Guid]::NewGuid().ToString('N').Substring(0, 6) + '-windows-compose'
$taskLocal = Join-Path $taskRoot ('.local/' + $taskRunId)
$taskFolder = Join-Path $taskRoot ('evidencias/' + $taskRunId)
$taskCommands = [Collections.Generic.List[object]]::new()

function Write-Utf8 {
    param([string]$Path, [string]$Text)
    [void][IO.Directory]::CreateDirectory([IO.Path]::GetDirectoryName($Path))
    [IO.File]::WriteAllText($Path, $Text, $taskUtf8)
}

function Write-Json {
    param([string]$Path, $Value)
    # PS 5.1 decorates ConvertFrom-Json arrays with Count; copy their elements
    # so they serialize as JSON arrays rather than { value: [...], Count: n }.
    if ($Value -is [array]) { $Value = @($Value | ForEach-Object { $_ }) }
    Write-Utf8 $Path ((ConvertTo-Json -InputObject $Value -Depth 100) + "`n")
}

function Protect-Text {
    param([AllowEmptyString()][string]$Text)
    foreach ($secret in @('administracao_local', 'somente_leitura_local', $env:DB_ADMIN_PASSWORD, $env:DB_READER_PASSWORD)) {
        if ($secret) { $Text = $Text.Replace($secret, '[REDACTED]') }
    }
    return $Text
}

function ConvertTo-NativeArgument {
    param([AllowEmptyString()][string]$Value)
    if ($Value.Length -gt 0 -and $Value -notmatch '[\s"]') { return $Value }
    # Windows CommandLineToArgvW quoting; no shell interprets these arguments.
    $escaped = $Value -replace '(\\*)"', '$1$1\"'
    $escaped = $escaped -replace '(\\+)$', '$1$1'
    return '"' + $escaped + '"'
}

function Invoke-CapturedCommand {
    param([string]$Phase, [string]$Executable, [string[]]$CommandArgs, [string]$LogPrefix)
    $started = [DateTimeOffset]::UtcNow
    $stdout = ''; $stderr = ''; $code = 127; $resolvedPath = $null
    $proc = [Diagnostics.Process]::new()
    try {
        $resolved = Get-Command $Executable -CommandType Application -ErrorAction Stop | Select-Object -First 1
        $resolvedPath = $resolved.Source
        if ([IO.Path]::GetExtension($resolvedPath) -in @('.cmd', '.bat')) {
            throw 'Use the native git.exe/docker.exe executables, not a shell wrapper.'
        }
        $info = [Diagnostics.ProcessStartInfo]::new()
        $info.FileName = $resolvedPath
        $info.Arguments = (($CommandArgs | ForEach-Object { ConvertTo-NativeArgument $_ }) -join ' ')
        $info.WorkingDirectory = $taskRoot
        $info.UseShellExecute = $false
        $info.CreateNoWindow = $true
        $info.RedirectStandardOutput = $true
        $info.RedirectStandardError = $true
        $info.StandardOutputEncoding = $taskUtf8
        $info.StandardErrorEncoding = $taskUtf8
        $proc.StartInfo = $info
        [void]$proc.Start()
        # Drain both streams asynchronously so verbose Docker builds cannot deadlock.
        $outTask = $proc.StandardOutput.ReadToEndAsync()
        $errTask = $proc.StandardError.ReadToEndAsync()
        $proc.WaitForExit()
        $stdout = $outTask.GetAwaiter().GetResult()
        $stderr = $errTask.GetAwaiter().GetResult()
        $code = $proc.ExitCode
    } catch {
        $stderr += $_.Exception.Message + "`n"
    } finally { $proc.Dispose() }
    $stdout = Protect-Text $stdout
    $stderr = Protect-Text $stderr
    $ended = [DateTimeOffset]::UtcNow
    $meta = [ordered]@{
        phase = $Phase
        command = $Executable + ' ' + ($CommandArgs -join ' ')
        arguments = @($CommandArgs)
        executable = $resolvedPath
        started_at_utc = $started.ToString('o')
        ended_at_utc = $ended.ToString('o')
        duration_seconds = [Math]::Round(($ended - $started).TotalSeconds, 3)
        exit_code = $code
        stdout_log = $null
        stderr_log = $null
    }
    if ($LogPrefix) {
        $meta.stdout_log = 'logs/' + $LogPrefix + '.stdout.log'
        $meta.stderr_log = 'logs/' + $LogPrefix + '.stderr.log'
        Write-Utf8 (Join-Path $taskLocal $meta.stdout_log) $stdout
        Write-Utf8 (Join-Path $taskLocal $meta.stderr_log) $stderr
    }
    return [pscustomobject]@{ Info = $meta; Stdout = $stdout; Stderr = $stderr }
}

function Get-ObservedError {
    param($Result)
    $lines = @(($Result.Stderr + "`n" + $Result.Stdout) -split '\r?\n' | Where-Object { $_.Trim() })
    $relevant = @($lines | Where-Object { $_ -match '(?i)error|failed|failure|denied|cannot|unable|not found|falha|erro|exception|timeout' })
    if ($relevant.Count -gt 0) { return ($relevant | Select-Object -Last 12) -join "`n" }
    if ($lines.Count -gt 0) { return ($lines | Select-Object -Last 12) -join "`n" }
    return 'Command exited with code ' + $Result.Info.exit_code + ' without output.'
}

function Get-RoundHashes {
    param([string[]]$Exclude)
    $hashes = [ordered]@{}
    Get-ChildItem -LiteralPath $taskFolder -File -Recurse | Sort-Object FullName | ForEach-Object {
        $relative = $_.FullName.Substring($taskFolder.Length + 1).Replace('\', '/')
        if ($relative -notin $Exclude) {
            $hashes[$relative] = (Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
        }
    }
    return $hashes
}

function Save-IncompleteExperiment {
    param([string]$Phase, [string]$ObservedError, $Git)
    [void][IO.Directory]::CreateDirectory($taskFolder)
    $questions = Get-Content -LiteralPath (Join-Path $taskRoot 'queries/questions.json') -Raw -Encoding UTF8 | ConvertFrom-Json
    $existing = @{}
    $recordsPath = Join-Path $taskFolder 'records.json'
    if (Test-Path -LiteralPath $recordsPath) {
        try {
            $existingRecords = Get-Content -LiteralPath $recordsPath -Raw -Encoding UTF8 | ConvertFrom-Json
            foreach ($record in $existingRecords) {
                $existing[$record.configuration + '-' + $record.question_id] = $record
            }
        } catch { $existing = @{} }
    }
    # Preserve any interrupted evaluator output before completing the planned matrix.
    foreach ($name in @('records.json', 'summary.json', 'checks.json', 'requirements.json', 'manifest.json', 'relatorio.html')) {
        $original = Join-Path $taskFolder $name
        if (Test-Path -LiteralPath $original) {
            Copy-Item -LiteralPath $original -Destination (Join-Path $taskFolder ('interrupted-' + $name))
        }
    }
    foreach ($directory in @('ontology', 'mappings', 'catalog', 'queries', 'sql', 'docs')) {
        $destination = Join-Path $taskFolder ('artifacts/' + $directory)
        if (!(Test-Path -LiteralPath $destination)) {
            [void][IO.Directory]::CreateDirectory((Join-Path $taskFolder 'artifacts'))
            Copy-Item -LiteralPath (Join-Path $taskRoot $directory) -Destination $destination -Recurse
        }
    }
    $records = @(
        foreach ($configuration in @('original', 'incompativel', 'corrigida')) {
            foreach ($question in $questions) {
                $key = $configuration + '-' + $question.id
                if ($existing.ContainsKey($key)) { $existing[$key]; continue }
                [ordered]@{
                    execution_id = $key
                    question_id = $question.id
                    configuration = $configuration
                    requirements = @($question.requirements)
                    mapping_ids = @($question.mapping_ids)
                    timestamp = [DateTimeOffset]::UtcNow.ToString('o')
                    git_commit = $Git.commit
                    status = 'blocked'
                    query_executed = $false
                    configuration_prepared = $false
                    phase = $Phase
                    error = $ObservedError
                    attempt_kind = 'planned_query_blocked_by_prerequisite'
                    note = 'Planned matrix position; no SPARQL request was issued. This is not the deliberate schema incompatibility.'
                }
            }
        }
    )
    $stats = [ordered]@{}
    foreach ($configuration in @('original', 'incompativel', 'corrigida')) {
        $selected = @($records | Where-Object { $_.configuration -eq $configuration })
        $stats[$configuration] = [ordered]@{ total = $selected.Count }
        foreach ($status in @('correct', 'incorrect', 'blocked', 'error')) {
            $stats[$configuration][$status] = @($selected | Where-Object { $_.status -eq $status }).Count
        }
    }
    $summary = [ordered]@{
        timestamp = [DateTimeOffset]::UtcNow.ToString('o')
        run_id = $taskRunId
        configurations = $stats
        attempts = $records.Count
        planned_attempts = 30
        git = $Git
        traceability_complete = $false
        protocol_passed = $false
        execution_status = 'blocked'
        failed_phase = $Phase
        error = $ObservedError
        human_review = 'pendente_revisao_humana'
        scope = 'Incomplete Docker Compose reproduction. Planned blocked entries are not executed queries or evidence of the controlled schema change.'
    }
    $requirements = Get-Content -LiteralPath (Join-Path $taskRoot 'docs/requirements.json') -Raw -Encoding UTF8 | ConvertFrom-Json
    foreach ($requirement in $requirements) {
        $status = if ($requirement.id -in @('R01', 'R05')) { 'pendente_revisao_humana' } else { 'nao_avaliado' }
        $requirement | Add-Member -NotePropertyName status -NotePropertyValue $status -Force
        $requirement | Add-Member -NotePropertyName technical_status -NotePropertyValue 'nao_avaliado' -Force
        $requirement | Add-Member -NotePropertyName qualification -NotePropertyValue 'Execution incomplete; human review remains pending.' -Force
    }
    Write-Json $recordsPath $records
    Write-Json (Join-Path $taskFolder 'summary.json') $summary
    Write-Json (Join-Path $taskFolder 'checks.json') ([ordered]@{
        status = 'nao_avaliado'; failed_phase = $Phase; error = $ObservedError
        architecture_review = 'pendente_revisao_humana'; catalog_review = 'pendente_revisao_humana'
    })
    Write-Json (Join-Path $taskFolder 'requirements.json') $requirements
    $htmlError = [Net.WebUtility]::HtmlEncode($ObservedError)
    $htmlPhase = [Net.WebUtility]::HtmlEncode($Phase)
    $rows = ($records | ForEach-Object {
        '<tr><td>' + [Net.WebUtility]::HtmlEncode([string]$_.configuration) + '</td><td>' +
        [Net.WebUtility]::HtmlEncode([string]$_.question_id) + '</td><td>' +
        [Net.WebUtility]::HtmlEncode([string]$_.status) + '</td></tr>'
    }) -join "`n"
    $report = @"
<!doctype html><html lang="pt-BR"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Experimento bloqueado - $taskRunId</title><style>body{font:16px system-ui;max-width:1100px;margin:40px auto;padding:0 24px;color:#14273d}pre{white-space:pre-wrap;background:#fff5df;padding:16px}table{border-collapse:collapse}th,td{padding:8px 24px;border-bottom:1px solid #ddd;text-align:left}code{overflow-wrap:anywhere}</style>
<h1>Reproducao Docker Compose incompleta</h1><p>Rodada: <code>$taskRunId</code></p><p>Commit: <code>$($Git.commit)</code></p>
<p>Etapa: <strong>$htmlPhase</strong></p><pre>$htmlError</pre>
<p>As 30 posicoes planejadas foram preservadas. Registros com <code>query_executed=false</code> nao representam consultas executadas. O bloqueio de infraestrutura nao demonstra a falha controlada da configuracao incompativel.</p>
<p>R01: revisao de responsabilidades e interfaces pendente. R05: conferencia humana do catalogo pendente.</p>
<p><a href="execution.json">Execucao e comandos</a> | <a href="records.json">Registros</a> | <a href="summary.json">Resumo</a> | <a href="requirements.json">Requisitos</a> | <a href="host-manifest.json">Integridade</a></p>
<table><thead><tr><th>Configuracao</th><th>Questao</th><th>Estado</th></tr></thead><tbody>$rows</tbody></table></html>
"@
    Write-Utf8 (Join-Path $taskFolder 'relatorio.html') $report
    Write-Json (Join-Path $taskFolder 'manifest.json') ([ordered]@{
        run_id = $taskRunId; git = $Git
        files_sha256 = Get-RoundHashes @('manifest.json', 'host-manifest.json', 'execution.json')
    })
}

$taskPhase = 'git_preflight'
$taskFailure = $null
$taskExitCode = 0
$taskGit = $null
$taskAccepted = $false
try {
    Set-Location -LiteralPath $taskRoot
    # These probes run before any output directory exists.
    $commit = Invoke-CapturedCommand 'git_commit' 'git' @('rev-parse', 'HEAD')
    $state = Invoke-CapturedCommand 'git_status' 'git' @('status', '--porcelain', '--untracked-files=normal')
    [void][IO.Directory]::CreateDirectory($taskLocal)
    Write-Utf8 (Join-Path $taskLocal 'git-commit.stdout.log') $commit.Stdout
    Write-Utf8 (Join-Path $taskLocal 'git-commit.stderr.log') $commit.Stderr
    Write-Utf8 (Join-Path $taskLocal 'git-status.stdout.log') $state.Stdout
    Write-Utf8 (Join-Path $taskLocal 'git-status.stderr.log') $state.Stderr
    if ($commit.Info.exit_code -ne 0 -or $state.Info.exit_code -ne 0) {
        throw 'Git preflight failed. See .local/' + $taskRunId + '/git-*.log.'
    }
    $taskGit = [ordered]@{ commit = $commit.Stdout.Trim(); dirty = [bool]$state.Stdout.Trim(); status = $state.Stdout.Trim() }
    if ($taskGit.dirty) {
        throw 'Commit or resolve the current changes before reproducing the experiment. Git status is saved under .local/' + $taskRunId + '.'
    }
    $taskAccepted = $true
    $steps = @(
        @{ phase = 'docker_version'; args = @('version') },
        @{ phase = 'compose_version'; args = @('compose', 'version') },
        @{ phase = 'compose_config'; args = @('compose', 'config', '--quiet') },
        @{ phase = 'build'; args = @('compose', '--profile', 'avaliacao', 'build', 'avaliador') },
        @{ phase = 'tests'; args = @('compose', 'run', '--rm', '--no-deps', '--entrypoint', 'python', 'avaliador', '-m', 'unittest', 'discover', '-s', 'tests', '-v') },
        @{ phase = 'postgres_startup'; args = @('compose', 'up', '-d', '--wait', 'postgres') },
        @{ phase = 'evaluate'; args = @('compose', 'run', '--rm', '--no-deps', '-e', ('EVIDENCE_RUN_ID=' + $taskRunId), '-e', 'EVIDENCE_LATEST_FILE=latest-windows.json', 'avaliador') }
    )
    $sequence = 0
    foreach ($step in $steps) {
        $sequence++
        $taskPhase = $step.phase
        Write-Host ('[' + $taskPhase + '] docker ' + ($step.args -join ' '))
        $result = Invoke-CapturedCommand $taskPhase 'docker' $step.args ('{0:D2}-{1}' -f $sequence, $taskPhase)
        $taskCommands.Add($result.Info)
        if ($result.Info.exit_code -ne 0) {
            $taskExitCode = $result.Info.exit_code
            $taskFailure = Get-ObservedError $result
            break
        }
    }
    if (!$taskFailure) {
        $summaryPath = Join-Path $taskFolder 'summary.json'
        if (!(Test-Path -LiteralPath $summaryPath)) {
            $taskFailure = 'Evaluator returned success but did not write summary.json.'
            $taskExitCode = 2
        } else {
            $summary = Get-Content -LiteralPath $summaryPath -Raw -Encoding UTF8 | ConvertFrom-Json
            if (!$summary.protocol_passed) {
                $taskFailure = 'Evaluator summary reports protocol_passed=false.'
                $taskExitCode = 1
            }
        }
    }
} catch {
    $taskFailure = Protect-Text $_.Exception.Message
    if ($taskExitCode -eq 0) { $taskExitCode = 2 }
} finally {
    if ($taskAccepted) {
        # Diagnostic collection never masks the earlier failure or changes services.
        $dbLogs = Invoke-CapturedCommand 'postgres_logs' 'docker' @('compose', 'logs', '--no-color', '--timestamps', 'postgres') '08-postgres_logs'
        $taskCommands.Add($dbLogs.Info)
        $configuredImages = Invoke-CapturedCommand 'configured_images' 'docker' @('compose', 'config', '--images') '09-configured_images'
        $taskCommands.Add($configuredImages.Info)
        if ($configuredImages.Info.exit_code -eq 0) {
            $imageNames = @($configuredImages.Stdout -split '\r?\n' | Where-Object { $_.Trim() } | Sort-Object -Unique)
            if ($imageNames.Count -gt 0) {
                # Select provenance fields only; do not dump image/container environments.
                $imageFormat = '{"Id":{{json .Id}},"RepoTags":{{json .RepoTags}},"RepoDigests":{{json .RepoDigests}},"Created":{{json .Created}},"Architecture":{{json .Architecture}},"Os":{{json .Os}}}'
                $imageInfo = Invoke-CapturedCommand 'image_provenance' 'docker' (@('image', 'inspect', '--format', $imageFormat) + $imageNames) '10-image_provenance'
                $taskCommands.Add($imageInfo.Info)
            }
        }
        [void][IO.Directory]::CreateDirectory($taskFolder)
        $logsPath = Join-Path $taskFolder 'logs'
        [void][IO.Directory]::CreateDirectory($logsPath)
        Get-ChildItem -LiteralPath (Join-Path $taskLocal 'logs') -File | ForEach-Object {
            Copy-Item -LiteralPath $_.FullName -Destination (Join-Path $logsPath $_.Name)
        }
        Get-ChildItem -LiteralPath $taskLocal -Filter 'git-*.log' -File | ForEach-Object {
            Copy-Item -LiteralPath $_.FullName -Destination (Join-Path $logsPath $_.Name)
        }
        $complete = $false
        try {
            $summaryPath = Join-Path $taskFolder 'summary.json'
            $recordsPath = Join-Path $taskFolder 'records.json'
            $savedSummary = Get-Content -LiteralPath $summaryPath -Raw -Encoding UTF8 | ConvertFrom-Json
            $savedRecords = Get-Content -LiteralPath $recordsPath -Raw -Encoding UTF8 | ConvertFrom-Json
            $complete = @($savedRecords).Count -eq 30 -and (Test-Path -LiteralPath (Join-Path $taskFolder 'manifest.json')) -and (Test-Path -LiteralPath (Join-Path $taskFolder 'relatorio.html'))
        } catch { $complete = $false }
        if (!$complete) {
            if (!$taskFailure) { $taskFailure = 'Evaluator evidence is incomplete.'; $taskExitCode = 2 }
            Save-IncompleteExperiment $taskPhase $taskFailure $taskGit
        }
        $execution = [ordered]@{
            run_id = $taskRunId
            started_at_utc = $taskStarted.ToString('o')
            ended_at_utc = [DateTimeOffset]::UtcNow.ToString('o')
            tested_commit = $taskGit.commit
            git_before_execution = $taskGit
            host = [ordered]@{
                os = [Environment]::OSVersion.VersionString
                machine = [Environment]::MachineName
                process_architecture_bits = [IntPtr]::Size * 8
                powershell = $PSVersionTable.PSVersion.ToString()
                timezone = [TimeZoneInfo]::Local.Id
            }
            runtime_mode = 'docker-compose-from-windows'
            status = if ($taskExitCode -eq 0) { 'completed' } else { 'failed' }
            exit_code = $taskExitCode
            failed_phase = if ($taskFailure) { $taskPhase } else { $null }
            observed_error = $taskFailure
            host_fallback_used = !$complete
            commands = @($taskCommands.ToArray())
            note = 'Docker/PostgreSQL services are left running. No automatic commit or cleanup was performed.'
        }
        Write-Json (Join-Path $taskFolder 'execution.json') $execution
        Write-Json (Join-Path $taskFolder 'host-manifest.json') ([ordered]@{
            run_id = $taskRunId
            git = $taskGit
            files_sha256 = Get-RoundHashes @('host-manifest.json')
        })
        $savedSummary = Get-Content -LiteralPath (Join-Path $taskFolder 'summary.json') -Raw -Encoding UTF8 | ConvertFrom-Json
        Write-Json (Join-Path $taskRoot 'evidencias/latest-windows.json') ([ordered]@{
            run_id = $taskRunId
            report = 'evidencias/' + $taskRunId + '/relatorio.html'
            summary = $savedSummary
        })
        Write-Host ('Evidence: evidencias/' + $taskRunId)
        Write-Host ('Report: evidencias/' + $taskRunId + '/relatorio.html')
    } elseif ($taskFailure) {
        Write-Utf8 (Join-Path $taskLocal 'preflight-error.log') ($taskFailure + "`n")
    }
    Set-Location -LiteralPath $taskOriginalLocation.Path
}
if ($taskFailure) { Write-Warning $taskFailure }
exit $taskExitCode
