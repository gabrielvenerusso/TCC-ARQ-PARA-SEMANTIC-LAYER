"""Combine functional evidence with analysis of exact artifact versions.

Analysis records are explicit evidence, never inferred from the presence of a
document or from catalog metadata. SHA-256 comparisons use the original bytes.
"""
from __future__ import annotations

from collections import Counter
import hashlib
import json
from pathlib import Path
import re


REVIEWED_FILES = {
    'R01': {'docs/ARQUITETURA.md'},
    'R05': {'catalog/original.json', 'catalog/corrigido.json'},
}
SCOPE_ID = 'synthetic-sales-orders-v1'
METHODS = {'R01': 'análise da arquitetura', 'R05': 'definições do domínio'}


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _get(value, *keys):
    for key in keys:
        if not isinstance(value, dict) or key not in value:
            return None
        value = value[key]
    return value


def _boolean(value):
    return value if type(value) is bool else None


def _correct(stats, configuration):
    value = _get(stats, configuration, 'correct')
    return value == 10 if type(value) is int and value >= 0 else None


def _preserved(checks, key):
    value = _boolean(_get(checks, 'mutation', key))
    return None if value is None else not value


def _all(*values):
    # A known failure remains visible even when other evidence is absent.
    if any(value is False for value in values):
        return False
    return True if all(value is True for value in values) else None


def _status(value):
    return 'atendido' if value is True else 'não atendido' if value is False else 'não avaliado'


def _load_analysis(path):
    try:
        payload = json.loads(path.read_text(encoding='utf-8'))
        if not isinstance(payload, dict) or type(payload.get('schema_version')) is not int or payload['schema_version'] != 1:
            raise ValueError('Versão do registro de análise não reconhecida.')
        if payload.get('scope_id') != SCOPE_ID:
            raise ValueError('Registro não corresponde ao cenário sintético de pedidos de venda.')
        if not isinstance(payload.get('analyses'), list):
            raise ValueError('Lista de análises ausente ou inválida.')
        return payload['analyses'], _sha256(path), None
    except (OSError, UnicodeError, ValueError) as exc:
        return [], None, f'Registro de análise ausente ou inválido: {exc}'


def _analysis_result(rid, records, artifact_root, registry_sha256, error):
    paths = REVIEWED_FILES[rid]
    current = {}
    for relative in sorted(paths):
        try:
            current[relative] = _sha256(artifact_root / relative)
        except OSError:
            current[relative] = None
    result = {
        'analysis_status': 'não avaliado',
        'analysis_record': None,
        'analysis_files_sha256': current,
        'analysis_registry_sha256': registry_sha256,
    }
    if error:
        result['analysis_reason'] = error
        return result
    candidates = []
    for record in records:
        if not isinstance(record, dict) or record.get('requirement_id') != rid:
            continue
        fingerprints = record.get('files_sha256')
        criteria = record.get('criteria')
        valid = (
            all(isinstance(record.get(key), str) and record[key].strip()
                for key in ['id', 'method', 'scope'])
            and record.get('conclusion') in ['atendido', 'não atendido']
            and record.get('method') == METHODS[rid]
            and isinstance(criteria, list) and bool(criteria)
            and all(isinstance(item, str) and item.strip() for item in criteria)
            and isinstance(fingerprints, dict) and set(fingerprints) == paths
            and all(isinstance(value, str) and re.fullmatch(r'[0-9a-f]{64}', value)
                    for value in fingerprints.values())
        )
        if valid and fingerprints == current:
            candidates.append(record)
    if len(candidates) != 1:
        result['analysis_reason'] = (
            'Há registros conflitantes para esta versão; é necessária uma análise inequívoca.'
            if len(candidates) > 1 else
            'Não há análise completa correspondente aos arquivos desta versão. '
            'Arquivos alterados exigem nova análise.'
        )
        return result
    record = candidates[0]
    result.update(
        analysis_status=record['conclusion'],
        analysis_record=record['id'],
        analysis_method=record['method'],
        analysis_scope=record['scope'],
        analysis_criteria=record['criteria'],
        analysis_reason='Análise registrada para os hashes exatos dos arquivos considerados.',
    )
    return result


