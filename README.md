# Arquitetura de base para camadas semânticas

Protótipo do TCC de Engenharia de Software da Univille, aplicado a pedidos de venda
sintéticos. A camada semântica usa PostgreSQL, catálogo, ontologia OWL, mapeamentos
R2RML e Ontop. A avaliação compara dez questões de competência em três
configurações e gera registros JSON e um relatório HTML.

O [relatório final](docs/analise-final/relatorio.html) reúne os resultados da
execução documentada e a análise do atendimento aos requisitos. A análise final
foi registrada separadamente, sem repetir as consultas ou alterar as evidências
da execução original.

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

Abra o [relatório final](docs/analise-final/relatorio.html) diretamente no navegador:

```powershell
Start-Process '.\docs\analise-final\relatorio.html'
```

O relatório apresenta os resultados, a explicação dos bloqueios, o atendimento
aos requisitos e as limitações. Os registros técnicos vinculam a análise à
execução original e preservam versões e informações de integridade.

Para conferir os arquivos da análise e da execução documentada:

```powershell
python -m mvp verify docs/analise-final
$rodada = (Get-Content .\evidencias\latest-windows.json -Raw -Encoding UTF8 | ConvertFrom-Json).run_id
python -m mvp verify "evidencias/$rodada"
```

`latest-windows.json` aponta para a última rodada, inclusive em caso de bloqueio.
O comando `verify` confere os manifestos da avaliação e dos registros do Windows.
Os comandos Python exigem as dependências de `requirements.txt`. Também podem ser
executados no contêiner com `docker compose run --rm --no-deps avaliador verify`
seguido da pasta desejada, após construir a imagem atual.

Para produzir outra análise documental a partir de uma execução existente, use
uma pasta de saída nova:

```powershell
python -m mvp analyze "evidencias/$rodada" --output docs/nova-analise
```

Esse comando lê os registros existentes e as análises das versões correspondentes;
não inicia o banco nem executa consultas. A pasta da execução original permanece
preservada.

## Resultados registrados

A [execução documentada de 22/11/2026](evidencias/20261122T213200Z-ed2a2c-windows-compose/relatorio.html)
foi realizada no Windows com PowerShell e Docker Desktop/WSL 2. As respostas das
dez questões de competência foram comparadas com referências SQL obtidas antes
da alteração do esquema.

Os **15 testes passaram**. As **30 tentativas** tiveram os seguintes resultados:

| Configuração | Intervenção | Resultado observado |
|---|---|---|
| A | Esquema e artefatos originais | 10 respostas corretas em 10 questões |
| B | Coluna renomeada, com mapeamento e catálogo antigos | 10 tentativas bloqueadas na inicialização do Ontop |
| C | Mapeamento e catálogo corrigidos | 10 respostas corretas em 10 questões |

O bloqueio de B ocorreu porque o mapeamento ainda referenciava o nome antigo da
coluna. As consultas dessa configuração não chegaram a ser executadas. A correção
alterou três regras de mapeamento e a correspondência física do catálogo. A
ontologia e as consultas SPARQL permaneceram iguais nas três configurações.
Também passaram o controle de inferência, as restrições de escrita e a verificação
de preservação dos dados. As 30 tentativas possuem rastreabilidade. Os 130 arquivos
referenciados pelos manifestos foram verificados sem divergências.

Detalhes: [resumo](evidencias/20261122T213200Z-ed2a2c-windows-compose/summary.json),
[log dos testes](evidencias/20261122T213200Z-ed2a2c-windows-compose/logs/05-tests.stderr.log),
[comandos executados](evidencias/20261122T213200Z-ed2a2c-windows-compose/execution.json) e
[auditoria de preservação](evidencias/20261122T213200Z-ed2a2c-windows-compose/preservation-audit.json).

### Atendimento aos requisitos

Os sete requisitos foram considerados atendidos no cenário sintético. A análise
da arquitetura examina as responsabilidades dos componentes e suas interfaces.
A análise das definições do domínio examina os termos, as relações e a fórmula
do total do pedido. Esses exames são distintos dos testes de funcionamento.

Os critérios e arquivos constam na [matriz de requisitos](docs/requirements.json)
e no [registro de análises](docs/analises.json). Cada conclusão se aplica somente
aos arquivos com os hashes registrados. Alterações exigem nova análise da versão
correspondente; a ausência de análise suficiente mantém o requisito não avaliado.
Para o catálogo, uma falha estrutural continua a impedir o atendimento mesmo
quando suas definições já foram analisadas.

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
| `requirements.json` | Situação dos requisitos registrada naquela execução |
| `artifacts/` | Cópias dos artefatos avaliados |
| `manifest.json`, `host-manifest.json` | Commit e hashes para conferência da integridade |
| `environment.json` | Versões e recursos do ambiente |

Arquivos de etapas não alcançadas não são gerados. Um bloqueio anterior à
preparação do banco, por exemplo, não produz respostas SQL ou SPARQL.

A pasta `docs/analise-final/` contém a análise final em arquivos separados. Seu
`source.json` identifica a execução original; `summary.json` e `requirements.json`
apresentam a consolidação; `manifest.json` permite conferir a integridade. Os
registros históricos mantêm a situação dos requisitos que havia sido registrada
na época.

## Histórico e documentação

O MVP de `MVP_Semantic_Layer_Gabriel.zip` foi integrado a
`gabrielvenerusso/TCC-ARQ-PARA-SEMANTIC-LAYER` em uma branch derivada da `main`,
preservando o histórico do repositório. Os hashes do pacote e dos arquivos
preservados constam no [registro da integração](docs/integracao_mvp.json).

A Fase 0 registra o ambiente anterior à integração. Seus diagnósticos e pendências
são documentos históricos e não descrevem a situação atual do MVP. Esses arquivos
permanecem inalterados:

- [Inventário](environment.json) e [instantâneo original](results/environment/phase0-20261121T0442371275245Z/environment.json)
- [Diagnóstico histórico e fontes oficiais — Fase 0](docs/fase0_ambiente.md)
- [Pendências históricas do capítulo — Fase 0](docs/pendencias_capitulo4.md)

A [cópia de leitura do TCC revisado](docs/TCC_1_Gabriel_Venerusso_Revisado.docx)
reproduz integralmente o DOCX fornecido. O documento anterior em
`docs/TCC 1 - Gabriel Venerusso.docx` e as cópias preservadas nas evidências
permanecem como registros históricos.

As rodadas Linux
[20261111T053334Z-62b9aa](evidencias/20261111T053334Z-62b9aa/relatorio.html) e
[20261111T053821Z-b22840](evidencias/20261111T053821Z-b22840/relatorio.html)
foram preservadas com seus commits de origem, relatórios e avaliações antigas de
requisitos. Ambas registram 10 respostas corretas em A, 10 bloqueios em B e 10
respostas corretas em C, em execução nativa Linux. O índice `evidencias/latest.json`
também foi preservado. A análise final está vinculada à execução Windows e às
versões explicitamente examinadas, sem alterar as avaliações históricas ou
transferir automaticamente suas conclusões a versões posteriores.

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
por modelos de linguagem. O pequeno volume de dados, o domínio sintético e o
estudo de uma única alteração de esquema limitam os resultados. Não houve
avaliação em produção; os tempos registrados servem ao diagnóstico da execução.
