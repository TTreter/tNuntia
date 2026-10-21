"""
=============================================================================
API REST FastAPI e Servidor Web - tNuntia (v1.0.0)
=============================================================================
Fornece rotas para geração de cortes, notícias, pacote de redes sociais,
exportação multiformato e entrega da interface de estúdio.
"""

import os
import uuid
import tempfile
from pathlib import Path
from typing import Dict, List, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, FileResponse, Response

from .models import (
    NuntiaConfig,
    NuntiaOutput,
    ExportRequest,
    ClipDownloadRequest,
)
from .ai_engine import NuntiaAIEngine
from .exporter import NuntiaExporter
from .cutter import VideoCutter
from .tverbum_client import TVerbumClient

app = FastAPI(
    title="tNuntia API",
    description="Motor de Comunicação Legislativa e Geração de Cortes, Notícias e Redes Sociais com IA.",
    version="1.0.0",
)

# CORS liberado para frontend/integrações
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_OUTPUTS_STORE: Dict[str, NuntiaOutput] = {}
_TEMP_DIR = Path(tempfile.gettempdir()) / "tnuntia_downloads"
_TEMP_DIR.mkdir(parents=True, exist_ok=True)


@app.get("/", response_class=HTMLResponse)
async def serve_studio_ui():
    """Entrega a interface web de estúdio com player sincronizado do YouTube."""
    index_path = Path(__file__).parent / "web" / "index.html"
    if not index_path.exists():
        raise HTTPException(status_code=404, detail="Arquivo web/index.html não encontrado.")
    return HTMLResponse(content=index_path.read_text(encoding="utf-8"))


@app.get("/tnuntia-studio.js")
async def serve_studio_web_component():
    """Entrega o Web Component standalone <tnuntia-studio>."""
    js_path = Path(__file__).parent / "web" / "tnuntia-studio.js"
    if not js_path.exists():
        raise HTTPException(status_code=404, detail="Arquivo web/tnuntia-studio.js não encontrado.")
    return Response(
        content=js_path.read_text(encoding="utf-8"),
        media_type="application/javascript; charset=utf-8",
    )


@app.get("/api/health")
async def health_check():
    """Verifica status da API e conexão com o tVerbum."""
    tverbum_url = os.getenv("TVERBUM_API_URL", "http://localhost:8000")
    tverbum_status = "offline"
    try:
        import httpx
        res = httpx.get(f"{tverbum_url}/docs", timeout=1.5)
        if res.status_code == 200:
            tverbum_status = "online"
    except Exception:
        pass

    cache_path = TVerbumClient.get_shared_cache_path()

    return {
        "status": "online",
        "service": "tNuntia",
        "version": "1.0.0",
        "tverbum_api": {
            "url": tverbum_url,
            "status": tverbum_status,
        },
        "shared_cache": {
            "path": str(cache_path),
            "exists": cache_path.exists(),
        },
    }


@app.get("/api/tverbum/latest")
async def get_latest_tverbum_session():
    """Recupera os metadados da última ata gerada no tVerbum para importação com 1 clique."""
    tverbum_url = os.getenv("TVERBUM_API_URL", "http://localhost:8000").rstrip("/")
    import httpx
    import re
    try:
        async with httpx.AsyncClient(timeout=4.0) as client:
            # 1. Tenta a rota estruturada /api/session/latest
            try:
                res = await client.get(f"{tverbum_url}/api/session/latest")
                if res.status_code == 200:
                    data = res.json()
                    meta = data.get("metadata", {})
                    video_url = meta.get("url") or ""
                    return {
                        "found": True,
                        "session_id": data.get("id"),
                        "title": data.get("title"),
                        "organization_name": data.get("organization_name"),
                        "video_url": video_url,
                        "session_date": data.get("extracted_data", {}).get("session_date_iso"),
                    }
            except Exception:
                pass

            # 2. Fallback resiliente: se o tVerbum estiver rodando o processo antes do reload,
            # consulta a rota ativa /api/download/txt que contém a última ata gerada!
            try:
                res_txt = await client.get(f"{tverbum_url}/api/download/txt")
                if res_txt.status_code == 200 and len(res_txt.text.strip()) > 50:
                    first_lines = [l.strip() for l in res_txt.text.strip().split("\n") if l.strip()]
                    title = first_lines[0] if first_lines else "ATA DA SESSÃO"
                    org_name = ""
                    match = re.search(r"Câmara Municipal(?: de Vereadores)? de [A-Za-zÀ-ÿ\s]+?(?=\s+os integrantes|\s+reuniram|\.|\,)", res_txt.text)
                    if match:
                        org_name = match.group(0).strip()

                    return {
                        "found": True,
                        "session_id": "latest",
                        "title": title,
                        "organization_name": org_name,
                        "video_url": "",
                        "is_fallback": True,
                    }
            except Exception:
                pass

    except Exception as e:
        return {"found": False, "error": str(e)}

    return {"found": False, "message": "Nenhuma ata gerada recentemente no tVerbum."}


