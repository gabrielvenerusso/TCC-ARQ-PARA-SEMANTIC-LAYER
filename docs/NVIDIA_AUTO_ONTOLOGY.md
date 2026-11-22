# Relação com o Auto-Ontology da NVIDIA

Fonte primária: [NVIDIA/auto-ontology](https://github.com/NVIDIA/auto-ontology), versão consultada em 11/11/2026, commit `fc43a82600e18b19d159c52023f54f5572f537ac`. Trata-se de documentação e software, não de uma comprovação científica independente dos benefícios anunciados.

| Evidência no repositório | Relação com a arquitetura | Adaptação neste MVP |
|---|---|---|
| Termos, descrições, sinônimos e colunas no README e em `semantic/models.py` | Separar significado de negócio e esquema físico | Catálogo JSON com termos e referências aos mapeamentos |
| Atributos SQL e relacionamentos descritos no README | Tornar fórmulas e ligações explícitas | Métrica do total dos itens e relações PK/FK documentadas |
| Geração, revisão e certificação por pessoas no README | Identificar autoria e situação da definição | Campos de revisão humana, inicialmente pendentes |
| Eventos de SQL, resultado e erro em `docs/conversation-api.md` | Registrar percurso e resposta da consulta | Identificador, consulta, resultado/erro, versões e arquivos de evidência |
| Verificação de cobertura no README/MCP | Delimitar perguntas suportadas | Dez questões fixas e exclusões explícitas; sem classificador de linguagem natural |

## Diferenças que o TCC deve preservar

Nos artefatos examinados, a NVIDIA estrutura termos e atributos para geração e validação de SQL com modelos de linguagem. Não se deve apresentar esse fluxo como prova de uso de OWL 2 QL, mapeamentos R2RML ou reformulação SPARQL no mesmo sentido do Ontop. O MVP mantém esses padrões formais e consulta virtual. Sinônimos são documentação do catálogo; não ativam busca semântica automática.

O repositório informa benefícios e mostra exemplos, mas tais afirmações não medem o desempenho deste protótipo. Não foram realizados benchmark comparativo, instalação do Auto-Ontology ou testes com seus modelos. Sua integração com agentes constitui possibilidade de trabalho futuro.

## Referências para rastrear a análise

- [README na versão consultada](https://github.com/NVIDIA/auto-ontology/blob/fc43a82600e18b19d159c52023f54f5572f537ac/README.md).
- [Modelos de termos e colunas](https://github.com/NVIDIA/auto-ontology/blob/fc43a82600e18b19d159c52023f54f5572f537ac/auto_ontology/semantic/models.py).
- [Pipeline de compilação semântica](https://github.com/NVIDIA/auto-ontology/blob/fc43a82600e18b19d159c52023f54f5572f537ac/auto_ontology/semantic/pipeline.py).
- [Contrato de eventos da API de conversação](https://github.com/NVIDIA/auto-ontology/blob/fc43a82600e18b19d159c52023f54f5572f537ac/docs/conversation-api.md).

Referência bibliográfica sugerida: NVIDIA. **Auto Ontology**. [S. l.]: NVIDIA, 2026. Repositório de software, commit fc43a82600e18b19d159c52023f54f5572f537ac. Disponível em: https://github.com/NVIDIA/auto-ontology. Acesso em: 11 nov. 2026.

O projeto da NVIDIA é distribuído sob Apache-2.0. Não houve cópia de código ou imagens para este MVP; os diagramas do TCC são elaboração própria. PostgreSQL, Ontop, JDBC e bibliotecas Python mantêm suas próprias licenças; os binários são obtidos durante o build e não fazem parte do ZIP de fontes.
