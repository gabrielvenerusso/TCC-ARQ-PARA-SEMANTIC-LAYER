-- Dataset sintético determinístico v1. Não usa aleatoriedade nem data atual.
INSERT INTO experimento.cliente VALUES
 (1,'Cliente 01','Joinville'),(2,'Cliente 02','Blumenau'),
 (3,'Cliente 03',NULL),(4,'Cliente 04','Curitiba'),
 (5,'Cliente 05','Joinville'),(6,'Cliente 06','Florianópolis'),
 (7,'Cliente 07','Curitiba'),(8,'Cliente 08',NULL),
 (9,'Cliente 09','Joinville'),(10,'Cliente 10','São Paulo');
INSERT INTO experimento.produto
SELECT n,'Produto '||LPAD(n::text,2,'0'),
 CASE WHEN n<=4 THEN 'Material' ELSE 'Serviço' END
FROM generate_series(1,10) AS n;
INSERT INTO experimento.pedido
SELECT n,((n-1)%8)+1,DATE '2026-01-01'+(n-1)*3,((n-1)%3)+1
FROM generate_series(1,30) AS n;
-- Dois itens por pedido. O pedido 2 repete o produto 2 nos dois itens.
-- Item 3: 1 x 12,11; item 4: 2 x 12,21; total do pedido 2 = 36,53.
INSERT INTO experimento.item_pedido
SELECT (p-1)*2+j,p,
 CASE WHEN p=2 THEN 2 ELSE ((p+j-2)%8)+1 END,
 j,(10+p+j*0.10+0.01)::numeric(10,2)
FROM generate_series(1,30) AS p CROSS JOIN generate_series(1,2) AS j;
