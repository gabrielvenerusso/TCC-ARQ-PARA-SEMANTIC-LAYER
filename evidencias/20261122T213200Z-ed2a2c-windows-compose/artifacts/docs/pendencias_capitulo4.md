# Pendências do Capítulo 4 — registro parcial da Fase 0

Este arquivo registra verificações realizadas em 21/11/2026 e pontos que deverão ser retomados após a implementação e a avaliação. O Capítulo 4 ainda não foi redigido. As Fases 1 a 9 permanecem por executar; não há resultados das configurações A, B ou C nesta sessão. O documento original foi preservado.

## Afirmações do documento e evidência disponível

As observações locais devem ser conferidas em `environment.json` e no instantâneo `results/environment/phase0-20261121T0442371275245Z/environment.json`, que registra o Docker Engine acessível após o usuário iniciá-lo. A leitura do texto original e a inspeção de suas figuras estão registradas em `docs/fase0_ambiente.md`.

| Local e afirmação do TCC | Observação nesta fase | Ajuste sugerido ao autor |
|---|---|---|
| Resumo e abstract: dez respostas corretas na configuração original, dez tentativas bloqueadas após alteração e dez respostas corretas após correção | Não foram encontrados registros dessas rodadas no repositório inicial; as configurações não foram executadas nesta sessão. A ausência de registros não demonstra que uma execução anterior nunca ocorreu. | Confirmar posteriormente pelos novos registros ou fornecer os registros anteriores. Se os resultados diferirem, ajustar resumo, abstract e discussão aos valores efetivamente observados. |
| Quadro 3: PostgreSQL 17.11 testado | A versão existe oficialmente, mas PostgreSQL não foi localizado no PATH e nas pastas usuais inspecionadas; não houve conexão ao banco do experimento. | Manter a versão exigida para preparação; somente declarar teste após execução documentada. |
| Quadro 3: Ontop 5.5.0 testado com JDBC 42.7.8 | As versões existem oficialmente; Ontop não foi localizado no PATH e nas pastas usuais inspecionadas, e o driver não foi localizado na busca registrada no repositório. | Registrar posteriormente as versões realmente executadas, a validação e a consulta de fumaça. |
| Quadro 3: OpenJDK 21.0.13 testado | Foi encontrado Eclipse Temurin 25.0.2+10 no ambiente Windows. A versão 21.0.13 não foi executada. | Preparar OpenJDK 21 para o experimento, sem substituir silenciosamente pela JVM encontrada. Registrar fornecedor e build reais. |
| Quadro 3: Python 3.12.14, psycopg 3.2.10 e RDFLib 7.1.4 testados | Python 3.12 e esses pacotes não foram confirmados em um ambiente experimental funcional. Python 3.12.14 existe, mas é publicado oficialmente somente como código-fonte. | Preparar e registrar as versões exatas; qualquer divergência deverá ser documentada antes de alterar o quadro. |
| Seção 3.2: conexão e consultas verificadas em Linux x86_64 | A inspeção ocorreu em Windows 11 Pro AMD64. Após o usuário iniciar o Docker, `docker-desktop` passou a `Running` em WSL 2, com Engine Linux AMD64 e kernel `6.18.33.1-microsoft-standard-WSL2`. Não foram executadas consultas do MVP em Linux. | Distinguir a disponibilidade do Engine de uma execução do experimento; só declarar consultas e reprodução nativa testadas mediante suas evidências. |
| Seção 3.2: pacote contém Docker Compose, cuja execução no computador do pesquisador permanece posterior | O repositório inicial não continha configuração Compose. Docker cliente e Engine 29.5.3, Desktop 4.78.0 (229452) e Compose 5.1.4 foram confirmados. O Engine inicialmente inacessível tornou-se acessível depois que o usuário iniciou o Docker. Nenhum serviço do MVP foi executado. | Criar a configuração nas próximas fases; conservar a distinção entre Engine operacional, arquivo Compose disponível e reprodução do projeto efetivamente executada. |
| Quadro 3: Protégé 5.6.9 opcional e não utilizado na execução automatizada | Protégé não foi utilizado nesta fase. | Não declarar inspeção manual no Protégé sem realizá-la. A ferramenta permanece opcional. |
| Seção 3.2: catálogo implementado com extração, termos e revisão humana pendente | O catálogo ainda não foi implementado nesta sessão. | Confirmar a descrição após a Fase 4; manter a revisão humana pendente até decisão expressa do autor. |
| Seção 3.4: procedimento de comparação e intervenção A/B/C | Ainda não foi executado. | Redigir resultados somente após preservar as rodadas, inclusive falhas; não usar o resultado declarado no resumo como meta a fabricar. |

