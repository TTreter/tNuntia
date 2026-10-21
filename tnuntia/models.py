"""
=============================================================================
Modelos de Dados e Esquemas de Validação (Pydantic v2) - tNuntia
=============================================================================
Define os contratos para geração de cortes, notícias e publicações para
redes sociais a partir de sessões legislativas.
"""

from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel, Field


class VideoCut(BaseModel):
    """
    Representa a sugestão de um corte/highlight do vídeo da sessão para Shorts, Reels, TikTok ou YouTube.
    """

    id: str = Field(default="", description="Identificador único do corte (ex: 'cut-1')")
    title: str = Field(..., description="Título chamativo / manchete atraente para o vídeo")
    hook: str = Field(
        ...,
        description="Gancho inicial (primeiros 3 a 5 segundos) em texto ou fala para prender a atenção do público",
    )
    start_time: str = Field(..., description="Tempo de início no vídeo no formato HH:MM:SS ou MM:SS")
    end_time: str = Field(..., description="Tempo de término no formato HH:MM:SS ou MM:SS")
    duration_seconds: int = Field(default=0, description="Duração calculada do corte em segundos")
    speaker: str = Field(default="", description="Nome do orador ou participante central daquele trecho")
    category: str = Field(
        default="Geral",
        description="Categoria temática (ex: 'Polêmica/Debate', 'Saúde', 'Educação', 'Obras', 'Votação Histórica')",
    )
    virality_score: int = Field(
        default=7,
        ge=1,
        le=10,
        description="Potencial estimado de engajamento/relevância pública de 1 a 10",
    )
    summary: str = Field(default="", description="Resumo explicativo do contexto do corte")
    captions_snippet: str = Field(default="", description="Trecho da transcrição correspondente à fala")
    suggested_hashtags: List[str] = Field(
        default_factory=list,
        description="Hashtags sugeridas para o corte (ex: ['#CamaraMunicipal', '#Educacao'])",
    )
    youtube_jump_url: Optional[str] = Field(
        default=None,
        description="Link direto do YouTube iniciando no segundo exato do corte",
    )


class SpeakerQuote(BaseModel):
    """
    Aspas ou declaração marcante de um orador na sessão plenária.
    """

    speaker: str = Field(..., description="Nome do vereador ou orador da fala")
    quote: str = Field(..., description="Citação ou fala marcante exata")


class NewsArticle(BaseModel):
    """
    Notícia jornalística completa sobre os principais acontecimentos e deliberações da sessão.
    """

    headline: str = Field(..., description="Manchete jornalística atraente e objetiva")
    deck: str = Field(default="", description="Linha fina / subtítulo explicando o impacto principal")
    lead: str = Field(
        ...,
        description="Primeiro parágrafo jornalístico respondendo: Quem, O quê, Quando, Onde, Como e Por quê",
    )
    body: str = Field(
        ...,
        description="Corpo da notícia completo com intertítulos, contexto das discussões e detalhamento",
    )
    quotes: List[SpeakerQuote] = Field(
        default_factory=list,
        description="Aspas marcantes dos oradores na sessão plenária",
    )
    legislation_summary: List[str] = Field(
        default_factory=list,
        description="Resumo pontual das matérias aprovadas, rejeitadas ou encaminhadas",
    )
    tags: List[str] = Field(
        default_factory=list,
        description="Tags e palavras-chave jornalísticas para SEO e portal da Câmara",
    )


class CarouselSlide(BaseModel):
    """
    Slide individual para postagens em carrossel no Instagram ou LinkedIn.
    """

    slide_number: int = Field(..., description="Número ordinal do slide (1, 2, 3...)")
    title: str = Field(..., description="Título ou chamada de destaque do slide")
    content: str = Field(..., description="Texto conciso (máximo 2 a 3 frases) para leitura rápida")
    visual_suggestion: str = Field(
        default="",
        description="Orientação para o designer/editor (ex: 'Foto do plenário votando', 'Ícone de alerta')",
    )


class SocialMediaPackage(BaseModel):
    """
    Conjunto completo de publicações adaptadas para múltiplas redes sociais.
    """

    # --- Instagram / Facebook ---
    instagram_caption: str = Field(
        ...,
        description="Legenda persuasiva e engajadora com espaçamento, emojis e chamada para ação (CTA)",
    )
    instagram_carousel: List[CarouselSlide] = Field(
        default_factory=list,
        description="Estrutura de 4 a 7 slides para carrossel visual informativo",
    )

    # --- X (antigo Twitter) ---
    twitter_thread: List[str] = Field(
        default_factory=list,
        description="Fio encadeado de tweets (2 a 6 postagens curtas e sequenciais com até 270 caracteres cada)",
    )

    # --- WhatsApp / Telegram ---
    whatsapp_bulletin: str = Field(
        ...,
        description="Boletim informativo direto com formatação de negrito (*), marcadores e links para listas de transmissão",
    )

    # --- LinkedIn ---
    linkedin_post: str = Field(
        default="",
        description="Texto com viés institucional, focado em governança pública, transparência e cidadania",
    )

    suggested_hashtags: List[str] = Field(
        default_factory=list,
        description="Hashtags recomendadas para ampliar o alcance orgânico",
    )


