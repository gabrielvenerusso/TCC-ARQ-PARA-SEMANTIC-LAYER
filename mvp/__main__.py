"""CLI de demonstração e avaliação. python -m mvp --help"""
from __future__ import annotations

import argparse
from collections import Counter
from contextlib import contextmanager
from datetime import date, datetime, timezone
from decimal import Decimal
import hashlib
import html
import json
import os
from pathlib import Path
import platform
import re
import shutil
import signal
import subprocess
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid

import psycopg
from psycopg import sql
from psycopg.rows import dict_row
from rdflib import Graph, Namespace

ROOT = Path(__file__).resolve().parent.parent
XSD = 'http://www.w3.org/2001/XMLSchema#'
HOST = os.getenv('DB_HOST', 'postgres')
PORT = int(os.getenv('DB_PORT', '5432'))
ADMIN = os.getenv('DB_ADMIN_USER', 'tcc_admin')
PASSWORD = os.getenv('DB_ADMIN_PASSWORD', 'administracao_local')
READER_PASSWORD = os.getenv('DB_READER_PASSWORD', 'somente_leitura_local')
ONTOP = os.getenv('ONTOP_BIN', '/opt/ontop/ontop')
HTTP_PORT = int(os.getenv('ONTOP_PORT', '8080'))
EVIDENCE = Path(os.getenv('EVIDENCE_DIR', str(ROOT / 'evidencias')))


def now():
    return datetime.now(timezone.utc).isoformat()


def sanitize(value):
    text = str(value)
    for secret in [PASSWORD, READER_PASSWORD]:
        if secret:
            text = text.replace(secret, '[REDACTED]')
    return text


def dump(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2,
                               default=lambda x: str(x)) + '\n', encoding='utf-8')


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def git_info():
    def git(*args):
        p = subprocess.run(['git', '-c', f'safe.directory={ROOT}', '-C', str(ROOT), *args],
                           capture_output=True, text=True)
        return p.stdout.strip() if p.returncode == 0 else None
    return {'commit': git('rev-parse', 'HEAD'),
            'dirty': bool(git('status', '--porcelain', '--untracked-files=normal')),
            'status': git('status', '--porcelain', '--untracked-files=normal')}


def connect(db, reader=False):
    return psycopg.connect(host=HOST, port=PORT, dbname=db,
                           user='tcc_leitor' if reader else ADMIN,
                           password=READER_PASSWORD if reader else PASSWORD,
                           row_factory=dict_row, connect_timeout=10,
                           options='-c statement_timeout=15000')


def bootstrap(db, reset=False):
    if reset and db != 'tcc_avaliacao':
        raise ValueError('Reset permitido apenas no banco dedicado tcc_avaliacao.')
    with connect(db) as c:
        exists = c.execute("SELECT to_regclass('experimento.pedido') AS t").fetchone()['t']
        if exists and not reset:
            return
        if reset:
            c.execute('DROP SCHEMA IF EXISTS experimento CASCADE')
        c.execute((ROOT / 'sql/schema.sql').read_text())
        c.execute((ROOT / 'sql/seed.sql').read_text())
        c.execute(sql.SQL('REVOKE CREATE,TEMPORARY ON DATABASE {} FROM PUBLIC').format(sql.Identifier(db)))
        c.execute('REVOKE CREATE ON SCHEMA public FROM PUBLIC')


def metadata(db):
    with connect(db, True) as c:
        columns = c.execute("""SELECT table_name,column_name,data_type,is_nullable,
          numeric_precision,numeric_scale FROM information_schema.columns
          WHERE table_schema='experimento' ORDER BY table_name,ordinal_position""").fetchall()
        # pg_catalog exposes PK/FK constraints even to a SELECT-only role.
        constraints = c.execute("""SELECT r.relname AS table_name,c.conname AS name,
          c.contype AS kind,pg_get_constraintdef(c.oid) AS definition
          FROM pg_constraint c JOIN pg_class r ON r.oid=c.conrelid
          JOIN pg_namespace n ON n.oid=r.relnamespace
          WHERE n.nspname='experimento' ORDER BY r.relname,c.conname""").fetchall()
        version = c.execute('SELECT version() AS version').fetchone()['version']
        data = {}
        for table, pk in [('cliente','id_cliente'),('produto','id_produto'),('pedido','id_pedido'),('item_pedido','id_item')]:
            rows = c.execute(sql.SQL('SELECT * FROM experimento.{} ORDER BY {}').format(sql.Identifier(table), sql.Identifier(pk))).fetchall()
            data[table] = [dict((('cod_situacao' if k=='situacao_id' else k), str(v) if isinstance(v,(date,Decimal)) else v) for k,v in row.items()) for row in rows]
        return {'columns': columns, 'constraints': constraints, 'postgresql': version,
                'data': data, 'counts': {k:len(v) for k,v in data.items()},
                'data_sha256': hashlib.sha256(json.dumps(data,sort_keys=True,ensure_ascii=False).encode()).hexdigest()}


