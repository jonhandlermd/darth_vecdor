-- Index: idx_code_summary_vec_mean

-- DROP INDEX IF EXISTS <replaceme_schema>.idx_code_summary_vec_mean;

CREATE INDEX IF NOT EXISTS idx_code_summary_vec_mean
    ON <replaceme_schema>.code_summary_vectors USING hnsw
    (mean vector_cosine_ops)
    TABLESPACE pg_default;