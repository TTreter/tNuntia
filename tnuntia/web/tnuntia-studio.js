/**
 * =============================================================================
 * Web Component <tnuntia-studio> (tNuntia v1.0.0)
 * =============================================================================
 * Componente Web standalone encapsulado em Shadow DOM para integração em
 * sistemas externos (Next.js, React, Vue, PHP/Laravel, Django, etc.).
 *
 * Exemplo de uso:
 * <script src="http://localhost:8001/tnuntia-studio.js"></script>
 * <tnuntia-studio api-base="http://localhost:8001"></tnuntia-studio>
 */

class TnuntiaStudio extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: 'open' });
    this.apiBase = this.getAttribute('api-base') || 'http://localhost:8001';
  }

  connectedCallback() {
    this.render();
  }

  setResults(data) {
    this.renderResults(data);
  }

  render() {
    this.shadowRoot.innerHTML = `
      <style>
        :host {
          display: block;
          font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
          color: #0f172a;
        }
        .container {
          border: 1px solid #e2e8f0;
          border-radius: 12px;
          padding: 24px;
          background: #ffffff;
          box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1);
        }
        .header {
          display: flex;
          align-items: center;
          gap: 10px;
          margin-bottom: 20px;
        }
        h2 { margin: 0; font-size: 20px; color: #1e3a8a; }
        .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 16px; }
        input, select {
          width: 100%;
          padding: 10px;
          border: 1px solid #cbd5e1;
          border-radius: 6px;
          font-size: 14px;
          box-sizing: border-box;
        }
        button.btn-primary {
          background: #2563eb;
          color: #ffffff;
          padding: 12px 20px;
          border: none;
          border-radius: 6px;
          font-weight: 600;
          cursor: pointer;
          width: 100%;
        }
        button.btn-primary:hover { background: #1d4ed8; }
        .results { margin-top: 24px; border-top: 1px solid #e2e8f0; padding-top: 20px; display: none; }
        .cut-item {
          background: #f8fafc;
          border: 1px solid #e2e8f0;
          padding: 12px;
          border-radius: 8px;
          margin-bottom: 10px;
        }
        .badge {
          background: #dbeafe;
          color: #1e40af;
          padding: 2px 8px;
          border-radius: 4px;
          font-size: 12px;
          font-weight: bold;
        }
      </style>

      <div class="container">
        <div class="header">
          <span>🏛️</span>
          <h2>tNuntia — Estúdio de Comunicação</h2>
        </div>

        <div class="grid">
          <div>
            <label style="font-size: 13px; font-weight: 600;">Link do YouTube:</label>
            <input type="url" id="vid-url" placeholder="https://www.youtube.com/watch?v=...">
          </div>
          <div>
            <label style="font-size: 13px; font-weight: 600;">ID da Sessão no tVerbum (Opcional):</label>
            <input type="text" id="tverb-id" placeholder="Ex: UUID da ata salva">
          </div>
        </div>

        <button class="btn-primary" id="btn-run">Gerar Cortes, Notícias e Redes Sociais</button>

        <div class="results" id="res-box">
          <h3 id="res-title"></h3>
          <p id="res-summary" style="color: #475569; font-size: 14px;"></p>
          <div id="cuts-list"></div>
        </div>
      </div>
    `;

    this.shadowRoot.getElementById('btn-run').addEventListener('click', () => this.generate());
  }

  async generate() {
    const btn = this.shadowRoot.getElementById('btn-run');
    const url = this.shadowRoot.getElementById('vid-url').value;
    const tverbumId = this.shadowRoot.getElementById('tverb-id').value;

    if (!url) {
      alert('Informe o link do YouTube.');
      return;
    }

    btn.disabled = true;
    btn.innerText = 'Processando com Gemini...';

    try {
      const res = await fetch(`${this.apiBase}/api/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          video_url: url,
          tverbum_session_id: tverbumId || null,
        })
      });

      if (!res.ok) throw new Error('Falha ao processar conteúdo');
      const data = await res.json();
      this.renderResults(data);

      this.dispatchEvent(new CustomEvent('tnuntia-ready', { detail: data, bubbles: true, composed: true }));
    } catch (e) {
      alert(e.message);
    } finally {
      btn.disabled = false;
      btn.innerText = 'Gerar Cortes, Notícias e Redes Sociais';
    }
  }

  renderResults(data) {
    const box = this.shadowRoot.getElementById('res-box');
    box.style.display = 'block';
    this.shadowRoot.getElementById('res-title').innerText = data.session_title;
    this.shadowRoot.getElementById('res-summary').innerText = data.highlights.executive_summary;

    const list = this.shadowRoot.getElementById('cuts-list');
    list.innerHTML = '<h4>🎬 Sugestões de Cortes:</h4>';
    data.cuts.forEach(c => {
      const el = document.createElement('div');
      el.className = 'cut-item';
      el.innerHTML = `
        <div style="display: flex; justify-content: space-between; margin-bottom: 4px;">
          <span class="badge">${c.start_time} - ${c.end_time}</span>
          <span style="font-size: 12px; color: #d97706; font-weight: bold;">★ Relevância ${c.virality_score}/10</span>
        </div>
        <strong>${c.title}</strong>
        <p style="font-size: 13px; margin: 4px 0 0 0; color: #475569;">Gancho: "${c.hook}"</p>
      `;
      list.appendChild(el);
    });
  }
}

customElements.define('tnuntia-studio', TnuntiaStudio);
