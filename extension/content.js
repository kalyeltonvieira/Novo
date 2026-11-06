console.log("[Auditor IA] Extensão carregada no portal de transparência.");

// Injeta painel flutuante de auditoria ao vivo na página
const badge = document.createElement("div");
badge.className = "auditor-ia-badge";
badge.innerHTML = `
  <div style="font-weight: bold;">🧠 Auditor IA Ativo</div>
  <div style="font-size: 11px; opacity: 0.9;">Monitorando sobrepreço e CNPJs</div>
`;
document.body.appendChild(badge);
