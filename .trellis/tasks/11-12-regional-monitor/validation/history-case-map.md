# 旧验证套件逐 ID 映射（A2-SEARCH-06 单页迁移）

来源 A（51 项）：`validation/check_history_compat.py`（A1b 五页时代）
来源 B（87 项）：`validation/check_regional.py`（A2a 五页管线时代）

两文件保留在库可运行；五页入口类断言在单页版预期失败（见逐条去向）。
本表说明每个旧断言在新验证体系（`validation/check_search_query.py` Q1-Q13）
中的归属，或废弃原因与替代项。生成脚本按 `(类, 方法)` 匹配处置，不按裸测试名前缀。

**分类口径**（每条的“去向”只有三类）：

- **保留可跑**：断言语义在新版仍成立，旧测试**本身仍在旧套件里可运行可过**；
  新 Q 组可能也覆盖了同一行为，但**不称等效**（等效只给真正被新断言替代的）。
- **等效（恢复）**：旧测试前提已失效（如隔离根缺数据、五页入口消失），
  本轮在新套件补写等价断言并注明 `Qn test_xxx`；此类记为“恢复”。
- **废弃**：五页时代结构断言（页面集合/站内导航/页级来源表），单页迁移后
  无对应物，必须写明原因与替代项（替代项不等于等效）。

计数口径：「等效」= 文本含“新 Q 组等效”或“恢复（”且指向 Q 组测试的条目。

**历史行日期/列归属**：`Q10 test_history_card_same_week_values` 只校验
“年份 → 该年 goldstein”与单周日期，**不校验历史行日期与六列归属**；后者由
**保留**的 `T.test_01_real_w44_matches_csv`（旧套件，仍可跑）负责。

## 来源 A：`check_history_compat.py`（51 项）


### Reg

- `Reg.test_01_source_identical` → 保留可跑（函数体未动，旧套件仍在库）：FUNCS 六函数源码逐字节未变
- `Reg.test_02_outputs_identical_real_data` → 保留可跑（函数体未动，旧套件仍在库）：真实数据 A/B 输出对比，函数体未改即仍成立
- `Reg.test_03_v1_banner_history` → 保留可跑（函数体未动，旧套件仍在库）：v1 历史 run_status 兼容分支保留
- `Reg.test_03b_v2_banner_contract` → 新 Q 组等效（validation/check_search_query.py Q11 test_chip_missing_key_is_unknown_not_silent）：v2 缺键=状态未知，不再静默或误判失败

### D1

- `D1.test_01_order_independent` → 保留可跑（函数体未动，旧套件仍在库）：build_flu_view 周键/重复周/失败行契约未改
- `D1.test_02_invalid_iso_week_ignored_counted` → 保留可跑（函数体未动，旧套件仍在库）：build_flu_view 周键/重复周/失败行契约未改
- `D1.test_03_w53_valid_in_long_year` → 保留可跑（函数体未动，旧套件仍在库）：build_flu_view 周键/重复周/失败行契约未改
- `D1.test_04_duplicate_same_value_merged` → 保留可跑（函数体未动，旧套件仍在库）：build_flu_view 周键/重复周/失败行契约未改
- `D1.test_05_duplicate_conflict_marks_week` → 保留可跑（函数体未动，旧套件仍在库）：build_flu_view 周键/重复周/失败行契约未改
- `D1.test_06_bad_value_in_one_ok_row_conflicts` → 保留可跑（函数体未动，旧套件仍在库）：build_flu_view 周键/重复周/失败行契约未改
- `D1.test_07_fail_row_does_not_override_ok` → 保留可跑（函数体未动，旧套件仍在库）：build_flu_view 周键/重复周/失败行契约未改
- `D1.test_08_fail_only_week_is_fail` → 保留可跑（函数体未动，旧套件仍在库）：build_flu_view 周键/重复周/失败行契约未改
- `D1.test_09_rep_tiebreak_raw_strings` → 保留可跑（函数体未动，旧套件仍在库）：build_flu_view 周键/重复周/失败行契约未改

### D2

