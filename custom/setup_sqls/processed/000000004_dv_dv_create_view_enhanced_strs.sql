CREATE VIEW dv_objs.strs_enhanced AS
 SELECT
 	strs.id AS str_id,
	strs.str AS str_str,
    osesp.style AS str_expansion_style,
    osesp.style_version AS str_expansion_style_version,
    osvs.embedder_meta_id AS str_embedder_meta_id,
    osvs.cls AS str_cls_vec,
    osessv.orig_and_exp_mean AS str_exp_mean_vec
   FROM dv_objs.strs strs
   LEFT OUTER JOIN dv_objs.str_vectors osvs
   		ON strs.id = osvs.str_id
   LEFT OUTER JOIN dv_objs.str_expansion_set oses
   		ON strs.id = oses.orig_str_id
   LEFT OUTER JOIN dv_objs.str_expansion_set_populator osesp
   		ON oses.str_expansion_set_populator_id = osesp.id
   LEFT OUTER JOIN dv_objs.str_expansion_set_summary_vectors osessv
   		ON oses.id = osessv.str_expansion_set_id
   			AND osvs.embedder_meta_id = osessv.embedder_meta_id
