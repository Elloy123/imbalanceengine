import http.server
import socketserver
import os

PORT = 8000
os.chdir("../frontend")

Handler = http.server.SimpleHTTPRequestHandler

with socketserver.TCPServer(("", PORT), Handler) as httpd:
    print(f"🌐 Frontend rodando em http://localhost:{PORT}")
    print("   (Abra este link no navegador para ver o gráfico em tempo real)")
    httpd.serve_forever()