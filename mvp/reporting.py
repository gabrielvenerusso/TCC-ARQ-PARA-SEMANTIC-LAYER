"""Readable reports derived from recorded results and versioned analyses."""
from __future__ import annotations

import html
import json
from pathlib import Path

from mvp.analysis import summarize_requirements


def render_report(folder, summary, records, requirements=None, *, source_prefix='.', mutation=None):
    folder = Path(folder)
    if requirements is None:
        requirements = json.loads((folder/'requirements.json').read_text(encoding='utf-8'))
    esc = lambda value: html.escape(str(value), quote=True)
    labels = {'original': 'A — esquema original', 'incompativel': 'B — esquema alterado',
              'corrigida': 'C — artefatos corrigidos'}
    status_labels = {'correct': 'correta', 'incorrect': 'incorreta', 'blocked': 'bloqueada', 'error': 'erro'}
    cards = ''.join(
        f'<section class="card"><h2>{esc(labels.get(name, name))}</h2>'
        f'<strong>{values["correct"]}/{values["total"]}</strong><p>respostas corretas</p>'
        f'<p>{values["blocked"]} bloqueadas · {values["incorrect"]} incorretas · {values["error"]} erros</p></section>'
        for name, values in summary['configurations'].items())
    overview = summarize_requirements(requirements)
    coverage = (f'{overview["counts"]["atendido"]} de {overview["total"]} requisitos atendidos'
                f' no cenário sintético; {overview["counts"]["não atendido"]} não atendidos'
                f' e {overview["counts"]["não avaliado"]} não avaliados.')
    def explanation(requirement):
        if requirement.get('analysis_status') == 'atendido':
            if requirement['id'] == 'R01':
                return 'A análise da arquitetura identificou as responsabilidades dos componentes, suas entradas, saídas e interfaces de comunicação.'
            if requirement['id'] == 'R05':
                return ('As definições do domínio abrangem termos, relações e a fórmula do total do pedido. '
                        'Validade estrutural do catálogo nas configurações original e corrigida: '
                        + requirement['technical_status'] + '.')
        return requirement['qualification']
    requirement_rows = ''.join(
        f'<tr><th scope="row">{esc(r["description"])}</th><td>{esc(r["status"])}</td>'
        f'<td>{esc(explanation(r))}</td></tr>' for r in requirements)
    attempts = ''.join(
        f'<tr><td>{esc(labels.get(r["configuration"], r["configuration"]))}</td>'
        f'<td>{esc(r["question_id"])}</td><td>{esc(status_labels.get(r["status"], r["status"]))}</td>'
        f'<td>{esc(r.get("error", ""))}</td></tr>' for r in records)
    startup_blocks = [r for r in records if r['configuration'] == 'incompativel'
                      and r['status'] == 'blocked' and r.get('phase') == 'startup']
    paragraphs = []
    if summary.get('analysis_only'):
        paragraphs.append('Esta análise final utiliza a execução documentada. A consolidação documental não executou novas consultas e preservou os registros históricos.')
    if startup_blocks:
        paragraphs.append(
            f'Na configuração B, {len(startup_blocks)} tentativas foram bloqueadas na inicialização do Ontop. '
            'Os registros de erro devem ser considerados junto à alteração de esquema: '
            'as consultas bloqueadas não chegaram a ser enviadas ao serviço.')
    if summary.get('controlled_schema_block'):
        paragraphs.append('O mapeamento ainda referenciava o nome antigo da coluna renomeada. '
                          'A incompatibilidade impediu a inicialização do serviço, inclusive para consultas que não dependiam diretamente dessa coluna.')
    if mutation:
        if mutation.get('ontology_changed') is False and mutation.get('sparql_queries_changed') is False:
            paragraphs.append(
                f'Foram alteradas {len(mutation.get("mapping_rules_changed", []))} regras de mapeamento e as referências físicas do catálogo. '
                'A ontologia e as consultas SPARQL foram preservadas.')
    if summary.get('error'):
        paragraphs.append('Bloqueio da execução: ' + str(summary['error']))
    tests = summary.get('recorded_tests')
    if tests:
        paragraphs.append(f'Na execução original, os {tests["count"]} testes automatizados foram {tests["result"]}.')
    paragraphs.append('As tentativas bloqueadas e os erros permanecem no total. '
                      'A análise da arquitetura examina responsabilidades e interfaces; a análise das definições do domínio examina termos, relações e fórmulas. '
                      'Esses exames complementam os testes de funcionamento.')
    body = ''.join(f'<p>{esc(p)}</p>' for p in paragraphs)
    warnings = ''.join(f'<p class="notice">{esc(d)}</p>' for d in summary.get('discrepancies', []))
    def source_link(name, label):
        return f'<a href="{esc(source_prefix + "/" + name)}">{esc(label)}</a>'
    links = ' · '.join(source_link(name, label) for name, label in [
        ('records.json', 'Tentativas originais'), ('checks.json', 'Verificações de funcionamento'),
        ('manifest.json', 'Manifesto original')])
    documentary_links = ('<a href="source.json">Vínculo com a execução</a> · '
                         '<a href="analises.json">Análises e hashes dos componentes</a> · '
                         '<a href="criteria.json">Critérios utilizados</a> · ') if summary.get('analysis_only') else ''
    protocol = 'atendido' if summary.get('protocol_passed') else 'não atendido'
    trace = 'completa' if summary.get('traceability_complete') else 'incompleta ou não verificada'
    page = f'''<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Resultados e atendimento aos requisitos — camada semântica</title>
<style>
body{{font:16px/1.65 system-ui,sans-serif;color:#1c3043;background:#f5f7f9;margin:0}}
main{{max-width:1120px;margin:auto;padding:36px 24px 64px}}h1{{font-size:2rem;line-height:1.25}}
h2{{font-size:1.3rem;line-height:1.4}}.eyebrow{{font-size:.85rem;letter-spacing:.08em}}
.cards{{display:flex;gap:16px;flex-wrap:wrap;margin:28px 0}}.card{{background:white;padding:20px;flex:1;min-width:230px;border:1px solid #d7e0e8;border-radius:8px}}
.card h2{{font-size:1rem}}.card p{{margin:4px 0}}.card strong{{font-size:2.6rem;color:#135e76}}
table{{border-collapse:collapse;width:100%;background:white}}th,td{{padding:12px;text-align:left;vertical-align:top;border:1px solid #d7e0e8}}
thead{{background:#e5edf3}}tbody th{{font-weight:500}}.table-wrap{{overflow-x:auto}}
a{{color:#135e76}}details{{margin-top:28px;border-top:1px solid #bccad6;padding-top:16px}}summary{{cursor:pointer;font-weight:600}}
code{{overflow-wrap:anywhere}}.notice{{border-left:4px solid #9c5d00;padding:12px;background:#fff5df}}
@media(max-width:640px){{main{{padding:24px 14px}}h1{{font-size:1.6rem}}th,td{{padding:8px}}}}
</style></head><body><main>
<p class="eyebrow">TCC · PEDIDOS DE VENDA</p>
<h1>Resultados e atendimento aos requisitos</h1>
<p>O protótipo relaciona conceitos de pedidos de venda a dados no PostgreSQL por meio de ontologia OWL, mapeamentos R2RML, catálogo e Ontop. A avaliação compara dez questões de competência com referências SQL independentes em três configurações.</p>
<div class="cards">{cards}</div>{body}{warnings}
<p>Protocolo técnico: <b>{protocol}</b>. Rastreabilidade das {len(records)} tentativas: <b>{trace}</b>.</p>
<h2>Atendimento aos requisitos</h2><p>{esc(coverage)}</p>
<div class="table-wrap"><table><thead><tr><th>Requisito</th><th>Resultado</th><th>Fundamento</th></tr></thead><tbody>{requirement_rows}</tbody></table></div>
<h2>Limitações</h2>
<p>O estudo utiliza um domínio sintético, com 10 clientes, 10 produtos, 30 pedidos e 60 itens, e uma única alteração de esquema. Não houve avaliação em produção. Os tempos registrados servem ao diagnóstico e não constituem um estudo de desempenho. A rastreabilidade relaciona tentativas e arquivos, sem identificar a origem individual de cada valor retornado.</p>
<p>As conclusões da análise se aplicam somente às versões registradas. A ausência de análise suficiente ou a alteração dos arquivos exige novo exame da versão correspondente. Uma falha estrutural do catálogo continua visível mesmo quando suas definições foram analisadas.</p>
<details><summary>Registros técnicos e integridade</summary>
<p>Execução de origem: <code>{esc(summary["run_id"])}</code><br>Data registrada na execução: {esc(summary["timestamp"])}<br>Commit executado: <code>{esc(summary.get("git", {}).get("commit"))}</code></p>
<p>{documentary_links}<a href="summary.json">Resumo da análise</a> · <a href="requirements.json">Matriz detalhada</a> · <a href="manifest.json">Integridade deste relatório</a> · {links}</p>
<h2>Registro das {len(records)} tentativas</h2>
<div class="table-wrap"><table><thead><tr><th>Configuração</th><th>Questão</th><th>Resultado</th><th>Observação</th></tr></thead><tbody>{attempts}</tbody></table></div>
</details></main></body></html>'''
    (folder/'relatorio.html').write_text(page, encoding='utf-8')