- `D2.test_01_bad_values_rejected` → 保留可跑（函数体未动，旧套件仍在库）：数值有效性（真零有效、非法不转 0）契约未改
- `D2.test_02_zero_valid` → 保留可跑（函数体未动，旧套件仍在库）：数值有效性（真零有效、非法不转 0）契约未改
- `D2.test_03_latest_bad_value_no_silent_fallback` → 保留可跑（函数体未动，旧套件仍在库）：数值有效性（真零有效、非法不转 0）契约未改
- `D2.test_04_bad_metadata_keeps_value_with_note` → 保留可跑（函数体未动，旧套件仍在库）：数值有效性（真零有效、非法不转 0）契约未改
- `D2.test_05_url_validation` → 保留可跑（函数体未动，旧套件仍在库）：数值有效性（真零有效、非法不转 0）契约未改

### M

- `M.test_01_up_down_flat` → 保留可跑（函数体未动，旧套件仍在库）：环比边界（跨年 W1、W53、跳周、缺失/异常前周、真零）旧套件 11 项逐一覆盖，Q10 只校验当前数据那一条，不构成等效
- `M.test_02_gap_no_compare` → 保留可跑（函数体未动，旧套件仍在库）：环比边界（跨年 W1、W53、跳周、缺失/异常前周、真零）旧套件 11 项逐一覆盖，Q10 只校验当前数据那一条，不构成等效
- `M.test_03_w1_cross_year` → 保留可跑（函数体未动，旧套件仍在库）：环比边界（跨年 W1、W53、跳周、缺失/异常前周、真零）旧套件 11 项逐一覆盖，Q10 只校验当前数据那一条，不构成等效
- `M.test_04_w1_prev_year_w53` → 保留可跑（函数体未动，旧套件仍在库）：环比边界（跨年 W1、W53、跳周、缺失/异常前周、真零）旧套件 11 项逐一覆盖，Q10 只校验当前数据那一条，不构成等效
- `M.test_05_w51_jump_w1_not_adjacent` → 保留可跑（函数体未动，旧套件仍在库）：环比边界（跨年 W1、W53、跳周、缺失/异常前周、真零）旧套件 11 项逐一覆盖，Q10 只校验当前数据那一条，不构成等效
- `M.test_06_prev_anomalous_vs_missing` → 保留可跑（函数体未动，旧套件仍在库）：环比边界（跨年 W1、W53、跳周、缺失/异常前周、真零）旧套件 11 项逐一覆盖，Q10 只校验当前数据那一条，不构成等效
- `M.test_07_single_week_is_missing` → 保留可跑（函数体未动，旧套件仍在库）：环比边界（跨年 W1、W53、跳周、缺失/异常前周、真零）旧套件 11 项逐一覆盖，Q10 只校验当前数据那一条，不构成等效
- `M.test_08_banner_later_fail_and_no_false_history_fail` → 保留可跑（函数体未动，旧套件仍在库）：环比边界（跨年 W1、W53、跳周、缺失/异常前周、真零）旧套件 11 项逐一覆盖，Q10 只校验当前数据那一条，不构成等效
- `M.test_11_anomalous_anchor_with_later_fail_banner` → 保留可跑（函数体未动，旧套件仍在库）：环比边界（跨年 W1、W53、跳周、缺失/异常前周、真零）旧套件 11 项逐一覆盖，Q10 只校验当前数据那一条，不构成等效
- `M.test_09_zero_participates` → 保留可跑（函数体未动，旧套件仍在库）：环比边界（跨年 W1、W53、跳周、缺失/异常前周、真零）旧套件 11 项逐一覆盖，Q10 只校验当前数据那一条，不构成等效
- `M.test_10_no_yoy_key` → 保留可跑（函数体未动，旧套件仍在库）：环比边界（跨年 W1、W53、跳周、缺失/异常前周、真零）旧套件 11 项逐一覆盖，Q10 只校验当前数据那一条，不构成等效

### H

