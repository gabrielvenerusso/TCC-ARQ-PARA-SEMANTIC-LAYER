"""Consolidate a recorded run without opening a database or running queries."""
from __future__ import annotations

from collections import Counter
import json
import os
from pathlib import Path
import re
import shutil

from mvp.analysis import requirement_results, summarize_requirements
from mvp.reporting import render_report


def analyze_run(source, output, *, root, analysis_path=None):
    # Imported lazily to share the existing hashing and integrity implementation.
    from mvp.__main__ import catalog_check, digest, dump, git_info, verify_evidence

    source, output, root = Path(source).resolve(), Path(output).resolve(), Path(root).resolve()
    if output == source or source in output.parents or output in source.parents:
        raise ValueError('A análise deve ficar separada da execução original.')
    evidence_root = (root/'evidencias').resolve()
    if output == evidence_root or evidence_root in output.parents:
        raise ValueError('A análise documental deve ficar fora de evidencias/.')
    if output.exists():
        raise FileExistsError('A pasta de saída já existe; escolha uma pasta nova.')
    integrity = verify_evidence(source)
    if not integrity['valid']:
        raise ValueError('Integridade da execução inválida: ' + ', '.join(integrity['invalid']))
    covered = set()
    for name in integrity['manifests']:
        covered.update(json.loads((source/name).read_text(encoding='utf-8'))['files_sha256'])
    required = {'records.json', 'summary.json', 'checks.json'}
    if not required.issubset(covered):
        raise ValueError('O manifesto não cobre os registros necessários à análise.')
    load = lambda name: json.loads((source/name).read_text(encoding='utf-8'))
    original_summary, records, checks = load('summary.json'), load('records.json'), load('checks.json')
    mutation = load('mutation.json') if 'mutation.json' in covered else None
    discrepancies = []
    stats = {}
    for name in ['original', 'incompativel', 'corrigida']:
        counts = Counter(r['status'] for r in records if r['configuration'] == name)
        if set(counts) - {'correct', 'incorrect', 'blocked', 'error'}:
            raise ValueError('Estado de tentativa desconhecido.')
        stats[name] = {'total': sum(counts.values()),
                       **{s: counts[s] for s in ['correct', 'incorrect', 'blocked', 'error']}}
    if stats != original_summary.get('configurations') or len(records) != original_summary.get('attempts'):
        discrepancies.append('O resumo original diverge das tentativas registradas. As contagens desta análise foram obtidas de records.json.')
    artifacts = source/'artifacts'
    catalogs = {}
    for name, filename in [('original', 'original'), ('incompativel', 'original'), ('corrigida', 'corrigido')]:
        cat_path = f'artifacts/catalog/{filename}.json'
        meta_path = f'{name}/metadata.json'
        if cat_path in covered and meta_path in covered:
            catalogs[name] = catalog_check(load(cat_path), load(meta_path))
            saved = checks.get('catalog', {}).get(name, {})
            if catalogs[name]['valid'] != saved.get('valid'):
                discrepancies.append(f'A validade estrutural do catálogo em {name} diverge do registro original; foi mantido o resultado da conferência com os metadados preservados.')
    questions = load('artifacts/queries/questions.json') if 'artifacts/queries/questions.json' in covered else []
    expected_pairs = {(name, q['id']) for name in stats for q in questions}
    actual_pairs = [(r['configuration'], r['question_id']) for r in records]
    def traced(record):
        paths = [record.get('expected'), record.get('startup_log'), *record.get('artifacts', {}).values()]
        if record['status'] in ['correct', 'incorrect']:
            paths.append(record.get('result'))
        elif not record.get('error'):
            return False
        return bool(record.get('git_commit')) and bool(record.get('artifacts')) and all(
            path in covered and (source/path).is_file() for path in paths)
    trace = (original_summary.get('traceability_complete') is True
             and bool(expected_pairs) and set(actual_pairs) == expected_pairs
             and len(actual_pairs) == len(expected_pairs)
             and len({r['execution_id'] for r in records}) == len(records)
             and all(traced(r) for r in records))
    if trace != original_summary.get('traceability_complete'):
        discrepancies.append('A rastreabilidade declarada no resumo original não foi confirmada pelos arquivos e pelas tentativas preservados.')
    # An artifact outside the original manifests is not sufficient analysis evidence.
    from mvp.analysis import REVIEWED_FILES
    for paths in REVIEWED_FILES.values():
        if not all('artifacts/' + path in covered for path in paths):
            raise ValueError('Arquivos analisados não cobertos pelo manifesto original.')
    registry = Path(analysis_path) if analysis_path else root/'docs/analises.json'
    requirements = requirement_results(stats, {**checks, 'mutation': mutation}, catalogs, trace, root=root,
                                       artifact_root=artifacts, analysis_path=registry)
    tests = None
    test_log = 'logs/05-tests.stderr.log'
    if test_log in covered:
        text = (source/test_log).read_text(encoding='utf-8-sig')
        match = re.search(r'Ran (\d+) tests?\b', text)
        if match:
            tests = {'count': int(match[1]), 'result': 'aprovados' if re.search(r'^OK\s*$', text, re.M) else 'não aprovados',
                     'log': test_log}
    startup = source/'incompativel/startup.log'
    controlled_block = ('incompativel/startup.log' in covered
                        and 'cod_situacao' in startup.read_text(encoding='utf-8')
                        and 'InvalidMappingSourceQueriesException' in startup.read_text(encoding='utf-8')
                        and any(r['configuration'] == 'incompativel' and r.get('phase') == 'startup'
                                and r['status'] == 'blocked' for r in records))
    summary = {key: original_summary.get(key) for key in ['timestamp', 'run_id', 'git', 'protocol_passed']}
    summary.update(analysis_only=True, queries_executed_by_analysis=0,
                   configurations=stats, attempts=len(records), traceability_complete=trace,
                   requirements=summarize_requirements(requirements), recorded_tests=tests,
                   controlled_schema_block=controlled_block, discrepancies=discrepancies,
                   scope='Análise da execução documentada no domínio sintético de pedidos de venda.')
    source_hashes = {p.relative_to(source).as_posix(): digest(p) for p in sorted(source.rglob('*')) if p.is_file()}
    relative_source = Path(os.path.relpath(source, output)).as_posix()
    provenance = {
        'kind': 'documentary_analysis', 'source_run': original_summary['run_id'],
        'source_path': relative_source, 'source_git': original_summary['git'],
        'source_files_sha256': source_hashes, 'source_integrity': integrity,
        'generation_git': git_info(), 'queries_executed': 0,
        'analysis_registry_sha256': digest(registry) if registry.is_file() else None,
        'criteria_sha256': digest(root/'docs/requirements.json'),
        'generator_files_sha256': {name: digest(root/name) for name in
                                  ['mvp/__main__.py', 'mvp/analysis.py', 'mvp/reporting.py', 'mvp/final_analysis.py']},
    }
    output.mkdir(parents=True)
    if registry.is_file():
        shutil.copyfile(registry, output/'analises.json')
    else:
        dump(output/'analises.json', {'schema_version': 1, 'analyses': [], 'note': 'Registro não disponível na geração.'})
    shutil.copyfile(root/'docs/requirements.json', output/'criteria.json')
    dump(output/'source.json', provenance)
    dump(output/'requirements.json', requirements)
    dump(output/'summary.json', summary)
    render_report(output, summary, records, requirements, source_prefix=relative_source, mutation=mutation)
    dump(output/'manifest.json', {
        'kind': 'documentary_analysis', 'source_run': original_summary['run_id'],
        'files_sha256': {p.relative_to(output).as_posix(): digest(p)
                         for p in sorted(output.rglob('*')) if p.is_file()},
        'source': {'path': relative_source, 'files_sha256': source_hashes},
    })
    return summary
