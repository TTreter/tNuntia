"""
=============================================================================
Exportador Multiformato (Markdown, DOCX, HTML, JSON, TXT) - tNuntia
=============================================================================
Exporta os produtos gerados (Cortes, Notícia, Redes Sociais) para arquivos
físicos prontos para a assessoria de imprensa e comunicação.
"""

import json
from pathlib import Path
from typing import Optional
from docx import Document
from docx.shared import Pt, Inches, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH

from .models import NuntiaOutput


class NuntiaExporter:
    """Exportador para múltiplos formatos dos produtos do tNuntia."""

    @classmethod
    def to_markdown(cls, output: NuntiaOutput, file_path: Optional[str] = None) -> str:
        """Gera o dossiê completo de comunicação em formato Markdown."""
        lines = []
        lines.append(f"# 🏛️ Dossiê de Comunicação: {output.session_title}")
        lines.append(f"> **Data da Sessão**: {output.session_date or 'Não informada'} | **Vídeo**: [{output.video_url}]({output.video_url})\n")
        lines.append("---\n")

        # 1. Destaques Executivos
        lines.append("## 📌 Destaques Executivos da Sessão\n")
        lines.append(f"{output.highlights.executive_summary}\n")
        if output.highlights.main_themes:
            lines.append("**Principais Temas:**")
            for t in output.highlights.main_themes:
                lines.append(f"- {t}")
            lines.append("")
        if output.highlights.key_decisions:
            lines.append("**Principais Deliberações e Votações:**")
            for d in output.highlights.key_decisions:
                lines.append(f"- {d}")
            lines.append("")

        lines.append("---\n")

        # 2. Cortes de Vídeo (Highlights/Shorts)
        lines.append("## 🎬 Sugestões de Cortes para Redes (Shorts / Reels / TikTok)\n")
        for i, cut in enumerate(output.cuts, 1):
            jump_link = cut.youtube_jump_url or f"{output.video_url}&t={cut.start_time}"
            lines.append(f"### {i}. {cut.title}")
            lines.append(f"- ⏱️ **Timestamp**: [{cut.start_time} até {cut.end_time}]({jump_link}) ({cut.duration_seconds}s)")
            lines.append(f"- 🗣️ **Orador/Tema**: {cut.speaker or 'Plenário'} | **Categoria**: `{cut.category}`")
            lines.append(f"- 🔥 **Gancho (Hook 3s)**: *\"{cut.hook}\"*")
            lines.append(f"- ⭐ **Potencial Viral**: {cut.virality_score}/10")
            if cut.summary:
                lines.append(f"- 📝 **Contexto**: {cut.summary}")
            if cut.captions_snippet:
                lines.append(f"- 💬 **Fala**: *\"{cut.captions_snippet}\"*")
            if cut.suggested_hashtags:
                lines.append(f"- 🏷️ **Hashtags**: {' '.join(cut.suggested_hashtags)}")
            lines.append("")

        lines.append("---\n")

        # 3. Notícia Jornalística
        lines.append("## 📰 Notícia para Portal e Imprensa Local\n")
        lines.append(f"# {output.news.headline}\n")
        if output.news.deck:
            lines.append(f"*{output.news.deck}*\n")
        lines.append(f"**{output.session_date or ''}** — {output.news.lead}\n")
        lines.append(f"{output.news.body}\n")

        if output.news.quotes:
            lines.append("### 🗣️ Falas em Destaque:")
            for q in output.news.quotes:
                spk = q.speaker if hasattr(q, "speaker") else q.get("speaker", "")
                txt = q.quote if hasattr(q, "quote") else q.get("quote", "")
                lines.append(f"> \"{txt}\"  \n> — **{spk}**\n")

        if output.news.legislation_summary:
            lines.append("### 📜 Matérias da Pauta e Votações:")
            for m in output.news.legislation_summary:
                lines.append(f"- {m}")
            lines.append("")

        if output.news.tags:
            lines.append(f"**Tags**: {', '.join(output.news.tags)}\n")

        lines.append("---\n")

        # 4. Redes Sociais
        lines.append("## 📱 Pacote para Redes Sociais\n")
        lines.append("### 📸 Instagram & Facebook")
        lines.append("```text")
        lines.append(output.social.instagram_caption)
        lines.append("```\n")

        if output.social.instagram_carousel:
            lines.append("#### 🎠 Estrutura para Carrossel (Slides)")
            for s in output.social.instagram_carousel:
                lines.append(f"- **Card {s.slide_number} - {s.title}**: {s.content}")
                if s.visual_suggestion:
                    lines.append(f"  *(Visual: {s.visual_suggestion})*")
            lines.append("")

        lines.append("### 🐦 Fio para X (Twitter)")
        for idx, tweet in enumerate(output.social.twitter_thread, 1):
            lines.append(f"**Tweet {idx}** ({len(tweet)} caracteres):")
            lines.append(f"> {tweet}\n")

        lines.append("### 💬 Boletim para WhatsApp e Grupos Comunitários")
        lines.append("```text")
        lines.append(output.social.whatsapp_bulletin)
        lines.append("```\n")

        if output.social.linkedin_post:
            lines.append("### 💼 Publicação Institucional (LinkedIn)")
            lines.append("```text")
            lines.append(output.social.linkedin_post)
            lines.append("```\n")

        md_content = "\n".join(lines)
        if file_path:
            Path(file_path).write_text(md_content, encoding="utf-8")
        return md_content

    @classmethod
    def to_docx(cls, output: NuntiaOutput, file_path: str) -> None:
        """Gera documento Word formal (.docx)."""
        doc = Document()

        # Margens
        for section in doc.sections:
            section.top_margin = Inches(1.0)
            section.bottom_margin = Inches(1.0)
            section.left_margin = Inches(1.0)
            section.right_margin = Inches(1.0)

        # Título principal
        title_p = doc.add_paragraph()
        title_run = title_p.add_run(f"Dossiê de Comunicação: {output.session_title}")
        title_run.font.name = "Arial"
        title_run.font.size = Pt(16)
        title_run.font.bold = True
        title_run.font.color.rgb = RGBColor(24, 43, 73)

        doc.add_paragraph(f"Vídeo de Referência: {output.video_url} | Data: {output.session_date or 'N/A'}")
        doc.add_paragraph().paragraph_format.space_after = Pt(12)

        # 1. Destaques Executivos
        doc.add_heading("1. Destaques Executivos", level=1)
        doc.add_paragraph(output.highlights.executive_summary)

        # 2. Cortes de Vídeo
        doc.add_heading("2. Sugestões de Cortes para Redes Sociais", level=1)
        for i, cut in enumerate(output.cuts, 1):
            p = doc.add_paragraph()
            r_title = p.add_run(f"Corte {i}: {cut.title}\n")
            r_title.bold = True
            p.add_run(f"Tempo: {cut.start_time} até {cut.end_time} ({cut.duration_seconds}s) | Orador: {cut.speaker}\n")
            p.add_run(f"Gancho (3s): \"{cut.hook}\"\n")
            p.add_run(f"Contexto: {cut.summary}\n")

        # 3. Notícia
        doc.add_heading("3. Matéria Jornalística", level=1)
        p_news_head = doc.add_paragraph()
        r_nh = p_news_head.add_run(output.news.headline)
        r_nh.bold = True
        r_nh.font.size = Pt(14)

        if output.news.deck:
            p_deck = doc.add_paragraph()
            r_deck = p_deck.add_run(output.news.deck)
            r_deck.italic = True

        doc.add_paragraph(output.news.lead)
        doc.add_paragraph(output.news.body)

        # 4. Redes Sociais
        doc.add_heading("4. Redes Sociais e WhatsApp", level=1)
        doc.add_heading("Boletim WhatsApp:", level=2)
        doc.add_paragraph(output.social.whatsapp_bulletin)

        doc.add_heading("Legenda Instagram:", level=2)
        doc.add_paragraph(output.social.instagram_caption)

        doc.save(file_path)

    @classmethod
    def to_json(cls, output: NuntiaOutput, file_path: Optional[str] = None) -> str:
        """Gera representação JSON completa."""
        data = output.model_dump(mode="json")
        json_str = json.dumps(data, ensure_ascii=False, indent=2)
        if file_path:
            Path(file_path).write_text(json_str, encoding="utf-8")
        return json_str

    @classmethod
    def to_txt(cls, output: NuntiaOutput, file_path: Optional[str] = None) -> str:
        """Gera texto puro formatado para copiar e colar rápido."""
        txt = cls.to_markdown(output)
        if file_path:
            Path(file_path).write_text(txt, encoding="utf-8")
        return txt

    @classmethod
    def to_html(cls, output: NuntiaOutput, file_path: Optional[str] = None) -> str:
        """Gera página HTML estilizada e moderna com os resultados."""
        md = cls.to_markdown(output)
        # HTML template moderno e limpo
        html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8">
  <title>{output.session_title} - tNuntia</title>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; line-height: 1.6; color: #1e293b; max-width: 900px; margin: 40px auto; padding: 0 20px; }}
    h1 {{ color: #0f172a; border-bottom: 2px solid #e2e8f0; padding-bottom: 8px; }}
    h2 {{ color: #1e3a8a; margin-top: 32px; border-bottom: 1px solid #cbd5e1; padding-bottom: 6px; }}
    h3 {{ color: #334155; }}
    pre {{ background: #f8fafc; border: 1px solid #e2e8f0; padding: 14px; border-radius: 8px; overflow-x: auto; font-size: 14px; }}
    blockquote {{ border-left: 4px solid #3b82f6; margin: 0; padding-left: 16px; color: #475569; font-style: italic; }}
    .badge {{ display: inline-block; background: #e0e7ff; color: #3730a3; padding: 2px 8px; border-radius: 4px; font-size: 12px; font-weight: bold; }}
  </style>
</head>
<body>
  <pre>{md}</pre>
</body>
</html>"""
        if file_path:
            Path(file_path).write_text(html, encoding="utf-8")
        return html