- `H.test_01_anchor_from_data_not_clock` → 保留可跑（函数体未动，旧套件仍在库）：历史年窗口选择、单年诚实提示、内部缺口、锚周异常等旧套件 9 项覆盖，Q10 仅校验当前同周表值，不构成等效
- `H.test_02_window_three_prior_years_only` → 保留可跑（函数体未动，旧套件仍在库）：历史年窗口选择、单年诚实提示、内部缺口、锚周异常等旧套件 9 项覆盖，Q10 仅校验当前同周表值，不构成等效
- `H.test_03_single_year_honest_note` → 保留可跑（函数体未动，旧套件仍在库）：历史年窗口选择、单年诚实提示、内部缺口、锚周异常等旧套件 9 项覆盖，Q10 仅校验当前同周表值，不构成等效
- `H.test_04_empty_view` → 保留可跑（函数体未动，旧套件仍在库）：历史年窗口选择、单年诚实提示、内部缺口、锚周异常等旧套件 9 项覆盖，Q10 仅校验当前同周表值，不构成等效
- `H.test_05_internal_gaps_only` → 保留可跑（函数体未动，旧套件仍在库）：历史年窗口选择、单年诚实提示、内部缺口、锚周异常等旧套件 9 项覆盖，Q10 仅校验当前同周表值，不构成等效
- `H.test_06_anchor_week_bad_but_year_kept` → 保留可跑（函数体未动，旧套件仍在库）：历史年窗口选择、单年诚实提示、内部缺口、锚周异常等旧套件 9 项覆盖，Q10 仅校验当前同周表值，不构成等效
- `H.test_07_w53_anchor_vs_52_week_years` → 保留可跑（函数体未动，旧套件仍在库）：历史年窗口选择、单年诚实提示、内部缺口、锚周异常等旧套件 9 项覆盖，Q10 仅校验当前同周表值，不构成等效
- `H.test_08_fail_anchor_week_is_missing_not_anomalous` → 保留可跑（函数体未动，旧套件仍在库）：历史年窗口选择、单年诚实提示、内部缺口、锚周异常等旧套件 9 项覆盖，Q10 仅校验当前同周表值，不构成等效
- `H.test_09_invalid_rows_counted_and_surfaced` → 保留可跑（函数体未动，旧套件仍在库）：历史年窗口选择、单年诚实提示、内部缺口、锚周异常等旧套件 9 项覆盖，Q10 仅校验当前同周表值，不构成等效

### B

- `B.test_01_javascript_url_no_link` → 保留可跑（函数体未动，旧套件仍在库）：javascript: 伪协议不生成链接
- `B.test_02_bad_url_anchor_branch_too` → 保留可跑（函数体未动，旧套件仍在库）：flu_body_html/_hist_src_cell 白名单与转义实现未改
- `B.test_03_url_attribute_escaped` → 保留可跑（函数体未动，旧套件仍在库）：flu_body_html/_hist_src_cell 白名单与转义实现未改
- `B.test_04_line_html_escaped` → 保留可跑（函数体未动，旧套件仍在库）：flu_body_html/_hist_src_cell 白名单与转义实现未改
- `B.test_05_block_level_no_injection` → 保留可跑（函数体未动，旧套件仍在库）：flu_body_html/_hist_src_cell 白名单与转义实现未改

### G

- `G.test_01_axis_domain_fixed` → 保留可跑（函数体未动，旧套件仍在库）：history_svg 几何实现未改
- `G.test_02_scale_algorithm` → 保留可跑（函数体未动，旧套件仍在库）：history_svg 几何实现未改
- `G.test_03_single_point_visible` → 保留可跑（函数体未动，旧套件仍在库）：history_svg 几何实现未改

### T

- `T.test_01_real_w44_matches_csv` → 保留可跑（函数体未动，旧套件仍在库）：同周表真实 W44 夹具、实时 CSV 推导、转义；历史行**日期与六列归属**由本组 test_01_real_w44_matches_csv 负责（Q10 只校验年份→指数与单周日期，不校验历史行日期列）
- `T.test_01b_live_csv_derived` → 保留可跑（函数体未动，旧套件仍在库）：同周表真实 W44 夹具、实时 CSV 推导、转义；历史行**日期与六列归属**由本组 test_01_real_w44_matches_csv 负责（Q10 只校验年份→指数与单周日期，不校验历史行日期列）
- `T.test_02_escaping` → 保留可跑（函数体未动，旧套件仍在库）：同周表真实 W44 夹具、实时 CSV 推导、转义；历史行**日期与六列归属**由本组 test_01_real_w44_matches_csv 负责（Q10 只校验年份→指数与单周日期，不校验历史行日期列）

### E

- `E.test_01_render_isolated_no_data_write` → 废弃（单页版内联脚本，旧断言 assertNotIn('<script') 与现页面冲突；替代=Q7 test_site_dir_single_page + Q6 test_build_keeps_data）
- `E.test_02_data_bytes_unchanged` → 新 Q 组等效（validation/check_search_query.py Q6 test_build_keeps_data）：构建前后 data/ 字节不变

