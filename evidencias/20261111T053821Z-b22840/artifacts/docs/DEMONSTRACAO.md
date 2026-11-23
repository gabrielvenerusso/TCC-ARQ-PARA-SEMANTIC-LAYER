# Roteiro para demonstrar ao orientador

1. Apresente os seis componentes na arquitetura. Explique que o Ontop é uma implementação possível.
2. Abra `catalog/original.json`: significado de PedidoConcluido, código 2 e definição do total. Explique o limite da revisão humana.
3. Abra `ontology/vendas.ttl` no Protégé ou no editor. Mostre a subclasse `PedidoConcluido` e sua superclasse `Pedido`.
4. Abra `mappings/original.ttl`: o código 2 está no filtro SQL do mapeamento; o significado da hierarquia está na ontologia.
5. Execute QC04 na interface ou terminal. Mostre o pedido 2 e os itens 12,11 + 24,42 = 36,53.
6. Execute QC08: o resultado esperado é verdadeiro. Mostre no relatório o controle negativo sem a hierarquia.
7. Rode o avaliador. Explique a renomeação de coluna, o bloqueio do mecanismo e a correção de três regras em um arquivo de mapeamento, mais o catálogo.
8. Abra `relatorio.html`, `records.json` e `manifest.json`. Relacione os resultados ao commit e aos arquivos, preservando as falhas.
9. Conclua apenas sobre a adequação técnica observada neste domínio: o experimento mostra a dependência dos mapeamentos em relação ao esquema e a possibilidade de manter a interface semântica nessa alteração específica.

O fenômeno observado é a manutenção do acesso semântico diante de uma mudança física controlada: correção das respostas, propagação da falha, esforço manual de adaptação e rastreabilidade. Não se medem produtividade de usuários, escala, desempenho de IA ou superioridade frente à NVIDIA.
