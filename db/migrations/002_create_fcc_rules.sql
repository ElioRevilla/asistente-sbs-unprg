CREATE TABLE IF NOT EXISTS fcc_rules (
  id SERIAL PRIMARY KEY,
  codigo TEXT NOT NULL UNIQUE,
  descripcion TEXT NOT NULL,
  factor_conversion NUMERIC(5,2) NOT NULL,
  articulo_fuente TEXT NOT NULL
);
