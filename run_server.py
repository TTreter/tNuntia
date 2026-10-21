"""
Inicializador local do tNuntia para Windows.
Verifica porta disponível, abre o navegador automaticamente e inicia o servidor FastAPI.
"""

import os
import sys
import socket
import threading
import time
import webbrowser
import uvicorn
from dotenv import load_dotenv

# Garante suporte a UTF-8 no console do Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Garante que o diretório raiz do projeto esteja no sys.path
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

load_dotenv(os.path.join(PROJECT_ROOT, ".env"))


def find_available_port(start_port: int = 8001, max_tries: int = 10) -> int:
    """Encontra uma porta livre a partir de start_port."""
    for port in range(start_port, start_port + max_tries):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(("127.0.0.1", port)) != 0:
                return port
    return start_port


def open_browser_delayed(url: str, delay: float = 1.5):
    """Abre o navegador padrão após o servidor iniciar."""
    time.sleep(delay)
    try:
        webbrowser.open(url)
    except Exception:
        pass


if __name__ == "__main__":
    preferred_port = int(os.getenv("PORT", 8001))
    port = find_available_port(preferred_port)
    url = f"http://localhost:{port}"

    print("=" * 60)
    print("  tNuntia v1.0 - Estúdio de Cortes, Notícias e Redes Sociais")
    print("=" * 60)
    print(f"  Interface Web : {url}")
    print(f"  Swagger API   : {url}/docs")
    print(f"  Web Component : {url}/tnuntia-studio.js")
    print("=" * 60)

    # Dispara a abertura do navegador em segundo plano
    threading.Thread(target=open_browser_delayed, args=(url,), daemon=True).start()

    uvicorn.run("tnuntia.api:app", host="0.0.0.0", port=port, reload=True)
