SELECT c.id_cliente AS id FROM experimento.cliente c WHERE NOT EXISTS(SELECT 1 FROM experimento.pedido p WHERE p.id_cliente=c.id_cliente);
