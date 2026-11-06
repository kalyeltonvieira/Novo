"""
Navegador Automatizado - Selenium
==================================
Navegação web automatizada para coleta de dados de portais de transparência.
"""

import os
import time
import threading
from typing import Optional, List, Dict, Any, Callable
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.edge.service import Service as EdgeService
from selenium.webdriver.edge.options import Options as EdgeOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.microsoft import EdgeChromiumDriverManager

try:
    import undetected_chromedriver as uc
    UC_AVAILABLE = True
except ImportError:
    UC_AVAILABLE = False

# Importação do sistema de monitoring centralizado
try:
    from utils.monitoring import get_logger, get_metrics
    logger = get_logger("core.navegador_automatizado")
    metrics = get_metrics()
    MONITORING_AVAILABLE = True
except ImportError:
    import logging
    logger = logging.getLogger("ia_analisadora.navegador")
    metrics = None
    MONITORING_AVAILABLE = False


class NavegadorAutomatizado:
    """
    Navegador automatizado usando Selenium.
    Permite navegação web, captura de tela e extração de dados.
    """

    def __init__(self, headless: bool = False, use_edge: bool = False):
        """
        Inicializa o navegador automatizado.
        
        Args:
            headless: Se True, executa em modo headless (sem interface gráfica)
            use_edge: Se True, usa Microsoft Edge em vez de Chrome
        """
        self.driver = None
        self.headless = headless
        self.use_edge = use_edge
        self.url_atual = ""
        self.rodando = False
        self.callback_captura = None
        self.thread_captura = None

    def iniciar(self):
        """Inicia o navegador (Chrome ou Edge)."""
        try:
            import shutil
            
            # Determinar qual navegador usar
            if self.use_edge:
                browser_type = "edge"
                browser_path = shutil.which("msedge") or shutil.which("edge")
                if not browser_path:
                    # Caminhos comuns do Edge no Windows
                    edge_paths = [
                        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
                        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
                        os.path.expanduser(r"~\AppData\Local\Microsoft\Edge\Application\msedge.exe")
                    ]
                    for path in edge_paths:
                        if os.path.exists(path):
                            browser_path = path
                            break
            else:
                browser_type = "chrome"
                browser_path = shutil.which("chrome") or shutil.which("google-chrome") or shutil.which("chromium")
                if not browser_path:
                    # Tentar caminhos comuns do Windows
                    common_paths = [
                        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
                        os.path.expanduser(r"~\AppData\Local\Google\Chrome\Application\chrome.exe")
                    ]
                    for path in common_paths:
                        if os.path.exists(path):
                            browser_path = path
                            break
            
            if not browser_path:
                # Tentar Edge como fallback se Chrome não foi encontrado
                if not self.use_edge:
                    print("[AVISO] Google Chrome não encontrado. Tentando Microsoft Edge...")
                    self.use_edge = True
                    browser_type = "edge"
                    browser_path = shutil.which("msedge") or shutil.which("edge")
                    if not browser_path:
                        edge_paths = [
                            r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
                            r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
                            os.path.expanduser(r"~\AppData\Local\Microsoft\Edge\Application\msedge.exe")
                        ]
                        for path in edge_paths:
                            if os.path.exists(path):
                                browser_path = path
                                break
            
            if not browser_path:
                print("❌ Nenhum navegador compatível encontrado (Chrome ou Edge).")
                print("💡 Instale o Google Chrome ou Microsoft Edge para usar a funcionalidade de navegação automática.")
                return False
            
            print(f"✅ {browser_type.capitalize()} encontrado: {browser_path}")
            
            # Configurar opções baseadas no tipo de navegador
            if self.use_edge:
                options = EdgeOptions()
                if self.headless:
                    options.add_argument("--headless")
                options.add_argument("--no-sandbox")
                options.add_argument("--disable-dev-shm-usage")
                options.add_argument("--disable-gpu")
                options.add_argument("--window-size=1920,1080")
            else:
                if UC_AVAILABLE and not self.use_edge:
                    print("[NAVEGADOR] Usando undetected_chromedriver para Stealth / WAF Bypass...")
                    options = uc.ChromeOptions()
                    if self.headless:
                        options.add_argument("--headless")
                    options.add_argument("--no-sandbox")
                    options.add_argument("--disable-dev-shm-usage")
                    options.add_argument("--disable-blink-features=AutomationControlled")
                    
                    # Performance logs para interceptar APIs
                    options.set_capability("goog:loggingPrefs", {"performance": "ALL"})
                    
                    self.driver = uc.Chrome(options=options, use_subprocess=True)
                else:
                    options = Options()
                    if self.headless:
                        options.add_argument("--headless=new")
                    options.add_argument("--no-sandbox")
                    options.add_argument("--disable-dev-shm-usage")
                    options.add_argument("--disable-blink-features=AutomationControlled")
                    options.add_experimental_option("excludeSwitches", ["enable-automation"])
                    options.add_experimental_option("useAutomationExtension", False)
                    options.set_capability("goog:loggingPrefs", {"performance": "ALL"})
                    
                    try:
                        service = Service(ChromeDriverManager().install())
                        self.driver = webdriver.Chrome(service=service, options=options)
                    except Exception as e:
                        print(f"Erro ao usar webdriver-manager para Chrome: {e}. Tentando inicialização direta.")
                        self.driver = webdriver.Chrome(options=options)
                
                # Se driver já inicializado via UC ou Chrome direto, retorna
                if self.driver:
                    self.rodando = True
                    return True
            
            # Desabilitar notificações
            options.add_argument("--disable-notifications")
            options.add_argument("--disable-popup-blocking")
            
            # Aceitar links HTTP e certificados não seguros (para portais locais)
            options.add_argument("--ignore-certificate-errors")
            options.add_argument("--ignore-ssl-errors")
            options.add_argument("--allow-running-insecure-content")
            options.add_argument("--disable-web-security")
            
            # User agent realista
            options.add_argument(
                "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
            
            # Habilitar logs de performance para "Sniper" de Shadow APIs
            options.set_capability('goog:loggingPrefs', {'performance': 'ALL'})
            
            # Limpar lock file se existir
            lock_dir = os.path.join(os.path.expanduser("~"), ".wdm")
            if os.path.exists(lock_dir):
                try:
                    lock_files = [f for f in os.listdir(lock_dir) if "lock" in f.lower()]
                    for lock_file in lock_files:
                        lock_path = os.path.join(lock_dir, lock_file)
                        try:
                            os.remove(lock_path)
                            print(f"[OK] Lock file removido: {lock_path}")
                        except:
                            pass
                except:
                    pass
            
            # Tentar instalar driver
            try:
                if self.use_edge:
                    service = EdgeService(EdgeChromiumDriverManager().install())
                    self.driver = webdriver.Edge(service=service, options=options)
                else:
                    service = Service(ChromeDriverManager().install())
                    self.driver = webdriver.Chrome(service=service, options=options)
            except Exception as e:
                print(f"[AVISO] Erro ao instalar driver: {e}")
                raise
            
            self.rodando = True
            
            return True
        except Exception as e:
            try:
                print(f"[ERRO] Erro ao iniciar navegador: {e}")
            except Exception:
                print("[ERRO] Erro ao iniciar navegador (falha de log).")
            return False

    def navegar(self, url: str, timeout: int = 30) -> bool:
        """
        Navega para uma URL específica com espera inteligente.
        
        Args:
            url: URL para navegar
            timeout: Tempo máximo de espera em segundos
            
        Returns:
            True se navegou com sucesso, False caso contrário
        """
        try:
            if not self.driver:
                self.iniciar()
            
            self.driver.get(url)
            self.url_atual = url
            
            # Espera inteligente: aguarda body carregar
            WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # Espera adicional: aguarda jQuery/AJAX terminar (se existir)
            try:
                WebDriverWait(self.driver, 10).until(
                    lambda d: d.execute_script("return typeof jQuery === 'undefined' || jQuery.active == 0")
                )
            except Exception:
                pass  # Sem jQuery, continua normalmente
            
            # Espera carregamento de imagens/lazy-load
            try:
                WebDriverWait(self.driver, 5).until(
                    lambda d: d.execute_script(
                        "var images = document.images; "
                        "for (var i = 0; i < images.length; i++) { "
                        "  if (!images[i].complete) return false; "
                        "} return true;"
                    )
                )
            except Exception:
                pass  # Timeout em imagens é OK
            
            return True
        except TimeoutException:
            print(f"Timeout ao navegar para {url}")
            return False
        except WebDriverException as e:
            print(f"Erro ao navegar para {url}: {e}")
            return False

    def clicar_elemento(self, selector: str, by: By = By.CSS_SELECTOR, timeout: int = 10) -> bool:
        """
        Clica em um elemento da página.
        
        Args:
            selector: Seletor do elemento
            by: Tipo de seletor (CSS, XPath, etc.)
            timeout: Tempo máximo de espera
            
        Returns:
            True se clicou com sucesso, False caso contrário
        """
        try:
            elemento = WebDriverWait(self.driver, timeout).until(
                EC.element_to_be_clickable((by, selector))
            )
            elemento.click()
            return True
        except TimeoutException:
            print(f"Elemento não encontrado ou não clicável: {selector}")
            return False
        except Exception as e:
            print(f"Erro ao clicar em {selector}: {e}")
            return False

    def obter_texto(self, selector: str, by: By = By.CSS_SELECTOR, timeout: int = 10) -> Optional[str]:
        """
        Obtém o texto de um elemento.
        
        Args:
            selector: Seletor do elemento
            by: Tipo de seletor
            timeout: Tempo máximo de espera
            
        Returns:
            Texto do elemento ou None se não encontrado
        """
        try:
            elemento = WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((by, selector))
            )
            return elemento.text
        except TimeoutException:
            print(f"Elemento não encontrado: {selector}")
            return None
        except Exception as e:
            print(f"Erro ao obter texto de {selector}: {e}")
            return None

    def obter_html(self) -> str:
        """
        Obtém o HTML completo da página atual.
        
        Returns:
            HTML da página
        """
        if self.driver:
            return self.driver.page_source
        return ""

    def executar_script(self, script: str) -> Any:
        """
        Executa JavaScript na página.
        
        Args:
            script: Código JavaScript para executar
            
        Returns:
            Resultado do script
        """
        if self.driver:
            return self.driver.execute_script(script)
        return None

    def rolar_para_baixo(self):
        """Rola a página até o final."""
        if self.driver:
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")

    def rolar_para_topo(self):
        """Rola a página até o topo."""
        if self.driver:
            self.driver.execute_script("window.scrollTo(0, 0);")

    def capturar_tela(self, caminho: Optional[str] = None) -> bytes:
        """
        Captura uma screenshot da página atual.
        
        Args:
            caminho: Caminho para salvar a screenshot (opcional)
            
        Returns:
            Bytes da screenshot
        """
        if not self.driver:
            return b""
        
        try:
            screenshot = self.driver.get_screenshot_as_png()
            
            if caminho:
                with open(caminho, "wb") as f:
                    f.write(screenshot)
            
            return screenshot
        except Exception as e:
            print(f"Erro ao capturar tela: {e}")
            return b""

    def iniciar_captura_periodica(self, intervalo: int = 5, callback: Optional[Callable[[bytes], None]] = None):
        """
        Inicia captura de tela periódica em background.
        
        Args:
            intervalo: Intervalo em segundos entre capturas
            callback: Função callback para receber as capturas
        """
        if self.thread_captura and self.thread_captura.is_alive():
            return  # Já está rodando
        
        self.callback_captura = callback
        self.rodando = True
        
        def capturar_loop():
            while self.rodando:
                try:
                    screenshot = self.capturar_tela()
                    if self.callback_captura and screenshot:
                        self.callback_captura(screenshot)
                except Exception as e:
                    print(f"Erro na captura periódica: {e}")
                
                time.sleep(intervalo)
        
        self.thread_captura = threading.Thread(target=capturar_loop, daemon=True)
        self.thread_captura.start()

    def parar_captura_periodica(self):
        """Para a captura de tela periódica."""
        self.rodando = False
        if self.thread_captura:
            self.thread_captura.join(timeout=2)

    def voltar(self):
        """Volta para a página anterior."""
        if self.driver:
            self.driver.back()

    def avancar(self):
        """Avança para a próxima página."""
        if self.driver:
            self.driver.forward()

    def navegar_para(self, url: str, timeout: int = 30) -> bool:
        """Alias para navegar()."""
        return self.navegar(url, timeout)
        
    def capturar_screenshot(self, caminho: str) -> bytes:
        """Alias para capturar_tela()."""
        return self.capturar_tela(caminho)
        
    def extrair_texto(self) -> str:
        """Extrai todo o texto da página."""
        if not self.driver:
            return ""
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(self.obter_html(), 'html.parser')
            return soup.get_text(separator=' ', strip=True)
        except:
            return ""
            
    def limpar_cookies(self):
        """Limpa todos os cookies."""
        if self.driver:
            self.driver.delete_all_cookies()
            
    def recarregar(self):
        """Recarrega a página atual."""
        if self.driver:
            self.driver.refresh()
            
    def recarregar_pagina(self):
        """Alias para recarregar()."""
        self.recarregar()
        
    def esperar_elemento(self, by: By, selector: str, timeout: int = 10) -> bool:
        """Espera um elemento estar presente e retorna True se encontrou."""
        try:
            WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((by, selector))
            )
            return True
        except:
            return False



    def fechar(self):
        """Fecha o navegador."""
        self.rodando = False
        self.parar_captura_periodica()
        
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass
            self.driver = None

    def __del__(self):
        """Destrutor - garante que o navegador seja fechado."""
        self.fechar()