As fontes oficiais que confirmam a existência das versões e as ressalvas da CLI estão em `docs/fase0_ambiente.md`. A existência de uma release não é evidência de que ela foi instalada ou testada neste computador.

## Decisões de implementação ainda pendentes

Está proposta uma reprodução com contêineres Linux no Docker Engine já operacional, mantendo as versões solicitadas e, para aderência ao Quadro 3, Python 3.12.14 e OpenJDK 21.0.13. Os serviços do experimento ainda não foram preparados ou executados. Imagens, binários, hashes e versões internas precisam ser conferidos. A execução nativa em uma distribuição Linux separada também permanece pendente.

O impedimento inicial do Docker foi resolvido durante a Fase 0. Na sondagem `docker info`, o Engine informou 12 CPUs e `8286515200` bytes de memória. Esses recursos são um inventário do ambiente disponível, não evidência de execução do MVP ou de desempenho.

O runner deverá acomodar `ASK` pelo endpoint SPARQL: a CLI `ontop query` documentada aceita somente `SELECT` e entrega CSV. Isso não exige mudança de ferramenta ou de versão. A estratégia final deverá preservar tipos, valores não vinculados e multiplicidade, e ser documentada antes da comparação.

A matriz de requisitos deverá ser fixada antes da avaliação da configuração A, embora sua consolidação documental esteja prevista na Fase 7. O mesmo vale para questões de competência, critérios de comparação e respostas esperadas. Nenhuma classificação de requisito como atendido foi produzida nesta fase.

## Rastro das afirmações numéricas do capítulo

Ainda não se aplica: `docs/capitulo4.md` não foi produzido. A tabela de rastro deverá ser construída a partir do texto efetivamente redigido e dos registros das Fases 1 a 7. As versões e os recursos mencionados neste registro parcial pertencem ao inventário da Fase 0, não a resultados de consultas do MVP.

## Marcadores para a redação posterior

- [PREENCHER: versões efetivamente executadas e recursos do ambiente; obter em environment.json e nos instantâneos da execução experimental.]
- [PREENCHER: contagens reais dos dados, integridade e rejeição de INSERT/UPDATE/DELETE/ALTER pelo usuário de leitura; obter nas evidências da Fase 1.]
- [PREENCHER: classes, propriedades, regras de mapeamento, validação e consulta de fumaça; obter nos artefatos e nas evidências da Fase 2.]
- [PREENCHER: lista final das dez questões, conferência manual e resultados esperados independentes; obter nos artefatos da Fase 3.]
- [PREENCHER: extração dos catálogos original e atualizado e vínculos com termos e questões; obter nas Fases 4 e 6.]
- [PREENCHER: resultados A/B/C, ponto de falha em B e extensão da correção em C; obter em results/runs/ após as Fases 5 e 6.]
- [PREENCHER: indicadores, requisitos e rastreabilidade verificável; obter no relatório e nos registros consolidados da Fase 7.]
- [PREENCHER: situação real da reprodução Docker Compose e nativa Linux; obter nos registros dos procedimentos efetivamente executados.]
- [PREENCHER: texto de 1.600 a 2.200 palavras, Quadro 7, rastro completo e autoverificação; realizar nas Fases 8 e 9.]

## Referências novas e figuras propostas

Não foi introduzida referência acadêmica nova no capítulo, que ainda não existe. As fontes técnicas usadas no diagnóstico constam de `docs/fase0_ambiente.md`. Caso a redação posterior precise citar Python, RDFLib ou outra fonte ausente das referências do TCC, a entrada ABNT deverá ser proposta aqui, marcada como NOVA e com o acesso a confirmar pelo autor.

Não foram propostas novas figuras ou quadros numerados. O Quadro 7 permanece previsto, sem valores preenchidos.

## Revisão humana e autoverificação

Permanecem dependentes do autor a lista final de CQ04 a CQ10, o vocabulário da ontologia, a conferência dos casos pequenos e a revisão semântica do catálogo. Os campos `revisado_por`, `data_revisao` e `status_revisao` deverão manter a revisão como pendente até que ela ocorra. Testes automatizados não substituem essa revisão.

A autoverificação da Fase 9 não foi realizada, pois o capítulo e as execuções ainda não existem. Não há conclusão sobre correção das respostas, rastreabilidade, adaptação à mudança de esquema, desempenho ou proveniência individual dos valores nesta fase.
