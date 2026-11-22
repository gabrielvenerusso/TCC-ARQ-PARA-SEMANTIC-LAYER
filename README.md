# Arquitetura de base para camadas semânticas

MVP do TCC de Engenharia de Software da Univille, no domínio sintético de
pedidos de venda: PostgreSQL, catálogo, ontologia OWL, mapeamentos R2RML e
Ontop. O avaliador compara dez questões de competência em três configurações
e produz registros JSON e um relatório HTML.

## Integração e registros preservados

O MVP de `MVP_Semantic_Layer_Gabriel.zip` foi integrado ao repositório
`gabrielvenerusso/TCC-ARQ-PARA-SEMANTIC-LAYER` em uma branch derivada da `main`.
O `.git` do ZIP não substitui o histórico deste repositório.
Os hashes do ZIP, da Fase 0 e dos manifestos Linux estão no
[registro da integração](docs/integracao_mvp.json).

A Fase 0 continua preservada como registro do ambiente observado antes da
integração. Seus textos descrevem aquela fase; não representam o estado atual
da implementação:

- [Inventário da Fase 0](environment.json)
- [Instantâneo original do inventário](results/environment/phase0-20261121T0442371275245Z/environment.json)
- [Diagnóstico e fontes oficiais](docs/fase0_ambiente.md)
- [Pendências parciais do capítulo registradas na Fase 0](docs/pendencias_capitulo4.md)

O documento `docs/TCC 1 - Gabriel Venerusso.docx` permanece inalterado. As
afirmações de resultados contidas nos documentos precisam ser confrontadas
com as evidências; não substituem registros de execução.

As duas rodadas Linux recebidas no ZIP foram preservadas integralmente:

- [Rodada 20261111T053334Z-62b9aa](evidencias/20261111T053334Z-62b9aa/relatorio.html)
- [Rodada 20261111T053821Z-b22840](evidencias/20261111T053821Z-b22840/relatorio.html)

Essas evidências registram execução nativa em Linux, com 10 respostas corretas
na configuração original, 10 bloqueios na incompatível e 10 respostas
corretas na corrigida. Seus commits pertencem ao pacote de origem. Os
arquivos históricos, inclusive avaliações antigas de requisitos, não foram
reescritos. Novas rodadas registram o commit deste repositório e o avaliador
corrigido.

**R01 permanece pendente da revisão das responsabilidades e interfaces.** A
existência de `docs/ARQUITETURA.md` não conclui essa revisão. **A revisão do
catálogo também permanece pendente da conferência do autor.** A validação
estrutural de suas colunas é uma verificação técnica separada da revisão de
termos, métricas e relações. Um protocolo técnico aprovado não aprova essas
duas revisões humanas.

## Reproduzir no Windows

Use Git, PowerShell 5.1 ou superior e Docker Desktop iniciado com WSL 2 e
contêineres Linux. Execute os comandos na raiz desta cópia do repositório.
Java, Python, PostgreSQL, Ontop e JDBC são instalados nos contêineres; não é
necessário instalar esses runtimes no Windows.

Antes de uma rodada formal, versione as alterações do código e confira que
`git status --short` não mostra alterações pendentes. O script exige uma
árvore limpa, incluindo arquivos ainda não versionados. O commit testado é
registrado antes da criação dos resultados. O commit que acrescenta as
evidências será posterior ao commit testado.

```powershell
git status --short
git log -1 --oneline
docker version
docker compose version
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_experiment.ps1
```

O script verifica o ambiente, constrói a imagem, executa os testes, inicia o
PostgreSQL e chama o avaliador pelo Docker Compose. Cada execução gera uma
pasta nova `evidencias/<id>-windows-compose` com logs e o commit testado. Se
uma etapa impedir a continuação, seu nome, código de saída e erro observado
ficam registrados; as questões não executadas são identificadas como
bloqueadas, com `query_executed: false`.

`Bypass` vale apenas para esse processo e não altera a política do Windows.
A primeira construção precisa de rede para baixar as imagens e dependências.
As imagens base são fixadas por digest e os downloads de Ontop/JDBC por
SHA-256. O pacote Java fixa a série 21; a versão efetivamente instalada fica
em `environment.json` da rodada.
Execute uma rodada por vez: a avaliação recria somente o esquema
`experimento` do banco dedicado `tcc_avaliacao`. A demonstração usa outro
banco, `tcc_demo`.

| Configuração | Alteração | Resultado esperado pelo protocolo |
|---|---|---|
| A — `original` | Esquema e artefatos originais | Dez respostas corretas |
| B — `incompativel` | Renomeia `cod_situacao` para `situacao_id`, mantendo o mapeamento e catálogo antigos | Falha deliberada registrada nas dez tentativas |
| C — `corrigida` | Usa mapeamento e catálogo atualizados | Dez respostas corretas, com as mesmas consultas e ontologia |

As dez questões de cada configuração permanecem no denominador, totalizando
30 tentativas. O controle negativo adicional de QC08 remove somente os
axiomas de subclasse e deve retornar `false`. O avaliador também verifica
acesso somente leitura, casos de referência e preservação dos dados.

