SELECT p.id_pedido AS id,c.nome FROM experimento.pedido p JOIN experimento.cliente c USING(id_cliente) WHERE p.cod_situacao=2;
