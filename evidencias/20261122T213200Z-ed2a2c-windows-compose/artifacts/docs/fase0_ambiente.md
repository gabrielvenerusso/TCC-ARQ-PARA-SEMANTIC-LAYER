# Fase 0 — verificação do ambiente

Esta fase registrou o ambiente disponível e os impedimentos à execução do MVP. A inspeção foi realizada em 21/11/2026, antes da implementação do banco, da ontologia e dos mapeamentos. As configurações A, B e C não foram executadas. A conclusão da inspeção não significa que o ambiente esteja pronto para essas execuções.

## Documento de entrada

Foi lido integralmente `docs/TCC 1 - Gabriel Venerusso.docx`, incluindo resumo, capítulos 1 a 3, conteúdo dos quadros, sumário e referências. As cinco figuras incorporadas foram extraídas para inspeção visual. O Capítulo 4 contém somente o título. O arquivo original foi preservado, com SHA-256 `682ccfaf6bd4df8b7c68f485a5dfd158c09a61dc4b6d7168a575dad02f77c1ea`.

O documento apresenta resultados preliminares e versões anteriormente testadas. Essas afirmações foram tratadas como conteúdo a conferir, e não como evidências de uma execução desta sessão. As diferenças identificadas estão em `docs/pendencias_capitulo4.md`.

## Resultado da inspeção local

O inventário estruturado está em `environment.json`. A coleta `phase0-20261121T0442371275245Z`, preservada em `results/environment/phase0-20261121T0442371275245Z/environment.json`, já registra o Docker Engine acessível. O script `scripts/inspect_environment.ps1` permite repetir a coleta e preservar novos instantâneos. Os registros distinguem versões observadas, requisitos e componentes não localizados. Caminhos de busca e limitações da coleta precisam ser considerados: não localizar um componente no PATH ou nas pastas inspecionadas não demonstra sua ausência em todo o computador.

| Item | Observação local | Consequência para o MVP |
|---|---|---|
| Sistema operacional | Windows 11 Pro, versão `10.0.26200`, arquitetura AMD64 | Não corresponde à execução nativa Linux x86_64 descrita no TCC. |
| Processador | AMD Ryzen 5 5600X, 6 núcleos e 12 processadores lógicos | Recurso do ambiente observado; não constitui teste de desempenho. |
| Java | Eclipse Temurin `25.0.2+10` | A JVM encontrada diverge de OpenJDK 21; não foi utilizada como substituição para executar o MVP. |
| Docker | Cliente e Engine `29.5.3`; Docker Desktop `4.78.0 (229452)` | A comunicação com o Engine foi confirmada após o usuário iniciar o Docker. |
| Docker Compose | `5.1.4` | O comando de versão funcionou; os serviços do MVP não foram executados. |
| Plataforma do Engine | Linux AMD64, kernel `6.18.33.1-microsoft-standard-WSL2` | Permite preparar a rota com contêineres Linux; o MVP ainda não foi executado nela. |
| Recursos visíveis ao Engine | `docker info` informou 12 CPUs e `8286515200` bytes de memória | Inventário do Engine, distinto dos recursos físicos do Windows; não constitui teste de desempenho. |
| WSL | A distribuição `docker-desktop` foi listada como `Running`, versão 2 | Trata-se do ambiente do Docker; não foi executado um teste nativo do MVP em uma distribuição Linux separada. |
| Git | `2.53.0.windows.1` | Disponível para identificar os artefatos. |
| Python 3.12, PostgreSQL e Ontop CLI | Não localizados como executáveis funcionais no PATH e nas pastas usuais inspecionadas | As versões solicitadas ainda precisam ser preparadas para o experimento. |
| JDBC PostgreSQL | Nenhum artefato do driver localizado na busca registrada no repositório | A versão 42.7.8 ainda precisa ser disponibilizada e conferida na distribuição do Ontop. |
| psycopg 3.2.10 e RDFLib 7.1.4 | Não confirmados em um interpretador Python 3.12 | A disponibilidade dos pacotes no ambiente experimental permanece pendente. |
| Protégé Desktop | Não utilizado nesta fase | É opcional e não integra a execução automatizada prevista. |

Na tentativa inicial, o Engine estava inacessível porque o pipe `dockerDesktopLinuxEngine` não foi encontrado, inclusive com execução elevada; a distribuição `docker-desktop` estava parada. O usuário iniciou o Docker durante a coleta, e a nova verificação confirmou o Engine acessível e a distribuição em execução. Esse impedimento inicial foi resolvido.

Não foram instaladas as dependências do experimento nem criados usuários de banco, tabelas ou dados. Nenhum contêiner do MVP ou conjunto de serviços Compose do projeto foi executado. Também não foram executados `ontop validate`, a consulta de fumaça ou as questões de competência. O diagnóstico inicial de Docker não deve ser contabilizado como as dez tentativas bloqueadas da configuração B: essa configuração exige a mudança controlada no esquema de uma base preparada.

## Disponibilidade das versões solicitadas

A consulta às fontes oficiais confirmou que as versões abaixo existem. Disponibilidade publicada não equivale a instalação local, download conferido ou execução bem-sucedida.

