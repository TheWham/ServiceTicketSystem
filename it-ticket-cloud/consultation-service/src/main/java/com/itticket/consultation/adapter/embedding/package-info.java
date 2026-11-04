/**
 * 语义答案缓存的嵌入端口与 OpenAI 兼容实现。
 * 职责边界:本包只负责「文本 →归一化向量」,不持有任何缓存状态;
 * 相似度匹配、条目存储、哨兵复核在 {@code com.itticket.consultation.adapter.cache}。
 * 嵌入供应商在装配期由 AiCompositionConfig 选择,业务代码不分支。
 */
package com.itticket.consultation.adapter.embedding;