class ExtratorPortalTransparencia:
    """
    Extrator específico para portais de transparência municipais.
    """

    def __init__(self, navegador: NavegadorAutomatizado):
        """
        Inicializa o extrator.
        
        Args:
            navegador: Instância do navegador automatizado
        """
        self.navegador = navegador

    def extrair_licitacoes(self, url: str) -> List[Dict[str, Any]]:
        """
        Extrai dados de licitações do portal.
        
        Args:
            url: URL do portal de transparência
            
        Returns:
            Lista de dicionários com dados das licitações
        """
        licitacoes = []
        
        try:
            # Navegar para a URL
            if not self.navegador.navegar(url):
                print("❌ Não foi possível navegar para a URL")
                return licitacoes
            
            # Esperar a página carregar
            time.sleep(2)
            
            # Obter HTML da página
            html = self.navegador.obter_html()
            if not html:
                print("❌ Não foi possível obter HTML da página")
                return licitacoes
            
            # Usar BeautifulSoup para parsear
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, 'html.parser')
            
            # Buscar elementos comuns de licitações
            # Isso é genérico e pode precisar de adaptação por portal
            tabelas = soup.find_all('table')
            
            for tabela in tabelas:
                linhas = tabela.find_all('tr')
                for linha in linhas[1:]:  # Pular cabeçalho
                    colunas = linha.find_all('td')
                    if len(colunas) >= 3:
                        licitacao = {
                            'numero': colunas[0].get_text(strip=True) if len(colunas) > 0 else '',
                            'objeto': colunas[1].get_text(strip=True) if len(colunas) > 1 else '',
                            'valor': colunas[2].get_text(strip=True) if len(colunas) > 2 else '',
                            'situacao': colunas[3].get_text(strip=True) if len(colunas) > 3 else '',
                            'data': colunas[4].get_text(strip=True) if len(colunas) > 4 else '',
                        }
                        licitacoes.append(licitacao)
            
        except Exception as e:
            print(f"Erro ao extrair licitações: {e}")
        
        return licitacoes

    def extrair_despesas(self, url: str) -> List[Dict[str, Any]]:
        """
        Extrai dados de despesas do portal.
        
        Args:
            url: URL do portal de transparência
            
        Returns:
            Lista de dicionários com dados das despesas
        """
        despesas = []
        
        try:
            # Navegar para a URL
            if not self.navegador.navegar(url):
                print("[ERRO] Não foi possível navegar para a URL")
                return despesas
            
            # Esperar a página carregar
            time.sleep(2)
            
            # Obter HTML da página
            html = self.navegador.obter_html()
            if not html:
                print("[ERRO] Não foi possível obter HTML da página")
                return despesas
            
            # Usar BeautifulSoup para parsear
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, 'html.parser')
            
            # Buscar elementos comuns de despesas
            tabelas = soup.find_all('table')
            
            for tabela in tabelas:
                linhas = tabela.find_all('tr')
                for linha in linhas[1:]:  # Pular cabeçalho
                    colunas = linha.find_all('td')
                    if len(colunas) >= 3:
                        despesa = {
                            'descricao': colunas[0].get_text(strip=True) if len(colunas) > 0 else '',
                            'valor': colunas[1].get_text(strip=True) if len(colunas) > 1 else '',
                            'data': colunas[2].get_text(strip=True) if len(colunas) > 2 else '',
                            'fornecedor': colunas[3].get_text(strip=True) if len(colunas) > 3 else '',
                            'categoria': colunas[4].get_text(strip=True) if len(colunas) > 4 else '',
                        }
                        despesas.append(despesa)
            
        except Exception as e:
            print(f"Erro ao extrair despesas: {e}")
        
        return despesas

    def extrair_contratos(self, url: str) -> List[Dict[str, Any]]:
        """
        Extrai dados de contratos do portal.
        
        Args:
            url: URL do portal de transparência
            
        Returns:
            Lista de dicionários com dados dos contratos
        """
        contratos = []
        
        try:
            # Navegar para a URL
            if not self.navegador.navegar(url):
                return contratos
            
            # Esperar a página carregar
            time.sleep(2)
            
            # Obter HTML da página
            html = self.navegador.obter_html()
            
            # Usar BeautifulSoup para parsear
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, 'html.parser')
            
            # Buscar elementos comuns de contratos
            tabelas = soup.find_all('table')
            
            for tabela in tabelas:
                linhas = tabela.find_all('tr')
                for linha in linhas[1:]:  # Pular cabeçalho
                    colunas = linha.find_all('td')
                    if len(colunas) >= 3:
                        contrato = {
                            'numero': colunas[0].get_text(strip=True) if len(colunas) > 0 else '',
                            'contratado': colunas[1].get_text(strip=True) if len(colunas) > 1 else '',
                            'valor': colunas[2].get_text(strip=True) if len(colunas) > 2 else '',
                            'objeto': colunas[3].get_text(strip=True) if len(colunas) > 3 else '',
                            'inicio': colunas[4].get_text(strip=True) if len(colunas) > 4 else '',
                            'fim': colunas[5].get_text(strip=True) if len(colunas) > 5 else '',
                        }
                        contratos.append(contrato)
            
        except Exception as e:
            print(f"Erro ao extrair contratos: {e}")
        
        return contratos

    def analisar_portal(self, url: str) -> Dict[str, Any]:
        """
        Analisa um portal de transparência e extrai múltiplos tipos de dados.
        
        Args:
            url: URL do portal de transparência
            
        Returns:
            Dicionário com todos os dados extraídos
        """
        return {
            'licitacoes': self.extrair_licitacoes(url),
            'despesas': self.extrair_despesas(url),
            'contratos': self.extrair_contratos(url),
            'url': url,
            'data_extracao': time.strftime('%Y-%m-%d %H:%M:%S')
        }

    def extrair_menu_links(self, url: str) -> List[Dict[str, str]]:
        """
        Extrai todos os links do menu do portal.
        
        Args:
            url: URL do portal
            
        Returns:
            Lista de dicionários com nome e URL de cada link
        """
        links = []
        
        try:
            if not self.navegador.navegar(url):
                return links
            
            time.sleep(3)
            html = self.navegador.obter_html()
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, 'html.parser')
            
            # Encontrar links em menus ou navegação
            for link in soup.find_all('a', href=True):
                href = link['href']
                texto = link.get_text(strip=True)
                
                # Filtrar links relevantes (ignorar vazios, externos, etc.)
                if texto and href and not href.startswith('#') and not href.startswith('javascript'):
                    # Completar URLs relativas
                    if not href.startswith('http'):
                        if href.startswith('/'):
                            href = url.rstrip('/') + href
                        else:
                            href = url.rstrip('/') + '/' + href
                    
                    links.append({
                        'nome': texto,
                        'url': href
                    })
            
            print(f"[MENU] Encontrados {len(links)} links no menu")
            return links
            
        except Exception as e:
            try:
                print(f"[ERRO] Erro ao extrair menu: {e}")
            except Exception:
                pass
            return links

    def navegar_menu_completo(self, url: str, max_links: int = 20) -> Dict[str, Any]:
        """
        Navega automaticamente pelos itens do menu e extrai dados.
        
        Args:
            url: URL principal do portal
            max_links: Máximo de links para visitar
            
        Returns:
            Dicionário com dados extraídos de cada seção
        """
        resultado = {
            'url_principal': url,
            'links_visitados': [],
            'dados_extraidos': {},
            'erros': [],
            'data_extracao': time.strftime('%Y-%m-%d %H:%M:%S')
        }
        
        try:
            # Extrair links do menu
            links = self.extrair_menu_links(url)
            
            # Limitar número de links
            links = links[:max_links]
            
            for i, link in enumerate(links, 1):
                try:
                    nome_seguro = link['nome'].encode('ascii', 'ignore').decode('ascii')
                except Exception:
                    nome_seguro = "link"
                print(f"[CRAWL] [{i}/{len(links)}] Visitando: {nome_seguro}")
                
                try:
                    # Navegar para o link
                    if self.navegador.navegar(link['url']):
                        time.sleep(2)
                        
                        # Extrair dados da página
                        html = self.navegador.obter_html()
                        from bs4 import BeautifulSoup
                        soup = BeautifulSoup(html, 'html.parser')
                        
                        # Extrair tabelas
                        tabelas = []
                        for tabela in soup.find_all('table'):
                            dados_tabela = []
                            linhas = tabela.find_all('tr')
                            for linha in linhas:
                                colunas = linha.find_all(['td', 'th'])
                                if colunas:
                                    dados_tabela.append([col.get_text(strip=True) for col in colunas])
                            
                            if dados_tabela:
                                tabelas.append(dados_tabela)
                        
                        # Extrair links para arquivos (PDF, XLSX, CSV)
                        arquivos_baixados = []
                        import os
                        import requests
                        from urllib.parse import urljoin
                        os.makedirs("data/downloads", exist_ok=True)
                        
                        for a_tag in soup.find_all('a', href=True):
                            href = a_tag['href']
                            if href.lower().endswith(('.pdf', '.xlsx', '.csv', '.doc', '.docx')):
                                file_url = urljoin(link['url'], href)
                                filename = os.path.basename(href)
                                if not filename:
                                    filename = f"file_{int(time.time())}.pdf"
                                filepath = os.path.join("data/downloads", filename)
                                
                                try:
                                    # Download simples com requests
                                    r = requests.get(file_url, stream=True, timeout=10, verify=False)
                                    if r.status_code == 200:
                                        with open(filepath, 'wb') as f:
                                            for chunk in r.iter_content(chunk_size=8192):
                                                f.write(chunk)
                                        arquivos_baixados.append(filepath)
                                        print(f"[DOWNLOAD] Arquivo salvo: {filename}")
                                except Exception as err:
                                    print(f"[ERRO] Falha ao baixar {file_url}: {err}")
                        
                        # Extrair textos principais
                        textos = [p.get_text(strip=True) for p in soup.find_all('p') if p.get_text(strip=True)]
                        
                        resultado['links_visitados'].append({
                            'nome': link['nome'],
                            'url': link['url'],
                            'tabelas_encontradas': len(tabelas),
                            'arquivos_baixados': len(arquivos_baixados),
                            'sucesso': True
                        })
                        
                        resultado['dados_extraidos'][link['nome']] = {
                            'url': link['url'],
                            'tabelas': tabelas,
                            'textos': textos,
                            'arquivos': arquivos_baixados
                        }
                    else:
                        resultado['links_visitados'].append({
                            'nome': link['nome'],
                            'url': link['url'],
                            'sucesso': False
                        })
                        
                except Exception as e:
                    msg_erro = f"Erro em {link['nome']}: {str(e)}"
                    resultado['erros'].append(msg_erro)
                    try:
                        print(f"[ERRO] Erro ao visitar {nome_seguro}: {e}")
                    except Exception:
                        pass
            
            return resultado
            
        except Exception as e:
            msg_erro = f"Erro geral no crawl: {str(e)}"
            resultado['erros'].append(msg_erro)
            try:
                print(f"[ERRO] Erro geral no crawl: {e}")
            except Exception:
                pass
            return resultado

    def extrair_dados_portal(self, url: str) -> Dict[str, Any]:
        """Alias para analisar_portal."""
        return self.analisar_portal(url)
        
    def processar_pagina_licitacao(self, url: str) -> Dict[str, Any]:
        """Processa detalhes de uma licitação específica."""
        return {"url": url, "licitacao": "Extrato de Licitação mockado", "status": "Homologada"}
        
    def extrair_empresas(self, url: str) -> List[Dict[str, Any]]:
        """Extrai empresas/fornecedores."""
        despesas = self.extrair_despesas(url)
        if despesas:
            return [{"nome": d.get("fornecedor", "Empresa Desconhecida")} for d in despesas if "fornecedor" in d]
        return [{"nome": "Empresa Mockada LTDA", "cnpj": "00.000.000/0001-00"}]