def catalog_check(cat, meta):
    available={(c['table_name'],c['column_name']) for c in meta['columns']}
    missing=sorted({f"{t['table']}.{col}" for t in cat['terms'] for col in t['columns'] if (t['table'],col) not in available})
    return {'valid': not missing, 'missing_columns': missing,
            'human_review': cat['review']['status']}


def normalize(value, datatype):
    optional=datatype.endswith('?')
    datatype=datatype.rstrip('?')
    if value is None:
        if not optional:
            raise ValueError(f'Campo obrigatório {datatype} sem valor')
        return None
    if datatype=='integer':
        if isinstance(value,bool) or Decimal(str(value)) != Decimal(str(value)).to_integral_value():
            raise ValueError(f'Inteiro inválido: {value}')
        return str(int(value))
    if datatype=='decimal':
        n=Decimal(str(value))
        if not n.is_finite():
            raise ValueError('Decimal não finito')
        return format(n.normalize(),'f')
    if datatype=='date':
        return date.fromisoformat(str(value)).isoformat()
    if datatype in ('string','iri'):
        if not isinstance(value,str):
            raise ValueError('Texto/IRI esperado')
        return value
    raise ValueError('Tipo não suportado: '+datatype)


def normalize_sql(rows, q):
    if q['kind']=='ask':
        if len(rows)!=1 or type(rows[0].get('answer')) is not bool:
            raise ValueError('Referência ASK deve retornar exatamente um booleano')
        return {'boolean': rows[0]['answer']}
    return {'fields': list(q['fields']), 'rows': [
        [normalize(row[k],t) for k,t in q['fields'].items()] for row in rows]}


def normalize_sparql(response, q):
    if q['kind']=='ask':
        if type(response.get('boolean')) is not bool:
            raise ValueError('Resposta ASK não é booleana')
        return {'boolean':response['boolean']}
    if set(response['head']['vars']) != set(q['fields']):
        raise ValueError('Colunas da resposta divergem do contrato')
    rows=[]
    integer_types={'integer','int','long','short','byte','nonNegativeInteger','positiveInteger','unsignedInt','unsignedLong'}
    for binding in response['results']['bindings']:
        if not set(binding).issubset(q['fields']):
            raise ValueError('Vínculo inesperado')
        row=[]
        for k,typ in q['fields'].items():
            v=binding.get(k)
            if v is not None:
                dt=v.get('datatype',XSD+'string').removeprefix(XSD)
                target=typ.rstrip('?')
                valid=((target=='iri' and v['type']=='uri') or
                       (v['type'] in ('literal','typed-literal') and
                        ((target=='integer' and dt in integer_types) or
                         (target=='decimal' and dt=='decimal') or
                         (target in ('date','string') and dt==target and 'xml:lang' not in v))))
                if not valid:
                    raise ValueError(f'Tipo incompatível em {k}: {v}')
            row.append(normalize(v['value'] if v is not None else None,typ))
        rows.append(row)
    return {'fields':list(q['fields']),'rows':rows}


def compare(expected, actual, ordered=False):
    if 'boolean' in expected:
        return {'correct':expected==actual}
    if expected['fields']!=actual.get('fields'):
        return {'correct':False,'reason':'fields'}
    e=Counter(tuple(r) for r in expected['rows']); a=Counter(tuple(r) for r in actual['rows'])
    return {'correct':expected['rows']==actual['rows'] if ordered else e==a,
            'missing':list((e-a).elements()),'extra':list((a-e).elements())}


