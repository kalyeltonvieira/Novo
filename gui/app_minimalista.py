"""
Interface Minimalista - Auditor IA
====================================
Design inspirado em ChatGPT, Linear e Notion.
Foco total na análise com componentes interativos.
"""

import os
import sys
import json
import re
import threading
import time
import base64
import io
from datetime import datetime
from typing import Optional, Dict, Any, List
from tkinter import filedialog, messagebox
import tkinter as tk
from PIL import Image, ImageTk
from dotenv import load_dotenv

load_dotenv()

# Garante que a raiz do projeto está no path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import customtkinter as ctk
except ImportError:
    print("Instalando dependências da GUI...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "customtkinter"])
    import customtkinter as ctk

from core.entrada_dados import ColetorDados
from core.leitor_universal import LeitorUniversal
from core.correlacionador import Correlacionador
from core.detector_anomalias import DetectorAnomalias
from core.base_conhecimento import BaseConhecimento
from core.camada_reports import CamadaReports
from core.entidades import (
    Documento, Alerta, Relatorio, TipoAnomalia, TipoDocumento
)
from core.agentes.supervisor import SupervisorRouter
from core.agentes.especialistas import (
    NavegadorAgente, CorrelacionadorAgente, AnalistaAgente,
    GeolocalizadorAgente, LaudoGenerator, TimelineAuditor
)

# Importação opcional do gerenciador de IA
try:
    from utils.ai_providers import AIProvider, get_ai_manager, AIManager
    AI_AVAILABLE = True
except ImportError:
    AI_AVAILABLE = False

# Importação opcional do navegador automatizado
try:
    from core.navegador_automatizado import NavegadorAutomatizado
    NAVEGADOR_AVAILABLE = True
except ImportError:
    NAVEGADOR_AVAILABLE = False



class AuditorIaApp:
    """
    Interface minimalista estilo ChatGPT/Linear.
    Foco em análise com componentes interativos.
    """

    # Paleta de cores minimalista (fundo preto, cinzas, acento sutil)
    CORES = {
        "bg_main": "#0a0a0a",           # Preto quase absoluto
        "bg_sidebar": "#111111",        # Cinza muito escuro
        "bg_card": "#1a1a1a",          # Cinza escuro
        "bg_input": "#222222",         # Cinza médio escuro
        "border": "#333333",           # Cinza médio
        "text_primary": "#ffffff",      # Branco
        "text_secondary": "#888888",   # Cinza claro
        "text_muted": "#555555",       # Cinza médio
        "accent": "#3b82f6",           # Azul sutil (como Linear)
        "accent_hover": "#2563eb",     # Azul mais escuro
        "success": "#10b981",          # Verde sutil
        "warning": "#f59e0b",          # Amarelo sutil
        "danger": "#ef4444",           # Vermelho sutil
        "critical": "#dc2626",         # Vermelho escuro
    }

    def __init__(self):
        # Componentes do sistema
        self.coletor = ColetorDados()
        self.leitor = LeitorUniversal()
        self.correlacionador = Correlacionador()
        self.detector = DetectorAnomalias()
        self.base_conhecimento = BaseConhecimento()
        self.reports = CamadaReports()

        # Carregar NVIDIA API key APENAS do .env (que é o local correto).
        # Antes deste patch, o código lia do config.json e ainda criava o
        # arquivo com uma chave hardcoded se ele não existisse — vetor sério
        # de vazamento. Agora: nada em texto puro, nada hardcoded.
        import os
        import sys

        nvidia_key = os.getenv("NVIDIA_API_KEY")
        if nvidia_key:
            print(f"🔑 NVIDIA API Key encontrada no .env ({nvidia_key[:8]}…)")
        else:
            print("⚠️ NVIDIA_API_KEY não encontrada no .env. Defina em .env antes de usar IA.")

        # Preferências (provedor, modelo, idioma, tema) continuam vindo do config.json
        config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.json")
        provider_config = "nvidia"  # padrão não-sensível
        if os.path.exists(config_path):
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    config_data = json.load(f)
                    provider_config = config_data.get("config_ai_provider", "nvidia")
            except (OSError, json.JSONDecodeError):
                pass

        # Configuração de IA
        if AI_AVAILABLE:
            # Mapear string para enum
            if provider_config == "huggingface":
                provider = AIProvider.HUGGINGFACE
                # HF_TOKEN também vem do .env (python-dotenv já carregou)
                hf_token = os.getenv("HF_TOKEN")
                if hf_token:
                    print(f"🔑 HF_TOKEN encontrada no .env ({hf_token[:6]}…)")
                else:
                    print("⚠️ HF_TOKEN não encontrada no .env. Defina em .env antes de usar HuggingFace.")
            else:
                provider = AIProvider.NVIDIA

            self.ai_manager = AIManager(default_provider=provider)
            self.ai_provider = provider
        else:
            self.ai_manager = None
            self.ai_provider = None
        
        self.use_ai = False  # Começa desativado, usuário deve ativar nas configurações

        # Configuração de navegador
        self.navegador = None
        self.navegador_ativo = False
        self.screenshot_atual = None
        
        # Tentar inicializar navegador (Chrome ou Edge)
        if NAVEGADOR_AVAILABLE:
            try:
                # Tentar Chrome primeiro
                test_navegador = NavegadorAutomatizado(headless=True, use_edge=False)
                if test_navegador.iniciar():
                    test_navegador.fechar()
                    self.navegador = NavegadorAutomatizado(headless=True, use_edge=False)
                    print("✅ Navegador Chrome automatizado inicializado com sucesso")
                else:
                    # Tentar Edge como fallback
                    print("⚠️ Chrome não disponível, tentando Edge...")
                    test_navegador = NavegadorAutomatizado(headless=True, use_edge=True)
                    if test_navegador.iniciar():
                        test_navegador.fechar()
                        self.navegador = NavegadorAutomatizado(headless=True, use_edge=True)
                        print("✅ Navegador Edge automatizado inicializado com sucesso")
                    else:
                        print("⚠️ Navegador não pôde ser iniciado. Funcionalidade desabilitada.")
            except Exception as e:
                print(f"⚠️ Erro ao inicializar navegador: {e}")
                print("💡 A funcionalidade de navegador será desabilitada.")

        # Estado da aplicação
        self.documentos: List[Documento] = []
        self.alertas: List[Alerta] = []
        self.alertas_personalizados = []  # Alertas configurados pelo usuário
        self.processando = False
        self.sidebar_item_selecionado = "casos"
        self.layout_dividido = False  # False = chat apenas, True = chat + navegador
        self._historico_chat = []
        self.arquivo_anexado_texto = None
        self.arquivo_anexado_nome = None
        self.documentos_anexados = []  # Lista de documentos anexados para busca
        self.mostrar_pensamento = False  # Estado do toggle de pensamento
        self.pensamento_atual = ""  # Pensamento atual do modelo
        self.historico_widgets = []  # Widgets do histórico na sidebar
        
        # Histórico de conversas persistente
        self.historico_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "chat_historico.json")
        self._carregar_historico_persistente()

        # Configuração do Supervisor Multi-Agente
        if self.ai_manager:
            especialistas = [
                CorrelacionadorAgente(self.correlacionador),
                AnalistaAgente(self.correlacionador),
                GeolocalizadorAgente(self.correlacionador),
                LaudoGenerator(self.correlacionador),
                TimelineAuditor(self.correlacionador)
            ]
            
            # Adicionar NavegadorAgente apenas se navegador estiver disponível
            if self.navegador:
                especialistas.insert(0, NavegadorAgente(self.navegador))
            
            self.supervisor = SupervisorRouter(self.ai_manager, especialistas)
        else:
            self.supervisor = None

        # Configurar tema
        self._configurar_tema()
        
        # Criar janela
        self._criar_janela()
        
        # Criar layout
        self._criar_layout()
        
        # Carregar dados iniciais
        self._carregar_dados_iniciais()

    def _configurar_tema(self):
        """Configura o tema escuro minimalista."""
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("dark-blue")

    def _criar_janela(self):
        """Cria a janela principal."""
        self.janela = ctk.CTk()
        self.janela.title("Auditor IA")
        self.janela.geometry("1400x900")
        self.janela.minsize(1200, 800)
        
        # Configurar fundo
        self.janela.configure(fg_color=self.CORES["bg_main"])

    def _carregar_historico_persistente(self):
        """Carrega o histórico de conversas do arquivo JSON."""
        if os.path.exists(self.historico_path):
            try:
                with open(self.historico_path, "r", encoding="utf-8") as f:
                    self._historico_chat = json.load(f)
                print(f"✅ Histórico carregado: {len(self._historico_chat)} mensagens")
            except Exception as e:
                print(f"❌ Erro ao carregar histórico: {e}")
                self._historico_chat = []

    def _salvar_historico_persistente(self):
        """Salva o histórico de conversas no arquivo JSON."""
        try:
            with open(self.historico_path, "w", encoding="utf-8") as f:
                json.dump(self._historico_chat, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"❌ Erro ao salvar histórico: {e}")
    
    def _atualizar_lista_historico_sidebar(self):
        """Atualiza a lista de conversas na sidebar."""
        # Remover widgets antigos do histórico
        if hasattr(self, 'historico_widgets'):
            for widget in self.historico_widgets:
                widget.destroy()
        
        self.historico_widgets = []
        
        # Agrupar mensagens por conversa (simples: pares usuário-IA)
        conversas = []
        conversa_atual = []
        
        for msg in self._historico_chat:
            conversa_atual.append(msg)
            if msg['role'] == 'IA Analisadora':
                conversas.append(conversa_atual.copy())
                conversa_atual = []
        
        # Adicionar conversa atual se não estiver completa
        if conversa_atual:
            conversas.append(conversa_atual)
        
        # Exibir conversas na sidebar (todas, não só as últimas 10)
        for i, conversa in enumerate(reversed(conversas)):  # Reverso para mostrar mais recentes primeiro
            # Pegar primeira mensagem do usuário como título
            titulo = "Nova conversa"
            for msg in conversa:
                if msg['role'] == 'Usuário':
                    titulo = msg['content'][:30] + "..." if len(msg['content']) > 30 else msg['content']
                    break
            
            conversa_btn = ctk.CTkButton(
                self.historico_scroll_frame,  # Usar scroll frame
                text=f"{i+1}. {titulo}",
                font=ctk.CTkFont(size=12),
                fg_color="transparent",
                text_color=self.CORES["text_secondary"],
                hover_color=self.CORES["bg_input"],
                anchor="w",
                height=35,
                corner_radius=6,
                command=lambda c=conversa: self._carregar_conversa(c),
            )
            conversa_btn.pack(fill="x", padx=5, pady=2)
            self.historico_widgets.append(conversa_btn)
    
    def _carregar_conversa(self, conversa: list):
        """Carrega uma conversa específica no chat."""
        # Limpar chat atual
        for widget in self.chat_frame.winfo_children():
            widget.destroy()
        
        # Exibir mensagens da conversa
        for msg in conversa:
            if msg['role'] == 'Usuário':
                self._adicionar_mensagem_usuario(msg['content'])
            elif msg['role'] == 'IA Analisadora':
                self._adicionar_mensagem_ia(msg['content'], typewriter=False)
        
        # Atualizar o histórico atual para esta conversa
        self._historico_chat = conversa.copy()

    def _criar_layout(self):
        """Cria o layout principal: sidebar + área de conteúdo."""
        # Container principal
        self.main_container = ctk.CTkFrame(
            self.janela,
            fg_color=self.CORES["bg_main"],
        )
        self.main_container.pack(fill="both", expand=True)

        # Estado da sidebar
        self.sidebar_visible = True

        # Sidebar primeiro (mas sem selecionar item ainda)
        self._criar_sidebar_inicial()
        
        # Área de conteúdo (cria header_title)
        self._criar_area_conteudo()
        
        # Agora seleciona o item padrão
        self._selecionar_sidebar("casos")

    def _alternar_layout_dividido(self):
        """Alterna entre layout normal (chat) e layout dividido (chat + navegador)."""
        self.layout_dividido = not self.layout_dividido
        
        # Salvar mensagens do chat antes de destruir
        mensagens_salvas = []
        if hasattr(self, 'chat_frame'):
            for widget in self.chat_frame.winfo_children():
                # Tentar extrair texto dos widgets
                try:
                    if hasattr(widget, 'cget'):
                        texto = widget.cget('text')
                        if texto and texto.strip():
                            # Identificar tipo de mensagem pelo estilo
                            fg_color = widget.cget('fg_color') if hasattr(widget, 'cget') else None
                            if fg_color == self.CORES["accent"]:
                                mensagens_salvas.append({'tipo': 'usuario', 'texto': texto})
                            else:
                                mensagens_salvas.append({'tipo': 'ia', 'texto': texto})
                except:
                    pass
        
        # Recriar área de conteúdo
        for widget in self.content_area.winfo_children():
            widget.destroy()
        
        if self.layout_dividido:
            # Layout dividido: chat + navegador
            self._criar_layout_dividido()
        else:
            # Layout normal: apenas chat
            self._criar_area_chat()
            self._criar_header()
        
        # Restaurar mensagens salvas
        for msg in mensagens_salvas:
            if msg['tipo'] == 'usuario':
                self._adicionar_mensagem_usuario(msg['texto'])
            else:
                self._adicionar_mensagem_ia(msg['texto'], typewriter=False)

    def _criar_layout_dividido(self):
        """Cria layout dividido estilo manus.ai (chat + navegador)."""
        # Header com controles
        self._criar_header_dividido()
        
        # Container dividido
        dividido_container = ctk.CTkFrame(
            self.content_area,
            fg_color=self.CORES["bg_main"],
        )
        dividido_container.pack(fill="both", expand=True, padx=20, pady=10)

        # Painel esquerdo: Chat (60%)
        chat_panel = ctk.CTkFrame(
            dividido_container,
            fg_color=self.CORES["bg_card"],
            corner_radius=12,
        )
        chat_panel.pack(side="left", fill="both", expand=True, padx=(0, 10))

        # Título do painel de chat
        chat_title = ctk.CTkLabel(
            chat_panel,
            text="💬 Chat",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=self.CORES["text_primary"],
        )
        chat_title.pack(pady=(10, 5), padx=15, anchor="w")

        # Scrollable frame para mensagens
        self.chat_frame = ctk.CTkScrollableFrame(
            chat_panel,
            fg_color="transparent",
            label_text="",
        )
        self.chat_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        # Mensagem inicial
        self._adicionar_mensagem_ia(
            "Olá! Sou o Auditor IA. Analise contratos, despesas e licitações públicas. "
            "Carregue documentos ou faça uma pergunta para começar."
        )

        # Área de input
        self._criar_area_input_dividido(chat_panel)

        # Painel direito: Navegador (40%)
        navegador_panel = ctk.CTkFrame(
            dividido_container,
            fg_color=self.CORES["bg_card"],
            corner_radius=12,
        )
        navegador_panel.pack(side="right", fill="both", expand=True)

        # Header do navegador
        nav_header = ctk.CTkFrame(
            navegador_panel,
            fg_color="transparent",
        )
        nav_header.pack(fill="x", padx=10, pady=(10, 5))

        nav_title = ctk.CTkLabel(
            nav_header,
            text="🌐 Navegador",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=self.CORES["text_primary"],
        )
        nav_title.pack(side="left", padx=5)

        # Controles do navegador
        nav_controls = ctk.CTkFrame(
            navegador_panel,
            fg_color=self.CORES["bg_input"],
            corner_radius=8,
        )
        nav_controls.pack(fill="x", padx=10, pady=5)

        # URL input
        url_entry = ctk.CTkEntry(
            nav_controls,
            placeholder_text="https://...",
            fg_color="transparent",
            border_width=0,
            text_color=self.CORES["text_primary"],
            placeholder_text_color=self.CORES["text_muted"],
            height=32,
        )
        url_entry.pack(side="left", fill="x", expand=True, padx=10, pady=5)
        url_entry.insert(0, "https://www.portalcr2.com.br/entidade/ourilandia-do-norte")

        # Botões de navegação
        nav_btn = ctk.CTkButton(
            nav_controls,
            text="Navegar",
            width=80,
            height=32,
            fg_color=self.CORES["accent"],
            text_color=self.CORES["text_primary"],
            hover_color=self.CORES["accent_hover"],
            corner_radius=6,
            command=lambda: self._navegar_url(url_entry.get())
        )
        nav_btn.pack(side="right", padx=(5, 10), pady=5)

        # Área de visualização do navegador (screenshot)
        self.navegador_view = ctk.CTkFrame(
            navegador_panel,
            fg_color=self.CORES["bg_main"],
            corner_radius=8,
        )
        self.navegador_view.pack(fill="both", expand=True, padx=10, pady=(5, 10))

        # Label placeholder
        self.navegador_placeholder = ctk.CTkLabel(
            self.navegador_view,
            text="Navegador inativo\nClique em 'Navegar' para iniciar",
            font=ctk.CTkFont(size=12),
            text_color=self.CORES["text_muted"],
        )
        self.navegador_placeholder.pack(expand=True)

    def _criar_header_dividido(self):
        """Cria header específico para layout dividido."""
        self.header = ctk.CTkFrame(
            self.content_area,
            height=60,
            fg_color=self.CORES["bg_main"],
        )
        self.header.pack(fill="x", padx=20, pady=(20, 10))
        self.header.pack_propagate(False)

        # Botão toggle sidebar
        self.toggle_sidebar_btn = ctk.CTkButton(
            self.header,
            text="☰",
            width=40,
            height=32,
            fg_color="transparent",
            text_color=self.CORES["text_secondary"],
            hover_color=self.CORES["bg_card"],
            corner_radius=6,
            font=ctk.CTkFont(size=16),
            command=self._toggle_sidebar,
        )
        self.toggle_sidebar_btn.pack(side="left", padx=(0, 15), pady=10)

        # Título da seção
        self.header_title = ctk.CTkLabel(
            self.header,
            text="Análise com Navegador",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color=self.CORES["text_primary"],
        )
        self.header_title.pack(side="left", pady=10)

        # Botão alternar layout
        toggle_layout_btn = ctk.CTkButton(
            self.header,
            text="☐ Layout",
            width=100,
            height=32,
            fg_color="transparent",
            text_color=self.CORES["text_secondary"],
            hover_color=self.CORES["bg_card"],
            corner_radius=6,
            font=ctk.CTkFont(size=12),
            command=self._alternar_layout_dividido,
        )
        toggle_layout_btn.pack(side="right", padx=(0, 10), pady=10)

    def _criar_area_input_dividido(self, parent):
        """Cria área de input para layout dividido."""
        input_frame = ctk.CTkFrame(
            parent,
            fg_color=self.CORES["bg_main"],
        )
        input_frame.pack(fill="x", pady=(10, 0))

        # Container do input
        input_container = ctk.CTkFrame(
            input_frame,
            fg_color=self.CORES["bg_input"],
            corner_radius=12,
        )
        input_container.pack(fill="x", pady=10)

        # Campo de texto
        self.input_text = ctk.CTkTextbox(
            input_container,
            height=50,
            fg_color="transparent",
            border_width=0,
            text_color=self.CORES["text_primary"],
            font=ctk.CTkFont(size=14),
        )
        self.input_text.pack(side="left", fill="both", expand=True, padx=15, pady=10)
        # Bind para Enter
        self.input_text.bind("<Return>", self._on_enter_press)
        self.input_text.bind("<KP_Enter>", self._on_enter_press)

        # Botão enviar
        send_btn = ctk.CTkButton(
            input_container,
            text="Enviar",
            width=80,
            height=50,
            fg_color=self.CORES["accent"],
            text_color=self.CORES["text_primary"],
            hover_color=self.CORES["accent_hover"],
            corner_radius=8,
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self._enviar_mensagem,
        )
        send_btn.pack(side="right", padx=10, pady=10)

        # Placeholder
        self.input_text.insert("1.0", "Pergunte qualquer coisa sobre contratos, despesas ou licitações...")
        self.input_text.configure(fg_color=self.CORES["bg_input"])

    def _navegar_url(self, url: str):
        """Navega para a URL especificada e inicia captura periódica."""
        if not self.navegador:
            self._adicionar_mensagem_ia("⚠️ Navegador não disponível. Instale Selenium.")
            return

        if not url:
            return

        # Iniciar navegador se não estiver ativo
        if not self.navegador_ativo:
            if not self.navegador.iniciar():
                self._adicionar_mensagem_ia("❌ Não foi possível iniciar o navegador. Verifique se o Chrome está instalado.")
                return
            self.navegador_ativo = True

        # Navegar para URL
        if self.navegador.navegar(url):
            # Iniciar captura periódica
            self.navegador.iniciar_captura_periodica(
                intervalo=5,
                callback=self._atualizar_screenshot
            )
            
            # Remover placeholder
            if hasattr(self, 'navegador_placeholder'):
                self.navegador_placeholder.destroy()

    def _atualizar_screenshot(self, screenshot_bytes: bytes):
        """Atualiza a visualização do navegador com nova screenshot."""
        try:
            # Converter bytes para imagem
            image = Image.open(io.BytesIO(screenshot_bytes))
            
            # Redimensionar para caber no painel
            image.thumbnail((600, 400))
            
            # Converter para PhotoImage
            photo = ImageTk.PhotoImage(image)
            
            # Atualizar label
            if hasattr(self, 'navegador_image_label'):
                self.navegador_image_label.configure(image=photo)
                self.navegador_image_label.image = photo
            else:
                self.navegador_image_label = ctk.CTkLabel(
                    self.navegador_view,
                    image=photo,
                    text="",
                )
                self.navegador_image_label.pack(expand=True)
                self.navegador_image_label.image = photo
        except Exception as e:
            print(f"Erro ao atualizar screenshot: {e}")

    def _criar_sidebar_inicial(self):
        """Cria a sidebar de navegação (sem selecionar item)."""
        self.sidebar = ctk.CTkFrame(
            self.main_container,
            width=240,
            fg_color=self.CORES["bg_sidebar"],
            corner_radius=0,
        )
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        # Logo/Título
        logo_frame = ctk.CTkFrame(
            self.sidebar,
            fg_color="transparent",
        )
        logo_frame.pack(fill="x", padx=20, pady=(20, 30))

        logo_label = ctk.CTkLabel(
            logo_frame,
            text="Auditor IA",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=self.CORES["text_primary"],
        )
        logo_label.pack(anchor="w")

        # Itens de navegação
        self.sidebar_items = [
            ("casos", "Casos"),
            ("municipios", "Municípios"),
            ("estados", "Estados"),
            ("uniao", "União"),
            ("favoritos", "Favoritos"),
            ("relatorios", "Relatórios"),
            ("alertas", "Alertas"),
            ("dashboard", "Dashboard"),
            ("navegador", "Navegador"),
        ]

        self.sidebar_buttons = {}
        for item_id, label in self.sidebar_items:
            btn = ctk.CTkButton(
                self.sidebar,
                text=label,
                font=ctk.CTkFont(size=14),
                fg_color="transparent",
                text_color=self.CORES["text_secondary"],
                hover_color=self.CORES["bg_card"],
                anchor="w",
                height=40,
                corner_radius=0,
                command=lambda i=item_id: self._selecionar_sidebar(i),
            )
            btn.pack(fill="x", padx=0, pady=0)
            self.sidebar_buttons[item_id] = btn
        
        # Separador
        separator = ctk.CTkFrame(
            self.sidebar,
            height=1,
            fg_color=self.CORES["bg_input"],
        )
        separator.pack(fill="x", padx=20, pady=(20, 10))
        
        # Seção de histórico
        historico_label = ctk.CTkLabel(
            self.sidebar,
            text="Histórico de Conversas",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=self.CORES["text_muted"],
        )
        historico_label.pack(anchor="w", padx=20, pady=(10, 5))
        
        # Scrollable frame para histórico
        self.historico_scroll_frame = ctk.CTkScrollableFrame(
            self.sidebar,
            fg_color="transparent",
            label_text="",
        )
        self.historico_scroll_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        
        # Lista de conversas do histórico
        self._atualizar_lista_historico_sidebar()

        # Separador
        separator = ctk.CTkFrame(
            self.sidebar,
            height=1,
            fg_color=self.CORES["border"],
        )
        separator.pack(fill="x", pady=20)

        # Configurações na parte inferior
        config_btn = ctk.CTkButton(
            self.sidebar,
            text="Configurações",
            font=ctk.CTkFont(size=14),
            fg_color="transparent",
            text_color=self.CORES["text_secondary"],
            hover_color=self.CORES["bg_card"],
            anchor="w",
            height=40,
            corner_radius=0,
            command=self._abrir_configuracoes,
        )
        config_btn.pack(side="bottom", fill="x", padx=0, pady=0)

    def _selecionar_sidebar(self, item_id: str):
        """Seleciona um item da sidebar."""
        self.sidebar_item_selecionado = item_id
        
        # Atualizar visual dos botões
        for btn_item_id, btn in self.sidebar_buttons.items():
            if btn_item_id == item_id:
                btn.configure(
                    fg_color=self.CORES["bg_card"],
                    text_color=self.CORES["text_primary"],
                )
            else:
                btn.configure(
                    fg_color="transparent",
                    text_color=self.CORES["text_secondary"],
                )
        
        # Atualizar área de conteúdo
        self._atualizar_conteudo(item_id)

    def _criar_area_conteudo(self):
        """Cria a área principal de conteúdo."""
        self.content_area = ctk.CTkFrame(
            self.main_container,
            fg_color=self.CORES["bg_main"],
        )
        self.content_area.pack(side="right", fill="both", expand=True)

        # Header
        self._criar_header()
        
        # Área de chat/análise
        self._criar_area_chat()

    def _criar_header(self):
        """Cria o header com busca e perfil."""
        self.header = ctk.CTkFrame(
            self.content_area,
            height=60,
            fg_color=self.CORES["bg_main"],
        )
        self.header.pack(fill="x", padx=20, pady=(20, 10))
        self.header.pack_propagate(False)

        # Botão toggle sidebar (hambúrguer)
        self.toggle_sidebar_btn = ctk.CTkButton(
            self.header,
            text="☰",
            width=40,
            height=32,
            fg_color="transparent",
            text_color=self.CORES["text_secondary"],
            hover_color=self.CORES["bg_card"],
            corner_radius=6,
            font=ctk.CTkFont(size=16),
            command=self._toggle_sidebar,
        )
        self.toggle_sidebar_btn.pack(side="left", padx=(0, 15), pady=10)

        # Título da seção
        self.header_title = ctk.CTkLabel(
            self.header,
            text="Casos",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color=self.CORES["text_primary"],
        )
        self.header_title.pack(side="left", pady=10)

        # Toggle de pensamento
        self.pensamento_switch = ctk.CTkSwitch(
            self.header,
            text="Mostrar Pensamento",
            command=self._toggle_pensamento,
            fg_color=self.CORES["accent"],
            progress_color=self.CORES["accent"],
            text_color=self.CORES["text_primary"],
            text_color_disabled=self.CORES["text_muted"],
        )
        self.pensamento_switch.pack(side="right", padx=(0, 15), pady=10)

        # Busca
        search_frame = ctk.CTkFrame(
            self.header,
            fg_color=self.CORES["bg_input"],
            corner_radius=8,
        )
        search_frame.pack(side="right", padx=(0, 20), pady=10)

        search_entry = ctk.CTkEntry(
            search_frame,
            placeholder_text="Buscar...",
            fg_color="transparent",
            border_width=0,
            text_color=self.CORES["text_primary"],
            placeholder_text_color=self.CORES["text_muted"],
            width=200,
            height=30,
        )
        search_entry.pack(side="left", padx=10, pady=5)

        # Perfil
        perfil_btn = ctk.CTkButton(
            self.header,
            text="Perfil",
            width=80,
            height=32,
            fg_color=self.CORES["bg_card"],
            text_color=self.CORES["text_primary"],
            hover_color=self.CORES["border"],
            corner_radius=6,
            font=ctk.CTkFont(size=12),
        )
        perfil_btn.pack(side="right", padx=(0, 10), pady=10)

        # Botão alternar layout
        toggle_layout_btn = ctk.CTkButton(
            self.header,
            text="☐ Layout",
            width=100,
            height=32,
            fg_color="transparent",
            text_color=self.CORES["text_secondary"],
            hover_color=self.CORES["bg_card"],
            corner_radius=6,
            font=ctk.CTkFont(size=12),
            command=self._alternar_layout_dividido,
        )
        toggle_layout_btn.pack(side="right", padx=(0, 10), pady=10)

    def _criar_area_chat(self):
        """Cria a área de chat/análise."""
        # Scrollable frame para mensagens
        self.chat_frame = ctk.CTkScrollableFrame(
            self.content_area,
            fg_color=self.CORES["bg_main"],
            label_text="",
        )
        self.chat_frame.pack(fill="both", expand=True, padx=20, pady=10)

        # Mensagem inicial
        self._adicionar_mensagem_ia(
            "Olá! Sou o Auditor IA. Analise contratos, despesas e licitações públicas. "
            "Carregue documentos ou faça uma pergunta para começar."
        )

        # Área de input
        self._criar_area_input()

    def _criar_area_input(self):
        """Cria a área de input de texto."""
        self.input_frame = ctk.CTkFrame(
            self.content_area,
            fg_color=self.CORES["bg_main"],
        )
        self.input_frame.pack(fill="x", padx=20, pady=(10, 20))

        # Container do input
        input_container = ctk.CTkFrame(
            self.input_frame,
            fg_color=self.CORES["bg_input"],
            corner_radius=12,
        )
        input_container.pack(fill="x", pady=10)

        # Botão Anexo
        attach_btn = ctk.CTkButton(
            input_container,
            text="📎",
            width=40,
            height=50,
            fg_color="transparent",
            text_color=self.CORES["text_primary"],
            hover_color=self.CORES["bg_card"],
            corner_radius=8,
            font=ctk.CTkFont(size=20),
            command=self._anexar_arquivo,
        )
        attach_btn.pack(side="left", padx=(10, 0), pady=10)

        # Campo de texto
        self.input_text = ctk.CTkTextbox(
            input_container,
            height=50,
            fg_color="transparent",
            border_width=0,
            text_color=self.CORES["text_primary"],
            font=ctk.CTkFont(size=14),
        )
        self.input_text.pack(side="left", fill="both", expand=True, padx=15, pady=10)
        # Bind para Enter (teclado principal e numérico)
        self.input_text.bind("<Return>", self._on_enter_press)
        self.input_text.bind("<KP_Enter>", self._on_enter_press)

        # Botão enviar
        send_btn = ctk.CTkButton(
            input_container,
            text="Enviar",
            width=80,
            height=50,
            fg_color=self.CORES["accent"],
            text_color=self.CORES["text_primary"],
            hover_color=self.CORES["accent_hover"],
            corner_radius=8,
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self._enviar_mensagem,
        )
        send_btn.pack(side="right", padx=10, pady=10)

        # Placeholder
        self.input_text.insert("1.0", "Pergunte qualquer coisa sobre contratos, despesas ou licitações...")
        self.input_text.configure(fg_color=self.CORES["bg_input"])

    def _adicionar_mensagem_usuario(self, texto: str):
        """Adiciona uma mensagem do usuário."""
        mensagem_frame = ctk.CTkFrame(
            self.chat_frame,
            fg_color="transparent",
        )
        mensagem_frame.pack(fill="x", pady=(20, 10), anchor="e")

        # Balão de mensagem
        balloon = ctk.CTkFrame(
            mensagem_frame,
            fg_color=self.CORES["accent"],
            corner_radius=12,
        )
        balloon.pack(side="right")

        texto_label = ctk.CTkLabel(
            balloon,
            text=texto,
            font=ctk.CTkFont(size=14),
            text_color=self.CORES["text_primary"],
            wraplength=580,
            justify="right",
        )
        texto_label.pack(padx=15, pady=10)

    def _adicionar_mensagem_ia(self, texto: str, componentes: List = None, typewriter: bool = True):
        """Adiciona uma mensagem da IA com componentes opcionais e efeito typewriter."""
        mensagem_frame = ctk.CTkFrame(
            self.chat_frame,
            fg_color="transparent",
        )
        mensagem_frame.pack(fill="x", pady=(10, 20), anchor="w")

        # Header da mensagem com botão de copiar
        header_frame = ctk.CTkFrame(
            mensagem_frame,
            fg_color="transparent",
        )
        header_frame.pack(fill="x", padx=15, pady=(5, 0))

        # Botão de copiar
        copiar_btn = ctk.CTkButton(
            header_frame,
            text="📋",
            width=30,
            height=30,
            fg_color="transparent",
            text_color=self.CORES["text_muted"],
            hover_color=self.CORES["bg_input"],
            corner_radius=6,
            command=lambda t=texto: self._copiar_texto(t)
        )
        copiar_btn.pack(side="right", padx=(0, 5))

        # Texto da IA
        texto_label = ctk.CTkLabel(
            mensagem_frame,
            text="",
            font=ctk.CTkFont(size=14),
            text_color=self.CORES["text_primary"],
            wraplength=800,
            justify="left",
        )
        texto_label.pack(padx=15, pady=10)

        # Efeito typewriter
        if typewriter and texto:
            self._typewriter_effect(texto_label, texto)
        else:
            texto_label.configure(text=texto)

        # Componentes (cards, tabelas, etc.)
        if componentes:
            for componente in componentes:
                self._renderizar_componente(mensagem_frame, componente)

    def _copiar_texto(self, texto: str):
        """Copia o texto para o clipboard."""
        self.janela.clipboard_clear()
        self.janela.clipboard_append(texto)
        self.janela.update()
        print("📋 Texto copiado para o clipboard")

    def _typewriter_effect(self, label, texto: str, delay: int = 10):
        """Efeito typewriter para escrever texto caractere por caractere."""
        def type_char(index):
            if index < len(texto):
                try:
                    # Verificar se o widget ainda existe
                    if label.winfo_exists():
                        label.configure(text=texto[:index + 1])
                        self.janela.after(delay, lambda: type_char(index + 1))
                except tk.TclError:
                    # Widget foi destruído, parar o efeito
                    pass
        
        type_char(0)

    def _renderizar_componente(self, parent, componente: Dict):
        """Renderiza um componente da IA (card, tabela, etc.)."""
        tipo = componente.get("tipo")
        
        if tipo == "card_anomalia":
            self._renderizar_card_anomalia(parent, componente)
        elif tipo == "card_resumo":
            self._renderizar_card_resumo(parent, componente)
        elif tipo == "tabela":
            self._renderizar_tabela(parent, componente)
        elif tipo == "grafico":
            self._renderizar_grafico(parent, componente)

    def _renderizar_card_anomalia(self, parent, dados: Dict):
        """Renderiza um card de anomalia."""
        card = ctk.CTkFrame(
            parent,
            fg_color=self.CORES["bg_card"],
            corner_radius=12,
            border_width=1,
            border_color=self.CORES["danger"],
        )
        card.pack(fill="x", pady=10, anchor="w")

        # Header do card
        header = ctk.CTkFrame(
            card,
            fg_color="transparent",
        )
        header.pack(fill="x", padx=15, pady=(15, 10))

        # Título
        titulo = ctk.CTkLabel(
            header,
            text="⚠️ Anomalia Detectada",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=self.CORES["danger"],
        )
        titulo.pack(side="left")

        # Severidade
        severidade = dados.get("severidade", "média")
        severidade_label = ctk.CTkLabel(
            header,
            text=severidade.upper(),
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=self.CORES["text_primary"],
            fg_color=self.CORES["danger"] if severidade == "alta" else self.CORES["warning"],
            corner_radius=4,
            padx=8,
            pady=4,
        )
        severidade_label.pack(side="right")

        # Conteúdo do card
        conteudo = dados.get("conteudo", {})
        
        # Linhas de informação
        for chave, valor in conteudo.items():
            linha = ctk.CTkFrame(
                card,
                fg_color="transparent",
            )
            linha.pack(fill="x", padx=15, pady=5)

            chave_label = ctk.CTkLabel(
                linha,
                text=f"{chave}:",
                font=ctk.CTkFont(size=12),
                text_color=self.CORES["text_muted"],
                width=150,
                anchor="w",
            )
            chave_label.pack(side="left")

            valor_label = ctk.CTkLabel(
                linha,
                text=str(valor),
                font=ctk.CTkFont(size=12),
                text_color=self.CORES["text_primary"],
                anchor="w",
            )
            valor_label.pack(side="left", padx=(10, 0))

        # Botões de ação
        botoes_frame = ctk.CTkFrame(
            card,
            fg_color="transparent",
        )
        botoes_frame.pack(fill="x", padx=15, pady=(10, 15))

        for btn_text in ["Ver Evidências", "Abrir Contratos", "Gerar Relatório"]:
            btn = ctk.CTkButton(
                botoes_frame,
                text=btn_text,
                width=120,
                height=32,
                fg_color=self.CORES["bg_input"],
                text_color=self.CORES["text_primary"],
                hover_color=self.CORES["border"],
                corner_radius=6,
                font=ctk.CTkFont(size=11),
            )
            btn.pack(side="left", padx=(0, 10))

    def _renderizar_card_resumo(self, parent, dados: Dict):
        """Renderiza um card de resumo."""
        card = ctk.CTkFrame(
            parent,
            fg_color=self.CORES["bg_card"],
            corner_radius=12,
        )
        card.pack(fill="x", pady=10, anchor="w")

        # Header
        header = ctk.CTkFrame(
            card,
            fg_color="transparent",
        )
        header.pack(fill="x", padx=15, pady=(15, 10))

        titulo = ctk.CTkLabel(
            header,
            text=dados.get("titulo", "Resumo"),
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=self.CORES["text_primary"],
        )
        titulo.pack(side="left")

        # Métricas
        metricas = dados.get("metricas", {})
        for chave, valor in metricas.items():
            linha = ctk.CTkFrame(
                card,
                fg_color="transparent",
            )
            linha.pack(fill="x", padx=15, pady=5)

            chave_label = ctk.CTkLabel(
                linha,
                text=f"{chave}:",
                font=ctk.CTkFont(size=12),
                text_color=self.CORES["text_muted"],
                width=200,
                anchor="w",
            )
            chave_label.pack(side="left")

            valor_label = ctk.CTkLabel(
                linha,
                text=str(valor),
                font=ctk.CTkFont(size=12, weight="bold"),
                text_color=self.CORES["text_primary"],
                anchor="w",
            )
            valor_label.pack(side="left", padx=(10, 0))

        card.pack(padx=15, pady=(0, 15))

    def _renderizar_tabela(self, parent, dados: Dict):
        """Renderiza uma tabela."""
        card = ctk.CTkFrame(
            parent,
            fg_color=self.CORES["bg_card"],
            corner_radius=12,
        )
        card.pack(fill="x", pady=10, anchor="w")

        header = ctk.CTkLabel(
            card,
            text=dados.get("titulo", "Tabela"),
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=self.CORES["text_primary"],
        )
        header.pack(padx=15, pady=(15, 10))

        # Dados da tabela
        colunas = dados.get("colunas", [])
        linhas = dados.get("linhas", [])

        if colunas and linhas:
            # Criar scrollable frame para tabela
            tabela_frame = ctk.CTkScrollableFrame(
                card,
                fg_color="transparent",
                height=200,
            )
            tabela_frame.pack(fill="x", padx=15, pady=(0, 15))

            # Header da tabela
            header_row = ctk.CTkFrame(
                tabela_frame,
                fg_color=self.CORES["bg_input"],
            )
            header_row.pack(fill="x", pady=(0, 5))

            for i, coluna in enumerate(colunas):
                col_label = ctk.CTkLabel(
                    header_row,
                    text=coluna,
                    font=ctk.CTkFont(size=11, weight="bold"),
                    text_color=self.CORES["text_primary"],
                )
                col_label.pack(side="left", padx=10, pady=5)

            # Linhas da tabela
            for linha in linhas:
                row = ctk.CTkFrame(
                    tabela_frame,
                    fg_color="transparent",
                )
                row.pack(fill="x", pady=2)

                for i, valor in enumerate(linha):
                    val_label = ctk.CTkLabel(
                        row,
                        text=str(valor),
                        font=ctk.CTkFont(size=11),
                        text_color=self.CORES["text_secondary"],
                    )
                    val_label.pack(side="left", padx=10, pady=5)
        else:
            # Placeholder se não houver dados
            placeholder = ctk.CTkLabel(
                card,
                text="Nenhum dado disponível",
                text_color=self.CORES["text_muted"],
            )
            placeholder.pack(padx=15, pady=(0, 15))

    def _renderizar_grafico(self, parent, dados: Dict):
        """Renderiza um gráfico."""
        # Placeholder - pode usar Plotly ou matplotlib
        card = ctk.CTkFrame(
            parent,
            fg_color=self.CORES["bg_card"],
            corner_radius=12,
        )
        card.pack(fill="x", pady=10, anchor="w")

        header = ctk.CTkLabel(
            card,
            text=dados.get("titulo", "Gráfico"),
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=self.CORES["text_primary"],
        )
        header.pack(padx=15, pady=(15, 10))

        placeholder = ctk.CTkLabel(
            card,
            text="[Gráfico será renderizado aqui]",
            text_color=self.CORES["text_muted"],
        )
        placeholder.pack(padx=15, pady=(0, 15))

    def _atualizar_conteudo(self, item_id: str):
        """Atualiza o conteúdo baseado no item selecionado."""
        # Atualizar título do header
        titulos = {
            "casos": "Casos",
            "municipios": "Municípios",
            "estados": "Estados",
            "uniao": "União",
            "favoritos": "Favoritos",
            "relatorios": "Relatórios",
            "alertas": "Alertas",
            "dashboard": "Dashboard",
            "navegador": "Navegador",
        }
        self.header_title.configure(text=titulos.get(item_id, item_id))

        # Limpar área de chat
        for widget in self.chat_frame.winfo_children():
            widget.destroy()

        # Adicionar conteúdo específico
        if item_id == "dashboard":
            self._renderizar_dashboard()
        elif item_id == "casos":
            self._renderizar_casos()
        elif item_id == "navegador":
            # Ativar layout dividido
            if not self.layout_dividido:
                self._alternar_layout_dividido()
        elif item_id == "municipios":
            self._renderizar_municipios()
        elif item_id == "estados":
            self._renderizar_estados()
        elif item_id == "uniao":
            self._renderizar_uniao()
        elif item_id == "favoritos":
            self._renderizar_favoritos()
        elif item_id == "relatorios":
            self._renderizar_relatorios()
        elif item_id == "alertas":
            self._renderizar_alertas()
        else:
            self._adicionar_mensagem_ia(f"Selecione ou crie um caso de {titulos.get(item_id)} para começar.")

    def _renderizar_dashboard(self):
        """Renderiza o dashboard com métricas."""
        # Card de resumo com métricas reais
        resumo_card = {
            "tipo": "card_resumo",
            "titulo": "Visão Geral do Sistema",
            "metricas": {
                "Documentos carregados": str(len(self.documentos)),
                "Documentos anexados": str(len(self.documentos_anexados)),
                "Conversas salvas": str(len(self._historico_chat)),
                "Alertas ativos": str(len(self.alertas)),
                "IA disponível": "Sim" if self.ai_manager else "Não",
                "Navegador disponível": "Sim" if self.navegador else "Não",
            }
        }
        self._renderizar_componente(self.chat_frame, resumo_card)
        
        # Card de estatísticas do chat
        if self._historico_chat:
            mensagens_usuario = len([m for m in self._historico_chat if m['role'] == 'Usuário'])
            mensagens_ia = len([m for m in self._historico_chat if m['role'] == 'IA Analisadora'])
            
            chat_stats = {
                "tipo": "card_resumo",
                "titulo": "Estatísticas do Chat",
                "metricas": {
                    "Mensagens do usuário": str(mensagens_usuario),
                    "Respostas da IA": str(mensagens_ia),
                    "Total de interações": str(len(self._historico_chat)),
                }
            }
            self._renderizar_componente(self.chat_frame, chat_stats)
        
        # Card de documentos anexados
        if self.documentos_anexados:
            docs_info = "\n".join([f"- {doc['nome']}" for doc in self.documentos_anexados])
            self._adicionar_mensagem_ia(f"📎 Documentos disponíveis para busca:\n{docs_info}", typewriter=False)
        
        # Card de alertas
        if self.alertas:
            alertas_info = "\n".join([f"- {alerta.titulo}: {alerta.severidade}" for alerta in self.alertas[:5]])
            self._adicionar_mensagem_ia(f"⚠️ Alertas recentes:\n{alertas_info}", typewriter=False)
        else:
            self._adicionar_mensagem_ia("✅ Nenhum alerta ativo no momento.", typewriter=False)

    def _renderizar_casos(self):
        """Renderiza a lista de casos."""
        self._adicionar_mensagem_ia(
            "Carregue documentos ou faça uma pergunta para começar uma nova análise."
        )

    def _renderizar_municipios(self):
        """Renderiza a lista de municípios."""
        self._adicionar_mensagem_ia(
            "🏛️ Análise de Municípios\n\n"
            "Carregue documentos de prefeituras ou use o navegador para acessar portais de transparência municipais.",
            typewriter=False
        )

    def _renderizar_estados(self):
        """Renderiza a lista de estados."""
        self._adicionar_mensagem_ia(
            "🗺️ Análise de Estados\n\n"
            "Carregue documentos de governos estaduais ou use o navegador para acessar portais de transparência estaduais.",
            typewriter=False
        )

    def _renderizar_uniao(self):
        """Renderiza a lista de dados da União."""
        self._adicionar_mensagem_ia(
            "🏛️ Análise da União\n\n"
            "Carregue documentos federais ou use o navegador para acessar o Portal da Transparência da União.",
            typewriter=False
        )

    def _renderizar_favoritos(self):
        """Renderiza a lista de favoritos."""
        self._adicionar_mensagem_ia(
            "⭐ Favoritos\n\n"
            "Marque casos importantes como favoritos para acesso rápido.\n\n"
            "Funcionalidade em desenvolvimento.",
            typewriter=False
        )

    def _renderizar_relatorios(self):
        """Renderiza a lista de relatórios."""
        reports_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "reports")
        if os.path.exists(reports_dir):
            relatorios = os.listdir(reports_dir)
            if relatorios:
                relatorios_info = "\n".join([f"- {r}" for r in relatorios[:10]])
                self._adicionar_mensagem_ia(
                    f"📄 Relatórios disponíveis:\n{relatorios_info}",
                    typewriter=False
                )
            else:
                self._adicionar_mensagem_ia(
                    "📄 Nenhum relatório gerado ainda.\nGere relatórios após analisar documentos.",
                    typewriter=False
                )
        else:
            self._adicionar_mensagem_ia(
                "📄 Diretório de relatórios não encontrado.",
                typewriter=False
            )

    def _renderizar_alertas(self):
        """Renderiza a lista de alertas."""
        if self.alertas:
            alertas_info = "\n".join([f"⚠️ {alerta.titulo} ({alerta.severidade})" for alerta in self.alertas[:10]])
            self._adicionar_mensagem_ia(
                f"Alertas ativos:\n{alertas_info}",
                typewriter=False
            )
        elif self.alertas_personalizados:
            alertas_info = "\n".join([f"⚠️ {a['titulo']} ({a['severidade']})" for a in self.alertas_personalizados[:10]])
            self._adicionar_mensagem_ia(
                f"Alertas personalizados:\n{alertas_info}",
                typewriter=False
            )
        else:
            self._adicionar_mensagem_ia(
                "⚠️ Nenhum alerta configurado.\nUse o chat para criar alertas personalizados.",
                typewriter=False
            )

    def _criar_alerta_personalizado(self, titulo: str, descricao: str, severidade: str = "média"):
        """Cria um alerta personalizado."""
        alerta = {
            'titulo': titulo,
            'descricao': descricao,
            'severidade': severidade,
            'data': time.strftime('%Y-%m-%d %H:%M:%S'),
            'ativo': True
        }
        self.alertas_personalizados.append(alerta)
        return alerta

    def _listar_alertas_personalizados(self):
        """Lista todos os alertas personalizados."""
        if not self.alertas_personalizados:
            return "Nenhum alerta personalizado configurado."
        
        resultado = "📋 Alertas Personalizados:\n\n"
        for i, alerta in enumerate(self.alertas_personalizados, 1):
            status = "✅" if alerta['ativo'] else "❌"
            resultado += f"{status} {i}. {alerta['titulo']} ({alerta['severidade']})\n"
            resultado += f"   {alerta['descricao']}\n"
            resultado += f"   Criado em: {alerta['data']}\n\n"
        
        return resultado

    def _desativar_alerta(self, indice: int):
        """Desativa um alerta personalizado pelo índice."""
        if 0 <= indice < len(self.alertas_personalizados):
            self.alertas_personalizados[indice]['ativo'] = False
            return f"Alerta '{self.alertas_personalizados[indice]['titulo']}' desativado."
        return "Índice inválido."

    def _verificar_alertas(self, texto: str):
        """Verifica se o texto contém padrões que devem disparar alertas."""
        alertas_disparados = []
        
        for alerta in self.alertas_personalizados:
            if alerta['ativo'] and alerta['titulo'].lower() in texto.lower():
                alertas_disparados.append(alerta)
        
        return alertas_disparados

    def _toggle_pensamento(self):
        """Alterna o estado de mostrar pensamento."""
        self.mostrar_pensamento = not self.mostrar_pensamento
        estado = "ativado" if self.mostrar_pensamento else "desativado"
        self._adicionar_mensagem_ia(f"🧠 Mostrar pensamento {estado}", typewriter=False)

    def _adicionar_pensamento(self, pensamento: str):
        """Adiciona um pensamento do modelo ao chat."""
        if not self.mostrar_pensamento:
            return
        
        pensamento_frame = ctk.CTkFrame(
            self.chat_frame,
            fg_color=self.CORES["bg_input"],
            corner_radius=8,
        )
        pensamento_frame.pack(fill="x", pady=(5, 10), anchor="w", padx=15)

        # Título do pensamento
        titulo = ctk.CTkLabel(
            pensamento_frame,
            text="🧠 Pensamento",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=self.CORES["text_muted"],
        )
        titulo.pack(padx=10, pady=(8, 4), anchor="w")

        # Conteúdo do pensamento
        conteudo = ctk.CTkLabel(
            pensamento_frame,
            text=pensamento,
            font=ctk.CTkFont(size=11),
            text_color=self.CORES["text_secondary"],
            wraplength=800,
            justify="left",
        )
        conteudo.pack(padx=10, pady=(0, 8), anchor="w")

    def _on_enter_press(self, event):
        """Lida com pressionamento de Enter no campo de texto."""
        # Verifica se Shift está pressionado (para nova linha)
        if event.state & 0x0001:  # Shift key
            return  # Permite nova linha normal
        
        # Se não tem Shift, envia a mensagem
        self._enviar_mensagem()
        return "break"  # Impede nova linha

    def _anexar_arquivo(self):
        """Abre janela para anexar arquivo no chat."""
        caminho = filedialog.askopenfilename(
            title="Selecione um arquivo",
            filetypes=[("Documentos", "*.pdf *.txt *.csv *.docx *.html")]
        )
        if caminho:
            self._adicionar_mensagem_ia(f"⏳ Processando arquivo: {os.path.basename(caminho)}...")
            
            def processar():
                try:
                    doc = self.leitor.processar_documento(caminho)
                    if doc:
                        self.arquivo_anexado_texto = doc.texto
                        self.arquivo_anexado_nome = os.path.basename(caminho)
                        
                        # Adicionar à lista de documentos para busca
                        self.documentos_anexados.append({
                            'nome': os.path.basename(caminho),
                            'texto': doc.texto,
                            'caminho': caminho
                        })
                        
                        self.janela.after(0, lambda: self._adicionar_mensagem_ia(f"✅ Arquivo '{self.arquivo_anexado_nome}' carregado. O que deseja saber sobre ele?"))
                    else:
                        self.janela.after(0, lambda: self._adicionar_mensagem_ia(f"❌ Não foi possível extrair texto de: {os.path.basename(caminho)}"))
                except Exception as e:
                    self.janela.after(0, lambda: self._adicionar_mensagem_ia(f"❌ Erro ao ler arquivo: {e}"))
            
            t = threading.Thread(target=processar)
            t.daemon = True
            t.start()

    def _buscar_em_documentos(self, termo: str) -> List[Dict]:
        """Busca termo nos documentos anexados."""
        resultados = []
        termo_lower = termo.lower()
        
        for doc in self.documentos_anexados:
            texto = doc['texto'].lower()
            if termo_lower in texto:
                # Encontrar contexto ao redor do termo
                pos = texto.find(termo_lower)
                inicio = max(0, pos - 100)
                fim = min(len(doc['texto']), pos + len(termo) + 100)
                contexto = doc['texto'][inicio:fim]
                
                resultados.append({
                    'documento': doc['nome'],
                    'contexto': contexto,
                    'posicao': pos
                })
        
        return resultados

    def _enviar_mensagem(self):
        """Envia a mensagem do usuário."""
        texto = self.input_text.get("1.0", "end").strip()
        if not texto:
            return

        # Limpar input
        self.input_text.delete("1.0", "end")
        self.input_text.insert("1.0", "Pergunte qualquer coisa sobre contratos, despesas ou licitações...")

        # Adicionar mensagem do usuário
        self._adicionar_mensagem_usuario(texto)

        # Usar thread para não travar GUI
        thread = threading.Thread(target=self._processar_pergunta, args=(texto,))
        thread.daemon = True
        thread.start()

    def _processar_pergunta(self, pergunta: str, invisivel: bool = False):
        """Processa a pergunta do usuário usando o sistema Multi-Agente (Supervisor)."""
        if not invisivel:
            self.janela.after(0, lambda: self._adicionar_mensagem_ia("⏳ Supervisor analisando sua pergunta..."))

        # Debug: verificar estado
        print(f"DEBUG: ai_manager={self.ai_manager is not None}, supervisor={self.supervisor is not None}")
        
        if self.ai_manager and self.supervisor:
            try:
                prompt_final = pergunta
                
                if self.arquivo_anexado_texto:
                    prompt_final += f"\n\n=== CONTEÚDO DO ARQUIVO ({self.arquivo_anexado_nome}) ===\n{self.arquivo_anexado_texto[:8000]}"
                    self.arquivo_anexado_texto = None
                    self.arquivo_anexado_nome = None

                # Constroi contexto (histórico)
                contexto = "Histórico da conversa:\n"
                for m in self._historico_chat[-6:]:
                    contexto += f"{m['role']}: {m['content']}\n"
                
                # Definir um callback para atualizar a UI em tempo real com as ações do Supervisor
                def ui_callback(msg: str):
                    self.janela.after(0, lambda: self._adicionar_mensagem_ia(msg))
                    
                    # Se o supervisor invocar o navegador, abre o painel lateral automaticamente
                    if "AgenteNavegador" in msg or "Navegador" in msg:
                        self.janela.after(0, lambda: self._alternar_layout_dividido() if not self.layout_dividido else None)
                
                # Definir callback para mostrar pensamentos
                def pensamento_callback(pensamento: str):
                    self.janela.after(0, lambda: self._adicionar_pensamento(pensamento))
                
                # Executa a orquestração
                resposta = self.supervisor.processar(
                    prompt_usuario=prompt_final,
                    contexto_historico=contexto,
                    callback_ui=ui_callback,
                    callback_pensamento=pensamento_callback
                )
                    
                if not resposta:
                    resposta = "Ocorreu um erro ao obter a resposta final da IA."
                
                # Parsing da resposta FINAL para blocos JSON (UI Cards)
                json_blocks = re.findall(r'```json\s*(.*?)\s*```', resposta, re.DOTALL)
                componentes = []
                texto_limpo = re.sub(r'```json\s*(.*?)\s*```', '', resposta, flags=re.DOTALL).strip()
                
                for j_block in json_blocks:
                    try:
                        dados_json = json.loads(j_block)
                        # Só renderiza como card se não for uma instrução de delegação perdida
                        if "tipo" in dados_json:
                            componentes.append(dados_json)
                    except json.JSONDecodeError:
                        pass
                
                self._historico_chat.append({"role": "Usuário", "content": pergunta})
                self._historico_chat.append({"role": "IA Analisadora", "content": resposta})
                
                # Salvar histórico persistente
                self._salvar_historico_persistente()
                
                # Atualizar lista de histórico na sidebar
                self.janela.after(0, lambda: self._atualizar_lista_historico_sidebar())
                
                if texto_limpo or componentes:
                    self.janela.after(0, lambda: self._adicionar_mensagem_ia(texto_limpo if texto_limpo else "Análise concluída:", componentes=componentes))

            except Exception as e:
                error_msg = str(e)
                # Verificar se é erro de limite de API
                if "ResourceExhausted" in error_msg or "503" in error_msg:
                    self.janela.after(0, lambda msg=error_msg: self._adicionar_mensagem_ia(f"⚠️ Limite de requisições da API atingido. Aguarde alguns minutos antes de tentar novamente."))
                else:
                    self.janela.after(0, lambda msg=error_msg: self._adicionar_mensagem_ia(f"❌ Erro ao orquestrar agentes: {msg}"))
        else:
            # Mensagem mais específica sobre o problema
            problemas = []
            if not self.ai_manager:
                problemas.append("Gerenciador de IA não disponível")
            if not self.supervisor:
                problemas.append("Supervisor não inicializado")
            
            self.janela.after(0, lambda: self._adicionar_mensagem_ia(f"⚠️ Para análise avançada, corrija: {', '.join(problemas)}"))

    def _toggle_sidebar(self):
        """ Alterna a visibilidade da sidebar (estilo ChatGPT)."""
        if self.sidebar_visible:
            # Esconder sidebar
            self.sidebar.pack_forget()
            self.toggle_sidebar_btn.configure(text="☰")
            self.sidebar_visible = False
        else:
            # Mostrar sidebar
            self.sidebar.pack(side="left", fill="y", before=self.content_area)
            self.toggle_sidebar_btn.configure(text="✕")
            self.sidebar_visible = True

    def _abrir_configuracoes(self):
        """Abre as configurações na área de conteúdo."""
        from gui.configuracoes import abrir_configuracoes
        
        # Salvar estado atual do chat
        self._salvar_estado_chat()
        
        def callback_salvar(config, cancelar=False):
            """Callback quando configurações são salvas ou canceladas."""
            if not cancelar and config:
                # Atualizar configurações da aplicação
                self.config = config
                print("Configurações atualizadas:", config)
                
                # Configurar NVIDIA API key
                nvidia_api_key = config.get("config_nvidia_api_key")
                if nvidia_api_key:
                    # Set API key no ambiente
                    import os
                    os.environ["NVIDIA_API_KEY"] = nvidia_api_key
                    # Recriar ai_manager com nova API key
                    from utils.ai_providers import reset_ai_manager
                    reset_ai_manager()
                    self.ai_manager = get_ai_manager()
            
            # Restaurar chat
            self._restaurar_chat()
        
        # Passar a área de conteúdo onde renderizar as configurações
        abrir_configuracoes(self.janela, self.content_area, callback_salvar)

    def _salvar_estado_chat(self):
        """Salva o estado atual do chat."""
        self.chat_estado_salvo = []
        for widget in self.chat_frame.winfo_children():
            self.chat_estado_salvo.append(widget)
        # Esconder o chat frame
        self.chat_frame.pack_forget()
        # Esconder o input frame
        self.input_frame.pack_forget()

    def _restaurar_chat(self):
        """Restaura o chat após fechar configurações."""
        # Limpar área de conteúdo
        for widget in self.content_area.winfo_children():
            widget.destroy()
        
        # Recriar header
        self._criar_header()
        
        # Recriar área de chat
        self._criar_area_chat()

    def _carregar_dados_iniciais(self):
        """Carrega dados iniciais do sistema."""
        try:
            # Carregar documentos do diretório data
            data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
            if os.path.exists(data_dir):
                self.coletor = ColetorDados()
                arquivos = self.coletor.coletar_pasta(data_dir)
                if arquivos:
                    print(f"📁 Encontrados {len(arquivos)} arquivos em {data_dir}")
                    # Processar documentos (opcional, pode ser pesado)
                    # for arquivo in arquivos:
                    #     doc = self.leitor.processar_documento(arquivo)
                    #     if doc:
                    #         self.documentos.append(doc)
        except Exception as e:
            print(f"⚠️ Erro ao carregar dados iniciais: {e}")

    def iniciar(self):
        """Inicia a aplicação."""
        self.janela.mainloop()


def main():
    """Ponto de entrada da aplicação minimalista."""
    app = AuditorIaApp()
    app.iniciar()


if __name__ == "__main__":
    main()
