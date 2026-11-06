"""
Exemplo de Uso da GUI - IA Analisadora
=======================================
Demonstra como iniciar a interface gráfica.
"""

from gui.app import IAAnalisadoraApp


def iniciar_gui():
    """
    Inicia a interface gráfica da IA Analisadora.
    """
    print("🧠 Iniciando IA Analisadora - Cérebro da Transparência...")
    print("📱 Interface Gráfica Moderna com CustomTkinter")
    
    app = IAAnalisadoraApp()
    app.iniciar()


if __name__ == "__main__":
    iniciar_gui()
