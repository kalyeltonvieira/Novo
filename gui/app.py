"""
Interface Gráfica Principal - IA Analisadora
============================================
Sistema completo para análise de documentos públicos com:
- Dashboard com cards e gráficos
- Upload/coleta de documentos
- Visualização do grafo de relacionamentos
- Alertas de anomalias
- Geração de relatórios
"""

import os
import sys
import json
import re
import threading
import webbrowser
from datetime import datetime
from typing import Optional, Dict, Any, List
from tkinter import filedialog, messagebox
import tkinter as tk

# Garante que a raiz do projeto está no path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import customtkinter as ctk
    from CTkMessagebox import CTkMessagebox
    from CTkTable import CTkTable
except ImportError:
    print("Instalando dependências da GUI...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "customtkinter", "CTkMessagebox", "CTkTable"])
    import customtkinter as ctk
    from CTkMessagebox import CTkMessagebox
    from CTkTable import CTkTable

from core.entrada_dados import ColetorDados
from core.leitor_universal import LeitorUniversal
from core.correlacionador import Correlacionador
from core.detector_anomalias import DetectorAnomalias
from core.base_conhecimento import BaseConhecimento
from core.camada_reports import CamadaReports
from core.entidades import (
    Documento, Alerta, Relatorio, TipoAnomalia, TipoDocumento
)

# Importação opcional do gerenciador de IA
try:
    from utils.ai_providers import AIProvider, get_ai_manager
    AI_AVAILABLE = True
except ImportError:
    AI_AVAILABLE = False


class IAAnalisadoraApp:
    """
    Aplicação principal com interface gráfica moderna.
    """

    # Paleta de cores temática
    CORES = {
        "bg_dark": "#0f1923",
        "bg_card": "#1a2a3a",
        "bg_input": "#243447",
        "primary": "#00d4ff",
        "success": "#00ff88",
        "warning": "#ffaa00",
        "danger": "#ff4444",
        "critical": "#ff0000",
        "text": "#e0e0e0",
        "text_secondary": "#8899aa",
        "border": "#2a3a4a",
    }

    def __init__(self):
        self.coletor = ColetorDados()
        self.leitor = LeitorUniversal()
        self.correlacionador = Correlacionador()
        self.detector = DetectorAnomalias()
        self.base_conhecimento = BaseConhecimento()
        self.reports = CamadaReports()

        # Configuração de IA
        self.ai_manager = get_ai_manager() if AI_AVAILABLE else None
        self.use_ai = False
        self.ai_provider = AIProvider.LOCAL if AI_AVAILABLE else None

        self.documentos: List[Documento] = []
        self.alertas: List[Alerta] = []
        self.processando = False
        self._lock = threading.Lock()  # Protege acesso concorrente a self.documentos
        self._historico_chat = []

        self._configurar_tema()
        self._criar_janela()
        self._criar_widgets()
        self._carregar_dados_iniciais()

    def _configurar_tema(self):
        """Configura o tema escuro do CustomTkinter."""
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

    def _criar_janela(self):
        """Cria a janela principal."""
        self.janela = ctk.CTk()
        self.janela.title("IA Analisadora - Cérebro da Transparência")
        self.janela.geometry("1400x850")
        self.janela.minsize(1200, 700)

        # Tenta carregar ícone
        try:
            self.janela.iconbitmap("gui/icon.ico")
        except Exception:
            pass

    def _criar_widgets(self):
        """Cria todos os widgets da interface."""
        # === TOP BAR ===
        self._criar_top_bar()

        # === CONTEÚDO PRINCIPAL ===
        self.tabview = ctk.CTkTabview(
            self.janela,
            fg_color=self.CORES["bg_dark"],
            segmented_button_fg_color=self.CORES["bg_card"],
            segmented_button_selected_color=self.CORES["primary"],
            segmented_button_selected_hover_color=self.CORES["primary"],
        )
        self.tabview.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        # Abas
        self.tab_dashboard = self.tabview.add("📊 Dashboard")
        self.tab_coleta = self.tabview.add("📂 Coleta")
        self.tab_grafo = self.tabview.add("🔗 Grafo")
        self.tab_alertas = self.tabview.add("⚠️ Alertas")
        self.tab_relatorios = self.tabview.add("📄 Relatórios")
        self.tab_chat = self.tabview.add("💬 Copilot")

        self._criar_dashboard()
        self._criar_coleta()
        self._criar_grafo()
        self._criar_alertas()
        self._criar_relatorios()
        self._criar_chat()

    def _criar_top_bar(self):
        """Cria barra superior com título e ações."""
        top_frame = ctk.CTkFrame(self.janela, height=60, fg_color=self.CORES["bg_card"])
        top_frame.pack(fill="x", padx=10, pady=10)
        top_frame.pack_propagate(False)

        # Logo/Título
        titulo = ctk.CTkLabel(
            top_frame,
            text="🧠 IA Analisadora",
            font=ctk.CTkFont(size=22, weight="bold"),
            text_color=self.CORES["primary"],
        )
        titulo.pack(side="left", padx=20, pady=10)

        subtitulo = ctk.CTkLabel(
            top_frame,
            text="O Cérebro da Transparência",
            font=ctk.CTkFont(size=12),
            text_color=self.CORES["text_secondary"],
        )
        subtitulo.pack(side="left", padx=(0, 20), pady=10)

        # Status
        self.status_label = ctk.CTkLabel(
            top_frame,
            text="✅ Pronto",
            font=ctk.CTkFont(size=12),
            text_color=self.CORES["success"],
        )
        self.status_label.pack(side="right", padx=20, pady=10)

        # Botão de processar tudo
        self.btn_processar = ctk.CTkButton(
            top_frame,
            text="▶ Processar Tudo",
            command=self.processar_tudo,
            fg_color=self.CORES["primary"],
            hover_color="#00b8e6",
            font=ctk.CTkFont(size=13, weight="bold"),
            width=150,
        )
        self.btn_processar.pack(side="right", padx=10, pady=10)

        # Seletor de provedor de IA
        if AI_AVAILABLE:
            ai_frame = ctk.CTkFrame(top_frame, fg_color="transparent")
            ai_frame.pack(side="right", padx=10, pady=10)

            ctk.CTkLabel(
                ai_frame,
                text="🤖 IA:",
                font=ctk.CTkFont(size=11),
                text_color=self.CORES["text_secondary"],
            ).pack(side="left", padx=(0, 5))

            self.ai_provider_var = ctk.StringVar(value="local")
            self.ai_provider_menu = ctk.CTkOptionMenu(
                ai_frame,
                values=["local", "openai", "anthropic", "google", "cohere", "openrouter", "groq", "together", "mistral", "ollama"],
                variable=self.ai_provider_var,
                command=self._mudar_provedor_ia,
                width=140,
                font=ctk.CTkFont(size=11),
            )
            self.ai_provider_menu.pack(side="left")

            # Checkbox para habilitar IA
            self.use_ai_var = ctk.BooleanVar(value=False)
            self.use_ai_checkbox = ctk.CTkCheckBox(
                ai_frame,
                text="Usar IA",
                variable=self.use_ai_var,
                command=self._toggle_ia,
                font=ctk.CTkFont(size=11),
            )
            self.use_ai_checkbox.pack(side="left", padx=(10, 0))

    # === DASHBOARD ===
    def _criar_dashboard(self):
        """Cria a aba de Dashboard."""
        # Frame de cards
        cards_frame = ctk.CTkFrame(self.tab_dashboard, fg_color="transparent")
        cards_frame.pack(fill="x", pady=10)

        # Cards métricas
        self.cards = {}
        metricas = [
            ("documentos", "📄 Documentos", "0", self.CORES["primary"]),
            ("entidades", "🏷️ Entidades", "0", self.CORES["success"]),
            ("alertas", "⚠️ Alertas", "0", self.CORES["warning"]),
            ("valor", "💰 Valor Total", "R$ 0,00", self.CORES["danger"]),
        ]

        for i, (key, titulo, valor, cor) in enumerate(metricas):
            card = ctk.CTkFrame(cards_frame, fg_color=self.CORES["bg_card"], corner_radius=15)
            card.grid(row=0, column=i, padx=10, pady=5, sticky="nsew")
            cards_frame.grid_columnconfigure(i, weight=1)

            ctk.CTkLabel(
                card, text=titulo,
                font=ctk.CTkFont(size=12),
                text_color=self.CORES["text_secondary"],
            ).pack(pady=(15, 5))

            label_valor = ctk.CTkLabel(
                card, text=valor,
                font=ctk.CTkFont(size=28, weight="bold"),
                text_color=cor,
            )
            label_valor.pack(pady=(0, 15))
            self.cards[key] = label_valor

        # Frame de logs
        log_frame = ctk.CTkFrame(self.tab_dashboard, fg_color=self.CORES["bg_card"], corner_radius=15)
        log_frame.pack(fill="both", expand=True, pady=10)

        ctk.CTkLabel(
            log_frame, text="📋 Log de Atividades",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=self.CORES["primary"],
        ).pack(pady=10)

        self.log_text = ctk.CTkTextbox(
            log_frame,
            fg_color=self.CORES["bg_input"],
            text_color=self.CORES["text"],
            font=ctk.CTkFont(size=11),
            height=200,
        )
        self.log_text.pack(fill="both", expand=True, padx=15, pady=(0, 15))
        self.log_text.insert("end", "Sistema iniciado. Pronto para análise.\n")

    def adicionar_log(self, mensagem: str, tipo: str = "info"):
        """Adiciona mensagem ao log."""
        cor = {
            "info": self.CORES["text"],
            "success": self.CORES["success"],
            "warning": self.CORES["warning"],
            "error": self.CORES["danger"],
            "critical": self.CORES["critical"],
        }.get(tipo, self.CORES["text"])

        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.insert("end", f"[{timestamp}] ", "timestamp")
        self.log_text.insert("end", f"{mensagem}\n", tipo)
        self.log_text.tag_config("timestamp", foreground=self.CORES["text_secondary"])
        self.log_text.tag_config(tipo, foreground=cor)
        self.log_text.see("end")

    # === COLETA ===
    def _criar_coleta(self):
        """Cria a aba de Coleta de Documentos."""
        frame = ctk.CTkScrollableFrame(self.tab_coleta, fg_color="transparent")
        frame.pack(fill="both", expand=True, pady=10)

        # Seção: Upload de Arquivos
        upload_frame = ctk.CTkFrame(frame, fg_color=self.CORES["bg_card"], corner_radius=15)
        upload_frame.pack(fill="x", pady=10, padx=10)

        ctk.CTkLabel(
            upload_frame, text="📁 Upload de Documentos",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=self.CORES["primary"],
        ).pack(pady=15)

        ctk.CTkLabel(
            upload_frame,
            text="Suporta: PDF, PNG, JPG, HTML, TXT, CSV, XLSX",
            font=ctk.CTkFont(size=11),
            text_color=self.CORES["text_secondary"],
        ).pack()

        botoes_frame = ctk.CTkFrame(upload_frame, fg_color="transparent")
        botoes_frame.pack(pady=15)

        ctk.CTkButton(
            botoes_frame,
            text="📂 Selecionar Arquivos",
            command=self.selecionar_arquivos,
            fg_color=self.CORES["primary"],
            hover_color="#00b8e6",
            width=180,
        ).pack(side="left", padx=10)

        ctk.CTkButton(
            botoes_frame,
            text="📁 Selecionar Pasta",
            command=self.selecionar_pasta,
            fg_color=self.CORES["success"],
            hover_color="#00cc6a",
            width=180,
        ).pack(side="left", padx=10)

        # Seção: URL
        url_frame = ctk.CTkFrame(frame, fg_color=self.CORES["bg_card"], corner_radius=15)
        url_frame.pack(fill="x", pady=10, padx=10)

        ctk.CTkLabel(
            url_frame, text="🌐 Coletar de URL",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=self.CORES["primary"],
        ).pack(pady=15)

        url_input_frame = ctk.CTkFrame(url_frame, fg_color="transparent")
        url_input_frame.pack(fill="x", padx=20, pady=10)

        self.url_entry = ctk.CTkEntry(
            url_input_frame,
            placeholder_text="https://exemplo.com/documento.pdf",
            fg_color=self.CORES["bg_input"],
            border_color=self.CORES["border"],
            height=40,
        )
        self.url_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))

        ctk.CTkButton(
            url_input_frame,
            text="Coletar",
            command=self.coletar_url,
            fg_color=self.CORES["primary"],
            hover_color="#00b8e6",
            width=100,
        ).pack(side="right")

        # Seção: Texto Direto
        texto_frame = ctk.CTkFrame(frame, fg_color=self.CORES["bg_card"], corner_radius=15)
        texto_frame.pack(fill="x", pady=10, padx=10)

        ctk.CTkLabel(
            texto_frame, text="📝 Texto Direto",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=self.CORES["primary"],
        ).pack(pady=15)

        self.texto_entry = ctk.CTkTextbox(
            texto_frame,
            fg_color=self.CORES["bg_input"],
            border_color=self.CORES["border"],
            height=120,
            font=ctk.CTkFont(size=12),
        )
        self.texto_entry.pack(fill="x", padx=20, pady=10)

        ctk.CTkButton(
            texto_frame,
            text="Processar Texto",
            command=self.processar_texto,
            fg_color=self.CORES["success"],
            hover_color="#00cc6a",
            width=180,
        ).pack(pady=10)

        # Seção: Portais e APIs
        portal_frame = ctk.CTkFrame(frame, fg_color=self.CORES["bg_card"], corner_radius=15)
        portal_frame.pack(fill="x", pady=10, padx=10)

        ctk.CTkLabel(
            portal_frame, text="🏛️ Portais e APIs Públicas",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=self.CORES["primary"],
        ).pack(pady=15)

        botoes_portal = ctk.CTkFrame(portal_frame, fg_color="transparent")
        botoes_portal.pack(pady=10)

        ctk.CTkButton(
            botoes_portal,
            text="TCU - Licitações",
            command=lambda: self.coletar_api_tcu("licitacoes"),
            fg_color=self.CORES["warning"],
            hover_color="#cc8800",
            width=150,
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            botoes_portal,
            text="TCU - Contratos",
            command=lambda: self.coletar_api_tcu("contratos"),
            fg_color=self.CORES["warning"],
            hover_color="#cc8800",
            width=150,
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            botoes_portal,
            text="Portal Transparência",
            command=self.coletar_portal,
            fg_color=self.CORES["warning"],
            hover_color="#cc8800",
            width=150,
        ).pack(side="left", padx=5)

    def selecionar_arquivos(self):
        """Abre seletor de arquivos."""
        arquivos = filedialog.askopenfilenames(
            title="Selecionar Documentos",
            filetypes=[
                ("Documentos", "*.pdf *.png *.jpg *.jpeg *.html *.txt *.csv *.xlsx"),
                ("PDF", "*.pdf"),
                ("Imagens", "*.png *.jpg *.jpeg"),
                ("Planilhas", "*.csv *.xlsx"),
                ("Texto", "*.txt"),
                ("HTML", "*.html"),
                ("Todos", "*.*"),
            ],
        )
        if arquivos:
            thread = threading.Thread(target=self._processar_arquivos, args=(list(arquivos),))
            thread.daemon = True
            thread.start()

    def selecionar_pasta(self):
        """Abre seletor de pasta."""
        pasta = filedialog.askdirectory(title="Selecionar Pasta com Documentos")
        if pasta:
            thread = threading.Thread(target=self._processar_pasta, args=(pasta,))
            thread.daemon = True
            thread.start()

    def _processar_arquivos(self, caminhos: list):
        """Processa arquivos em background."""
        self._set_processando(True)
        try:
            for caminho in caminhos:
                doc = self.leitor.processar_documento(caminho)
                if doc:
                    with self._lock:
                        self.documentos.append(doc)
                    self.janela.after(0, lambda d=doc: self.adicionar_log(
                        f"✅ Documento processado: {os.path.basename(d.fonte)} "
                        f"({len(d.entidades)} entidades encontradas)",
                        "success"
                    ))
                    self.janela.after(0, self._atualizar_dashboard)

            self.janela.after(0, lambda: self.adicionar_log(
                f"📊 Total: {len(caminhos)} arquivos processados", "success"
            ))
            # Persiste documentos
            self._salvar_documentos()
        finally:
            self._set_processando(False)

    def _processar_pasta(self, pasta: str):
        """Processa pasta em background."""
        self._set_processando(True)
        try:
            caminhos = self.coletor.coletar_pasta(pasta)
            self._processar_arquivos(caminhos)
        finally:
            self._set_processando(False)

    def coletar_url(self):
        """Coleta documento de URL."""
        url = self.url_entry.get().strip()
        if not url:
            CTkMessagebox(title="Aviso", message="Digite uma URL!", icon="warning")
            return

        thread = threading.Thread(target=self._processar_url, args=(url,))
        thread.daemon = True
        thread.start()

    def _processar_url(self, url: str):
        """Processa URL em background."""
        self._set_processando(True)
        try:
            doc = self.leitor.processar_url(url)
            if doc:
                with self._lock:
                    self.documentos.append(doc)
                self.janela.after(0, lambda: self.adicionar_log(
                    f"✅ URL processada: {url[:50]}... ({len(doc.entidades)} entidades)",
                    "success"
                ))
                self.janela.after(0, self._atualizar_dashboard)
                self._salvar_documentos()
            else:
                self.janela.after(0, lambda: self.adicionar_log(
                    f"❌ Falha ao processar URL: {url}", "error"
                ))
        finally:
            self._set_processando(False)

    def processar_texto(self):
        """Processa texto inserido diretamente."""
        texto = self.texto_entry.get("1.0", "end").strip()
        if not texto:
            CTkMessagebox(title="Aviso", message="Digite um texto!", icon="warning")
            return

        thread = threading.Thread(target=self._processar_texto_bg, args=(texto,))
        thread.daemon = True
        thread.start()

    def _processar_texto_bg(self, texto: str):
        """Processa texto em background."""
        self._set_processando(True)
        try:
            doc = self.leitor.processar_texto_direto(texto)
            with self._lock:
                self.documentos.append(doc)
            self.janela.after(0, lambda: self.adicionar_log(
                f"✅ Texto processado ({len(doc.entidades)} entidades)", "success"
            ))
            self.janela.after(0, self._atualizar_dashboard)
            self._salvar_documentos()
        finally:
            self._set_processando(False)

    def coletar_api_tcu(self, tipo: str):
        """Coleta dados da API do TCU."""
        thread = threading.Thread(target=self._processar_api_tcu, args=(tipo,))
        thread.daemon = True
        thread.start()

    def _processar_api_tcu(self, tipo: str):
        """Processa dados do TCU em background."""
        self._set_processando(True)
        try:
            dados = self.coletor.coletar_tcu(tipo, ano=datetime.now().year)
            if dados:
                texto = json.dumps(dados, ensure_ascii=False)
                doc = self.leitor.processar_texto_direto(texto, fonte=f"TCU-{tipo}")
                self.documentos.append(doc)
                self.janela.after(0, lambda: self.adicionar_log(
                    f"✅ TCU {tipo}: {len(dados)} registros processados", "success"
                ))
                self.janela.after(0, self._atualizar_dashboard)
            else:
                self.janela.after(0, lambda: self.adicionar_log(
                    f"❌ Nenhum dado encontrado no TCU ({tipo})", "warning"
                ))
        finally:
            self._set_processando(False)

    def coletar_portal(self):
        """Coleta dados de portal da transparência."""
        url = ctk.CTkInputDialog(
            text="Digite a URL do Portal da Transparência:",
            title="Coletar Portal",
        ).get_input()

        if url:
            thread = threading.Thread(target=self._processar_portal, args=(url,))
            thread.daemon = True
            thread.start()

    def _processar_portal(self, url: str):
        """Processa portal em background."""
        self._set_processando(True)
        try:
            dados = self.coletor.coletar_portal_transparencia(url)
            if dados:
                texto = json.dumps(dados, ensure_ascii=False)
                doc = self.leitor.processar_texto_direto(texto, fonte=url)
                self.documentos.append(doc)
                self.janela.after(0, lambda: self.adicionar_log(
                    f"✅ Portal: {len(dados)} registros extraídos", "success"
                ))
                self.janela.after(0, self._atualizar_dashboard)
            else:
                self.janela.after(0, lambda: self.adicionar_log(
                    f"❌ Nenhum dado encontrado no portal", "warning"
                ))
        finally:
            self._set_processando(False)

    # === GRAFO ===
    def _criar_grafo(self):
        """Cria a aba de visualização do Grafo."""
        frame = ctk.CTkFrame(self.tab_grafo, fg_color="transparent")
        frame.pack(fill="both", expand=True)

        # Controles
        controle_frame = ctk.CTkFrame(frame, fg_color=self.CORES["bg_card"], corner_radius=15)
        controle_frame.pack(fill="x", pady=10)

        ctk.CTkLabel(
            controle_frame, text="🔗 Grafo de Relacionamentos",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=self.CORES["primary"],
        ).pack(pady=10)

        btn_frame = ctk.CTkFrame(controle_frame, fg_color="transparent")
        btn_frame.pack(pady=10)

        ctk.CTkButton(
            btn_frame,
            text="🔄 Atualizar Grafo",
            command=self.atualizar_grafo_html,
            fg_color=self.CORES["primary"],
            hover_color="#00b8e6",
            width=180,
        ).pack(side="left", padx=10)

        ctk.CTkButton(
            btn_frame,
            text="🌐 Abrir no Navegador",
            command=self.abrir_grafo_navegador,
            fg_color=self.CORES["success"],
            hover_color="#00cc6a",
            width=180,
        ).pack(side="left", padx=10)

        # Área de visualização
        self.grafo_frame = ctk.CTkFrame(frame, fg_color=self.CORES["bg_card"], corner_radius=15)
        self.grafo_frame.pack(fill="both", expand=True, pady=10)

        self.grafo_label = ctk.CTkLabel(
            self.grafo_frame,
            text="💡 Nenhum dado processado ainda.\n\nCarregue documentos na aba 'Coleta'\ne clique em 'Atualizar Grafo'.",
            font=ctk.CTkFont(size=14),
            text_color=self.CORES["text_secondary"],
        )
        self.grafo_label.pack(expand=True)

    def atualizar_grafo_html(self):
        """Gera e exibe o grafo HTML."""
        if not self.documentos:
            CTkMessagebox(title="Aviso", message="Nenhum documento para analisar. Carregue documentos primeiro!", icon="warning")
            return

        thread = threading.Thread(target=self._gerar_grafo_bg)
        thread.daemon = True
        thread.start()

    def _gerar_grafo_bg(self):
        """Gera grafo em background."""
        self._set_processando(True)
        try:
            # Pipeline completo
            self.correlacionador = Correlacionador()
            relacionamentos = self.correlacionador.processar_documentos(self.documentos)

            self.base_conhecimento = BaseConhecimento()
            for doc in self.documentos:
                self.base_conhecimento.adicionar_entidades(doc.entidades)
            self.base_conhecimento.adicionar_relacionamentos(relacionamentos)
            self.base_conhecimento.adicionar_pessoas(self.correlacionador.pessoas)
            self.base_conhecimento.adicionar_empresas(self.correlacionador.empresas)

            dados_grafo = self.base_conhecimento.exportar_para_vis()
            html_grafo = self._gerar_html_grafo(dados_grafo)

            caminho = os.path.join("data", "grafo_visualizacao.html")
            os.makedirs("data", exist_ok=True)
            with open(caminho, "w", encoding="utf-8") as f:
                f.write(html_grafo)

            self.janela.after(0, lambda: self.grafo_label.configure(
                text=f"✅ Grafo gerado com {len(dados_grafo['nodes'])} nós e {len(dados_grafo['edges'])} arestas.\n"
                     f"📁 Arquivo salvo em: {caminho}\n\nClique em 'Abrir no Navegador' para visualizar.",
                text_color=self.CORES["success"],
            ))
            self.janela.after(0, lambda: self.adicionar_log(
                f"🔗 Grafo gerado: {len(dados_grafo['nodes'])} entidades, {len(dados_grafo['edges'])} relações",
                "success",
            ))

        except Exception as e:
            self.janela.after(0, lambda: self.adicionar_log(f"❌ Erro ao gerar grafo: {e}", "error"))
        finally:
            self._set_processando(False)

    def _gerar_html_grafo(self, dados: dict) -> str:
        """Gera HTML com visualização interativa do grafo (vis.js)."""
        nodes_json = json.dumps(dados.get("nodes", []))
        edges_json = json.dumps(dados.get("edges", []))

        return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Grafo - IA Analisadora</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ background: #0f1923; font-family: 'Segoe UI', Tahoma, sans-serif; }}
        #mynetwork {{ width: 100%; height: 100vh; }}
        .info {{ position: fixed; bottom: 20px; left: 50%; transform: translateX(-50%);
                 background: #1a2a3a; color: #e0e0e0; padding: 10px 20px; border-radius: 8px;
                 border: 1px solid #2a3a4a; font-size: 13px; }}
    </style>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/vis/4.21.0/vis.min.js"></script>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/vis/4.21.0/vis.min.css">
</head>
<body>
    <div id="mynetwork"></div>
    <div class="info">🖱️ Arraste para navegar • Scroll para zoom • Clique nos nós para detalhes</div>
    <script>
        const nodes = new vis.DataSet({nodes_json});
        const edges = new vis.DataSet({edges_json});

        const container = document.getElementById('mynetwork');
        const data = {{ nodes, edges }};
        const options = {{
            physics: {{
                stabilization: true,
                barnesHut: {{ gravitationalConstant: -3000, springLength: 150, springConstant: 0.04 }},
            }},
            interaction: {{ hover: true, tooltipDelay: 200, navigationButtons: true, keyboard: true }},
            nodes: {{
                font: {{ color: '#e0e0e0', size: 12, face: 'Segoe UI' }},
                borderWidth: 2,
                shadow: {{ enabled: true, size: 10 }},
            }},
            edges: {{
                font: {{ color: '#8899aa', size: 10, align: 'middle' }},
                smooth: {{ type: 'continuous' }},
                arrows: {{ to: {{ enabled: true, scaleFactor: 0.5 }} }},
            }},
            groups: {{
                pessoa: {{ color: {{ background: '#00d4ff', border: '#0099cc' }}, shape: 'dot', size: 20 }},
                empresa: {{ color: {{ background: '#ff6600', border: '#cc5200' }}, shape: 'square', size: 25 }},
                orgao_publico: {{ color: {{ background: '#00ff88', border: '#00cc6a' }}, shape: 'star', size: 30 }},
                valor: {{ color: {{ background: '#ff4444', border: '#cc0000' }}, shape: 'diamond', size: 15 }},
                alerta: {{ color: {{ background: '#ff0000', border: '#cc0000' }}, shape: 'triangle', size: 20 }},
                contrato: {{ color: {{ background: '#ffaa00', border: '#cc8800' }}, shape: 'hexagon', size: 22 }},
                default: {{ color: {{ background: '#8899aa', border: '#667788' }}, shape: 'dot', size: 15 }},
            }},
        }};

        const network = new vis.Network(container, data, options);

        network.on('click', function(params) {{
            if (params.nodes.length > 0) {{
                const nodeId = params.nodes[0];
                const node = nodes.get(nodeId);
                alert('🔍 Entidade: ' + (node.label || nodeId) + '\\n\\n' +
                      '📋 Dados: ' + JSON.stringify(node, null, 2));
            }}
        }});
    </script>
</body>
</html>"""

    def abrir_grafo_navegador(self):
        """Abre o grafo no navegador padrão."""
        caminho = os.path.join("data", "grafo_visualizacao.html")
        if os.path.exists(caminho):
            webbrowser.open(f"file://{os.path.abspath(caminho)}")
        else:
            CTkMessagebox(title="Aviso", message="Gere o grafo primeiro clicando em 'Atualizar Grafo'!", icon="warning")

    # === ALERTAS ===
    def _criar_alertas(self):
        """Cria a aba de Alertas."""
        frame = ctk.CTkFrame(self.tab_alertas, fg_color="transparent")
        frame.pack(fill="both", expand=True)

        # Controles
        controle_frame = ctk.CTkFrame(frame, fg_color=self.CORES["bg_card"], corner_radius=15)
        controle_frame.pack(fill="x", pady=10)

        ctk.CTkLabel(
            controle_frame, text="⚠️ Detector de Anomalias",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=self.CORES["primary"],
        ).pack(pady=10)

        ctk.CTkButton(
            controle_frame,
            text="🔍 Detectar Anomalias",
            command=self.detectar_anomalias,
            fg_color=self.CORES["danger"],
            hover_color="#cc0000",
            font=ctk.CTkFont(size=14, weight="bold"),
            width=250,
        ).pack(pady=15)

        # Área de resultados
        self.alertas_frame = ctk.CTkScrollableFrame(frame, fg_color=self.CORES["bg_card"], corner_radius=15)
        self.alertas_frame.pack(fill="both", expand=True, pady=10)

        self.alertas_label = ctk.CTkLabel(
            self.alertas_frame,
            text="💡 Clique em 'Detectar Anomalias' para analisar os documentos processados.",
            font=ctk.CTkFont(size=14),
            text_color=self.CORES["text_secondary"],
        )
        self.alertas_label.pack(pady=30)

    def detectar_anomalias(self):
        """Executa detecção de anomalias."""
        if not self.documentos:
            CTkMessagebox(title="Aviso", message="Nenhum documento para analisar!", icon="warning")
            return

        thread = threading.Thread(target=self._detectar_anomalias_bg)
        thread.daemon = True
        thread.start()

    def _detectar_anomalias_bg(self):
        """Detecta anomalias em background."""
        self._set_processando(True)
        try:
            # Pipeline completo
            self.correlacionador = Correlacionador()
            relacionamentos = self.correlacionador.processar_documentos(self.documentos)

            self.detector = DetectorAnomalias()
            self.alertas = self.detector.processar(
                self.documentos,
                relacionamentos,
                self.correlacionador.pessoas,
                self.correlacionador.empresas,
            )

            # Atualiza base de conhecimento
            self.base_conhecimento.adicionar_alertas(self.alertas)

            self.janela.after(0, self._exibir_alertas)
            self.janela.after(0, self._atualizar_dashboard)

        except Exception as e:
            self.janela.after(0, lambda: self.adicionar_log(f"❌ Erro ao detectar anomalias: {e}", "error"))
        finally:
            self._set_processando(False)

    def _exibir_alertas(self):
        """Exibe alertas na interface."""
        for widget in self.alertas_frame.winfo_children():
            widget.destroy()

        if not self.alertas:
            ctk.CTkLabel(
                self.alertas_frame,
                text="✅ Nenhuma anomalia detectada!",
                font=ctk.CTkFont(size=16, weight="bold"),
                text_color=self.CORES["success"],
            ).pack(pady=30)
            return

        # Cards de resumo
        resumo_frame = ctk.CTkFrame(self.alertas_frame, fg_color="transparent")
        resumo_frame.pack(fill="x", pady=10)

        criticos = sum(1 for a in self.alertas if a.severidade == "critica")
        altos = sum(1 for a in self.alertas if a.severidade == "alta")
        medios = sum(1 for a in self.alertas if a.severidade == "media")

        ctk.CTkLabel(
            resumo_frame,
            text=f"🔴 Críticos: {criticos}  |  🟠 Altos: {altos}  |  🟡 Médios: {medios}  |  Total: {len(self.alertas)}",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=self.CORES["text"],
        ).pack(pady=10)

        # Lista de alertas
        for alerta in self.alertas[:50]:
            cor_sev = {
                "critica": self.CORES["critical"],
                "alta": self.CORES["danger"],
                "media": self.CORES["warning"],
                "baixa": self.CORES["primary"],
            }.get(alerta.severidade, self.CORES["text"])

            alerta_card = ctk.CTkFrame(
                self.alertas_frame,
                fg_color=self.CORES["bg_input"],
                corner_radius=10,
                border_width=1,
                border_color=cor_sev,
            )
            alerta_card.pack(fill="x", pady=5, padx=10)

            header = ctk.CTkFrame(alerta_card, fg_color="transparent")
            header.pack(fill="x", padx=15, pady=(10, 5))

            ctk.CTkLabel(
                header,
                text=alerta.titulo,
                font=ctk.CTkFont(size=14, weight="bold"),
                text_color=cor_sev,
            ).pack(side="left")

            ctk.CTkLabel(
                header,
                text=alerta.tipo.value.upper(),
                font=ctk.CTkFont(size=10),
                text_color=self.CORES["text_secondary"],
            ).pack(side="right", padx=10)

            ctk.CTkLabel(
                alerta_card,
                text=f"{alerta.descricao[:300]}...",
                font=ctk.CTkFont(size=11),
                text_color=self.CORES["text"],
                wraplength=800,
                justify="left",
            ).pack(fill="x", padx=15, pady=(0, 5))

            footer = ctk.CTkFrame(alerta_card, fg_color="transparent")
            footer.pack(fill="x", padx=15, pady=(0, 10))

            ctk.CTkLabel(
                footer,
                text=f"Confiança: {alerta.score_confianca:.0%}",
                font=ctk.CTkFont(size=10),
                text_color=self.CORES["text_secondary"],
            ).pack(side="left", padx=(0, 20))

            if alerta.valor_envolvido:
                ctk.CTkLabel(
                    footer,
                    text=f"Valor: R$ {alerta.valor_envolvido:,.2f}",
                    font=ctk.CTkFont(size=10),
                    text_color=self.CORES["warning"],
                ).pack(side="left")

        self.adicionar_log(f"⚠️ {len(self.alertas)} anomalias detectadas!", "warning")

    # === RELATÓRIOS ===
    def _criar_relatorios(self):
        """Cria a aba de Relatórios."""
        frame = ctk.CTkFrame(self.tab_relatorios, fg_color="transparent")
        frame.pack(fill="both", expand=True)

        # Controles
        controle_frame = ctk.CTkFrame(frame, fg_color=self.CORES["bg_card"], corner_radius=15)
        controle_frame.pack(fill="x", pady=10)

        ctk.CTkLabel(
            controle_frame, text="📄 Geração de Relatórios",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=self.CORES["primary"],
        ).pack(pady=15)

        botoes_frame = ctk.CTkFrame(controle_frame, fg_color="transparent")
        botoes_frame.pack(pady=10)

        ctk.CTkButton(
            botoes_frame,
            text="📊 Gerar Relatório HTML",
            command=self.gerar_relatorio_html,
            fg_color=self.CORES["primary"],
            hover_color="#00b8e6",
            width=200,
        ).pack(side="left", padx=10)

        ctk.CTkButton(
            botoes_frame,
            text="📁 Exportar JSON",
            command=self.exportar_json,
            fg_color=self.CORES["success"],
            hover_color="#00cc6a",
            width=200,
        ).pack(side="left", padx=10)

        ctk.CTkButton(
            botoes_frame,
            text="📋 Relatório de Denúncia",
            command=self.gerar_denuncia,
            fg_color=self.CORES["danger"],
            hover_color="#cc0000",
            width=200,
        ).pack(side="left", padx=10)

        # Área de resultados
        self.relatorio_frame = ctk.CTkFrame(frame, fg_color=self.CORES["bg_card"], corner_radius=15)
        self.relatorio_frame.pack(fill="both", expand=True, pady=10)

        self.relatorio_text = ctk.CTkTextbox(
            self.relatorio_frame,
            fg_color=self.CORES["bg_input"],
            text_color=self.CORES["text"],
            font=ctk.CTkFont(size=12),
        )
        self.relatorio_text.pack(fill="both", expand=True, padx=15, pady=15)
        self.relatorio_text.insert("end", "💡 Clique em um botão acima para gerar relatórios.\n\n")

    def gerar_relatorio_html(self):
        """Gera relatório HTML completo."""
        if not self.documentos:
            CTkMessagebox(title="Aviso", message="Nenhum documento para gerar relatório!", icon="warning")
            return

        thread = threading.Thread(target=self._gerar_relatorio_html_bg)
        thread.daemon = True
        thread.start()

    def _gerar_relatorio_html_bg(self):
        """Gera relatório em background."""
        self._set_processando(True)
        try:
            # Garante que o pipeline de correlação foi executado
            if not self.correlacionador.relacionamentos and self.documentos:
                self.correlacionador = Correlacionador()
                self.correlacionador.processar_documentos(self.documentos)

            dados_dashboard = self.reports.gerar_dashboard(
                self.documentos, self.alertas,
                self.correlacionador.relacionamentos,
                self.correlacionador.pessoas,
                self.correlacionador.empresas,
            )
            caminho = self.reports.exportar_html(dados_dashboard)

            self.janela.after(0, lambda: self.relatorio_text.delete("1.0", "end"))
            self.janela.after(0, lambda: self.relatorio_text.insert("end",
                f"✅ Relatório HTML gerado com sucesso!\n\n"
                f"📁 Arquivo: {caminho}\n\n"
                f"📊 Dados incluídos:\n"
                f"  • {dados_dashboard['resumo']['total_documentos']} documentos\n"
                f"  • {dados_dashboard['resumo']['total_alertas']} alertas\n"
                f"  • R$ {dados_dashboard['resumo']['valor_total_envolvido']:,.2f} em valores\n\n"
                f"Abra o arquivo no navegador para visualizar o relatório completo."
            ))
            self.janela.after(0, lambda: self.adicionar_log(
                f"📄 Relatório HTML gerado: {caminho}", "success"
            ))

            # Abre no navegador
            webbrowser.open(f"file://{os.path.abspath(caminho)}")

        except Exception as e:
            self.janela.after(0, lambda: self.adicionar_log(f"❌ Erro ao gerar relatório: {e}", "error"))
        finally:
            self._set_processando(False)

    def exportar_json(self):
        """Exporta dados para JSON."""
        if not self.documentos:
            CTkMessagebox(title="Aviso", message="Nenhum dado para exportar!", icon="warning")
            return

        thread = threading.Thread(target=self._exportar_json_bg)
        thread.daemon = True
        thread.start()

    def _exportar_json_bg(self):
        """Exporta JSON em background."""
        self._set_processando(True)
        try:
            # Garante que o pipeline de correlação foi executado
            if not self.correlacionador.relacionamentos and self.documentos:
                self.correlacionador = Correlacionador()
                self.correlacionador.processar_documentos(self.documentos)

            dados_dashboard = self.reports.gerar_dashboard(
                self.documentos, self.alertas,
                self.correlacionador.relacionamentos,
                self.correlacionador.pessoas,
                self.correlacionador.empresas,
            )
            caminho = self.reports.exportar_json(dados_dashboard)

            self.janela.after(0, lambda: self.relatorio_text.delete("1.0", "end"))
            self.janela.after(0, lambda: self.relatorio_text.insert("end",
                f"✅ Dados exportados para JSON!\n\n"
                f"📁 Arquivo: {caminho}"
            ))
            self.janela.after(0, lambda: self.adicionar_log(
                f"📁 JSON exportado: {caminho}", "success"
            ))

        except Exception as e:
            self.janela.after(0, lambda: self.adicionar_log(f"❌ Erro ao exportar JSON: {e}", "error"))
        finally:
            self._set_processando(False)

    def gerar_denuncia(self):
        """Gera relatório de denúncia."""
        if not self.alertas:
            CTkMessagebox(title="Aviso", message="Nenhum alerta para gerar denúncia! Detecte anomalias primeiro.", icon="warning")
            return

        # Seleciona alerta mais crítico
        alerta = max(self.alertas, key=lambda a: (
            {"critica": 0, "alta": 1, "media": 2, "baixa": 3}[a.severidade],
            a.score_confianca
        ))

        denuncia = self.reports.gerar_relatorio_denuncia(alerta, [])

        self.relatorio_text.delete("1.0", "end")
        self.relatorio_text.insert("end",
            f"📋 RELATÓRIO DE DENÚNCIA\n"
            f"{'='*60}\n\n"
            f"📌 Título: {denuncia['titulo']}\n"
            f"📅 Data: {denuncia['data_geracao']}\n\n"
            f"📝 Resumo:\n{denuncia['resumo']}\n\n"
            f"🔍 Detalhes:\n"
            f"  • Tipo: {denuncia['detalhes']['tipo_anomalia']}\n"
            f"  • Severidade: {denuncia['detalhes']['severidade'].upper()}\n"
            f"  • Confiança: {denuncia['detalhes']['confianca']}\n"
            f"  • Data detecção: {denuncia['detalhes']['data_deteccao']}\n"
            f"  • Status: {denuncia['detalhes']['status']}\n"
        )
        if denuncia['detalhes']['valor_envolvido']:
            self.relatorio_text.insert("end",
                f"  • Valor envolvido: R$ {denuncia['detalhes']['valor_envolvido']:,.2f}\n\n"
            )

        self.adicionar_log(f"📋 Relatório de denúncia gerado: {alerta.titulo}", "warning")

    # === CHAT COPILOT ===
    def _criar_chat(self):
        """Cria a aba do Chat Copilot."""
        frame = ctk.CTkFrame(self.tab_chat, fg_color="transparent")
        frame.pack(fill="both", expand=True)
        
        # Histórico de Mensagens
        self.chat_scroll = ctk.CTkScrollableFrame(frame, fg_color=self.CORES["bg_card"], corner_radius=15)
        self.chat_scroll.pack(fill="both", expand=True, pady=(10, 5), padx=10)
        
        # Área de Input
        input_frame = ctk.CTkFrame(frame, fg_color=self.CORES["bg_card"], corner_radius=15, height=60)
        input_frame.pack(fill="x", pady=(5, 10), padx=10)
        input_frame.pack_propagate(False)
        
        self.chat_entry = ctk.CTkEntry(
            input_frame, 
            placeholder_text="Pergunte à IA ou cole um link para analisar...",
            fg_color=self.CORES["bg_input"],
            border_color=self.CORES["border"]
        )
        self.chat_entry.pack(side="left", fill="both", expand=True, padx=(10, 5), pady=10)
        self.chat_entry.bind("<Return>", lambda e: self._enviar_mensagem_chat())
        
        self.btn_chat_enviar = ctk.CTkButton(
            input_frame, 
            text="Enviar", 
            command=self._enviar_mensagem_chat,
            fg_color=self.CORES["primary"],
            hover_color="#00b8e6",
            width=100
        )
        self.btn_chat_enviar.pack(side="right", padx=(5, 10), pady=10)
        
        self._adicionar_balao_chat("IA", "Olá! Sou a IA Analisadora. Como posso ajudar com a sua auditoria hoje? Cole links de prefeituras ou portais se quiser que eu os leia para você!")

    def _adicionar_balao_chat(self, remetente, mensagem):
        """Adiciona um balão de fala no chat."""
        balao = ctk.CTkFrame(self.chat_scroll, fg_color="transparent")
        balao.pack(fill="x", pady=5, padx=5)
        
        cor_nome = self.CORES["success"] if remetente == "Usuário" else self.CORES["primary"]
        alinhamento = "e" if remetente == "Usuário" else "w"
        
        ctk.CTkLabel(
            balao, 
            text=f"[{remetente}]", 
            font=ctk.CTkFont(size=12, weight="bold"), 
            text_color=cor_nome
        ).pack(anchor=alinhamento)
        
        texto_msg = ctk.CTkLabel(
            balao, 
            text=mensagem,
            font=ctk.CTkFont(size=12),
            text_color=self.CORES["text"],
            wraplength=900,
            justify="left" if remetente == "IA" else "right"
        )
        texto_msg.pack(anchor=alinhamento)
        
        # Desce a barra de rolagem ao adicionar msg
        self.janela.after(50, lambda: self.chat_scroll._parent_canvas.yview_moveto(1.0))

    def _enviar_mensagem_chat(self):
        """Dispara ao enviar uma mensagem no chat."""
        texto = self.chat_entry.get().strip()
        if not texto: return
        
        self.chat_entry.delete(0, "end")
        self._adicionar_balao_chat("Usuário", texto)
        
        if not AI_AVAILABLE or not self.use_ai:
            self._adicionar_balao_chat("IA", "⚠️ Por favor, habilite a IA no painel superior (Usar IA) para conversarmos.")
            return
            
        self.btn_chat_enviar.configure(state="disabled")
        self.chat_entry.configure(state="disabled")
        
        thread = threading.Thread(target=self._processar_chat_bg, args=(texto,))
        thread.daemon = True
        thread.start()

    def _processar_chat_bg(self, texto_usuario):
        """Processa a requisição do chat em background."""
        try:
            prompt_final = texto_usuario
            
            # Detecta URLs no prompt
            urls = re.findall(r'(https?://[^\s]+)', texto_usuario)
            textos_coletados = []
            if urls:
                self.janela.after(0, lambda: self._adicionar_balao_chat("IA", "⏳ Detecção de link! Acessando o site para ler o conteúdo..."))
                for url in urls:
                    dados = self.coletor.coletar_url(url)
                    if dados and 'conteudo' in dados:
                        from bs4 import BeautifulSoup
                        soup = BeautifulSoup(dados['conteudo'], "html.parser")
                        textos_coletados.append(f"Conteúdo de {url}:\n{soup.get_text(strip=True)[:5000]}")
                
                if textos_coletados:
                    prompt_final += "\n\n=== CONTEÚDO DOS LINKS COLETADOS ===\n" + "\n".join(textos_coletados)
            
            # Constroi contexto (histórico)
            contexto = "Histórico da conversa:\n"
            for m in self._historico_chat[-6:]:
                contexto += f"{m['role']}: {m['content']}\n"
            
            prompt_completo = contexto + f"\nNova Mensagem do Usuário: {prompt_final}"
            
            client = self.ai_manager.get_client()
            if not client or not client.is_available():
                resposta = "Desculpe, o provedor de IA atual não está disponível."
            else:
                resposta = client.chat_completion(
                    prompt=prompt_completo,
                    system_prompt="Você é a 'IA Analisadora', uma especialista em auditoria e investigação de anomalias públicas. Responda de forma direta, clara e inteligente. Considere o histórico e analise os links se forem fornecidos no prompt.",
                    max_tokens=1500
                )
                
            if not resposta:
                resposta = "Ocorreu um erro ao obter a resposta da IA. Tente outro provedor."
            
            # Salva no historico
            self._historico_chat.append({"role": "Usuário", "content": texto_usuario})
            self._historico_chat.append({"role": "IA Analisadora", "content": resposta})
            
            self.janela.after(0, lambda: self._adicionar_balao_chat("IA", resposta))
            
        except Exception as e:
            self.janela.after(0, lambda: self._adicionar_balao_chat("IA", f"❌ Erro no chat: {e}"))
        finally:
            self.janela.after(0, lambda: self.btn_chat_enviar.configure(state="normal"))
            self.janela.after(0, lambda: self.chat_entry.configure(state="normal"))
            self.janela.after(0, lambda: self.chat_entry.focus())

    # === MÉTODOS AUXILIARES ===
    def _mudar_provedor_ia(self, choice):
        """Muda o provedor de IA selecionado."""
        if not AI_AVAILABLE:
            return
        
        provider_map = {
            "local": AIProvider.LOCAL,
            "openai": AIProvider.OPENAI,
            "anthropic": AIProvider.ANTHROPIC,
            "google": AIProvider.GOOGLE,
            "cohere": AIProvider.COHERE,
            "openrouter": AIProvider.OPENROUTER,
            "groq": AIProvider.GROQ,
            "together": AIProvider.TOGETHER,
            "mistral": AIProvider.MISTRAL,
            "ollama": AIProvider.OLLAMA,
        }
        
        self.ai_provider = provider_map.get(choice, AIProvider.LOCAL)
        
        if self.ai_manager:
            self.ai_manager.set_provider(self.ai_provider)
        
        self.adicionar_log(f"🤖 Provedor de IA alterado para: {choice}", "info")
        
        # Se mudou para local, desabilita checkbox
        if choice == "local":
            self.use_ai_var.set(False)
            self.use_ai = False
        else:
            # Verifica se o provedor está disponível
            client = self.ai_manager.get_client(self.ai_provider) if self.ai_manager else None
            if client and not client.is_available():
                CTkMessagebox(
                    title="Aviso",
                    message=f"API key para {choice.upper()} não configurada. Configure no arquivo .env",
                    icon="warning"
                )
                self.use_ai_var.set(False)

    def _toggle_ia(self):
        """Alterna o uso de IA."""
        if not AI_AVAILABLE:
            return
        
        self.use_ai = self.use_ai_var.get()
        
        if self.use_ai:
            # Atualiza configuração dos componentes
            provider = self.ai_provider_var.get()
            self._mudar_provedor_ia(provider)
            
            # Reconfigura leitor e detector com IA
            self.leitor = LeitorUniversal(config={"use_ai": True})
            self.detector = DetectorAnomalias(config={"use_ai": True})
            
            self.adicionar_log("🤖 IA habilitada para análise", "success")
        else:
            # Reconfigura sem IA
            self.leitor = LeitorUniversal(config={"use_ai": False})
            self.detector = DetectorAnomalias(config={"use_ai": False})
            
            self.adicionar_log("🤖 IA desabilitada. Usando spaCy local.", "info")

    def processar_tudo(self):
        """Executa o pipeline completo."""
        if not self.documentos:
            CTkMessagebox(title="Aviso", message="Nenhum documento para processar! Carregue documentos na aba 'Coleta'.", icon="warning")
            return

        thread = threading.Thread(target=self._processar_tudo_bg)
        thread.daemon = True
        thread.start()

    def _processar_tudo_bg(self):
        """Pipeline completo em background."""
        self._set_processando(True)
        try:
            self.janela.after(0, lambda: self.adicionar_log("🔄 Iniciando pipeline completo...", "info"))

            # 1. Correlacionar
            self.janela.after(0, lambda: self.adicionar_log("🔄 Correlacionando entidades...", "info"))
            relacionamentos = self.correlacionador.processar_documentos(self.documentos)
            self.janela.after(0, lambda: self.adicionar_log(
                f"✅ {len(relacionamentos)} relacionamentos encontrados", "success"
            ))

            # 2. Detectar anomalias
            self.janela.after(0, lambda: self.adicionar_log("🔄 Detectando anomalias...", "info"))
            self.detector = DetectorAnomalias()
            self.alertas = self.detector.processar(
                self.documentos,
                relacionamentos,
                self.correlacionador.pessoas,
                self.correlacionador.empresas,
            )
            self.janela.after(0, lambda: self.adicionar_log(
                f"✅ {len(self.alertas)} anomalias detectadas", "warning"
            ))

            # 3. Base de conhecimento
            self.janela.after(0, lambda: self.adicionar_log("🔄 Atualizando base de conhecimento...", "info"))
            self.base_conhecimento = BaseConhecimento()
            for doc in self.documentos:
                self.base_conhecimento.adicionar_entidades(doc.entidades)
            self.base_conhecimento.adicionar_relacionamentos(relacionamentos)
            self.base_conhecimento.adicionar_pessoas(self.correlacionador.pessoas)
            self.base_conhecimento.adicionar_empresas(self.correlacionador.empresas)
            self.base_conhecimento.adicionar_alertas(self.alertas)
            self.base_conhecimento.salvar()
            self.janela.after(0, lambda: self.adicionar_log("✅ Base de conhecimento salva", "success"))

            # 4. Atualizar interface
            self.janela.after(0, self._exibir_alertas)
            self.janela.after(0, self._atualizar_dashboard)
            self.janela.after(0, lambda: self.adicionar_log("🎯 Pipeline completo!", "success"))

        except Exception as e:
            self.janela.after(0, lambda: self.adicionar_log(f"❌ Erro no pipeline: {e}", "error"))
        finally:
            self._set_processando(False)

    def _set_processando(self, valor: bool):
        """Atualiza estado de processamento."""
        self.processando = valor
        status = "🔄 Processando..." if valor else "✅ Pronto"
        cor = self.CORES["warning"] if valor else self.CORES["success"]
        self.janela.after(0, lambda: self.status_label.configure(text=status, text_color=cor))
        self.janela.after(0, lambda: self.btn_processar.configure(
            state="disabled" if valor else "normal"
        ))

    def _atualizar_dashboard(self):
        """Atualiza cards do dashboard."""
        total_valores = 0
        total_entidades = sum(len(d.entidades) for d in self.documentos)
        for doc in self.documentos:
            for ent in doc.entidades:
                if ent.tipo.value == "valor":
                    try:
                        total_valores += abs(float(ent.normalizado))
                    except ValueError:
                        continue

        self.cards["documentos"].configure(text=str(len(self.documentos)))
        self.cards["entidades"].configure(text=str(total_entidades))
        self.cards["alertas"].configure(text=str(len(self.alertas)))
        self.cards["valor"].configure(text=f"R$ {total_valores:,.2f}")

    def _salvar_documentos(self):
        """Persiste documentos processados em disco."""
        try:
            with self._lock:
                docs = list(self.documentos)
            self.base_conhecimento.salvar_documentos(docs)
        except Exception as e:
            self.janela.after(0, lambda: self.adicionar_log(f"⚠️ Erro ao salvar documentos: {e}", "warning"))

    def _carregar_dados_iniciais(self):
        """Carrega dados salvos anteriores."""
        try:
            self.base_conhecimento.carregar()
            estatisticas = self.base_conhecimento.consultar_estatisticas()
            if estatisticas["total_entidades"] > 0:
                self.adicionar_log(
                    f"📂 Base de conhecimento carregada: "
                    f"{estatisticas['total_entidades']} entidades, "
                    f"{estatisticas['total_relacionamentos']} relações",
                    "info"
                )
            # Carrega documentos persistidos
            docs_salvos = self.base_conhecimento.carregar_documentos()
            if docs_salvos:
                with self._lock:
                    self.documentos = docs_salvos
                self.adicionar_log(
                    f"📂 {len(docs_salvos)} documento(s) carregado(s) da sessão anterior",
                    "info"
                )
                self._atualizar_dashboard()
        except Exception as e:
            self.adicionar_log(f"ℹ️ Nova base de conhecimento: {e}", "info")

    def iniciar(self):
        """Inicia a aplicação."""
        self.janela.mainloop()


def main():
    """Ponto de entrada da aplicação."""
    app = IAAnalisadoraApp()
    app.iniciar()


if __name__ == "__main__":
    main()