## 来源 B：`check_regional.py`（87 项）


### D1

- `D1.test_01_south_bracket` → 保留可跑（函数体未动，旧套件仍在库）：parse_issue 表1分母/括号互校/自算契约未改
- `D1.test_02_south_self_calc` → 保留可跑（函数体未动，旧套件仍在库）：parse_issue 表1分母/括号互校/自算契约未改
- `D1.test_03_north_self_calc_with_south_present` → 保留可跑（函数体未动，旧套件仍在库）：parse_issue 表1分母/括号互校/自算契约未改
- `D1.test_04_north_spaced_fallback` → 保留可跑（函数体未动，旧套件仍在库）：parse_issue 表1分母/括号互校/自算契约未改
- `D1.test_05_missing_table1_fails` → 保留可跑（函数体未动，旧套件仍在库）：parse_issue 表1分母/括号互校/自算契约未改
- `D1.test_06_north_column_check_fail` → 保留可跑（函数体未动，旧套件仍在库）：parse_issue 表1分母/括号互校/自算契约未改

### D2

- `D2.test_01_bracket_mismatch_fails` → 保留可跑（函数体未动，旧套件仍在库）：解析守卫（互校/笔误容差/计数域/合并版）未改
- `D2.test_02_table_sum_typo_warns` → 保留可跑（函数体未动，旧套件仍在库）：解析守卫（互校/笔误容差/计数域/合并版）未改
- `D2.test_03_num_over_den_fails` → 保留可跑（函数体未动，旧套件仍在库）：解析守卫（互校/笔误容差/计数域/合并版）未改
- `D2.test_04_title_mismatch_fails` → 保留可跑（函数体未动，旧套件仍在库）：解析守卫（互校/笔误容差/计数域/合并版）未改
- `D2.test_05_merged_issue_fails` → 保留可跑（函数体未动，旧套件仍在库）：解析守卫（互校/笔误容差/计数域/合并版）未改
- `D2.test_06_cover_leftover_warns` → 保留可跑（函数体未动，旧套件仍在库）：解析守卫（互校/笔误容差/计数域/合并版）未改

### H1

- `H1.test_01_normal` → 保留可跑（函数体未动，旧套件仍在库）：黑龙江 B1 三种版式与 upsert 守卫未改
- `H1.test_02_all_negative_variant` → 保留可跑（函数体未动，旧套件仍在库）：黑龙江 B1 三种版式与 upsert 守卫未改
- `H1.test_03_no_qizhong_variant` → 保留可跑（函数体未动，旧套件仍在库）：黑龙江 B1 三种版式与 upsert 守卫未改
- `H1.test_04_range_not_seven_days` → 保留可跑（函数体未动，旧套件仍在库）：黑龙江 B1 三种版式与 upsert 守卫未改
- `H1.test_05_title_body_conflict` → 保留可跑（函数体未动，旧套件仍在库）：黑龙江 B1 三种版式与 upsert 守卫未改
- `H1.test_06_upsert_guards` → 保留可跑（函数体未动，旧套件仍在库）：黑龙江 B1 三种版式与 upsert 守卫未改

### H2

- `H2.test_01_normal_with_tie_expansion` → 保留可跑（函数体未动，旧套件仍在库）：B2 整期校验/并列展开/构成校验未改
- `H2.test_02_total_mismatch_fails` → 保留可跑（函数体未动，旧套件仍在库）：B2 整期校验/并列展开/构成校验未改
- `H2.test_03_missing_group_fails` → 保留可跑（函数体未动，旧套件仍在库）：B2 整期校验/并列展开/构成校验未改
- `H2.test_04_rate_out_of_range_fails` → 保留可跑（函数体未动，旧套件仍在库）：B2 整期校验/并列展开/构成校验未改
- `H2.test_09_sample_count_revision_is_logged` → 保留可跑（函数体未动，旧套件仍在库）：B2 整期校验/并列展开/构成校验未改
- `H2.test_05_same_setting_twice_fails` → 保留可跑（函数体未动，旧套件仍在库）：B2 整期校验/并列展开/构成校验未改
- `H2.test_06_unparseable_fragment_fails` → 保留可跑（函数体未动，旧套件仍在库）：B2 整期校验/并列展开/构成校验未改
- `H2.test_07_tie_partner_rate_conflict_fails` → 保留可跑（函数体未动，旧套件仍在库）：B2 整期校验/并列展开/构成校验未改
- `H2.test_08_tie_partner_same_rate_ok` → 保留可跑（函数体未动，旧套件仍在库）：B2 整期校验/并列展开/构成校验未改