@app.post("/api/generate", response_model=NuntiaOutput)
def generate_communication_pack(config: NuntiaConfig):
    """
    Endpoint principal: Gera os Cortes, Notícia Jornalística e Redes Sociais.
    Aproveita automaticamente atas e transcrições do tVerbum para economizar tokens.
    """
    try:
        engine = NuntiaAIEngine(model_name=config.model_name)
        output = engine.generate(config)
        _OUTPUTS_STORE[output.id] = output
        return output
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/results/{output_id}", response_model=NuntiaOutput)
async def get_result_by_id(output_id: str):
    """Recupera o resultado de uma sessão processada anteriormente."""
    result = _OUTPUTS_STORE.get(output_id)
    if not result:
        raise HTTPException(status_code=404, detail="Resultado não encontrado.")
    return result


@app.get("/api/results", response_model=List[NuntiaOutput])
async def list_recent_results():
    """Lista todos os resultados em memória."""
    return list(_OUTPUTS_STORE.values())


@app.post("/api/export")
async def export_content(request: ExportRequest):
    """Exporta o dossiê de comunicação para .md, .docx, .html, .json ou .txt."""
    output = request.output
    safe_title = "".join(c for c in output.session_title if c.isalnum() or c in ("-", "_", " ")).strip()
    safe_title = safe_title.replace(" ", "_")[:40] or "dossie_comunicacao"
    unique_suffix = uuid.uuid4().hex[:6]
    fmt = request.format.lower().strip()

    if fmt == "md":
        file_path = _TEMP_DIR / f"{safe_title}_{unique_suffix}.md"
        NuntiaExporter.to_markdown(output, str(file_path))
        return FileResponse(path=str(file_path), filename=f"{safe_title}.md", media_type="text/markdown; charset=utf-8")
    elif fmt == "docx":
        file_path = _TEMP_DIR / f"{safe_title}_{unique_suffix}.docx"
        NuntiaExporter.to_docx(output, str(file_path))
        return FileResponse(path=str(file_path), filename=f"{safe_title}.docx", media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
    elif fmt == "html":
        file_path = _TEMP_DIR / f"{safe_title}_{unique_suffix}.html"
        NuntiaExporter.to_html(output, str(file_path))
        return FileResponse(path=str(file_path), filename=f"{safe_title}.html", media_type="text/html; charset=utf-8")
    elif fmt == "json":
        file_path = _TEMP_DIR / f"{safe_title}_{unique_suffix}.json"
        NuntiaExporter.to_json(output, str(file_path))
        return FileResponse(path=str(file_path), filename=f"{safe_title}.json", media_type="application/json; charset=utf-8")
    elif fmt == "txt":
        file_path = _TEMP_DIR / f"{safe_title}_{unique_suffix}.txt"
        NuntiaExporter.to_txt(output, str(file_path))
        return FileResponse(path=str(file_path), filename=f"{safe_title}.txt", media_type="text/plain; charset=utf-8")
    else:
        raise HTTPException(status_code=400, detail="Formato não suportado. Use 'md', 'docx', 'html', 'json' ou 'txt'.")


@app.post("/api/cut-video")
async def cut_video_clip(request: ClipDownloadRequest):
    """Aciona o utilitário de corte físico do vídeo via yt-dlp."""
    result = VideoCutter.cut_clip(
        video_url=request.video_url,
        start_time=request.start_time,
        end_time=request.end_time,
        title=request.title,
        vertical_crop=request.vertical_format,
    )
    if not result.get("success"):
        return {
            "status": "warning",
            "message": "Corte físico direto não pôde ser concluído no servidor, mas os comandos manuais foram gerados.",
            "data": result,
        }
    return {
        "status": "ok",
        "message": "Corte de vídeo concluído com sucesso.",
        "data": result,
    }