| Componente | Versão solicitada ou declarada no TCC | Fonte oficial consultada |
|---|---|---|
| PostgreSQL | `17.11` | [Notas de lançamento](https://www.postgresql.org/docs/release/17.11/) |
| Ontop | `5.5.0` | [Release da distribuição](https://github.com/ontop/ontop/releases/tag/ontop-5.5.0) e [notas de lançamento](https://ontop-vkg.org/guide/releases.html) |
| Driver JDBC PostgreSQL | `42.7.8` | [Changelog do pgJDBC](https://jdbc.postgresql.org/changelogs/2025-09-18-42.7.8-release/) |
| OpenJDK | `21`; o Quadro 3 declara `21.0.13` | [Eclipse Temurin 21.0.13+9](https://github.com/adoptium/temurin21-binaries/releases/tag/jdk-21.0.13%2B9) |
| Python | `3.12`; o Quadro 3 declara `3.12.14` | [Python 3.12.14](https://www.python.org/downloads/release/python-31214/) |
| psycopg | `3.2.10` | [Histórico oficial](https://www.psycopg.org/psycopg3/docs/news.html#psycopg-3-2-10) e [pacote publicado](https://pypi.org/project/psycopg/3.2.10/) |
| RDFLib | `7.1.4` | [Pacote publicado](https://pypi.org/project/rdflib/7.1.4/) |
| Protégé Desktop | `5.6.9`, opcional | [Release oficial](https://github.com/protegeproject/protege-distribution/releases/tag/protege-5.6.9) |

Python 3.12.14 é uma distribuição somente de código-fonte; não há instalador binário oficial para essa versão. A página oficial identifica 3.12.10 como a última versão da série com instaladores. Isso exige preparar a distribuição apropriada, mas não autoriza trocar silenciosamente a versão declarada no TCC.

O POM da tag Ontop 5.5.0 declara `jdk.version=11`, enquanto as notas históricas indicam Java 11 ou superior. Essas informações não substituem um teste com OpenJDK 21 e todas as dependências da distribuição. A compatibilidade efetiva continua pendente de execução. [POM da versão 5.5.0](https://raw.githubusercontent.com/ontop/ontop/ontop-5.5.0/pom.xml)

## CLI do Ontop consultada antes da implementação

O guia oficial documenta `ontop` em Linux e `ontop.bat` em Windows. O driver JDBC deve ser colocado no diretório `jdbc` da distribuição. `ontop query` é destinado a verificações rápidas, aceita somente `SELECT` e produz CSV. Para as questões `ASK` e a preservação dos tipos RDF, está proposto utilizar o endpoint SPARQL `/sparql`. A opção `--lazy` altera o momento da inicialização e deverá ser registrada caso usada. A opção `--dev` disponibiliza `/ontop/reformulate` para obter SQL como evidência complementar. [Guia oficial da CLI](https://ontop-vkg.org/guide/cli.html)

O comando `validate` consta do guia; seu funcionamento foi conferido também no código da tag 5.5.0. Ele carrega os artefatos, verifica colisões entre IRIs de classes e propriedades e carrega a especificação. Não equivale a certificação semântica humana nem a verificação formal exaustiva de OWL 2 QL. [Implementação de validate](https://raw.githubusercontent.com/ontop/ontop/ontop-5.5.0/client/cli/src/main/java/it/unibz/inf/ontop/cli/OntopValidate.java), [opções de ontologia e mapeamento](https://raw.githubusercontent.com/ontop/ontop/ontop-5.5.0/client/cli/src/main/java/it/unibz/inf/ontop/cli/OntopMappingOntologyRelatedCommand.java)

Os comandos a seguir são exemplos futuros, **não executados**. Os nomes de arquivo são ilustrativos. A ajuda da distribuição instalada deverá ser registrada antes do primeiro uso. As propriedades de conexão reais deverão permanecer em arquivo local ignorado pelo Git, sem senhas nos comandos ou nos relatórios.

```text
# Exemplos futuros para Linux — não executados
./ontop help validate
./ontop validate -m mapping.ttl -t ontology.ttl -p ontop.properties
./ontop help query
./ontop query -m mapping.ttl -t ontology.ttl -p ontop.properties -q smoke.rq -o smoke.csv
./ontop help endpoint
./ontop endpoint -m mapping.ttl -t ontology.ttl -p ontop.properties --port 8080
```

## Rota proposta para preparar o ambiente

A proposta é preparar a reprodução por Docker Compose com contêineres Linux no Engine já operacional, mantendo PostgreSQL 17.11, Ontop 5.5.0, JDBC 42.7.8, Python 3.12.14, psycopg 3.2.10, RDFLib 7.1.4 e Eclipse Temurin OpenJDK 21.0.13+9. A preparação desses serviços não foi executada nesta fase. A existência das imagens e dos binários apropriados, suas arquiteturas, hashes e versões internas deverá ser conferida antes da utilização. Não foi presumido que uma imagem do Ontop inclua a JVM ou o JDBC solicitados.

A execução nativa exigirá uma distribuição Linux x86_64 separada com essas mesmas versões. Essa rota também não foi executada. O uso da JVM 25 encontrada no Windows não foi adotado. A disponibilidade atual do Docker Engine não equivale a uma evidência de consulta semântica ou de conexão PostgreSQL, que ainda não ocorreram nesta fase.

Antes da avaliação da configuração A, a matriz de requisitos, as dez questões, os resultados esperados e as regras de comparação deverão ser fixados e versionados. Embora a Fase 7 consolide a matriz e os indicadores, sua definição não pode ficar para depois da avaliação da Fase 5. Cada fase deverá possuir seu commit e resumo, com a parada solicitada pelo autor antes da fase seguinte.
