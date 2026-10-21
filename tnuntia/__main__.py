"""
CLI Interface para execução do tNuntia diretamente pelo terminal.
Exemplo:
python -m tnuntia "https://www.youtube.com/watch?v=..." --export-md
"""

import sys
import argparse
from .models import NuntiaConfig
from .ai_engine import NuntiaAIEngine
from .exporter import NuntiaExporter


def main():
    parser = argparse.ArgumentParser(
        description="tNuntia CLI - Gera cortes, notícias e posts para redes sociais de vídeos de sessões."
    )
    parser.add_argument("video_url", help="URL do vídeo da sessão no YouTube")
    parser.add_argument("--org", default="", help="Nome da Câmara Municipal ou entidade")
    parser.add_argument("--tone", default="informativo", choices=["informativo", "popular", "institucional", "critico"])
    parser.add_argument("--cuts", type=int, default=5, help="Quantidade de cortes a sugerir")
    parser.add_argument("--tverbum-id", default=None, help="ID da ata/sessão já gerada no tVerbum")
    parser.add_argument("--export-md", default=None, help="Caminho do arquivo .md para salvar o dossiê")
    parser.add_argument("--export-docx", default=None, help="Caminho do arquivo .docx para salvar o dossiê")
    parser.add_argument("--export-json", default=None, help="Caminho do arquivo .json para salvar os dados")

    args = parser.parse_args()

    print(f"🏛️ tNuntia: Iniciando processamento de {args.video_url}...")
    config = NuntiaConfig(
        video_url=args.video_url,
        organization_name=args.org,
        audience_tone=args.tone,
        cuts_limit=args.cuts,
        tverbum_session_id=args.tverbum_id,
    )

    try:
        engine = NuntiaAIEngine()
        output = engine.generate(config)

        print("\n" + "=" * 60)
        print(f"✅ Sucesso! {output.session_title}")
        print(f"⏱️ Tempo: {output.metadata.get('elapsed_seconds')}s | Modelo: {output.metadata.get('model_used')}")
        print(f"🎬 Cortes Gerados: {len(output.cuts)}")
        print("=" * 60 + "\n")

        print(f"📰 MANCHETE: {output.news.headline}")
        print(f"📝 LEAD: {output.news.lead}\n")

        print("🎬 CORTES:")
        for cut in output.cuts:
            print(f"- [{cut.start_time} - {cut.end_time}] {cut.title} (Hook: \"{cut.hook}\")")

        if args.export_md:
            NuntiaExporter.to_markdown(output, args.export_md)
            print(f"\n💾 Dossiê Markdown salvo em: {args.export_md}")

        if args.export_docx:
            NuntiaExporter.to_docx(output, args.export_docx)
            print(f"💾 Dossiê Word salvo em: {args.export_docx}")

        if args.export_json:
            NuntiaExporter.to_json(output, args.export_json)
            print(f"💾 JSON completo salvo em: {args.export_json}")

    except Exception as e:
        print(f"❌ Erro ao processar: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
