SELECT p.id_pedido AS id,SUM(i.quantidade*i.valor_unitario) AS total FROM experimento.pedido p JOIN experimento.item_pedido i USING(id_pedido) WHERE p.cod_situacao=2 GROUP BY p.id_pedido;
