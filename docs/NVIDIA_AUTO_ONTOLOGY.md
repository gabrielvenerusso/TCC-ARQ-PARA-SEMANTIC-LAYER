# Relação com o Auto-Ontology da NVIDIA

A análise usa o repositório [NVIDIA/auto-ontology](https://github.com/NVIDIA/auto-ontology), consultado em 11/11/2026 no commit `fc43a82600e18b19d159c52023f54f5572f537ac`. A documentação do projeto serviu como referência para a organização do catálogo e o registro das consultas.

| Evidência no repositório | Relação com a arquitetura | Adaptação neste MVP |
|---|---|---|
| Termos, descrições, sinônimos e colunas no README e em `semantic/models.py` | Separar significado de negócio e esquema físico | Catálogo JSON com termos e referências aos mapeamentos |
| Atributos SQL e relacionamentos descritos no README | Tornar fórmulas e ligações explícitas | Métrica do total dos itens e relações PK/FK documentadas |
| Geração, revisão e certificação por pessoas no README | Identificar autoria e situação da definição | Campos de revisão humana, inicialmente pendentes |
| Eventos de SQL, resultado e erro em `docs/conversation-api.md` | Registrar percurso e resposta da consulta | Identificador, consulta, resultado/erro, versões e arquivos de evidência |
| Verificação de cobertura no README/MCP | Delimitar perguntas suportadas | Dez questões fixas e exclusões explícitas; sem classificador de linguagem natural |

## Diferenças de abordagem

Nos artefatos examinados, o Auto-Ontology organiza termos e atributos para geração e validação de SQL com modelos de linguagem. O MVP deste TCC usa ontologia OWL, mapeamentos R2RML e reformulação de SPARQL em SQL pelo Ontop. Os sinônimos do catálogo apenas documentam os termos de negócio; não são usados para interpretar consultas.

A comparação é documental. Não houve instalação do Auto-Ontology, execução dos seus modelos ou benchmark entre as ferramentas. Os benefícios descritos pela NVIDIA não foram medidos neste experimento. Uma integração com agentes pode ser investigada em trabalhos futuros.

## Referências

- [README na versão consultada](https://github.com/NVIDIA/auto-ontology/blob/fc43a82600e18b19d159c52023f54f5572f537ac/README.md).
- [Modelos de termos e colunas](https://github.com/NVIDIA/auto-ontology/blob/fc43a82600e18b19d159c52023f54f5572f537ac/auto_ontology/semantic/models.py).
- [Pipeline de compilação semântica](https://github.com/NVIDIA/auto-ontology/blob/fc43a82600e18b19d159c52023f54f5572f537ac/auto_ontology/semantic/pipeline.py).
- [Contrato de eventos da API de conversação](https://github.com/NVIDIA/auto-ontology/blob/fc43a82600e18b19d159c52023f54f5572f537ac/docs/conversation-api.md).

NVIDIA. **Auto Ontology**. [S. l.]: NVIDIA, 2026. Repositório de software, commit fc43a82600e18b19d159c52023f54f5572f537ac. Disponível em: https://github.com/NVIDIA/auto-ontology. Acesso em: 11 nov. 2026.

O projeto da NVIDIA é distribuído sob Apache-2.0. Não houve cópia de código ou imagens para este MVP; os diagramas do TCC são elaboração própria. PostgreSQL, Ontop, JDBC e bibliotecas Python mantêm suas próprias licenças; os binários são obtidos durante o build e não fazem parte do ZIP de fontes.
