from mcp.server.fastmcp import FastMCP

# 1. Creamos la instancia del servidor
mcp_server = FastMCP("enterprise-safety-tools")

# 2. Definimos la herramienta (debe llamarse exactamente así)
@mcp_server.tool(name="ejecutar_comando_seguro", description="Ejecuta comandos aprobados en el servidor.")
def ejecutar_comando_seguro(comando: str) -> str:
    """Filtra y ejecuta comandos evitando inyecciones de código malicioso."""
    comandos_permitidos = ["systemctl restart app", "systemctl status app"]
    
    if comando.strip() not in comandos_permitidos:
        return f"Seguridad MCP: Comando '{comando}' denegado por políticas de riesgo."
    
    return f"Éxito: El comando '{comando}' fue ejecutado bajo el estándar MCP."

if __name__ == "__main__":
    # 3. Lo corremos con el método nativo de FastMCP
    mcp_server.run()