CREATE TABLE IF NOT EXISTS simulation_sessions (
  id UUID PRIMARY KEY,
  user_id TEXT NOT NULL,
  case JSONB NOT NULL,
  state TEXT NOT NULL,
  round INT NOT NULL DEFAULT 0,
  classification JSONB,
  transcript JSONB NOT NULL DEFAULT '[]'::jsonb,
  verdict JSONB,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS simulation_sessions_user_idx
  ON simulation_sessions (user_id, updated_at DESC);
