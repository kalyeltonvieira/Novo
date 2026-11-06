"""
Configurações - Interface Minimalista
====================================
Simplificado para usar apenas NVIDIA API (DeepSeek).

IMPORTANTE: Chaves de API NUNCA são persistidas neste arquivo/config.json.
Elas ficam exclusivamente no .env (carregado via python-dotenv). Este módulo
só lida com preferências não-sensíveis (idioma, tema, provedor, modelo).
"""

import os
import json
import customtkinter as ctk
from customtkinter import CTkFont as ctkFont
from typing import Optional, Dict, Any, List


def _project_root() -> str:
    """Retorna o caminho absoluto da raiz do projeto (onde fica .env)."""
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _carregar_env_para_dict() -> Dict[str, str]:
    """Lê o .env e retorna dict com chaves sensíveis (sem escrevê-las em JSON)."""
    env_path = os.path.join(_project_root(), ".env")
    resultado: Dict[str, str] = {}
    if not os.path.exists(env_path):
        return resultado
    try:
        with open(env_path, "r", encoding="utf-8") as f:
            for linha in f:
                linha = linha.strip()
                if not linha or linha.startswith("#") or "=" not in linha:
                    continue
                chave, _, valor = linha.partition("=")
                resultado[chave.strip()] = valor.strip()
    except OSError:
        pass
    return resultado


def _salvar_env(chave: str, valor: str) -> bool:
    """
    Atualiza ou adiciona uma chave no .env preservando comentários e ordem.
    Retorna True em caso de sucesso.
    """
    env_path = os.path.join(_project_root(), ".env")
    linhas: List[str] = []
    encontrado = False

    if os.path.exists(env_path):
        try:
            with open(env_path, "r", encoding="utf-8") as f:
                linhas = f.readlines()
        except OSError:
            return False

    for i, linha in enumerate(linhas):
        s = linha.strip()
        if s and not s.startswith("#") and "=" in s:
            nome, _, _ = s.partition("=")
            if nome.strip() == chave:
                linhas[i] = f"{chave}={valor}\n"
                encontrado = True
                break

    if not encontrado:
        linhas.append(f"{chave}={valor}\n")

    try:
        with open(env_path, "w", encoding="utf-8") as f:
            f.writelines(linhas)
        return True
    except OSError:
        return False