def request(query, port=HTTP_PORT):
    req=urllib.request.Request(f'http://127.0.0.1:{port}/sparql',
        data=urllib.parse.urlencode({'query':query}).encode(),
        headers={'Accept':'application/sparql-results+json','Content-Type':'application/x-www-form-urlencoded'})
    try:
        with urllib.request.urlopen(req,timeout=20) as response:
            return json.load(response)
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f'HTTP {exc.code}: '+sanitize(exc.read().decode(errors='replace'))) from exc


@contextmanager
def endpoint(db, mapping, logpath, ontology='ontology/vendas.ttl'):
    logpath=Path(logpath);logpath.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='tcc-ontop-') as temp:
        props=Path(temp)/'jdbc.properties'
        # Password is deliberately excluded from CLI arguments and evidence.
        props.write_text(f'jdbc.url=jdbc:postgresql://{HOST}:{PORT}/{db}\njdbc.user=tcc_leitor\njdbc.password={READER_PASSWORD}\njdbc.driver=org.postgresql.Driver\n')
        props.chmod(0o600)
        cmd=[ONTOP,'endpoint','--ontology',str(ROOT/ontology),'--mapping',str(ROOT/mapping),
             '--properties',str(props),'--port',str(HTTP_PORT),'--cors-allowed-origins','http://localhost:8080']
        env=os.environ.copy();env['ONTOP_LOG_LEVEL']='WARN'
        proc=None
        with logpath.open('w',encoding='utf-8') as log:
            try:
                proc=subprocess.Popen(cmd,stdout=log,stderr=subprocess.STDOUT,env=env,start_new_session=True)
                deadline=time.monotonic()+90;error=None;ready=False
                while time.monotonic()<deadline:
                    if proc.poll() is not None:
                        error=f'Ontop encerrou na inicialização (código {proc.returncode}); consultar startup.log.'
                        break
                    try:
                        request('ASK {}');ready=True;break
                    except Exception:
                        time.sleep(0.3)
                if not ready and not error:
                    error='Tempo limite de 90 s na inicialização do Ontop.'
                yield {'ready':ready,'error':error,'pid':proc.pid}
            finally:
                if proc and proc.poll() is None:
                    os.killpg(proc.pid,signal.SIGTERM)
                    try: proc.wait(timeout=8)
                    except subprocess.TimeoutExpired:
                        os.killpg(proc.pid,signal.SIGKILL);proc.wait(timeout=5)
        logpath.write_text(sanitize(logpath.read_text(errors='replace')),encoding='utf-8')


def readonly_check(db):
    results={}
    with connect(db,True) as c:
        results['select_count']=c.execute('SELECT COUNT(*) AS n FROM experimento.pedido').fetchone()['n']
        for name,statement in {
            'insert':"INSERT INTO experimento.cliente VALUES (999,'Teste',NULL)",
            'update':"UPDATE experimento.cliente SET nome='Teste' WHERE id_cliente=1",
            'delete':'DELETE FROM experimento.item_pedido WHERE id_item=1',
            'ddl':'ALTER TABLE experimento.pedido ADD COLUMN intrusao INTEGER'}.items():
            try:
                with c.transaction(force_rollback=True):
                    c.execute(statement)
                results[name]={'blocked':False}
            except psycopg.errors.InsufficientPrivilege as e:
                results[name]={'blocked':True,'sqlstate':e.sqlstate}
    results['passed']=results['select_count']==30 and all(results[x]['blocked'] for x in ['insert','update','delete','ddl'])
    return results


def environment(db):
    def output(cmd):
        p=subprocess.run(cmd,text=True,capture_output=True,timeout=30)
        return sanitize((p.stdout+p.stderr).strip())
    return {'timestamp':now(),'python':platform.python_version(),'os':platform.platform(),
            'machine':platform.machine(),'cpu':platform.processor(), 'cpu_count':os.cpu_count(),
            'memory_bytes':os.sysconf('SC_PAGE_SIZE')*os.sysconf('SC_PHYS_PAGES') if hasattr(os,'sysconf') else None,
            'java':output(['java','-version']),'ontop':output([ONTOP,'--version']),
            'jdbc':{'version':'42.7.8','sha256':digest(Path(ONTOP).parent/'jdbc/postgresql-42.7.8.jar')},
            'git_version':output(['git','--version']),
            'rdflib_version':__import__('rdflib').__version__,
            'resources_note':'Recursos visíveis ao processo; podem refletir limites do ambiente virtual.',
            'psycopg':psycopg.__version__,'database':db,
            'runtime_mode':os.getenv('MVP_RUNTIME_MODE','native')}


