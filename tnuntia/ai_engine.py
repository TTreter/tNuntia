"""
=============================================================================
Motor de Inteligência Artificial para Comunicação Legislativa (tNuntia)
=============================================================================
Utiliza Google Gemini com Structured Outputs para transformar transcrições
e atas legislativas em cortes virais, notícias de imprensa e publicações.
"""

import os
import json
import uuid
import time
from typing import Optional, List, Dict, Any, Tuple
from dotenv import load_dotenv
from google import genai
from google.genai import types

from .models import (
    NuntiaConfig,
    NuntiaOutput,
    NuntiaGeneratedPayload,
    VideoCut,
    NewsArticle,
    SocialMediaPackage,
    SessionHighlights,
)
from .tverbum_client import TVerbumClient, SessionIngestedData

load_dotenv()


class NuntiaAIEngine:
    """Motor de IA calibrado para jornalismo, redação publicitária e seleção de cortes."""

    FALLBACK_MODELS = [
        "gemini-3.8-flash",
        "gemini-3.7-flash",
        "gemini-3.6-flash",
        "gemini-3.1-flash-lite",
    ]

    def __init__(self, api_key: Optional[str] = None, model_name: Optional[str] = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError(
                "Chave de API do Google Gemini não encontrada. Defina GEMINI_API_KEY no arquivo .env."
            )
        self.model_name = model_name or os.getenv("DEFAULT_MODEL", "gemini-3.8-flash")
        self.client = genai.Client(api_key=self.api_key)

    def _build_system_instruction(self, config: NuntiaConfig) -> str:
        """Monta as instruções do sistema especializadas em jornalismo e mídias digitais."""
        tone_guidelines = {
            "informativo": (
                "Tom: Jornalístico e Neutro. Priorize rigor factual, clareza, imparcialidade e interesse público. "
                "Evite tomar partido ou usar linguagem laudatória ou pejorativa."
            ),
            "popular": (
                "Tom: Didático e Popular. Linguagem simples, próxima da população, explicando como as leis e "
                "discursos afetam a vida do cidadão no dia a dia."
            ),
            "institucional": (
                "Tom: Oficial e Corporativo. Foco na transparência pública, rito legislativo, harmonia institucional "
                "e prestação de contas à sociedade."
            ),
            "critico": (
                "Tom: Investigativo e Analítico. Enfatize cobranças, debates acalorados, posicionamentos da oposição "
                "e divergências sobre temas polêmicos."
            ),
        }

        selected_tone = tone_guidelines.get(config.audience_tone, tone_guidelines["informativo"])

        instruction = f"""Você é o Assessor de Comunicação e Estrategista de Mídias Digitais da Câmara Municipal.
Sua missão é transformar a sessão plenária em materiais de alto valor para a imprensa e a população.

DIRETRIZES GERAIS:
{selected_tone}

1. SELEÇÃO DE CORTES (VIDEO CUTS - SHORTS / REELS / TIKTOK):
- Identifique os {config.cuts_limit} momentos de maior impacto da sessão (debates acalorados, discursos comoventes, denúncias de problemas da cidade, aprovações de leis históricas).
- Cada corte deve ter duração ideal entre 30 e 90 segundos.
- 'hook': O gancho inicial (primeiros 3 segundos) DEVE ser extremamente forte para retenção de tela (ex: "Olha o que o vereador falou sobre o posto de saúde!").
- 'title': Título curto, atrativo e provocativo (sem ser sensacionalista falso).
- 'start_time' e 'end_time': Use a marcação temporal [HH:MM:SS] ou [MM:SS] baseada nos timestamps da transcrição.

2. NOTÍCIA JORNALÍSTICA (PORTAL & IMPRENSA):
- Manchete forte em estilo jornalístico clássico (verbo de ação no presente).
- Lead clássico respondendo Quem, O quê, Quando, Onde, Como e Por quê.
- Corpo dividido com intertítulos.
- Aspas reais e diretas ('quotes') dos vereadores com base nas falas registradas.
- Resumo claro das leis votadas e seus resultados.

3. REDES SOCIAIS & BOLETINS:
- Instagram: Legenda engajadora + Carrossel de 4 a 6 slides com textos diretos e orientações visuais.
- Twitter/X: Fio (Thread) encadeado de tweets rápidos (respeitando limite de 270 caracteres por tweet).
- WhatsApp: Boletim ideal para grupos de moradores e lideranças de bairro, usando negritos (*palavra*), emojis adequados e leitura limpa.
- LinkedIn: Post voltado a políticas públicas e governança.
"""
        if config.custom_instructions:
            instruction += f"\nINSTRUÇÕES ADICIONAIS DO ASSESSOR:\n{config.custom_instructions}\n"

        return instruction

    def _generate_structured_with_fallback(
        self, contents: List[Any], system_instruction: str
    ) -> Tuple[NuntiaGeneratedPayload, str]:
        """Chama a API com Structured Outputs e fallback automático de modelos."""
        models = [self.model_name] + [m for m in self.FALLBACK_MODELS if m != self.model_name]
        last_error = None

        for model in models:
            try:
                response = self.client.models.generate_content(
                    model=model,
                    contents=contents,
                    config=types.GenerateContentConfig(
                        system_instruction=system_instruction,
                        temperature=0.3,
                        response_mime_type="application/json",
                        response_schema=NuntiaGeneratedPayload,
                    ),
                )
                raw_text = (response.text or "").strip()
                cleaned = raw_text
                if cleaned.startswith("```"):
                    cleaned = cleaned.strip("`")
                    if cleaned.startswith("json"):
                        cleaned = cleaned[4:].strip()
                data = json.loads(cleaned)
                return (NuntiaGeneratedPayload(**data), model)
            except Exception as e:
                last_error = e
                err_str = str(e)
                if any(code in err_str for code in ("503", "429", "UNAVAILABLE", "404", "NOT_FOUND")):
                    continue
                # Se for erro fatal de schema ou outro, tenta próximo modelo
                continue

        raise RuntimeError(f"Falha ao gerar conteúdos com Gemini após tentar múltiplos modelos: {last_error}")

    def generate(self, config: NuntiaConfig) -> NuntiaOutput:
        """
        Executa o pipeline completo:
        1. Resolve dados da sessão (tVerbum API / cache SQLite ou YouTube autônomo);
        2. Monta o contexto para o Gemini;
        3. Gera os cortes, notícias e pacote social;
        4. Calcula os links de salto no YouTube e estatísticas.
        """
        start_time = time.time()

        # 1. Recuperação inteligente dos dados
        session_data = TVerbumClient.resolve_session_data(
            video_url=config.video_url,
            tverbum_api_url=config.tverbum_api_url,
            session_id=config.tverbum_session_id,
        )

        # 2. Contexto da Sessão
        context_lines = []
        if config.organization_name:
            context_lines.append(f"Câmara Municipal: {config.organization_name}")
        if config.city_and_state:
            context_lines.append(f"Localidade: {config.city_and_state}")
        if config.session_number:
            context_lines.append(f"Número da Sessão: {config.session_number}")
        if session_data.video_title:
            context_lines.append(f"Título da Transmissão: {session_data.video_title}")
        if session_data.upload_date:
            context_lines.append(f"Data da Sessão: {session_data.upload_date}")
        if config.agenda_context:
            context_lines.append(f"Pauta Oficial / Ordem do Dia:\n{config.agenda_context}")

        # Se houver dados ricos do tVerbum (Ata, Matérias, Linha do Tempo)
        if session_data.voted_matters:
            matters_str = "\n".join(
                [f"- {m.get('matter')}: {m.get('summary', '')} (Resultado: {m.get('result', '')})" for m in session_data.voted_matters]
            )
            context_lines.append(f"Matérias Votadas na Sessão (extraídas pelo tVerbum):\n{matters_str}")

        if session_data.timeline_map:
            timeline_str = "\n".join(
                [f"[{e.get('timestamp')}] {e.get('phase')}: {e.get('summary')}" for e in session_data.timeline_map[:30]]
            )
            context_lines.append(f"Linha do Tempo da Sessão (tVerbum):\n{timeline_str}")

        # Ata já redigida pelo tVerbum (grande fonte de tokens economizados!)
        if session_data.minute_body:
            context_lines.append(f"Texto Formal da Ata (gerada pelo tVerbum):\n{session_data.minute_body[:4000]}")

        prompt_body = "DADOS DE CONTEXTO DA SESSÃO:\n" + "\n".join(context_lines)

        # Adiciona a transcrição
        if session_data.transcript:
            prompt_body += f"\n\nTRANSCRIÇÃO COMPLETA DA SESSÃO COM TIMESTAMPS:\n{session_data.transcript[:65000]}"
        elif not session_data.minute_body:
            raise ValueError(
                "Não foi possível obter transcrição nem texto da ata para este vídeo. "
                "Verifique se o vídeo possui legendas ou gere a ata previamente pelo tVerbum."
            )

        # 3. Execução no Gemini
        system_instruction = self._build_system_instruction(config)
        ai_payload, used_model = self._generate_structured_with_fallback([prompt_body], system_instruction)

        # 4. Enriquecimento pós-geração (cálculo de segundos e links do YouTube)
        enriched_cuts: List[VideoCut] = []
        for i, cut in enumerate(ai_payload.cuts, 1):
            if not cut.id:
                cut.id = f"corte-{i}"
            start_sec = TVerbumClient.parse_timestamp_to_seconds(cut.start_time)
            end_sec = TVerbumClient.parse_timestamp_to_seconds(cut.end_time)
            cut.duration_seconds = max(0, end_sec - start_sec)
            cut.youtube_jump_url = f"{session_data.canonical_url}&t={start_sec}s"
            enriched_cuts.append(cut)

        elapsed = round(time.time() - start_time, 2)
        session_title = session_data.video_title or f"Sessão {config.session_number or ''}"

        # 5. Montagem do Objeto de Retorno
        return NuntiaOutput(
            id=str(uuid.uuid4()),
            video_url=session_data.canonical_url,
            video_id=session_data.video_id,
            session_title=session_title,
            session_date=session_data.upload_date or None,
            highlights=ai_payload.highlights,
            cuts=enriched_cuts,
            news=ai_payload.news,
            social=ai_payload.social,
            metadata={
                "model_used": used_model,
                "cache_source": session_data.cache_source,
                "elapsed_seconds": elapsed,
                "cuts_generated": len(enriched_cuts),
                "tverbum_integration_used": session_data.cache_source.startswith("tverbum"),
                "token_savings_strategy": "reuso_de_transcricao_e_ata" if session_data.cache_source.startswith("tverbum") else "direto",
            },
        )