def requirement_results(stats, checks, catalogs, trace, *, root,
                        artifact_root=None, analysis_path=None):
    """Evaluate requirements without converting missing evidence into success.

    ``root`` supplies the current requirement definitions and analysis registry;
    ``artifact_root`` supplies the evaluated versions (e.g. a historical snapshot).
    Technical values may be absent (``None``) when execution was blocked.
    """
    root = Path(root)
    artifact_root = Path(artifact_root) if artifact_root is not None else root
    analysis_path = Path(analysis_path) if analysis_path is not None else root / 'docs/analises.json'
    requirements = json.loads((root / 'docs/requirements.json').read_text(encoding='utf-8'))
    records, registry_sha256, error = _load_analysis(analysis_path)
    technical = {
        'R02': _correct(stats, 'original'),
        'R03': _boolean(_get(checks, 'readonly', 'passed')),
        'R04': _all(_boolean(_get(checks, 'inference', 'passed')), _correct(stats, 'corrigida')),
        'R05': _all(_boolean(_get(catalogs, 'original', 'valid')),
                    _boolean(_get(catalogs, 'corrigida', 'valid'))),
        'R06': _boolean(trace),
        'R07': _all(_boolean(_get(checks, 'data_preserved')), _correct(stats, 'corrigida'),
                    _preserved(checks, 'ontology_changed'), _preserved(checks, 'sparql_queries_changed')),
    }
    for requirement in requirements:
        rid = requirement['id']
        # Legacy metadata describes an earlier assessment, not this evaluation.
        requirement.pop('review_status', None)
        requirement['technical_status'] = 'não aplicável' if rid == 'R01' else _status(technical.get(rid))
        requirement['status'] = requirement['technical_status']
        if rid in REVIEWED_FILES:
            requirement.update(_analysis_result(rid, records, artifact_root, registry_sha256, error))
            analysis = requirement['analysis_status']
            if rid == 'R01':
                requirement['status'] = analysis
                requirement['qualification'] = (
                    'Análise da arquitetura: responsabilidades dos componentes e interfaces. '
                    + requirement['analysis_reason']
                )
            else:
                technical_status = requirement['technical_status']
                if 'não atendido' in [analysis, technical_status]:
                    requirement['status'] = 'não atendido'
                elif analysis == technical_status == 'atendido':
                    requirement['status'] = 'atendido'
                else:
                    requirement['status'] = 'não avaliado'
                requirement['qualification'] = (
                    f'Definições do domínio: {analysis}. '
                    f'Validade estrutural do catálogo nas configurações original e corrigida: {technical_status}. '
                    + requirement['analysis_reason']
                )
        elif requirement['status'] == 'atendido':
            requirement['qualification'] = {
                'R02': 'As dez respostas da configuração original correspondem às referências SQL, com conceitos associados aos dados pelos mapeamentos.',
                'R03': 'A leitura foi permitida; inserção, atualização, exclusão e alteração de estrutura foram bloqueadas.',
                'R04': 'As respostas da configuração corrigida correspondem às referências SQL; o controle sem hierarquia confirmou o efeito da inferência.',
                'R06': 'As tentativas remetem à configuração, aos arquivos utilizados e ao resultado ou erro registrado.',
                'R07': 'A correção recuperou as dez respostas, preservando os dados, a ontologia e as consultas SPARQL.',
            }.get(rid, 'Atendimento demonstrado no cenário sintético.')
        elif requirement['status'] == 'não atendido':
            requirement['qualification'] = 'Os registros indicam falha no critério técnico deste requisito.'
        else:
            requirement['qualification'] = 'Evidência técnica insuficiente para avaliar este requisito.'
    return requirements


def summarize_requirements(requirements):
    """Return machine-readable counts and the separate analysis conclusions."""
    counts = Counter(requirement['status'] for requirement in requirements)
    return {
        'total': len(requirements),
        'counts': {status: counts[status] for status in ['atendido', 'não atendido', 'não avaliado']},
        'all_requirements_met': bool(requirements) and counts['atendido'] == len(requirements),
        'analyses': {r['id']: r['analysis_status'] for r in requirements if 'analysis_status' in r},
    }