def mutation_details():
    rr=Namespace('http://www.w3.org/ns/r2rml#')
    def queries(path):
        g=Graph().parse(ROOT/path,format='turtle')
        return {str(m):str(g.value(t,rr.sqlQuery)) for m,t in g.subject_objects(rr.logicalTable)}
    old=queries('mappings/original.ttl');new=queries('mappings/corrigido.ttl')
    return {'change':'pedido.cod_situacao → pedido.situacao_id','logical_files_updated':2,
            'files':['mappings/original.ttl → mappings/corrigido.ttl','catalog/original.json → catalog/corrigido.json'],
            'mapping_rules_changed':[k for k in old if old[k]!=new[k]],
            'ontology_changed':False,'sparql_queries_changed':False,
            'note':'As versões antiga e nova são preservadas em arquivos distintos; atualização manual.'}


def requirement_results(stats, checks, catalogs, trace):
    """Technical evidence does not approve the researcher's qualitative reviews."""
    requirements=json.loads((ROOT/'docs/requirements.json').read_text(encoding='utf-8'))
    technical={'R02':stats['original']['correct']==10,'R03':checks['readonly']['passed'],
        'R04':checks['inference']['passed'] and stats['corrigida']['correct']==10,
        'R05':catalogs['corrigida']['valid'],'R06':trace,
        'R07':checks['data_preserved'] and stats['corrigida']['correct']==10}
    for requirement in requirements:
        rid=requirement['id']
        requirement['technical_status']=(
            'não aplicável' if rid=='R01' else 'atendido' if technical[rid] else 'não atendido')
        requirement['status']=requirement['technical_status']
        requirement['qualification']='Resultado técnico preliminar; revisão qualitativa pelo pesquisador pendente.'
        if rid=='R01':
            requirement['status']='pendente_revisao_humana'
            requirement['qualification']='A existência do documento não comprova a revisão das responsabilidades e interfaces pelo pesquisador.'
        elif rid=='R05':
            requirement['status']='pendente_revisao_humana'
            requirement['qualification']='A verificação estrutural do catálogo não substitui a conferência das definições pelo pesquisador.'
    return requirements


def evidence_filename(value, variable):
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]{0,99}',value):
        raise ValueError(f'{variable} deve ser um nome simples com até 100 caracteres.')
    return value


def save_run(folder, git, summary, records, requirements):
    dump(folder/'requirements.json',requirements);dump(folder/'summary.json',summary)
    render_report(folder,summary,records)
    files={str(p.relative_to(folder)):digest(p) for p in sorted(folder.rglob('*')) if p.is_file()}
    dump(folder/'manifest.json',{'run_id':folder.name,'git':git,'files_sha256':files})
    latest=evidence_filename(os.getenv('EVIDENCE_LATEST_FILE','latest.json'),'EVIDENCE_LATEST_FILE')
    dump(EVIDENCE/latest,{'run_id':folder.name,'report':str(folder/'relatorio.html'),'summary':summary})


def verify_evidence(folder):
    folder=Path(folder)
    manifests=['manifest.json']
    if (folder/'host-manifest.json').is_file():
        manifests.append('host-manifest.json')
    files=set();invalid=set()
    for name in manifests:
        manifest=json.loads((folder/name).read_text(encoding='utf-8'))
        for relative,expected in manifest['files_sha256'].items():
            files.add(relative)
            if not (folder/relative).is_file() or digest(folder/relative)!=expected:
                invalid.add(relative)
    return {'files':len(files),'invalid':sorted(invalid),'valid':not invalid,'manifests':manifests}


