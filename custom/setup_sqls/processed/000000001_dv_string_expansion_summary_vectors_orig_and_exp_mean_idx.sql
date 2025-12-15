-- Index: idx_orig_and_exp_mean

-- DROP INDEX IF EXISTS <replaceme_schema>.idx_orig_and_exp_mean;

CREATE INDEX IF NOT EXISTS idx_orig_and_exp_mean
    ON <replaceme_schema>.str_expansion_set_summary_vectors USING hnsw
    (orig_and_exp_mean vector_cosine_ops)
    TABLESPACE pg_default;