### C1

- `C1.test_01_atomic_write_kill_keeps_target` → 保留可跑（函数体未动，旧套件仍在库）：data_io/fetch_* 原子写未改，强杀证据仍有效
- `C1.test_02_legacy_sentinel_save_kill_two_tables` → 保留可跑（函数体未动，旧套件仍在库）：data_io/fetch_* 原子写未改，强杀证据仍有效
- `C1.test_03_tmp_writes_ignored_by_git` → 保留可跑（函数体未动，旧套件仍在库）：data_io/fetch_* 原子写未改，强杀证据仍有效
- `C1.test_04_flunet_save_kill_keeps_target` → 保留可跑（函数体未动，旧套件仍在库）：data_io/fetch_* 原子写未改，强杀证据仍有效
- `C1.test_05_tmp_writes_not_staged_by_git_add` → 保留可跑（函数体未动，旧套件仍在库）：data_io/fetch_* 原子写未改，强杀证据仍有效

### R1

- `R1.test_01_concurrent_second_refused` → 新 Q 组等效（validation/check_search_query.py Q9 test_live_lock_refused）：活锁一律拒绝
- `R1.test_02_skip_all_local_exit_zero` → 废弃（隔离根 data/ 为空，单页构建需 locations.csv 必然失败，旧前提失效；替代=Q9 三项锁策略测试）

### R2

- `R2.test_01_stale_lock_refused_then_force_unlock` → 新 Q 组等效（validation/check_search_query.py Q9 test_stale_lock_refused_with_manual_guidance）：--force-unlock 不再自动删锁，改人工指引
- `R2.test_02_live_lock_force_unlock_refused` → 新 Q 组等效（validation/check_search_query.py Q9 test_live_lock_refused）：活锁强制解锁被拒

### U1

- `U1.test_01_pages_and_no_external_resources` → 废弃（五页结构与页面集合断言，单页迁移后无意义；替代=Q7 test_site_dir_single_page）
- `U1.test_02_hlj_cq_no_sichuan_card` → 废弃（五页结构与页面集合断言，单页迁移后无意义；替代=Q7 test_site_dir_single_page）

### U2

- `U2.test_01_v2_partial_wording` → 新 Q 组等效（validation/check_search_query.py Q11 test_chip_failed_and_compute_failed）：横幅改编为单页+按产品分列文案
- `U2.test_02_run_id_mismatch_is_history` → 保留可跑（函数体未动，旧套件仍在库）：run_id 不匹配按历史处理，run_banner 契约仍在
- `U2.test_03_local_without_status_is_noted` → 保留可跑（函数体未动，旧套件仍在库）：local 无状态提示仍在
- `U2.test_04_all_ok_no_banner` → 保留可跑（函数体未动，旧套件仍在库）：全 ok 不出横幅仍在
- `U2.test_05_bad_json_unknown` → 保留可跑（函数体未动，旧套件仍在库）：坏 JSON 判 unknown 仍在
- `U2.test_06_per_page_relevance_filtering` → 废弃（按页相关性过滤随五页→单页失效（page 维度整体移除）；替代=Q11 test_chip_failed_and_compute_failed）
- `U2.test_07_compute_states` → 新 Q 组等效（validation/check_search_query.py Q11 test_chip_failed_and_compute_failed）：compute 状态改由卡片 chip 分产品呈现
- `U2.test_08_missing_fetch_key_unknown` → 新 Q 组等效（validation/check_search_query.py Q11 test_chip_missing_key_is_unknown_not_silent）：缺键=状态未知，不再输出空串

### U4

- `U4.test_01_nav_contract` → 废弃（五页站内导航链随单页迁移移除，无替代语义；替代=Q1 test_dom_scaffold）
- `U4.test_02_region_names_cards_no_values` → 恢复（validation/check_search_query.py Q13 test_zone_names_templates_carry_no_percentages 补回该断言语义）：片区名称卡改由 zone_names 模板承载，旧断言的「仅名称、无数值」语义在模板内容上恢复