class SessionHighlights(BaseModel):
    """
    Destaques executivos da sessão para consumo rápido e assessoria de imprensa.
    """

    executive_summary: str = Field(..., description="Resumo executivo de 2 a 3 parágrafos de toda a sessão")
    main_themes: List[str] = Field(default_factory=list, description="Lista dos 3 a 5 principais temas abordados")
    key_decisions: List[str] = Field(
        default_factory=list,
        description="Decisões mais importantes tomadas pelo plenário (votações, aprovações, vetos)",
    )


class NuntiaGeneratedPayload(BaseModel):
    """
    Esquema para Structured Outputs retornado diretamente pela chamada Gemini.
    """

    highlights: SessionHighlights = Field(...)
    cuts: List[VideoCut] = Field(default_factory=list)
    news: NewsArticle = Field(...)
    social: SocialMediaPackage = Field(...)


class NuntiaConfig(BaseModel):
    """
    Configurações de entrada para o processamento de uma sessão pelo tNuntia.
    """

    # Identificação do Vídeo ou da Sessão
    video_url: str = Field(..., description="URL do vídeo da sessão no YouTube")
    session_number: Optional[str] = Field(default="", description="Número da sessão ou da ata (ex: '21/2026')")
    organization_name: str = Field(default="", description="Nome da Câmara Municipal ou entidade")
    city_and_state: str = Field(default="", description="Município e Estado (ex: 'Porto Alegre - RS')")

    # Integração tVerbum
    tverbum_session_id: Optional[str] = Field(
        default=None,
        description="ID da ata já gerada no tVerbum para reuso total de transcrição e dados estruturados",
    )
    tverbum_api_url: Optional[str] = Field(
        default=None,
        description="URL da API do tVerbum (se não informada, lê de TVERBUM_API_URL ou tenta cache local)",
    )

    # Contexto Opcional
    agenda_context: Optional[str] = Field(
        default=None,
        description="Pauta oficial / Ordem do Dia para ancorar matérias e nomes",
    )
    custom_instructions: Optional[str] = Field(
        default=None,
        description="Instruções de tom de voz ou pautas prioritárias solicitadas pelo assessor/usuário",
    )

    # Parâmetros de Geração
    audience_tone: Literal["informativo", "popular", "institucional", "critico"] = Field(
        default="informativo",
        description="Tom do conteúdo: 'informativo' (padrão jornalístico), 'popular' (linguagem simples para redes), 'institucional' (formal)",
    )
    generate_cuts: bool = Field(default=True, description="Gera lista de sugestões de cortes/highlights")
    generate_news: bool = Field(default=True, description="Gera matéria jornalística completa")
    generate_social: bool = Field(default=True, description="Gera pacote completo de redes sociais")
    cuts_limit: int = Field(default=5, ge=1, le=15, description="Quantidade máxima de cortes a sugerir")
    model_name: Optional[str] = Field(default=None, description="Modelo do Gemini a utilizar")


class NuntiaOutput(BaseModel):
    """
    Resultado completo do processamento de uma sessão pelo tNuntia.
    """

    id: str = Field(default="", description="UUID da geração no tNuntia")
    video_url: str = Field(..., description="URL canônica do YouTube")
    video_id: str = Field(default="", description="ID de 11 caracteres do YouTube")
    session_title: str = Field(default="", description="Título da sessão plenária")
    session_date: Optional[str] = Field(default=None, description="Data da sessão (ISO YYYY-MM-DD)")

    # Produtos de Comunicação
    highlights: SessionHighlights = Field(...)
    cuts: List[VideoCut] = Field(default_factory=list)
    news: NewsArticle = Field(...)
    social: SocialMediaPackage = Field(...)

    # Estatísticas técnicas
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Dados de telemetria: modelo utilizado, tokens economizados, integração tVerbum utilizada",
    )


class ExportRequest(BaseModel):
    """
    Requisição para exportação dos produtos do tNuntia.
    """

    format: Literal["md", "html", "json", "docx", "txt"] = Field(default="md")
    output: NuntiaOutput


class ClipDownloadRequest(BaseModel):
    """
    Requisição para download e recorte físico do trecho do vídeo.
    """

    video_url: str
    start_time: str
    end_time: str
    title: str = "corte_sessao"
    vertical_format: bool = False  # 9:16 para reels/shorts