## Abrir e verificar o relatório

O índice `evidencias/latest-windows.json` aponta para a rodada criada pelo
script, mesmo que ela tenha sido bloqueada. O `latest.json` recebido no ZIP
é mantido como registro histórico.

```powershell
$rodada = (Get-Content .\evidencias\latest-windows.json -Raw -Encoding UTF8 | ConvertFrom-Json).run_id
Start-Process ".\evidencias\$rodada\relatorio.html"
docker compose run --rm --no-deps avaliador verify "evidencias/$rodada"
```

Também é possível abrir `evidencias/<rodada>/relatorio.html` com dois cliques.
O comando `verify` confere o manifesto da avaliação e, quando presente, o
manifesto dos registros coletados no Windows. Se a imagem não puder ser
construída, o relatório e os arquivos de bloqueio ainda podem ser lidos no
host; a verificação pelo contêiner depende dessa construção.

## Comandos individuais do Docker Compose

Para executar as etapas manualmente:

```powershell
docker compose build avaliador
docker compose run --rm --no-deps --entrypoint python avaliador -m unittest discover -s tests -v
docker compose up -d --wait postgres
docker compose run --rm -e EVIDENCE_LATEST_FILE=latest-windows.json avaliador
```

O comando de avaliação retorna zero quando o protocolo técnico é atendido.
Uma falha inesperada ou rastreabilidade incompleta retorna código diferente
de zero. A falha deliberada da configuração B faz parte do protocolo. Use o
script de reprodução para reunir também os logs das etapas de preparação.

## Conteúdo das evidências

Consulte o resumo e os logs da rodada para distinguir execução concluída de
bloqueio de infraestrutura. Os registros Linux importados são históricos e
não comprovam uma execução Docker no Windows.

| Arquivo ou pasta | Conteúdo |
|---|---|
| `execution.json` | Etapas do runner Windows, códigos de saída, bloqueios e commit testado |
| `logs/` | Saídas da preparação, construção, testes, avaliação e serviços |
| `summary.json` | Totais, resultado do protocolo e commit testado |
| `records.json` | Trinta tentativas, incluindo fase e motivo dos bloqueios |
| `expected/*.json` | Respostas SQL congeladas antes da alteração física |
| `original/`, `incompativel/`, `corrigida/` | Metadados, respostas e logs do Ontop |
| `checks.json` | Acesso somente leitura, inferência, dados e catálogo |
| `mutation.json` | Alteração física e artefatos adaptados |
| `requirements.json` | Requisitos, verificações técnicas e revisões pendentes |
| `artifacts/` | Cópias dos artefatos avaliados |
| `manifest.json` | Commit e hashes dos arquivos da avaliação |
| `host-manifest.json` | Hashes da rodada após incorporar os logs e registros do Windows |
| `environment.json` | Versões e recursos do ambiente da avaliação |

Os arquivos dependentes de uma etapa só existem se ela tiver sido alcançada.
Uma falha anterior à preparação do banco não produz respostas SQL ou SPARQL.

## Demonstração interativa

```powershell
docker compose up --build -d --wait camada
Start-Process 'http://localhost:8080'
docker compose exec camada python -m mvp list
docker compose exec camada python -m mvp query QC04
```

A interface do Ontop abre em `http://localhost:8080`; o endpoint é
`http://localhost:8080/sparql`. QC04 calcula a soma de quantidade × valor
unitário dos itens. O pedido 2 deve ter total 36,53, sem frete, tributos,
descontos ou devoluções; a métrica não equivale a faturamento contábil.

Para consultar o estado, diagnosticar e encerrar os serviços:

```powershell
docker compose ps
docker compose logs --tail 100 postgres camada
docker compose down
```

`down` mantém o volume de dados e as evidências locais. As credenciais no
Compose são públicas e destinadas à demonstração local; PostgreSQL não
publica porta para o host, e a interface usa somente o loopback.

## Repetir o inventário da Fase 0

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\inspect_environment.ps1
```

O coletor consulta versões e recursos, sem instalar dependências, iniciar
serviços ou alterar bancos. Cada coleta preserva um novo instantâneo em
`results/environment/<id>/environment.json` e atualiza `environment.json`;
portanto, execute-o apenas quando quiser registrar um novo inventário. O
instantâneo original da Fase 0 permanece disponível. Acesso negado e comandos
indisponíveis são registrados.

## Artefatos e limites

Veja [arquitetura e limitações](docs/ARQUITETURA.md),
[roteiro de demonstração](docs/DEMONSTRACAO.md),
[questões de competência](queries/questions.json) e
[análise do Auto-Ontology](docs/NVIDIA_AUTO_ONTOLOGY.md).

O MVP utiliza consultas previamente definidas, um domínio sintético com dez
clientes, dez produtos, trinta pedidos e sessenta itens. Os tempos registrados
são diagnósticos; não constituem benchmark de produção. Não há geração
automática de ontologia ou consultas por modelos de linguagem. O Capítulo 4
e a revisão qualitativa pelo autor continuam como trabalho posterior.
