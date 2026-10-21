"""
=============================================================================
Cliente de Integração com tVerbum e Ingestão Multicanal (tNuntia)
=============================================================================
Responsável por recuperar dados já gerados pelo tVerbum (transcrição,
ata, linha do tempo, matérias votadas) com economia máxima de tokens,
ou realizar ingestão autônoma de fallback.
"""

import os
import re
import json
import sqlite3
import tempfile
from pathlib import Path
from typing import Optional, Dict, Any, Tuple, List
import httpx
from youtube_transcript_api import YouTubeTranscriptApi
import yt_dlp


class SessionIngestedData:
    """Dados consolidados da sessão obtidos via tVerbum ou ingestão direta."""

    def __init__(
        self,
        video_id: str,
        canonical_url: str,
        video_title: str = "",
        upload_date: str = "",
        transcript: str = "",
        timeline_map: Optional[List[Dict[str, Any]]] = None,
        voted_matters: Optional[List[Dict[str, Any]]] = None,
        present_members: Optional[List[str]] = None,
        minute_body: Optional[str] = None,
        cache_source: str = "direct_ingest",
    ):
        self.video_id = video_id
        self.canonical_url = canonical_url
        self.video_title = video_title
        self.upload_date = upload_date
        self.transcript = transcript
        self.timeline_map = timeline_map or []
        self.voted_matters = voted_matters or []
        self.present_members = present_members or []
        self.minute_body = minute_body
        self.cache_source = cache_source

    def has_minute(self) -> bool:
        return bool(self.minute_body and len(self.minute_body.strip()) > 50)