def blocked_bootstrap(folder, git, questions, error):
    """Preserve planned attempts when PostgreSQL preparation cannot complete."""
    message=sanitize(error)
    dump(folder/'failure.json',{'timestamp':now(),'phase':'bootstrap','error':message})
    (folder/'bootstrap.log').write_text(message+'\n',encoding='utf-8')
    records=[{'execution_id':f'{configuration}-{q["id"]}','question_id':q['id'],
        'configuration':configuration,'timestamp':now(),'git_commit':git['commit'],
        'status':'blocked','phase':'bootstrap','error':message,'query_executed':False,
        'startup_log':'bootstrap.log'}
        for configuration in ['original','incompativel','corrigida'] for q in questions]
    dump(folder/'records.json',records)
    dump(folder/'checks.json',{'status':'not_executed','phase':'bootstrap','error':message})
    requirements=json.loads((ROOT/'docs/requirements.json').read_text(encoding='utf-8'))
    for requirement in requirements:
        requirement['technical_status']='não executado'
        requirement['status']=('pendente_revisao_humana' if requirement['id'] in ['R01','R05'] else 'não avaliado')
        requirement['qualification']='Preparação do banco bloqueada; nenhuma consulta executada. Revisões humanas continuam pendentes.'
    summary={'timestamp':now(),'run_id':folder.name,'configurations':{
        name:{'total':len(questions),'correct':0,'incorrect':0,'blocked':len(questions),'error':0}
        for name in ['original','incompativel','corrigida']},'attempts':len(records),
        'queries_executed':0,'git':git,'traceability_complete':False,'protocol_passed':False,
        'human_review':'pendente_revisao_humana','phase':'bootstrap','error':message,
        'scope':'Rodada bloqueada antes das consultas; registros representam tentativas planejadas.'}
    save_run(folder,git,summary,records,requirements)
    print(f'Bloqueio na preparação do banco: {message}\nRelatório: {folder / "relatorio.html"}',flush=True)
    return 2


def render_report(folder, summary, records):
    esc=lambda s:html.escape(str(s))
    rows=''.join(f'<tr><td>{esc(r["configuration"])}</td><td>{esc(r["question_id"])}</td><td>{esc(r["status"])}</td><td>{esc(r.get("error", ""))}</td></tr>' for r in records)
    cards=''.join(f'<div class="card"><b>{esc(k)}</b><strong>{v["correct"]}/{v["total"]}</strong><span>respostas corretas · {v["blocked"]} bloqueadas</span></div>' for k,v in summary['configurations'].items())
    (folder/'relatorio.html').write_text(f'''<!doctype html><html lang="pt-BR"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Avaliação — camada semântica</title><style>body{{font:16px system-ui;background:#f3f6fa;color:#14273d;margin:0}}main{{max-width:1100px;margin:auto;padding:40px 24px}}h1{{font-size:32px}}.cards{{display:flex;gap:16px;flex-wrap:wrap}}.card{{background:white;padding:24px;border-radius:12px;flex:1;min-width:220px}}strong{{display:block;font-size:40px;color:#135e76;margin:12px 0}}span{{font-size:14px}}table{{border-collapse:collapse;width:100%;background:white}}th,td{{padding:12px;text-align:left;border-bottom:1px solid #dde4eb}}td:last-child{{font-size:13px}}code{{overflow-wrap:anywhere}}a{{color:#135e76}}.note{{border-left:4px solid #d89221;padding:16px;background:#fff5df}}</style><main><p>TCC · DOMÍNIO SINTÉTICO DE PEDIDOS</p><h1>Camada semântica: resultados da avaliação</h1><p>Rodada <code>{esc(folder.name)}</code> · {esc(summary['timestamp'])}</p><div class="cards">{cards}</div><p class="note">A configuração incompatível contém uma falha deliberada. Bloqueios são mantidos no denominador. Esta avaliação técnica não mede desempenho em produção nem substitui revisão humana das definições.</p><p class="note"><b>Revisões humanas:</b> R01: revisão das responsabilidades e interfaces pendente. R05: conferência do catálogo pendente. O resultado técnico não aprova essas revisões.</p><p>Veredito do protocolo técnico: <b>{esc(summary['protocol_passed'])}</b> · Rastreabilidade completa: <b>{esc(summary['traceability_complete'])}</b> · Commit: <code>{esc(summary['git']['commit'])}</code></p><p><a href="summary.json">Resumo JSON</a> · <a href="checks.json">Verificações</a> · <a href="manifest.json">Manifesto e hashes</a> · <a href="records.json">Registros completos</a> · <a href="requirements.json">Matriz de requisitos</a></p><h2>As 30 tentativas</h2><table><thead><tr><th>Configuração</th><th>Questão</th><th>Resultado</th><th>Observação</th></tr></thead><tbody>{rows}</tbody></table></main></html>''',encoding='utf-8')


