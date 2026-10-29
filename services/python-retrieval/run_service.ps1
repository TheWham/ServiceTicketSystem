. "D:\day12\demos\handoff-ai-config\ai-env.ps1"
Set-Location "D:\day12\demos\services\python-retrieval"
$env:PYTHONIOENCODING = "utf-8"
$host.UI.RawUI.WindowTitle = "py-rag-8310"
python -m rag_service
