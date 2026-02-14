"""
ImbalanceEngine - Servidor WebSocket + HTTP
Versão corrigida: usa biblioteca 'websockets' (sem implementação manual)
Compatível com Windows (asyncio fix aplicado)
"""
import asyncio
import websockets
import json
import time
import threading
import os
from http.server import HTTPServer, SimpleHTTPRequestHandler
from binance_ws import BinanceDataFeed
from engine_orchestrator import VolumeEngineOrchestrator

# ============================================
# Estado global
# ============================================
connected_clients = set()
current_orchestrator = None

# Lista de engines disponíveis (enviada ao frontend)
ENGINE_LIST = [
    {"id": "tick_velocity",  "name": "⚡ Velocidade dos Trades",       "description": "Trades rápidos = maior volume"},
    {"id": "side_inference", "name": "🎯 Inferência de Side",          "description": "Refina side usando padrões de preço"},
    {"id": "spread_weight",  "name": "📉 Ponderação por Volatilidade", "description": "Ajusta volume conforme volatilidade recente"},
    {"id": "micro_cluster",  "name": "🧩 Micro-Agrupamento (100ms)",   "description": "Detecta micro-absorções de ordens"},
    {"id": "atr_normalize",  "name": "📊 Normalização por ATR",        "description": "Estabiliza volume em alta volatilidade"},
]


# ============================================
# WebSocket: broadcast para todos os clientes
# ============================================
async def broadcast(message: dict):
    """Envia mensagem para todos os clientes conectados."""
    if not connected_clients:
        return
    
    data = json.dumps(message)
    
    # Envia para todos, remove clientes mortos
    disconnected = set()
    for client in connected_clients:
        try:
            await client.send(data)
        except websockets.exceptions.ConnectionClosed:
            disconnected.add(client)
        except Exception as e:
            print(f"⚠️ Erro ao enviar para cliente: {e}")
            disconnected.add(client)
    
    for client in disconnected:
        connected_clients.discard(client)
        print(f"👋 Cliente removido ({len(connected_clients)} restantes)")


# ============================================
# WebSocket: handler de cada conexão
# ============================================
async def ws_handler(websocket):
    """Gerencia uma conexão WebSocket individual."""
    global current_orchestrator
    
    # Registra cliente
    connected_clients.add(websocket)
    print(f"🔌 Cliente conectado ({len(connected_clients)} total)")
    
    # Envia lista de engines imediatamente
    try:
        await websocket.send(json.dumps({
            "type": "engine_list",
            "engines": ENGINE_LIST
        }))
    except Exception as e:
        print(f"⚠️ Erro ao enviar engine_list: {e}")
    
    # Escuta mensagens do cliente
    try:
        async for message in websocket:
            try:
                data = json.loads(message)
                msg_type = data.get("type", "")
                
                if msg_type == "get_engine_list":
                    await websocket.send(json.dumps({
                        "type": "engine_list",
                        "engines": ENGINE_LIST
                    }))
                
                elif msg_type == "set_engines":
                    try:
                        current_orchestrator = VolumeEngineOrchestrator(
                            engine_names=data["engines"],
                            weights=data.get("weights", {})
                        )
                        await broadcast({
                            "type": "engines_updated",
                            "engines": data["engines"],
                            "weights": data.get("weights", {})
                        })
                        print(f"⚙️ Engines atualizados: {data['engines']}")
                    except Exception as e:
                        await websocket.send(json.dumps({
                            "type": "error",
                            "message": str(e)
                        }))
                
            except json.JSONDecodeError:
                print(f"❌ JSON inválido: {message[:80]}")
    
    except websockets.exceptions.ConnectionClosed:
        pass
    except Exception as e:
        print(f"⚠️ Erro na conexão: {e}")
    finally:
        connected_clients.discard(websocket)
        print(f"👋 Cliente desconectado ({len(connected_clients)} restantes)")


# ============================================
# Binance: coleta e retransmite trades
# ============================================
async def binance_forwarder():
    """Conecta à Binance e retransmite trades para clientes WebSocket."""
    global current_orchestrator
    
    # Engines padrão
    current_orchestrator = VolumeEngineOrchestrator(
        engine_names=["tick_velocity", "side_inference", "micro_cluster"],
        weights={"tick_velocity": 1.0, "side_inference": 1.0, "micro_cluster": 1.5}
    )
    
    feed = BinanceDataFeed(symbol="btcusdt", orchestrator=current_orchestrator)
    
    async def on_data(payload):
        await broadcast(payload)
    
    # Loop de reconexão (sem recursão)
    while True:
        try:
            await feed.connect(on_data)
        except Exception as e:
            print(f"⚠️ Erro Binance: {e}. Reconectando em 5s...")
            await asyncio.sleep(5)


# ============================================
# HTTP: serve o frontend
# ============================================
def start_http_server():
    """Servidor HTTP simples para servir o index.html."""
    frontend_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "frontend")
    
    if not os.path.exists(frontend_dir):
        # Tenta caminho alternativo (se backend e frontend estão no mesmo nível)
        frontend_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "frontend")
    
    if not os.path.exists(frontend_dir):
        print(f"⚠️ Diretório frontend não encontrado! Procurado em:")
        print(f"   {frontend_dir}")
        print(f"   Coloque o index.html na pasta 'frontend' ao lado da pasta 'backend'")
        return
    
    os.chdir(frontend_dir)
    
    # Suprime logs do HTTP server (muito verboso)
    class QuietHandler(SimpleHTTPRequestHandler):
        def log_message(self, format, *args):
            pass  # Silencia GET /index.html logs
    
    httpd = HTTPServer(("localhost", 8000), QuietHandler)
    print("🌐 Frontend: http://localhost:8000")
    httpd.serve_forever()


# ============================================
# Main: inicializa tudo
# ============================================
async def main():
    # Servidor WebSocket (porta 8765)
    server = await websockets.serve(ws_handler, "localhost", 8765)
    print("📡 WebSocket: ws://localhost:8765")
    
    # Coleta Binance (roda em paralelo)
    await binance_forwarder()


if __name__ == "__main__":
    print("=" * 60)
    print("🚀 IMBALANCEENGINE - BTC/USDT Tempo Real")
    print("=" * 60)
    
    # Fix para Windows: evita erro de event loop
    if hasattr(asyncio, 'WindowsSelectorEventLoopPolicy'):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    # Thread separada para HTTP (não conflita com asyncio)
    http_thread = threading.Thread(target=start_http_server, daemon=True)
    http_thread.start()
    
    print("\n✅ Engines: tick_velocity, side_inference, micro_cluster")
    print("✅ Abra no navegador: http://localhost:8000")
    print("⚠️  Dados públicos Binance - sem API key\n")
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Servidor encerrado")
    except Exception as e:
        print(f"\n❌ Erro: {e}")
        print("💡 Execute: pip install websockets --upgrade")