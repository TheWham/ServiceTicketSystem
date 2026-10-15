"""
Demo 4: IT 知识库文档清洗 + LLM Wiki 知识卡片生成 一键运行入口
Layer 1 物理清洗（clean_pipeline.py 规则引擎）
 -> Layer 1.5 LLM 清洗（deepseek-v4-flash 语义级正文清洗）
 -> Layer 2 LLM 知识治理精修（kimi-k3 元数据萃取）
 -> Wiki 卡片落盘（wiki_generator.py）

用法：
    python run_demo.py              # 全流程（LLM 在线清洗 + 萃取）
    python run_demo.py --limit 3    # 只处理前 3 个条目（调试）
    python run_demo.py --offline    # 离线降级：不调用 LLM，全部使用规则结果
"""

import argparse
import os
import sys
from dataclasses import replace
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from rag_pipeline.ingestion.clean_pipeline import CleanPipeline
from rag_pipeline.ingestion.llm_synthesizer import LlmSynthesizer, load_api_config
from rag_pipeline.ingestion.wiki_generator import generate_wiki

DOCX_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "IT常见问题RAG知识库.docx")
OUTPUT_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "artifacts", "output")


def banner(text: str):
    print("\n" + "=" * 70)
    print(text)
    print("=" * 70)


def main():
    parser = argparse.ArgumentParser(description="IT 知识库清洗 + Wiki 生成流水线")
    parser.add_argument("--limit", type=int, default=0, help="只处理前 N 个条目（0 = 全部）")
    parser.add_argument("--offline", action="store_true", help="离线模式：不调用 LLM，全部走规则兜底")
    args = parser.parse_args()

    banner("🚀 [Demo 4] IT 知识库文档清洗 + LLM Wiki 知识卡片生成")

    banner("📄 [Step 1] Layer 1 数据物理清洗（版面解析 + 规则清洗 + 条目切分）")
    pipeline = CleanPipeline(DOCX_PATH)
    entries, stats = pipeline.run(os.path.join(OUTPUT_ROOT, "cleaned"))
    for k, v in stats.items():
        print(f"   [规则统计] {k}: {v}")
    print(f"\n   [OK] 清洗完成：{len(entries)} 个条目（含 {stats['appendix_entries']} 个附录），"
          f"纯净 Markdown 已写入 output/cleaned/")

    if args.limit:
        entries = entries[: args.limit]
        print(f"   [调试模式] 仅处理前 {args.limit} 个条目")

    synthesizer = None
    cfg = None
    if not args.offline:
        cfg = load_api_config()
        api_key = cfg.get("api_key", "")
        if not api_key or api_key.startswith("sk-replace-") or api_key == "sk-...":
            print("\n   [警告] 未找到有效 LLM_API_KEY，自动降级为离线模式")
        else:
            print(f"\n   [配置] base_url={cfg['base_url']}")
            print(f"   [配置] 清洗模型={cfg['clean_model']} | 精修模型={cfg['chat_model']}")
            synthesizer = LlmSynthesizer(cfg, cache_dir=os.path.join(OUTPUT_ROOT, ".llm_cache"))

    banner(f"🧹 [Step 2] LLM 语义级清洗（{cfg['clean_model'] if synthesizer else '离线'}：错别字修正 + 术语规范化 + 排版规整）")
    if synthesizer is None:
        print("   [离线模式] 跳过 LLM 清洗，直接使用 Layer 1 规则清洗结果")
    else:
        clean_ok = clean_fallback = fix_total = 0
        cleaned_entries = []
        for i, e in enumerate(entries, 1):
            result = synthesizer.clean_entry(e)
            fix_total += len(result.get("fixes", []))
            fields = dict(result["fields"])
            remark = fields.pop("备注", e.remark)
            body = [] if "正文" in fields else e.body_paras
            cleaned_entries.append(replace(e, fields=fields, remark=remark, body_paras=body))
            if result.get("clean_source") == "llm":
                clean_ok += 1
                fix_desc = f"，修改 {len(result['fixes'])} 处" if result.get("fixes") else "，无需修改"
                print(f"   [{i:>2}/{len(entries)}] ✅ {e.code} 清洗完成{fix_desc}")
            else:
                clean_fallback += 1
                print(f"   [{i:>2}/{len(entries)}] ⚠️  {e.code} LLM 清洗失败，保留规则清洗原文"
                      f"（{result.get('clean_error', '')[:60]}）")
        entries = cleaned_entries
        print(f"\n   [OK] 清洗完成：LLM 成功 {clean_ok} 条，回退 {clean_fallback} 条，累计修改 {fix_total} 处")

    banner(f"🤖 [Step 3] LLM Wiki 知识治理精修（{cfg['chat_model'] if synthesizer else '离线'}：frontmatter 元数据萃取）")
    metas = {}
    if synthesizer is None:
        print("   [离线模式] 跳过 LLM 萃取，全部使用规则兜底元数据（meta_source=rule）")
        for e in entries:
            metas[e.code] = LlmSynthesizer.fallback_frontmatter(e)
    else:
        llm_ok = llm_fallback = 0
        for i, e in enumerate(entries, 1):
            meta = synthesizer.extract_frontmatter(e)
            metas[e.code] = meta
            if meta.get("meta_source") == "llm":
                llm_ok += 1
                print(f"   [{i:>2}/{len(entries)}] ✅ {e.code} -> {meta.get('title')}")
            else:
                llm_fallback += 1
                print(f"   [{i:>2}/{len(entries)}] ⚠️  {e.code} LLM 萃取失败，规则兜底"
                      f"（{meta.get('llm_error', '')[:60]}）")
        print(f"\n   [OK] 萃取完成：LLM 成功 {llm_ok} 条，规则兜底 {llm_fallback} 条")

        conflicts = synthesizer.detect_conflicts(metas)
        if conflicts:
            print(f"   [版本冲突] 检出 {len(conflicts)} 条废止/冲突说明：")
            for code, note in conflicts.items():
                print(f"      ⚡ {code}: {note}")
        else:
            print("   [版本冲突] 未检出冲突条款（符合预期）")

    banner("📚 [Step 4] 生成企业标准 Wiki 知识卡片库（YAML Frontmatter + 溯源）")
    paths = generate_wiki(entries, metas, os.path.join(OUTPUT_ROOT, "wiki"))
    print(f"   [OK] 已生成 {len(paths)} 个 Markdown 文件（含 _index.md 总索引）")
    print(f"   [目录] {os.path.join(OUTPUT_ROOT, 'wiki')}")

    banner(f"✅ [Demo 4] 执行完毕！共产出 {len(entries)} 张 Wiki 知识卡片")
    print("   产物一览：")
    print(f"   - 清洗后纯净 Markdown : {os.path.join(OUTPUT_ROOT, 'cleaned')}")
    print(f"   - Wiki 知识卡片库     : {os.path.join(OUTPUT_ROOT, 'wiki')}")
    print(f"   - LLM 萃取缓存        : {os.path.join(OUTPUT_ROOT, '.llm_cache')}（重跑零成本）")


if __name__ == "__main__":
    main()
