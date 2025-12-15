-- Index: str_vector_cls_idx

-- DROP INDEX IF EXISTS <replaceme_schema>.str_vector_cls_idx;

CREATE INDEX IF NOT EXISTS str_vector_cls_idx
    ON <replaceme_schema>.str_vectors USING hnsw
    (cls vector_cosine_ops)
    TABLESPACE pg_default;