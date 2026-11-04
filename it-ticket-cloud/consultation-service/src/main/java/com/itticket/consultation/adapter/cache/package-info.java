/**
 * 语义答案缓存:问题向量的余弦相似度(≥配置阈值)匹配 + 知识版本哨兵复核。
 * 职责边界:本包不发起检索、不做生成,只负责「出缓存前的正确性复核」——
 * 命中条目逐条 citations 的 versionId 对 MySQL 当前发布版本校验,
 * 失效即驱逐并穿透;条目只收带引用的实证答案(拒答/澄清/通用回答/降级永不入缓存)。
 */
package com.itticket.consultation.adapter.cache;
