# Arquitetura de base para camadas semânticas

MVP do TCC de Engenharia de Software da Univille, no domínio sintético de
pedidos de venda. O fluxo previsto é PostgreSQL → catálogo → ontologia OWL 2 QL
→ mapeamentos R2RML → Ontop → registros JSON → relatório HTML.

## Situação atual

A Fase 0 foi executada: leitura integral do documento de entrada, consulta às
fontes oficiais e inventário do ambiente. O Docker Engine ficou acessível após
ser iniciado pelo autor. O ambiente do MVP ainda precisa ser preparado nas
versões exigidas; nenhuma das configurações A, B ou C foi executada.

- [Inventário observado](environment.json)
- [Diagnóstico e fontes oficiais](docs/fase0_ambiente.md)
- [Pendências parciais do capítulo](docs/pendencias_capitulo4.md)

O documento `docs/TCC 1 - Gabriel Venerusso.docx` é a entrada e deve permanecer
inalterado. As afirmações de resultados contidas nele não substituem registros
de execução do MVP. O Capítulo 4 será escrito após as Fases 1 a 7.

## Repetir o inventário do Windows

Na raiz do repositório, com PowerShell 5.1 ou superior:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\inspect_environment.ps1
```

`Bypass` vale apenas para esse processo; o comando não muda a política do
Windows. O coletor consulta versões e recursos, sem instalar dependências,
iniciar serviços ou alterar bancos. Não requer Python. Acesso negado e comandos
indisponíveis são registrados. Em uma sessão restrita, Docker, WSL e CIM podem
exigir permissão adicional de leitura.

Cada coleta preserva um instantâneo em `results/environment/<id>/environment.json`
e atualiza `environment.json`. O hash Git é o commit existente durante a coleta;
o estado da árvore e o hash do coletor também são registrados. O commit que
preserva o resultado pode ser posterior ao commit registrado na observação.

## Etapas restantes

As Fases 1 a 7 implementarão banco, ontologia e mapeamentos, questões de
competência, catálogo, avaliação A/B/C e documentação de reprodução. As Fases 8
e 9 produzirão e revisarão o Capítulo 4. Há uma parada e um commit por fase,
conforme solicitado pelo autor.

As instruções de Docker Compose, execução nativa Linux e avaliação serão
incluídas quando os respectivos artefatos forem implementados e executados.
O coletor atual verifica apenas o host Windows. Ainda não há evidência de
conexão PostgreSQL, validação Ontop, comparação de respostas, acesso somente
leitura ou reprodução completa. Credenciais e ferramentas locais ficam fora
do Git; resultados de execução e inventários ficam versionados.
