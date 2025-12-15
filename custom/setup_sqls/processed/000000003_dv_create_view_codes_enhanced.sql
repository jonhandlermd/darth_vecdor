CREATE VIEW dv_objs.codes_enhanced AS
SELECT
	codes.code AS subj_code
	, cstrs.str AS subj_str
	, csvs.cls AS subj_str_cls_vec
	, ccsvs.mean AS subj_summary_mean_vec
	, csessv.orig_and_exp_mean AS subj_main_exp_mean_vec
	, csm.subj_all_exp_mean_vec
	, codes.id AS subj_id
	, cstrs.id AS subj_str_id
	, csvs.embedder_meta_id AS embedder_meta_id
	, csesp.style AS subj_expansion_style
	, csesp.style_version AS subj_expansion_style_version
	, csm.subj_all_exp_mean_exp_style
	, csm.subj_all_exp_mean_exp_style_version
FROM dv_objs.codes codes
LEFT OUTER JOIN dv_objs.strs cstrs
	ON codes.main_str_id = cstrs.id
LEFT OUTER JOIN dv_objs.str_vectors csvs
	ON csvs.str_id = cstrs.id
LEFT OUTER JOIN dv_objs.code_summary_vectors ccsvs
	ON ccsvs.code_id = codes.id AND ccsvs.embedder_meta_id = csvs.embedder_meta_id
LEFT OUTER JOIN dv_objs.str_expansion_set cses
	ON cses.orig_str_id = codes.main_str_id
LEFT OUTER JOIN dv_objs.str_expansion_set_populator csesp
	ON csesp.id = cses.str_expansion_set_populator_id
LEFT OUTER JOIN dv_objs.str_expansion_set_summary_vectors csessv
	ON csessv.str_expansion_set_id = cses.id
LEFT OUTER JOIN
	(
	SELECT
		cs.code_id
		, csesp.style AS subj_all_exp_mean_exp_style
		, csesp.style_version AS subj_all_exp_mean_exp_style_version
		, csessv.embedder_meta_id AS subj_all_exp_mean_embedder_meta_id
		, AVG(csessv.orig_and_exp_mean) AS subj_all_exp_mean_vec
	FROM dv_objs.code_strs cs
	LEFT OUTER JOIN dv_objs.str_expansion_set cses
		ON cses.orig_str_id = cs.str_id
	LEFT OUTER JOIN dv_objs.str_expansion_set_populator csesp
		ON csesp.id = cses.str_expansion_set_populator_id
	LEFT OUTER JOIN dv_objs.str_expansion_set_summary_vectors csessv
		ON csessv.str_expansion_set_id = cses.id
	GROUP BY cs.code_id, csesp.style,  csesp.style_version, csessv.embedder_meta_id
	) csm
	ON csm.code_id = codes.id AND csessv.embedder_meta_id = csvs.embedder_meta_id
