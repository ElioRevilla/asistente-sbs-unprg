CREATE TABLE IF NOT EXISTS example_mastery (
  student_key TEXT NOT NULL,
  concept TEXT NOT NULL,
  mastery_score FLOAT NOT NULL DEFAULT 0.5,
  attempts INT NOT NULL DEFAULT 0,
  last_answer_correct BOOLEAN,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  PRIMARY KEY (student_key, concept)
);

CREATE INDEX IF NOT EXISTS example_mastery_student_idx
  ON example_mastery (student_key, mastery_score);