### D3

- `D3.test_01_judge_from_result_joint_checks` → 保留可跑（函数体未动，旧套件仍在库）：结果联合校验/compute/HLJ CLI/缓存绑定未改
- `D3.test_01b_read_result_and_step_of_branches` → 保留可跑（函数体未动，旧套件仍在库）：结果联合校验/compute/HLJ CLI/缓存绑定未改
- `D3.test_02_flunet_columns_contract` → 保留可跑（函数体未动，旧套件仍在库）：结果联合校验/compute/HLJ CLI/缓存绑定未改
- `D3.test_03_compute_ok_row_empty_value_fails_file` → 保留可跑（函数体未动，旧套件仍在库）：结果联合校验/compute/HLJ CLI/缓存绑定未改
- `D3.test_04_hlj_cli_arg_validation` → 保留可跑（函数体未动，旧套件仍在库）：结果联合校验/compute/HLJ CLI/缓存绑定未改
- `D3.test_04b_hlj_products_alias_offline` → 保留可跑（函数体未动，旧套件仍在库）：结果联合校验/compute/HLJ CLI/缓存绑定未改
- `D3.test_05_cache_full_binding` → 保留可跑（函数体未动，旧套件仍在库）：结果联合校验/compute/HLJ CLI/缓存绑定未改

### E1

- `E1.test_01_render_leaves_data_untouched` → 废弃（依赖 build_site.PAGES 五页入口，单页后已无该符号；替代=Q7 test_site_dir_single_page + Q6 test_build_keeps_data）
- `E1.test_02_validate_pages_rejects_incomplete_set` → 保留可跑（函数体未动，旧套件仍在库）：_validate_pages 拒绝缺模板/缺数据块仍在
- `E1.test_03_validate_pages_rejects_bad_links` → 保留可跑（函数体未动，旧套件仍在库）：拒绝脚本外链/外链资源仍在
- `E1.test_04_validate_pages_accepts_valid_set` → 废弃（正例构造含五页站内跳转，单页版校验必然拒绝；替代=Q7 test_index_contains_validated_content）

### R3

- `R3.test_01_preagg_failure_exit2_no_build` → 保留可跑（函数体未动，旧套件仍在库）：预聚合失败→exit2 不构建仍在
- `R3.test_02_build_failure_closes_gate` → 保留可跑（函数体未动，旧套件仍在库）：构建失败关发布门仍在
- `R3.test_03_partial_fetch_failure_exit1_still_builds` → 恢复（validation/check_search_query.py Q13 test_partial_fetch_failure_exit1_still_builds 补回该断言语义）：隔离根补 data/locations.csv + location_product_map.csv，凑齐构建前提后该正向路径重新可跑
- `R3.test_04_fetch_timeout_marks_unknown_pipeline_finishes` → 保留可跑（函数体未动，旧套件仍在库）：超时标 unknown 且管线正常收尾仍在
- `R3.test_05_final_status_write_failure_closes_gate` → 恢复（validation/check_search_query.py Q13 test_final_status_write_failure_closes_gate 补回该断言语义）：隔离根补最小目录数据 + 注入 write_run_status 失败后重跑

### R4

- `R4.test_01_empty_lock_refused` → 新 Q 组等效（validation/check_search_query.py Q9 test_stale_lock_refused_with_manual_guidance）：空/坏 JSON/非法 pid 一律拒绝且不删锁
- `R4.test_02_broken_json_lock_refused` → 新 Q 组等效（validation/check_search_query.py Q9 test_stale_lock_refused_with_manual_guidance）：空/坏 JSON/非法 pid 一律拒绝且不删锁
- `R4.test_03_pid_zero_lock_refused` → 新 Q 组等效（validation/check_search_query.py Q9 test_stale_lock_refused_with_manual_guidance）：空/坏 JSON/非法 pid 一律拒绝且不删锁
- `R4.test_04_force_unlock_still_refuses_unrecognizable_locks` → 新 Q 组等效（validation/check_search_query.py Q9 test_stale_lock_refused_with_manual_guidance）：空/坏 JSON/非法 pid 一律拒绝且不删锁
- `R4.test_05_two_recoverers_cannot_both_delete_lock` → 新 Q 组等效（validation/check_search_query.py Q9 test_no_dead_token_files_left）：恢复竞态改为残片清理断言

