import asyncio
import websockets
import json
import time
from binance_ws import BinanceDataFeed
from engine_orchestrator import VolumeEngineOrchestrator

connected_clients = set()
current_orchestrator = None

async def register(websocket):
    connected_clients.add(websocket)
    print(f"🔌 Novo cliente conectado ({len(connected_clients)} total)")

async def unregister(websocket):
    if websocket in connected_clients:
        connected_clients.remove(websocket)
    print(f"👋 Cliente desconectado ({len(connected_clients)} restantes)")

async def broadcast(message):
    if connected_clients:
        await asyncio.gather(
            *[client.send(json.dumps(message)) for client in connected_clients],
            return_exceptions=True
        )

async def handler(websocket, path):
    await register(websocket)
    try:
        async for message in websocket:
            try:
                data = json.loads(message)
                
                if data.get("type") == "set_engines":
                    global current_orchestrator
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
                
                elif data.get("type") == "get_engine_list":
                    await websocket.send(json.dumps({
                        "type": "engine_list",
                        "engines": [
                            {"id": "tick_velocity", "name": "⚡ Velocidade dos Trades", "description": "Trades rápidos = maior volume"},
                            {"id": "side_inference", "name": "🎯 Inferência de Side", "description": "Refina side usando padrões de preço"},
                            {"id": "spread_weight", "name": "📉 Ponderação por Volatilidade", "description": "Ajusta volume conforme volatilidade recente"},
                            {"id": "micro_cluster", "name": "🧩 Micro-Agrupamento (100ms)", "description": "Detecta micro-absorções de ordens"},
                            {"id": "atr_normalize", "name": "📊 Normalização por ATR", "description": "Estabiliza volume em alta volatilidade"},
                        ]
                    }))
            except json.JSONDecodeError:
                print(f"❌ JSON inválido recebido: {message[:50]}")
    
    except Exception as e:
        print(f"⚠️ Erro na conexão WebSocket: {e}")
    finally:
        await unregister(websocket)

async def binance_forwarder():
    global current_orchestrator
    
    # Inicializa com engines padrão
    current_orchestrator = VolumeEngineOrchestrator(
        engine_names=["tick_velocity", "side_inference", "micro_cluster"],
        weights={"tick_velocity": 1.0, "side_inference": 1.0, "micro_cluster": 1.5}
    )
    
    feed = BinanceDataFeed(symbol="btcusdt", orchestrator=current_orchestrator)
    
    async def on_data(payload):
        await broadcast(payload)
    
    # Correção crítica para Windows
    while True:
        try:
            await feed.connect(on_data)
        except Exception as e:
            print(f"⚠️ Erro na conexão com Binance: {e}")
            await asyncio.sleep(5)

async def main():
    # Correção crítica para Windows
    if hasattr(asyncio, 'WindowsSelectorEventLoopPolicy'):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    # Servidor WebSocket para frontend
    server = await websockets.serve(handler, "localhost", 8765)
    print("📡 Servidor WebSocket local rodando em ws://localhost:8765")
    
    # Inicia coleta de dados da Binance
    await binance_forwarder()

if __name__ == "__main__":
    print("="*70)
    print("🚀 IMBALANCEENGINE - Dados BTC/USDT da Binance em Tempo Real")
    print("="*70)
    print("\n✅ Servidor iniciado")
    print("✅ Conectando à Binance WebSocket público")
    print("✅ Engines ativos: tick_velocity, side_inference, micro_cluster")
    print("\n🌐 Abra no navegador: http://localhost:8000")
    print("\n⚠️  Dados 100% públicos - sem API key necessária")
    print("⚠️  Projeto isolado - zero risco para sua conta Exness\n")
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Servidor encerrado pelo usuário")
    except Exception as e:
        print(f"\n❌ Erro fatal: {e}")
        print("💡 Dica: Execute 'pip install websockets --upgrade' se vir erro de import")