class TVerbumClient:
    """
    Cliente para reaproveitamento inteligente de transcrições e atas do tVerbum.
    Prioriza:
    1. Sessão salva na API do tVerbum (se minute_id informado);
    2. Cache compartilhado SQLite nativo do tVerbum (zero overhead);
    3. Rota GET /api/transcription/{video_id} da API do tVerbum;
    4. Ingestão direta via youtube-transcript-api / yt-dlp (modo autônomo).
    """

    @staticmethod
    def extract_video_id(url: str) -> Optional[str]:
        """Extrai o ID do vídeo a partir de URLs do YouTube."""
        url = url.strip()
        patterns = [
            r"(?:v=|\/)([0-9A-Za-z_-]{11}).*",
            r"youtu\.be\/([0-9A-Za-z_-]{11})",
            r"youtube\.com\/live\/([0-9A-Za-z_-]{11})",
            r"youtube\.com\/shorts\/([0-9A-Za-z_-]{11})",
            r"youtube\.com\/embed\/([0-9A-Za-z_-]{11})",
        ]
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        if re.match(r"^[0-9A-Za-z_-]{11}$", url):
            return url
        return None

    @classmethod
    def get_canonical_url(cls, video_id: str) -> str:
        return f"https://www.youtube.com/watch?v={video_id}"

    @staticmethod
    def parse_timestamp_to_seconds(ts: str) -> int:
        """Converte string de timestamp HH:MM:SS ou MM:SS para segundos inteiros."""
        parts = ts.strip().replace("[", "").replace("]", "").split(":")
        try:
            if len(parts) == 3:
                return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
            elif len(parts) == 2:
                return int(parts[0]) * 60 + int(parts[1])
            elif len(parts) == 1:
                return int(parts[0])
        except Exception:
            pass
        return 0

    @staticmethod
    def format_seconds_to_timestamp(seconds: int) -> str:
        """Converte segundos para formato HH:MM:SS."""
        h = seconds // 3600
        m = (seconds % 3600) // 60
        s = seconds % 60
        return f"{h:02d}:{m:02d}:{s:02d}"

    @classmethod
    def get_shared_cache_path(cls) -> Path:
        """Localiza o banco de cache SQLite compartilhado com o tVerbum."""
        if os.getenv("TVERBUM_CACHE_PATH"):
            return Path(os.getenv("TVERBUM_CACHE_PATH"))
        if os.getenv("TVERBUM_CACHE_DIR"):
            return Path(os.getenv("TVERBUM_CACHE_DIR")) / "tverbum_video_cache.db"
        return Path(tempfile.gettempdir()) / "tverbum_video_cache.db"

    @classmethod
    def read_from_local_cache(cls, video_id: str) -> Optional[Tuple[str, Dict[str, Any]]]:
        """Tenta ler a transcrição e metadados direto do SQLite compartilhado."""
        cache_path = cls.get_shared_cache_path()
        if not cache_path.exists():
            return None
        try:
            conn = sqlite3.connect(str(cache_path))
            cursor = conn.cursor()
            cursor.execute(
                "SELECT transcript, metadata_json FROM video_cache WHERE video_id = ?",
                (video_id,),
            )
            row = cursor.fetchone()
            conn.close()
            if row:
                transcript, meta_json = row
                meta = json.loads(meta_json) if meta_json else {}
                if transcript and len(transcript.strip()) > 50:
                    return (transcript, meta)
        except Exception:
            pass
        return None

    @classmethod
    def fetch_from_tverbum_api(
        cls,
        video_id: str,
        tverbum_api_url: str = "http://localhost:8000",
        session_id: Optional[str] = None,
    ) -> Optional[SessionIngestedData]:
        """Consulta a API REST do tVerbum por sessão ou por transcrição."""
        base_url = tverbum_api_url.rstrip("/")
        client = httpx.Client(timeout=8.0)

        # 1. Se session_id fornecido, busca ata completa
        if session_id:
            try:
                res = client.get(f"{base_url}/api/session/{session_id}")
                if res.status_code == 200:
                    data = res.json()
                    extracted = data.get("extracted_data", {})
                    return SessionIngestedData(
                        video_id=video_id,
                        canonical_url=cls.get_canonical_url(video_id),
                        video_title=data.get("title", ""),
                        upload_date=extracted.get("session_date_iso", ""),
                        transcript=data.get("raw_transcript", ""),
                        timeline_map=data.get("timeline_map", []),
                        voted_matters=extracted.get("voted_matters", []),
                        present_members=extracted.get("present_members", []),
                        minute_body=data.get("body", ""),
                        cache_source="tverbum_session_api",
                    )
            except Exception:
                pass

            # Fallback caso o servidor tVerbum em execução ainda não tenha a rota /api/session/latest
            if session_id == "latest":
                try:
                    res_txt = client.get(f"{base_url}/api/download/txt")
                    if res_txt.status_code == 200 and len(res_txt.text.strip()) > 50:
                        return SessionIngestedData(
                            video_id=video_id,
                            canonical_url=cls.get_canonical_url(video_id),
                            minute_body=res_txt.text,
                            cache_source="tverbum_download_fallback",
                        )
                except Exception:
                    pass

        # 2. Busca transcrição em cache na rota de transcrição
        try:
            res = client.get(f"{base_url}/api/transcription/{video_id}")
            if res.status_code == 200:
                data = res.json()
                if data.get("found") and data.get("transcript"):
                    meta = data.get("metadata", {})
                    return SessionIngestedData(
                        video_id=video_id,
                        canonical_url=cls.get_canonical_url(video_id),
                        video_title=meta.get("video_title", ""),
                        upload_date=meta.get("upload_date_iso") or meta.get("upload_date", ""),
                        transcript=data["transcript"],
                        cache_source="tverbum_api_transcription",
                    )
        except Exception:
            pass

        return None

    @classmethod
    def ingest_direct_autonomous(cls, video_url: str, video_id: str) -> SessionIngestedData:
        """Ingestão autônoma direta do YouTube (sem depender do tVerbum estar aberto)."""
        # Extrai metadados do vídeo
        meta: Dict[str, Any] = {}
        try:
            ydl_opts = {
                "quiet": True,
                "no_warnings": True,
                "noplaylist": True,
                "skip_download": True,
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(video_url, download=False)
                if info:
                    meta["video_title"] = info.get("title", "")
                    meta["channel"] = info.get("uploader", "")
                    upload_date = info.get("upload_date", "")
                    if upload_date and len(upload_date) == 8:
                        meta["upload_date"] = f"{upload_date[6:8]}/{upload_date[4:6]}/{upload_date[0:4]}"
                        meta["upload_date_iso"] = f"{upload_date[0:4]}-{upload_date[4:6]}-{upload_date[6:8]}"
        except Exception:
            pass

        # Tenta obter transcrição de legendas
        transcript_text = ""
        try:
            api = YouTubeTranscriptApi()
            transcript_list = api.list(video_id)
            transcript = None
            try:
                transcript = transcript_list.find_transcript(["pt", "pt-BR"])
            except Exception:
                try:
                    transcript = transcript_list.find_generated_transcript(["pt", "pt-BR"])
                except Exception:
                    for t in transcript_list:
                        if t.is_translatable:
                            transcript = t.translate("pt")
                            break
            if transcript:
                raw_data = transcript.fetch().to_raw_data()
                lines = []
                for item in raw_data:
                    sec = int(item.get("start", 0))
                    ts = cls.format_seconds_to_timestamp(sec)
                    text = item.get("text", "").strip()
                    if text:
                        lines.append(f"[{ts}] {text}")
                transcript_text = "\n".join(lines)
        except Exception:
            pass

        return SessionIngestedData(
            video_id=video_id,
            canonical_url=cls.get_canonical_url(video_id),
            video_title=meta.get("video_title", ""),
            upload_date=meta.get("upload_date_iso", ""),
            transcript=transcript_text,
            cache_source="direct_autonomous_ingest",
        )

    @classmethod
    def resolve_session_data(
        cls,
        video_url: str,
        tverbum_api_url: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> SessionIngestedData:
        """
        Orquestra a obtenção de dados da forma mais econômica possível.
        """
        video_id = cls.extract_video_id(video_url)
        if not video_id:
            raise ValueError(f"Não foi possível extrair o ID do vídeo da URL: {video_url}")

        api_url = tverbum_api_url or os.getenv("TVERBUM_API_URL", "http://localhost:8000")

        # 1. Tenta API do tVerbum (caso session_id tenha sido passado)
        if session_id:
            from_api = cls.fetch_from_tverbum_api(video_id, api_url, session_id=session_id)
            if from_api and (from_api.has_minute() or from_api.transcript):
                return from_api

        # 2. Tenta Cache SQLite Compartilhado local
        local_cached = cls.read_from_local_cache(video_id)
        if local_cached:
            transcript, meta = local_cached
            return SessionIngestedData(
                video_id=video_id,
                canonical_url=cls.get_canonical_url(video_id),
                video_title=meta.get("video_title", ""),
                upload_date=meta.get("upload_date_iso") or meta.get("upload_date", ""),
                transcript=transcript,
                cache_source="tverbum_sqlite_cache",
            )

        # 3. Tenta API REST do tVerbum (busca por vídeo)
        from_api = cls.fetch_from_tverbum_api(video_id, api_url)
        if from_api and from_api.transcript:
            return from_api

        # 4. Fallback autônomo direto do YouTube
        return cls.ingest_direct_autonomous(video_url, video_id)