class ConfiguracoesWindow:
    """Janela de configurações simplificada."""

    # Paleta de cores
    CORES = {
        "bg_main": "#0a0a0a",
        "bg_sidebar": "#111111",
        "bg_card": "#1a1a1a",
        "bg_input": "#222222",
        "text_primary": "#ffffff",
        "text_secondary": "#a0a0a0",
        "text_muted": "#666666",
        "border": "#333333",
        "accent": "#3b82f6",
        "accent_hover": "#2563eb",
        "success": "#10b981",
        "warning": "#f59e0b",
        "danger": "#ef4444",
    }

    SECOES = [
        ("geral", "Geral"),
        ("banco_dados", "Banco de Dados"),
        ("busca", "Busca"),
        ("ocr", "OCR"),
        ("analise", "Análise"),
        ("alertas", "Alertas"),
        ("seguranca", "Segurança"),
        ("api", "API"),
        ("usuarios", "Usuários"),
        ("logs", "Logs"),
        ("avancado", "Avançado"),
    ]

    def __init__(self, parent, content_area, callback_salvar=None):
        self.parent = parent
        self.content_area = content_area
        self.callback_salvar = callback_salvar
        self.campos = {}  # Inicializar dicionário de campos
        self._campos_sensiveis: set = set()  # config_keys que vão para .env, NUNCA para config.json
        # Mapeamento: config_key -> env_key (para chaves sensíveis)
        self._env_keys: Dict[str, str] = {}

        # Carregar configurações existentes
        self.config = self._carregar_configuracoes()

        # Criar layout dentro da área de conteúdo
        self._criar_layout()

        # Carregar valores nos campos
        self._carregar_valores()

    def _carregar_configuracoes(self) -> dict:
        """Carrega preferências do config.json. Chaves sensíveis vêm do .env."""
        config_path = os.path.join(_project_root(), "config.json")
        prefs: dict = {}
        if os.path.exists(config_path):
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    prefs = json.load(f)
            except (OSError, json.JSONDecodeError):
                pass
        # Defaults não-sensíveis
        prefs.setdefault("config_geral_idioma", "pt-BR")
        prefs.setdefault("config_geral_tema", "Escuro")
        prefs.setdefault("config_geral_notificacoes", 1)
        prefs.setdefault("config_ai_provider", "nvidia")
        prefs.setdefault("config_ai_model", "deepseek-ai/deepseek-v4-flash")
        return prefs

    def _criar_layout(self):
        """Cria o layout principal dentro da área de conteúdo."""
        # Limpar área de conteúdo
        for widget in self.content_area.winfo_children():
            widget.destroy()

        # Container principal
        self.main_container = ctk.CTkFrame(
            self.content_area,
            fg_color=self.CORES["bg_main"],
        )
        self.main_container.pack(fill="both", expand=True)

        # Área de conteúdo primeiro (cria secao_content)
        self._criar_area_conteudo()
        
        # Sidebar depois (sem selecionar seção ainda)
        self._criar_sidebar()
        
        # Barra de ações (Salvar/Cancelar)
        self._criar_barro_acoes()
        
        # Agora seleciona a seção padrão
        self._selecionar_secao("geral")

    def _criar_area_conteudo(self):
        """Cria a área de conteúdo principal."""
        # Container do conteúdo
        content_container = ctk.CTkFrame(
            self.main_container,
            fg_color=self.CORES["bg_main"],
        )
        content_container.pack(side="right", fill="both", expand=True)

        # Header da seção
        self.secao_header = ctk.CTkFrame(
            content_container,
            height=60,
            fg_color=self.CORES["bg_main"],
        )
        self.secao_header.pack(fill="x", padx=20, pady=(20, 10))
        self.secao_header.pack_propagate(False)

        # Botão voltar
        voltar_btn = ctk.CTkButton(
            self.secao_header,
            text="← Voltar",
            width=80,
            height=32,
            fg_color="transparent",
            text_color=self.CORES["text_secondary"],
            hover_color=self.CORES["bg_card"],
            corner_radius=6,
            font=ctkFont(size=12),
            command=self._cancelar,
        )
        voltar_btn.pack(side="left", padx=(0, 15), pady=10)

        # Título da seção
        self.secao_titulo = ctk.CTkLabel(
            self.secao_header,
            text="Configurações",
            font=ctkFont(size=20, weight="bold"),
            text_color=self.CORES["text_primary"],
        )
        self.secao_titulo.pack(side="left", pady=10)

        # Área scrollable para o conteúdo
        self.secao_content = ctk.CTkScrollableFrame(
            content_container,
            fg_color=self.CORES["bg_main"],
            label_text="",
            scrollbar_button_color=self.CORES["border"],
            scrollbar_button_hover_color=self.CORES["text_secondary"],
        )
        self.secao_content.pack(fill="both", expand=True, padx=30, pady=10)
        
        # Forçar update para garantir que o widget foi criado
        self.content_area.update()

    def _criar_sidebar(self):
        """Cria a sidebar de seções."""
        self.sidebar = ctk.CTkFrame(
            self.main_container,
            width=200,
            fg_color=self.CORES["bg_sidebar"],
            corner_radius=0,
        )
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        # Título
        titulo = ctk.CTkLabel(
            self.sidebar,
            text="Configurações",
            font=ctkFont(size=16, weight="bold"),
            text_color=self.CORES["text_primary"],
        )
        titulo.pack(padx=20, pady=(20, 30))

        # Botões de seção
        self.sidebar_buttons = {}
        for secao_id, secao_nome in self.SECOES:
            btn = ctk.CTkButton(
                self.sidebar,
                text=secao_nome,
                font=ctkFont(size=13),
                fg_color="transparent",
                text_color=self.CORES["text_secondary"],
                hover_color=self.CORES["bg_card"],
                corner_radius=0,
                height=40,
                anchor="w",
                command=lambda sid=secao_id: self._selecionar_secao(sid),
            )
            btn.pack(fill="x", padx=10, pady=2)
            self.sidebar_buttons[secao_id] = btn

    def _criar_barro_acoes(self):
        """Cria a barra de ações (Salvar/Cancelar)."""
        acoes_frame = ctk.CTkFrame(
            self.main_container,
            height=60,
            fg_color=self.CORES["bg_main"],
        )
        acoes_frame.pack(side="bottom", fill="x")
        acoes_frame.pack_propagate(False)

        # Botão cancelar
        cancelar_btn = ctk.CTkButton(
            acoes_frame,
            text="Cancelar",
            width=100,
            height=32,
            fg_color="transparent",
            text_color=self.CORES["text_secondary"],
            hover_color=self.CORES["bg_card"],
            corner_radius=6,
            font=ctkFont(size=13),
            command=self._cancelar,
        )
        cancelar_btn.pack(side="right", padx=(0, 20), pady=12)

        # Botão salvar
        salvar_btn = ctk.CTkButton(
            acoes_frame,
            text="Salvar",
            width=100,
            height=32,
            fg_color=self.CORES["accent"],
            text_color=self.CORES["text_primary"],
            hover_color=self.CORES["accent_hover"],
            corner_radius=6,
            command=self._salvar,
        )
        salvar_btn.pack(side="right", padx=20, pady=12)

    def _selecionar_secao(self, secao_id: str):
        """Seleciona uma seção e atualiza o conteúdo."""
        # Atualizar visual dos botões
        for sid, btn in self.sidebar_buttons.items():
            if sid == secao_id:
                btn.configure(
                    fg_color=self.CORES["accent"],
                    text_color=self.CORES["text_primary"],
                )
            else:
                btn.configure(
                    fg_color="transparent",
                    text_color=self.CORES["text_secondary"],
                )

        # Atualizar conteúdo
        self._atualizar_conteudo(secao_id)

    def _atualizar_conteudo(self, secao_id: str):
        """Atualiza o conteúdo baseado na seção."""
        # Limpar conteúdo atual
        for widget in self.secao_content.winfo_children():
            widget.destroy()

        # Atualizar título
        nomes = {s_id: nome for s_id, nome in self.SECOES}
        self.secao_titulo.configure(text=nomes.get(secao_id, secao_id))

        # Renderizar conteúdo específico
        if secao_id == "geral":
            self._renderizar_geral()
        else:
            self._renderizar_em_desenvolvimento(secao_id)

    def _renderizar_geral(self):
        """Renderiza seção Geral."""
        # NVIDIA API Key — salva em .env, NUNCA no config.json
        self._criar_campo_env(
            label="NVIDIA API Key",
            env_key="NVIDIA_API_KEY",
            placeholder="nvapi-...",
            config_key="config_nvidia_api_key",
        )

        # Idioma
        self._criar_campo(
            "Idioma",
            "pt-BR",
            "dropdown",
            ["pt-BR", "en-US", "es-ES"],
            "config_geral_idioma"
        )

        # Tema
        self._criar_campo(
            "Tema",
            "Escuro",
            "dropdown",
            ["Escuro", "Claro", "Auto"],
            "config_geral_tema"
        )

        # Notificações
        self._criar_campo(
            "Notificações",
            True,
            "switch",
            None,
            "config_geral_notificacoes"
        )

    def _renderizar_em_desenvolvimento(self, secao_id: str):
        """Renderiza placeholder para seções em desenvolvimento."""
        label = ctk.CTkLabel(
            self.secao_content,
            text=f"Seção '{secao_id}' em desenvolvimento",
            font=ctkFont(size=14),
            text_color=self.CORES["text_muted"],
        )
        label.pack(pady=50)

    def _criar_campo(self, label: str, valor_padrao: Any, tipo: str, opcoes: Optional[list], config_key: str):
        """Cria um campo de configuração."""
        frame = ctk.CTkFrame(
            self.secao_content,
            fg_color=self.CORES["bg_card"],
            corner_radius=8,
        )
        frame.pack(fill="x", pady=8)

        # Label
        label_widget = ctk.CTkLabel(
            frame,
            text=label,
            font=ctkFont(size=13),
            text_color=self.CORES["text_primary"],
            anchor="w",
        )
        label_widget.pack(anchor="w", padx=15, pady=(12, 5))

        # Campo baseado no tipo
        if tipo == "text":
            campo = ctk.CTkEntry(
                frame,
                fg_color=self.CORES["bg_input"],
                border_width=0,
                text_color=self.CORES["text_primary"],
                placeholder_text_color=self.CORES["text_muted"],
                height=36,
            )
            campo.pack(fill="x", padx=(0, 20), pady=(0, 12))
            if valor_padrao:
                campo.insert(0, valor_padrao)
            self.campos[config_key] = campo

        elif tipo == "password":
            campo = ctk.CTkEntry(
                frame,
                fg_color=self.CORES["bg_input"],
                border_width=0,
                text_color=self.CORES["text_primary"],
                placeholder_text_color=self.CORES["text_muted"],
                show="•",
                height=36,
            )
            campo.pack(fill="x", padx=(0, 20), pady=(0, 12))
            if valor_padrao:
                campo.insert(0, valor_padrao)
            self.campos[config_key] = campo
            # Marcar como sensível — nunca gravar em config.json
            self._campos_sensiveis.add(config_key)

        elif tipo == "number":
            campo = ctk.CTkEntry(
                frame,
                fg_color=self.CORES["bg_input"],
                border_width=0,
                text_color=self.CORES["text_primary"],
                placeholder_text_color=self.CORES["text_muted"],
                height=36,
            )
            campo.pack(fill="x", padx=(0, 20), pady=(0, 12))
            if valor_padrao:
                campo.insert(0, str(valor_padrao))
            self.campos[config_key] = campo

        elif tipo == "dropdown":
            campo = ctk.CTkOptionMenu(
                frame,
                values=opcoes or [],
                fg_color=self.CORES["bg_input"],
                button_color=self.CORES["bg_input"],
                button_hover_color=self.CORES["border"],
                text_color=self.CORES["text_primary"],
                dropdown_text_color=self.CORES["text_primary"],
                dropdown_fg_color=self.CORES["bg_card"],
                height=36,
            )
            campo.set(valor_padrao)
            campo.pack(fill="x", padx=(0, 20), pady=(0, 12))
            self.campos[config_key] = campo

        elif tipo == "switch":
            campo = ctk.CTkSwitch(
                frame,
                text="",
                fg_color=self.CORES["accent"],
                progress_color=self.CORES["accent_hover"],
                button_color=self.CORES["text_primary"],
                button_hover_color=self.CORES["text_primary"],
            )
            campo.pack(anchor="e", padx=(0, 20), pady=(0, 12))
            campo.select() if valor_padrao else campo.deselect()
            self.campos[config_key] = campo

    def _criar_campo_env(self, label: str, env_key: str, placeholder: str, config_key: str) -> None:
        """
        Cria um campo de senha cujo valor é persistido APENAS no .env
        (nunca em config.json). O valor inicial vem do ambiente / .env.
        """
        frame = ctk.CTkFrame(
            self.secao_content,
            fg_color=self.CORES["bg_card"],
            corner_radius=8,
        )
        frame.pack(fill="x", pady=8)

        lbl = ctk.CTkLabel(
            frame, text=label,
            font=ctkFont(size=13),
            text_color=self.CORES["text_primary"],
            anchor="w",
        )
        lbl.pack(anchor="w", padx=15, pady=(12, 5))

        # Pega o valor atual do ambiente (que veio do .env via python-dotenv)
        valor_atual = os.getenv(env_key, "")

        campo = ctk.CTkEntry(
            frame,
            fg_color=self.CORES["bg_input"],
            border_width=0,
            text_color=self.CORES["text_primary"],
            placeholder_text_color=self.CORES["text_muted"],
            show="•",
            height=36,
        )
        campo.pack(fill="x", padx=(0, 20), pady=(0, 12))
        if valor_atual:
            campo.insert(0, valor_atual)
        if placeholder:
            # placeholder_text_color não funciona bem com insert prévio; usar placeholder visual
            try:
                campo.configure(placeholder_text=placeholder)
            except Exception:
                pass

        self.campos[config_key] = campo
        self._campos_sensiveis.add(config_key)
        self._env_keys[config_key] = env_key

    def _carregar_valores(self):
        """Carrega os valores salvos nos campos."""
        self.campos = {}
        # Re-renderizar a seção atual com valores carregados
        self._atualizar_conteudo("geral")
        
        # Carregar valores
        for config_key, valor in self.config.items():
            if config_key in self.campos:
                campo = self.campos[config_key]
                if isinstance(campo, ctk.CTkEntry):
                    campo.delete(0, "end")
                    campo.insert(0, str(valor))
                elif isinstance(campo, ctk.CTkOptionMenu):
                    campo.set(str(valor))
                elif isinstance(campo, ctk.CTkSwitch):
                    campo.select() if valor else campo.deselect()

    def _salvar(self):
        """
        Salva as configurações.
        - Preferências não-sensíveis → config.json
        - Campos sensíveis (senhas de API) → .env (nunca em config.json)
        """
        # 1) Campos sensíveis vão para .env primeiro
        env_atualizadas: Dict[str, str] = {}
        for config_key, campo in self.campos.items():
            if config_key in self._campos_sensiveis:
                valor = campo.get().strip() if hasattr(campo, "get") else ""
                env_key = self._env_keys.get(config_key)
                if env_key:
                    env_atualizadas[env_key] = valor

        for env_key, valor in env_atualizadas.items():
            if _salvar_env(env_key, valor):
                # Refletir imediatamente no ambiente do processo
                os.environ[env_key] = valor

        # 2) Preferências não-sensíveis vão para config.json
        for config_key, campo in self.campos.items():
            if config_key in self._campos_sensiveis:
                # Não persistir a chave em config.json; ela vive só no .env
                self.config.pop(config_key, None)
                continue
            if isinstance(campo, ctk.CTkEntry):
                self.config[config_key] = campo.get()
            elif isinstance(campo, ctk.CTkOptionMenu):
                self.config[config_key] = campo.get()
            elif isinstance(campo, ctk.CTkSwitch):
                self.config[config_key] = campo.get()

        config_path = os.path.join(_project_root(), "config.json")
        try:
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
        except OSError as e:
            print(f"Erro ao salvar configurações: {e}")

        # Limpar área de conteúdo (com proteção contra widgets já destruídos)
        try:
            for widget in self.content_area.winfo_children():
                widget.destroy()
        except Exception:
            pass

        # Callback
        if self.callback_salvar:
            self.callback_salvar(self.config, cancelar=False)

    def _cancelar(self):
        """Cancela as alterações."""
        # Limpar área de conteúdo (com proteção contra widgets já destruídos)
        try:
            for widget in self.content_area.winfo_children():
                widget.destroy()
        except:
            pass

        # Callback
        if self.callback_salvar:
            self.callback_salvar(self.config, cancelar=True)


def abrir_configuracoes(parent, content_area, callback_salvar=None):
    """Abre a janela de configurações."""
    ConfiguracoesWindow(parent, content_area, callback_salvar)