def evaluate():
    db='tcc_avaliacao'
    run_id=os.getenv('EVIDENCE_RUN_ID') or datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'-'+uuid.uuid4().hex[:6]
    evidence_filename(run_id,'EVIDENCE_RUN_ID')
    evidence_filename(os.getenv('EVIDENCE_LATEST_FILE','latest.json'),'EVIDENCE_LATEST_FILE')
    # Capture the source state before creating any evidence or generated files.
    git=git_info()
    folder=EVIDENCE/run_id;folder.mkdir(parents=True)
    questions=json.loads((ROOT/'queries/questions.json').read_text(encoding='utf-8'))
    try:
        bootstrap(db,reset=True)
    except Exception as exc:
        return blocked_bootstrap(folder,git,questions,exc)
    dump(folder/'environment.json',environment(db))
    # Snapshot all study artifacts before the first query.
    for directory in ['ontology','mappings','catalog','queries','sql','docs']:
        shutil.copytree(ROOT/directory,folder/'artifacts'/directory)
    expected={}
    with connect(db,True) as c:
        for q in questions:
            result=c.execute((ROOT/q['sql_reference']).read_text()).fetchall()
            expected[q['id']]=normalize_sql(result,q)
            dump(folder/'expected'/f'{q["id"]}.json',expected[q['id']])
    meta0=metadata(db)
    fixtures={'counts':meta0['counts']=={'cliente':10,'produto':10,'pedido':30,'item_pedido':60},
        'order_2_total': ['2','36.53'] in expected['QC04']['rows'],
        'clients_without_orders': sorted(expected['QC06']['rows'])==[['10'],['9']],
        'duplicates_preserved': expected['QC10']['rows']==[['2'],['2']],
        'empty_result': expected['QC09']['rows']==[],
        'nullable_city': sum(r[1] is None for r in expected['QC07']['rows'])==2}
    checks={'readonly':readonly_check(db),'fixtures':fixtures}
    records=[];stats={};catalogs={};fingerprints=[]
    stages=[('original','mappings/original.ttl','catalog/original.json'),
            ('incompativel','mappings/original.ttl','catalog/original.json'),
            ('corrigida','mappings/corrigido.ttl','catalog/corrigido.json')]
    for name,mapping,catalog in stages:
        if name=='incompativel':
            with connect(db) as c:c.execute((ROOT/'sql/mutate.sql').read_text())
        meta=metadata(db);fingerprints.append(meta['data_sha256']);dump(folder/name/'metadata.json',meta)
        catalogs[name]=catalog_check(json.loads((ROOT/catalog).read_text()),meta)
        print(f'[{name}] Inicializando Ontop...',flush=True)
        with endpoint(db,mapping,folder/name/'startup.log') as ep:
            for q in questions:
                rid=f'{name}-{q["id"]}';qr=(ROOT/q['sparql']).read_text()
                rec={'execution_id':rid,'question_id':q['id'],'requirements':q['requirements'],
                     'mapping_ids':q['mapping_ids'],'configuration':name,'timestamp':now(),
                     'git_commit':git['commit'],'data_sha256':meta['data_sha256'],
                     'artifacts':{'ontology':'artifacts/ontology/vendas.ttl','mapping':'artifacts/'+mapping,
                                  'catalog':'artifacts/'+catalog,'query':'artifacts/'+q['sparql'],
                                  'sql_reference':'artifacts/'+q['sql_reference'],'schema':f'{name}/metadata.json'},
                     'expected':f'expected/{q["id"]}.json','startup_log':f'{name}/startup.log'}
                start=time.monotonic()
                if not ep['ready']:
                    rec.update(status='blocked',error=ep['error'],phase='startup',query_executed=False)
                else:
                    rec['query_executed']=True
                    try:
                        raw=request(qr);out=f'{name}/{q["id"]}.raw.json';dump(folder/out,raw)
                        actual=normalize_sparql(raw,q);norm=f'{name}/{q["id"]}.normalized.json';dump(folder/norm,actual)
                        comparison=compare(expected[q['id']],actual,q['ordered'])
                        rec.update(status='correct' if comparison['correct'] else 'incorrect',
                                   result=out,normalized=norm,comparison=comparison)
                    except Exception as exc:
                        rec.update(status='error',error=sanitize(exc),phase='query')
                rec['duration_ms']=round((time.monotonic()-start)*1000,3);records.append(rec)
                dump(folder/'records.json',records)
        selected=[r for r in records if r['configuration']==name]
        stats[name]={'total':len(selected),**{s:sum(r['status']==s for r in selected) for s in ['correct','incorrect','blocked','error']}}
        print(f'[{name}] {stats[name]}',flush=True)
    # Negative control: remove ONLY subclass axioms; preserve mapping and query.
    with endpoint(db,'mappings/corrigido.ttl',folder/'negative_control/startup.log','ontology/sem_hierarquia.ttl') as ep:
        raw=request((ROOT/'queries/sparql/QC08.rq').read_text()) if ep['ready'] else {'error':ep['error']}
        dump(folder/'negative_control/QC08.raw.json',raw)
        checks['inference']={'with_hierarchy':expected['QC08']['boolean'],
                             'without_hierarchy':raw.get('boolean'),
                             'passed':raw.get('boolean') is False and any(r['configuration']=='corrigida' and r['question_id']=='QC08' and r['status']=='correct' for r in records)}
    checks['catalog']=catalogs
    checks['data_preserved']=len(set(fingerprints))==1
    dump(folder/'checks.json',checks);dump(folder/'mutation.json',mutation_details())
    files={str(p.relative_to(folder)):digest(p) for p in sorted(folder.rglob('*')) if p.is_file()}
    trace=bool(git['commit']) and not git['dirty'] and len(records)==30 and all(
        all(path in files for path in [r['expected'],r['startup_log'],*r['artifacts'].values()]) and
        (r.get('result') in files if r['status'] in ('correct','incorrect') else bool(r.get('error')))
        for r in records)
    passed=(stats['original']['correct']==10 and stats['corrigida']['correct']==10 and
            stats['incompativel']['correct']<10 and len(records)==30 and trace and
            checks['readonly']['passed'] and checks['inference']['passed'] and
            all(fixtures.values()) and checks['data_preserved'] and
            catalogs['original']['valid'] and not catalogs['incompativel']['valid'] and catalogs['corrigida']['valid'])
    summary={'timestamp':now(),'run_id':run_id,'configurations':stats,'attempts':30,
             'git':git,'traceability_complete':trace,'protocol_passed':passed,
             'human_review':'pendente_revisao_humana','scope':'Verificação técnica preliminar em domínio sintético; não é validação científica definitiva.'}
    requirements=requirement_results(stats,checks,catalogs,trace)
    save_run(folder,git,summary,records,requirements)
    print(f'Relatório: {folder / "relatorio.html"}\nProtocolo atendido: {passed}',flush=True)
    return 0 if passed else 1


