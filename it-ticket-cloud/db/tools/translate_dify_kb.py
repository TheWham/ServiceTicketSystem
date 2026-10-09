# -*- coding: utf-8 -*-
"""translate_dify_kb.py -- Batch-translate cleaned Markdown KB files (EN -> zh-CN)
through an OpenAI-compatible chat endpoint, keeping Dify-importable structure.

Credentials are read from (first wins):
  1. env TRANSLATE_BASE_URL / TRANSLATE_API_KEY / TRANSLATE_MODEL
  2. ../../consultation-service/ai-secrets.yml  (itticket.consultation.ai.*)

Usage:
  python translate_dify_kb.py <src_dir> <out_dir> [--workers 4] [--limit N]

The tool is idempotent: files that already exist in out_dir (non-empty) are skipped,
so an interrupted run can simply be restarted.
"""
import argparse
import concurrent.futures as futures
import json
import os
import re
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path

SYSTEM_PROMPT = (
    "You are a professional technical translator for an IT helpdesk knowledge base. "
    "Translate the given English Microsoft 365 admin documentation into natural, "
    "fluent Simplified Chinese (简体中文). Rules: "
    "1) Keep the Markdown structure EXACTLY: headings, lists, tables, blockquotes, bold/italic markers. "
    "2) NEVER translate or modify URLs, domains, email addresses, file paths, or code. "
    "3) Keep well-known product names in English (Microsoft 365, Teams, Outlook, OneDrive, Entra ID); "
    "UI control labels may be given as `中文（English）` on first mention. "
    "4) Keep the trailing attribution footer, translate only its label words. "
    "5) Output ONLY the translated Markdown, no explanations, no code fences around the whole document."
)


def load_creds(script_dir: Path):
    base = os.environ.get("TRANSLATE_BASE_URL", "").strip()
    key = os.environ.get("TRANSLATE_API_KEY", "").strip()
    model = os.environ.get("TRANSLATE_MODEL", "").strip()
    if base and key and model:
        return base, key, model

    secrets = script_dir.parent.parent / "consultation-service" / "ai-secrets.yml"
    vals = {}
    if secrets.is_file():
        for line in secrets.read_text(encoding="utf-8").splitlines():
            m = re.match(r"\s*(base-url|api-key|model):\s*\"?([^\"]*)\"?\s*$", line)
            if m:
                v = m.group(2)
                if v and "${" not in v:
                    vals[m.group(1)] = v
    base = base or os.environ.get("AI_BASE_URL", "") or vals.get("base-url", "")
    key = key or os.environ.get("AI_API_KEY", "") or vals.get("api-key", "")
    model = model or os.environ.get("AI_MODEL", "") or vals.get("model", "")
    return base.strip(), key.strip(), model.strip()


def chat_complete(base_url: str, api_key: str, model: str, content: str, timeout: int = 300) -> str:
    url = base_url.rstrip("/") + "/chat/completions"
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": content},
        ],
        "temperature": 0.2,
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": "Bearer " + api_key,
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return data["choices"][0]["message"]["content"].strip()


def strip_wrapping_fence(text: str) -> str:
    m = re.match(r"^```(?:markdown|md)?\s*\n(.*)\n```\s*$", text, flags=re.S)
    return m.group(1).strip() + "\n" if m else text + ("\n" if not text.endswith("\n") else "")


def translate_one(src: Path, dst: Path, base: str, key: str, model: str, retries: int = 3) -> str:
    content = src.read_text(encoding="utf-8")
    last_err = None
    for attempt in range(1, retries + 1):
        try:
            out = strip_wrapping_fence(chat_complete(base, key, model, content))
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_text(out, encoding="utf-8")
            return "ok"
        except Exception as exc:  # noqa: BLE001 - report and retry
            last_err = exc
            wait = 10 * attempt
            print(f"  retry {attempt}/{retries} {src.name}: {exc}; sleep {wait}s", flush=True)
            time.sleep(wait)
    return f"FAILED: {last_err}"


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("src_dir", type=Path)
    ap.add_argument("out_dir", type=Path)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--limit", type=int, default=0, help="translate at most N files (smoke test)")
    args = ap.parse_args(argv)

    base, key, model = load_creds(Path(__file__).resolve().parent)
    if not (base and key and model):
        print("missing credentials: set TRANSLATE_BASE_URL/TRANSLATE_API_KEY/TRANSLATE_MODEL "
              "or fill consultation-service/ai-secrets.yml", file=sys.stderr)
        return 2

    src_root = args.src_dir.resolve()
    out_root = args.out_dir.resolve()
    todo = []
    for src in sorted(src_root.rglob("*.md")):
        dst = out_root / src.relative_to(src_root)
        if dst.is_file() and dst.stat().st_size > 0:
            continue
        todo.append((src, dst))
    if args.limit:
        todo = todo[: args.limit]

    print(f"model={model} base={base}")
    print(f"pending: {len(todo)} files -> {out_root}")
    ok, failed = 0, []
    t0 = time.time()
    with futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        futs = {pool.submit(translate_one, s, d, base, key, model): (s, d) for s, d in todo}
        done = 0
        for fut in futures.as_completed(futs):
            src, dst = futs[fut]
            result = fut.result()
            done += 1
            if result == "ok":
                ok += 1
                print(f"[{done}/{len(todo)}] ok {src.relative_to(src_root)}", flush=True)
            else:
                failed.append(src)
                print(f"[{done}/{len(todo)}] {result} {src.relative_to(src_root)}", flush=True)
    mins = (time.time() - t0) / 60
    print(f"done: ok={ok} failed={len(failed)} elapsed={mins:.1f}min")
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
