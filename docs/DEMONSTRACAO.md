# Roteiro de demonstração

1. Apresente os seis componentes da arquitetura e a função do Ontop na execução das consultas.
2. Abra `catalog/original.json` e mostre a definição de PedidoConcluido, sua relação com o código 2 e o cálculo do total. A conferência dessas definições permanece pendente.
3. Abra `ontology/vendas.ttl` no Protégé ou no editor. Mostre a subclasse `PedidoConcluido` e sua superclasse `Pedido`.
4. Abra `mappings/original.ttl`: o código 2 está no filtro SQL do mapeamento; o significado da hierarquia está na ontologia.
5. Execute QC04 na interface ou terminal. Mostre o pedido 2 e os itens 12,11 + 24,42 = 36,53.
6. Execute QC08: o resultado esperado é verdadeiro. Mostre no relatório o controle negativo sem a hierarquia.
7. Rode o avaliador. Explique a renomeação de coluna, o bloqueio do mecanismo e a correção de três regras em um arquivo de mapeamento, mais o catálogo.
8. Abra `relatorio.html`, `records.json` e `manifest.json` na pasta da rodada. Mostre o commit testado, os arquivos utilizados e os registros das tentativas bloqueadas.
9. Retome o resultado da alteração: o mapeamento precisou acompanhar a mudança de coluna, enquanto a ontologia e as consultas SPARQL permaneceram iguais.

O experimento avalia a correção das respostas, o efeito da mudança de esquema, a adaptação dos artefatos e o registro das execuções. Seu escopo não inclui testes de escala, produtividade de usuários ou comparação de desempenho com outras ferramentas. A revisão de responsabilidades e interfaces (R01) continua pendente.
