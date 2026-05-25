CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS chunks (
  id TEXT PRIMARY KEY,
  capitulo TEXT,
  articulo INT,
  numeral TEXT,
  tipo_contenido TEXT,
  temas TEXT[],
  texto TEXT NOT NULL,
  referencias_cruzadas TEXT[],
  embedding VECTOR(768),
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS chunks_embedding_idx
  ON chunks USING hnsw (embedding vector_cosine_ops);
CREATE INDEX IF NOT EXISTS chunks_fts_idx
  ON chunks USING gin (to_tsvector('spanish', texto));
CREATE INDEX IF NOT EXISTS chunks_temas_idx
  ON chunks USING gin (temas);

CREATE TABLE IF NOT EXISTS provision_rules (
  id SERIAL PRIMARY KEY,
  categoria TEXT NOT NULL,
  tipo_credito TEXT NOT NULL,
  tipo_garantia TEXT,
  porcentaje_provision NUMERIC(5,2),
  articulo_fuente TEXT
);

CREATE TABLE IF NOT EXISTS students (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  nombre TEXT,
  email TEXT UNIQUE,
  creado_en TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS concept_mastery (
  student_id UUID REFERENCES students(id),
  concepto TEXT NOT NULL,
  mastery_score FLOAT DEFAULT 0.5,
  intentos INT DEFAULT 0,
  ultima_actividad TIMESTAMPTZ,
  PRIMARY KEY (student_id, concepto)
);

CREATE TABLE IF NOT EXISTS quiz_bank (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  concepto TEXT NOT NULL,
  tipo TEXT NOT NULL,
  dificultad FLOAT,
  nivel_bloom TEXT,
  pregunta TEXT NOT NULL,
  opciones JSONB,
  respuesta_correcta TEXT,
  explicacion TEXT,
  articulo_fuente TEXT,
  curada_por_humano BOOLEAN DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS quiz_attempts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  student_id UUID REFERENCES students(id),
  question_id UUID REFERENCES quiz_bank(id),
  respuesta_estudiante TEXT,
  correcto BOOLEAN,
  tiempo_segundos INT,
  creado_en TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS synthetic_cases (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tipo_credito TEXT,
  descripcion_caso JSONB,
  clasificacion_correcta TEXT,
  provision_correcta NUMERIC,
  articulo_fuente TEXT,
  modo TEXT,
  creado_en TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS session_log (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  student_id UUID REFERENCES students(id),
  modo TEXT NOT NULL,
  user_input TEXT,
  intent_detectado JSONB,
  chunks_recuperados TEXT[],
  llm_output TEXT,
  modelo_usado TEXT,
  tokens_input INT,
  tokens_output INT,
  latencia_ms INT,
  costo_usd NUMERIC(10,6),
  feedback_usuario INT,
  creado_en TIMESTAMPTZ DEFAULT NOW()
);
