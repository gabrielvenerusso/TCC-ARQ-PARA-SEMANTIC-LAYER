# Arquitetura de base para camadas semânticas

Protótipo do TCC de Engenharia de Software da Univille, aplicado a pedidos de venda
sintéticos. A camada semântica usa PostgreSQL, catálogo, ontologia OWL, mapeamentos
R2RML e Ontop. A avaliação compara dez questões de competência em três
configurações e gera registros JSON e um relatório HTML.

## Executar no Windows

Requisitos: Git, PowerShell 5.1 ou superior e Docker Desktop iniciado com WSL 2 e
contêineres Linux. Java, Python, PostgreSQL, Ontop e JDBC são instalados nos
contêineres.

Na raiz do repositório, confira o estado do Git e execute:

```powershell
git status --short
git log -1 --oneline
docker version
docker compose version
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_experiment.ps1
```

O script exige uma árvore limpa, incluindo arquivos ainda não versionados. Ele
constrói a imagem, executa os testes, inicia o PostgreSQL e roda a avaliação. Cada
rodada cria `evidencias/<id>-windows-compose`, com o commit testado, os resultados
e os logs. O commit que acrescenta as evidências é posterior ao commit testado.

A primeira construção precisa de rede. As imagens base são fixadas por digest,
e os downloads de Ontop e JDBC, por SHA-256. O pacote Java fixa a série 21;
`environment.json` registra a versão instalada. `Bypass` aplica-se apenas ao
processo do PowerShell, sem alterar a política do Windows.

Execute uma rodada por vez. A avaliação recria o esquema `experimento` do banco
`tcc_avaliacao`; a demonstração usa o banco separado `tcc_demo`. Se uma etapa
bloquear a execução, o script registra a etapa, o código de saída e o erro. As
questões não executadas ficam marcadas com `query_executed: false`.

## Abrir o relatório

```powershell
$rodada = (Get-Content .\evidencias\latest-windows.json -Raw -Encoding UTF8 | ConvertFrom-Json).run_id
Start-Process ".\evidencias\$rodada\relatorio.html"
docker compose run --rm --no-deps avaliador verify "evidencias/$rodada"
```

`latest-windows.json` aponta para a última rodada, inclusive em caso de bloqueio.
O comando `verify` confere os manifestos da avaliação e dos registros do Windows.
O HTML também pode ser aberto diretamente, sem Docker. A verificação pelo
contêiner depende da construção da imagem.

## Resultados registrados

A rodada de 22/11/2026,
[`20261122T213200Z-ed2a2c-windows-compose`](evidencias/20261122T213200Z-ed2a2c-windows-compose/relatorio.html),
foi executada com PowerShell 5.1 no Windows e Docker Desktop/WSL 2, sobre o commit
`c6822333f0ea47905c443763570665e094d4a220`, com árvore limpa.

Os **15 testes passaram**. As **30 tentativas** tiveram os seguintes resultados:

| Configuração | Intervenção | Resultado observado |
|---|---|---|
| A — `original` | Esquema e artefatos originais | 10 respostas corretas |
| B — `incompativel` | Renomeação de `cod_situacao` para `situacao_id`, com mapeamento e catálogo antigos | 10 bloqueios na inicialização do Ontop |
| C — `corrigida` | Mapeamento e catálogo atualizados | 10 respostas corretas |

O bloqueio de B era previsto: o mapeamento ainda referenciava `cod_situacao`.
A ontologia e as consultas permaneceram iguais nas três configurações. Também
passaram o controle de inferência, as restrições de escrita e a verificação de
preservação dos dados. Os 130 arquivos referenciados pelos manifestos foram
verificados sem divergências.

Detalhes: [resumo](evidencias/20261122T213200Z-ed2a2c-windows-compose/summary.json),
[log dos testes](evidencias/20261122T213200Z-ed2a2c-windows-compose/logs/05-tests.stderr.log),
[comandos executados](evidencias/20261122T213200Z-ed2a2c-windows-compose/execution.json) e
[auditoria de preservação](evidencias/20261122T213200Z-ed2a2c-windows-compose/preservation-audit.json).

### Revisões pendentes

R01 depende da revisão das responsabilidades e interfaces descritas em
`docs/ARQUITETURA.md`. A revisão do catálogo depende da conferência do autor sobre
termos, métricas e relações. Ambas permanecem pendentes: a presença do documento
e a validação das colunas do catálogo não concluem essas revisões.

O avaliador mantém bloqueios e erros no total de 30 tentativas. O controle
negativo de QC08 é adicional: remove apenas os axiomas de subclasse e deve
retornar `false`. O código de saída é zero quando o protocolo técnico passa;
falhas inesperadas ou rastreabilidade incompleta retornam código diferente de zero.

