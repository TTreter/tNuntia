"""
=============================================================================
Utilitário de Fatiamento e Exportação de Vídeos (tNuntia Cutter)
=============================================================================
Permite recortar frações exatas do vídeo do YouTube usando yt-dlp e ffmpeg
sem baixar o arquivo completo de várias horas.
"""

import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, Any, Optional
import yt_dlp

from .tverbum_client import TVerbumClient


class VideoCutter:
    """Recorta trechos do vídeo do YouTube e gera comandos de edição."""

    @classmethod
    def get_output_dir(cls) -> Path:
        output_dir = Path("tnuntia_clips")
        output_dir.mkdir(parents=True, exist_ok=True)
        return output_dir

    @classmethod
    def generate_cut_command(
        cls,
        video_url: str,
        start_time: str,
        end_time: str,
        output_filename: str = "corte.mp4",
        vertical_crop: bool = False,
    ) -> Dict[str, str]:
        """
        Gera comandos prontos de yt-dlp e ffmpeg para corte sem download completo.
        """
        ytdlp_cmd = (
            f'yt-dlp --download-sections "*{start_time}-{end_time}" '
            f'--force-keyframes-at-cuts "{video_url}" -o "{output_filename}"'
        )

        ffmpeg_cmd = (
            f'ffmpeg -ss {start_time} -to {end_time} -i input.mp4 '
            f'{"-vf crop=ih*(9/16):ih " if vertical_crop else ""}-c:v libx264 -c:a aac "{output_filename}"'
        )

        return {
            "ytdlp_command": ytdlp_cmd,
            "ffmpeg_command": ffmpeg_cmd,
        }

    @classmethod
    def cut_clip(
        cls,
        video_url: str,
        start_time: str,
        end_time: str,
        title: str = "corte_sessao",
        vertical_crop: bool = False,
        output_dir: Optional[Path] = None,
    ) -> Dict[str, Any]:
        """
        Executa o recorte do trecho do vídeo diretamente via yt-dlp.
        """
        dest_dir = output_dir or cls.get_output_dir()
        safe_title = "".join(c for c in title if c.isalnum() or c in ("-", "_", " ")).strip()
        safe_title = safe_title.replace(" ", "_")[:50] or "corte"
        output_file = dest_dir / f"{safe_title}.mp4"

        ydl_opts = {
            "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
            "outtmpl": str(output_file),
            "download_ranges": yt_dlp.utils.download_range_func(
                None,
                [(TVerbumClient.parse_timestamp_to_seconds(start_time), TVerbumClient.parse_timestamp_to_seconds(end_time))],
            ),
            "force_keyframes_at_cuts": True,
            "quiet": True,
            "no_warnings": True,
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([video_url])

            if output_file.exists():
                # Opcional: crop vertical com ffmpeg se disponível e solicitado
                if vertical_crop and shutil.which("ffmpeg"):
                    vertical_file = dest_dir / f"{safe_title}_vertical.mp4"
                    cmd = [
                        "ffmpeg",
                        "-y",
                        "-i",
                        str(output_file),
                        "-vf",
                        "crop=ih*(9/16):ih",
                        "-c:v",
                        "libx264",
                        "-c:a",
                        "copy",
                        str(vertical_file),
                    ]
                    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    if vertical_file.exists():
                        return {
                            "success": True,
                            "file_path": str(vertical_file),
                            "format": "vertical_9_16",
                        }

                return {
                    "success": True,
                    "file_path": str(output_file),
                    "format": "horizontal_16_9",
                }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "fallback_commands": cls.generate_cut_command(video_url, start_time, end_time, f"{safe_title}.mp4"),
            }

        return {
            "success": False,
            "error": "Arquivo não gerado.",
            "fallback_commands": cls.generate_cut_command(video_url, start_time, end_time, f"{safe_title}.mp4"),
        }
