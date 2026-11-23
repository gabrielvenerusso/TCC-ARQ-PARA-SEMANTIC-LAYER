CREATE SCHEMA experimento;
CREATE TABLE experimento.cliente (
 id_cliente INTEGER PRIMARY KEY, nome TEXT NOT NULL, cidade TEXT
);
CREATE TABLE experimento.produto (
 id_produto INTEGER PRIMARY KEY, descricao TEXT NOT NULL, categoria TEXT NOT NULL
);
CREATE TABLE experimento.pedido (
 id_pedido INTEGER PRIMARY KEY,
 id_cliente INTEGER NOT NULL REFERENCES experimento.cliente,
 data_pedido DATE NOT NULL,
 cod_situacao INTEGER NOT NULL CHECK (cod_situacao IN (1,2,3))
);
CREATE TABLE experimento.item_pedido (
 id_item INTEGER PRIMARY KEY,
 id_pedido INTEGER NOT NULL REFERENCES experimento.pedido,
 id_produto INTEGER NOT NULL REFERENCES experimento.produto,
 quantidade INTEGER NOT NULL CHECK (quantidade>0),
 valor_unitario NUMERIC(10,2) NOT NULL CHECK (valor_unitario>=0)
);
REVOKE ALL ON SCHEMA experimento FROM PUBLIC;
GRANT USAGE ON SCHEMA experimento TO tcc_leitor;
GRANT SELECT ON ALL TABLES IN SCHEMA experimento TO tcc_leitor;