## Testes e avaliação por etapa

```powershell
docker compose build avaliador
docker compose run --rm --no-deps --entrypoint python avaliador -m unittest discover -s tests -v
docker compose up -d --wait postgres
docker compose run --rm -e EVIDENCE_LATEST_FILE=latest-windows.json avaliador
```

Esses comandos executam as etapas separadamente. O script `run_experiment.ps1`
reúne também os logs de preparação e registra bloqueios anteriores à avaliação.

## Demonstração

```powershell
docker compose up --build -d --wait camada
Start-Process 'http://localhost:8080'
docker compose exec camada python -m mvp list
docker compose exec camada python -m mvp query QC04
```

O endpoint SPARQL fica em `http://localhost:8080/sparql`. QC04 soma quantidade ×
valor unitário dos itens; o pedido 2 deve totalizar 36,53. A medida exclui frete,
tributos, descontos e devoluções e não equivale a faturamento contábil.

Para consultar os serviços e encerrá-los:

```powershell
docker compose ps
docker compose logs --tail 100 postgres camada
docker compose down
```

`down` mantém os dados e as evidências. As credenciais do Compose são públicas e
destinadas à demonstração local. PostgreSQL não publica porta no host, e a
interface usa somente o loopback.

## Arquivos da rodada

| Arquivo ou pasta | Conteúdo |
|---|---|
| `execution.json`, `logs/` | Etapas, comandos, saídas, erros e commit testado |
| `summary.json`, `records.json` | Resumo e as 30 tentativas |
| `expected/*.json` | Respostas SQL obtidas antes da alteração física |
| `original/`, `incompativel/`, `corrigida/` | Metadados, respostas e logs do Ontop |
| `checks.json`, `mutation.json` | Verificações e descrição da alteração física |
| `requirements.json` | Requisitos, situação técnica e revisões pendentes |
| `artifacts/` | Cópias dos artefatos avaliados |
| `manifest.json`, `host-manifest.json` | Commit e hashes para conferência da integridade |
| `environment.json` | Versões e recursos do ambiente |

Arquivos de etapas não alcançadas não são gerados. Um bloqueio anterior à
preparação do banco, por exemplo, não produz respostas SQL ou SPARQL.

## Histórico e documentação

O MVP de `MVP_Semantic_Layer_Gabriel.zip` foi integrado a
`gabrielvenerusso/TCC-ARQ-PARA-SEMANTIC-LAYER` em uma branch derivada da `main`,
preservando o histórico do repositório. Os hashes do pacote e dos arquivos
preservados constam no [registro da integração](docs/integracao_mvp.json).

A Fase 0 registra o ambiente anterior à integração. Seus arquivos e o documento
`docs/TCC 1 - Gabriel Venerusso.docx` permanecem inalterados:

- [Inventário](environment.json) e [instantâneo original](results/environment/phase0-20261121T0442371275245Z/environment.json)
- [Diagnóstico e fontes oficiais](docs/fase0_ambiente.md)
- [Pendências do capítulo registradas na Fase 0](docs/pendencias_capitulo4.md)

As rodadas Linux
[20261111T053334Z-62b9aa](evidencias/20261111T053334Z-62b9aa/relatorio.html) e
[20261111T053821Z-b22840](evidencias/20261111T053821Z-b22840/relatorio.html)
foram preservadas com seus commits de origem, relatórios e avaliações antigas de
requisitos. Ambas registram 10 respostas corretas em A, 10 bloqueios em B e 10
respostas corretas em C, em execução nativa Linux. O índice `evidencias/latest.json`
também foi preservado. A correção de R01 aplica-se ao avaliador integrado e às
novas rodadas, sem alterar os registros anteriores.

Para coletar outro inventário do Windows:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\inspect_environment.ps1
```

O coletor consulta versões e recursos, registra um novo instantâneo em
`results/environment/<id>/environment.json` e atualiza `environment.json`.
Não instala dependências, inicia serviços ou altera bancos.

Consulte a [arquitetura](docs/ARQUITETURA.md), o [roteiro de demonstração](docs/DEMONSTRACAO.md),
as [questões de competência](queries/questions.json) e a [análise do Auto-Ontology](docs/NVIDIA_AUTO_ONTOLOGY.md).
O domínio contém 10 clientes, 10 produtos, 30 pedidos e 60 itens sintéticos.
As consultas são predefinidas; não há geração automática de ontologia ou consultas
por modelos de linguagem. Os tempos registrados são diagnósticos, não um
benchmark de produção. A redação do Capítulo 4 e a revisão qualitativa pelo autor
permanecem pendentes.
