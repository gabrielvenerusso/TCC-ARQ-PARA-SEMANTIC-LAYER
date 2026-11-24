# Roteiro de demonstração

1. Apresente os seis componentes da arquitetura e a função do Ontop na execução das consultas.
2. Abra `catalog/original.json` e mostre a definição de PedidoConcluido, sua relação com o código 2 e o cálculo do total. Relacione esses elementos aos critérios de análise das definições do domínio registrados em `docs/analises.json`.
3. Abra `ontology/vendas.ttl` no Protégé ou no editor. Mostre a subclasse `PedidoConcluido` e sua superclasse `Pedido`.
4. Abra `mappings/original.ttl`: o código 2 está no filtro SQL do mapeamento; o significado da hierarquia está na ontologia.
5. Execute QC04 na interface ou terminal. Mostre o pedido 2 e os itens 12,11 + 24,42 = 36,53.
6. Execute QC08: o resultado esperado é verdadeiro. Mostre no relatório o controle negativo sem a hierarquia.
7. Apresente os resultados da execução documentada: dez respostas corretas na configuração A, dez tentativas bloqueadas na inicialização do Ontop em B e dez respostas corretas em C. Explique a renomeação de coluna e a correção de três regras em um arquivo de mapeamento, mais o catálogo. A apresentação pode usar as evidências existentes, sem repetir o experimento.
8. Abra o [relatório final](analise-final/relatorio.html). Mostre o atendimento aos sete requisitos no cenário sintético, distinguindo a análise da arquitetura e das definições do domínio dos testes de funcionamento. Nos arquivos técnicos vinculados, mostre as 30 tentativas, os 15 testes aprovados na execução registrada, as versões e a conferência de integridade.
9. Retome o resultado da alteração: o mapeamento precisou acompanhar a mudança de coluna, enquanto a ontologia e as consultas SPARQL permaneceram iguais.

O experimento avalia a correção das respostas, o efeito da mudança de esquema, a adaptação dos artefatos e o registro das execuções. Os resultados se limitam a um domínio sintético, a um pequeno volume de dados e a uma alteração de esquema. Não houve avaliação em produção, testes de escala, estudo de produtividade de usuários ou comparação de desempenho com outras ferramentas. A análise final aplica-se às versões registradas e não aprova automaticamente alterações posteriores.