def serve():
    bootstrap('tcc_demo')
    log=Path(tempfile.gettempdir())/'tcc-demo-ontop.log'
    with endpoint('tcc_demo','mappings/original.ttl',log) as ep:
        if not ep['ready']:
            print(sanitize(log.read_text()));raise RuntimeError(ep['error'])
        print('Demonstração: http://localhost:8080 — endpoint /sparql',flush=True)
        while True:
            time.sleep(1)
            try:os.kill(ep['pid'],0)
            except ProcessLookupError:raise RuntimeError('Ontop foi encerrado')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',choices=['serve','evaluate','list','query','verify'])
    parser.add_argument('question',nargs='?',help='QC01 ... QC10 (comando query)')
    args=parser.parse_args()
    if args.command=='serve':serve();return 0
    if args.command=='evaluate':return evaluate()
    if args.command=='verify':
        if not args.question:parser.error('Informe a pasta da rodada em evidencias/.')
        result=verify_evidence(args.question)
        print(json.dumps(result,indent=2))
        return int(not result['valid'])
    questions=json.loads((ROOT/'queries/questions.json').read_text())
    if args.command=='list':
        for q in questions:print(q['id'],q['question'])
        return 0
    q=next((q for q in questions if q['id']==args.question),None)
    if q is None:parser.error('Informe um identificador entre QC01 e QC10.')
    print(json.dumps(request((ROOT/q['sparql']).read_text()),ensure_ascii=False,indent=2))
    return 0


if __name__=='__main__':
    try:raise SystemExit(main())
    except KeyboardInterrupt:raise SystemExit(130)
    except Exception as e:
        print('Falha: '+sanitize(e),flush=True);raise SystemExit(2)
