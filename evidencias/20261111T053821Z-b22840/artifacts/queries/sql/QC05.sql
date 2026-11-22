SELECT c.id_cliente AS id,COUNT(p.id_pedido) AS quantidade FROM experimento.cliente c LEFT JOIN experimento.pedido p USING(id_cliente) GROUP BY c.id_cliente;