### H3

- `H3.test_01_equal_multidoc_deterministic_rep` → 保留可跑（函数体未动，旧套件仍在库）：_pick_b2 代表选取与冲突保全未改
- `H3.test_02_conflict_multidoc_no_write` → 保留可跑（函数体未动，旧套件仍在库）：_pick_b2 代表选取与冲突保全未改
- `H3.test_03_only_newest_title_week_parsed` → 保留可跑（函数体未动，旧套件仍在库）：_pick_b2 代表选取与冲突保全未改
- `H3.test_04_all_parse_fail_reported` → 保留可跑（函数体未动，旧套件仍在库）：_pick_b2 代表选取与冲突保全未改
- `H3.test_05_unparseable_title_mixed_weeks_no_false_conflict` → 保留可跑（函数体未动，旧套件仍在库）：_pick_b2 代表选取与冲突保全未改
- `H3.test_06_unparseable_title_same_content_week_conflict_still_caught` → 保留可跑（函数体未动，旧套件仍在库）：_pick_b2 代表选取与冲突保全未改
- `H3.test_07_newest_title_fail_not_downgraded_to_older_week` → 保留可跑（函数体未动，旧套件仍在库）：_pick_b2 代表选取与冲突保全未改
- `H3.test_08_same_title_week_one_fail_one_ok_preserves` → 保留可跑（函数体未动，旧套件仍在库）：_pick_b2 代表选取与冲突保全未改

### D6

- `D6.test_01_b2_only_backfill_skips_b1_entirely` → 保留可跑（函数体未动，旧套件仍在库）：--products b2 回补隔离未改
- `D6.test_02_result_file_contains_only_requested_products` → 保留可跑（函数体未动，旧套件仍在库）：--products b2 回补隔离未改

### U5

- `U5.test_01_placeholder_anchors_latest_week` → 保留可跑（函数体未动，旧套件仍在库）：rank 占位把锚周顶到最新周，region_rank_block 未改
- `U5.test_02_two_settings_independent_weeks` → 保留可跑（函数体未动，旧套件仍在库）：rank 占位把锚周顶到最新周，region_rank_block 未改
- `U5.test_03_same_week_conflict_marks_anomaly` → 保留可跑（函数体未动，旧套件仍在库）：rank 占位把锚周顶到最新周，region_rank_block 未改
- `U5.test_04_source_labels_table2_only` → 保留可跑（函数体未动，旧套件仍在库）：rank 占位把锚周顶到最新周，region_rank_block 未改

### U6

- `U6.test_01_page_sources_match_actual_cards` → 废弃（PAGE_SOURCES 已无 chongqing 等五页键，口径改由模板承载；替代=Q1 test_dom_scaffold + Q2 test_chongqing_links_only）
- `U6.test_02_render_rejects_run_id_mismatch` → 保留可跑（函数体未动，旧套件仍在库）：render 拒绝 run_id 不匹配仍在

### E2

- `E2.test_01_render_failure_keeps_old_pages` → 废弃（依赖 build_site.PAGES 五页入口；替代=Q6 test_build_failure_keeps_old_page）
- `E2.test_02_replace_phase_failure_propagates` → 废弃（依赖 build_site.PAGES 五页替换阶段；替代=Q6 test_build_failure_keeps_old_page）

## 选择性执行入口（旧套件仍可跑的子集）

- `check_history_compat.py --check M`（11 项）/ `--check T`（3 项）
- `check_regional.py -k "D1"`（6 项）/ `-k "H1" -k "H2"`（15 项）；`-k` 只支持裸子串（`D1*` 匹配 0 条）
- 五页入口类 19 条预期失败项见 check_search_query.py 头部 docstring 清单，不作回归门

## 统计（生成时实算）

- 条目总数：138（来源 A 51 + 来源 B 87）
- 保留可跑：111
- 新 Q 组等效：13
- 恢复：3
- 废弃：11
- 等效合计（新 Q 组等效 + 恢复）：16

## 遗留两条

- `s1b_check.py` BAD 不置非零：历史诊断工具非门（oracle A02 接受）。
- `aliases` 列为空：别名级查询暂不可达；规范名查询不受影响（补数据属后续任务）。
