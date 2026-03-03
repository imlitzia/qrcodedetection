"""
QR Code Detection Server with WebSocket support.
- Serves the phone scanner page
- Serves the PC dashboard page
- WebSocket for real-time communication between phone and PC
"""

import http.server
import ssl
import socket
import os
import subprocess
import sys
import json
import hashlib
import base64
import struct
import threading
import time

HTTP_PORT = 8443
WS_PORT = 8444

# Store connected clients
phone_clients = {}
pc_clients = {}
session_data = {}  # session_id -> {qr_codes: [], api_key: '', model: ''}

def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "localhost"

def generate_ssl_cert():
    cert_file = "cert.pem"
    key_file = "key.pem"
    
    if os.path.exists(cert_file) and os.path.exists(key_file):
        print("Using existing SSL certificate...")
        return cert_file, key_file
    
    print("Generating self-signed SSL certificate...")
    cmd = [
        "openssl", "req", "-x509", "-newkey", "rsa:2048",
        "-keyout", key_file, "-out", cert_file,
        "-days", "365", "-nodes",
        "-subj", "/CN=localhost/O=QRDetector/C=US"
    ]
    
    try:
        subprocess.run(cmd, check=True, capture_output=True)
        print("SSL certificate generated!")
        return cert_file, key_file
    except Exception as e:
        print(f"Error generating certificate: {e}")
        return None, None

class WebSocketHandler:
    """Simple WebSocket server for real-time communication."""
    
    def __init__(self, port, ssl_context):
        self.port = port
        self.ssl_context = ssl_context
        self.clients = {}  # conn -> {'type': 'phone'|'pc', 'session': session_id}
        self.running = True
        
    def start(self):
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server.bind(("0.0.0.0", self.port))
        self.server.listen(5)
        
        if self.ssl_context:
            self.server = self.ssl_context.wrap_socket(self.server, server_side=True)
        
        print(f"WebSocket server running on port {self.port}")
        
        while self.running:
            try:
                self.server.settimeout(1)
                conn, addr = self.server.accept()
                thread = threading.Thread(target=self.handle_client, args=(conn, addr))
                thread.daemon = True
                thread.start()
            except socket.timeout:
                continue
            except Exception as e:
                if self.running:
                    print(f"WebSocket error: {e}")
    
    def handle_client(self, conn, addr):
        try:
            # WebSocket handshake
            data = conn.recv(4096).decode('utf-8')
            if 'Upgrade: websocket' not in data:
                conn.close()
                return
            
            # Extract WebSocket key
            key = None
            for line in data.split('\r\n'):
                if line.startswith('Sec-WebSocket-Key:'):
                    key = line.split(': ')[1].strip()
                    break
            
            if not key:
                conn.close()
                return
            
            # Generate accept key
            accept_key = base64.b64encode(
                hashlib.sha1((key + '258EAFA5-E914-47DA-95CA-C5AB0DC85B11').encode()).digest()
            ).decode()
            
            # Send handshake response
            response = (
                'HTTP/1.1 101 Switching Protocols\r\n'
                'Upgrade: websocket\r\n'
                'Connection: Upgrade\r\n'
                f'Sec-WebSocket-Accept: {accept_key}\r\n\r\n'
            )
            conn.send(response.encode())
            
            self.clients[conn] = {'type': None, 'session': None}
            
            # Handle messages
            while self.running:
                try:
                    message = self.receive_message(conn)
                    if message is None:
                        break
                    self.process_message(conn, message)
                except:
                    break
            
            # Cleanup
            if conn in self.clients:
                del self.clients[conn]
            conn.close()
            
        except Exception as e:
            print(f"Client handler error: {e}")
            try:
                conn.close()
            except:
                pass
    
    def receive_message(self, conn):
        try:
            header = conn.recv(2)
            if len(header) < 2:
                return None
            
            opcode = header[0] & 0x0F
            if opcode == 0x8:  # Close frame
                return None
            
            masked = header[1] & 0x80
            length = header[1] & 0x7F
            
            if length == 126:
                length = struct.unpack('>H', conn.recv(2))[0]
            elif length == 127:
                length = struct.unpack('>Q', conn.recv(8))[0]
            
            if masked:
                mask = conn.recv(4)
                data = conn.recv(length)
                decoded = bytes(b ^ mask[i % 4] for i, b in enumerate(data))
            else:
                decoded = conn.recv(length)
            
            return decoded.decode('utf-8')
        except:
            return None
    
    def send_message(self, conn, message):
        try:
            data = message.encode('utf-8')
            length = len(data)
            
            if length <= 125:
                header = bytes([0x81, length])
            elif length <= 65535:
                header = bytes([0x81, 126]) + struct.pack('>H', length)
            else:
                header = bytes([0x81, 127]) + struct.pack('>Q', length)
            
            conn.send(header + data)
        except:
            pass
    
    def process_message(self, conn, message):
        try:
            data = json.loads(message)
            msg_type = data.get('type')
            
            if msg_type == 'register':
                client_type = data.get('client_type')  # 'phone' or 'pc'
                session_id = data.get('session_id')
                
                self.clients[conn] = {'type': client_type, 'session': session_id}
                
                if session_id not in session_data:
                    session_data[session_id] = {'qr_codes': [], 'api_key': '', 'model': ''}
                
                # Send current data to newly connected client
                self.send_message(conn, json.dumps({
                    'type': 'sync',
                    'data': session_data[session_id]
                }))
                
                print(f"{client_type} connected to session {session_id}")
            
            elif msg_type == 'qr_detected':
                session_id = self.clients[conn].get('session')
                if session_id:
                    qr_data = data.get('qr_data')
                    # Forward to all PC clients in this session
                    for c, info in self.clients.items():
                        if info['session'] == session_id and info['type'] == 'pc':
                            self.send_message(c, json.dumps({
                                'type': 'qr_detected',
                                'qr_data': qr_data
                            }))
            
            elif msg_type == 'qr_analyzed':
                session_id = self.clients[conn].get('session')
                if session_id:
                    # Forward analysis result to phone
                    for c, info in self.clients.items():
                        if info['session'] == session_id and info['type'] == 'phone':
                            self.send_message(c, json.dumps({
                                'type': 'qr_analyzed',
                                'qr_data': data.get('qr_data'),
                                'category': data.get('category')
                            }))
            
            elif msg_type == 'config_update':
                session_id = self.clients[conn].get('session')
                if session_id:
                    session_data[session_id]['api_key'] = data.get('api_key', '')
                    session_data[session_id]['model'] = data.get('model', '')
                    
        except json.JSONDecodeError:
            pass


def run_http_server(port, ssl_context):
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    handler = http.server.SimpleHTTPRequestHandler
    
    httpd = http.server.HTTPServer(("0.0.0.0", port), handler)
    if ssl_context:
        httpd.socket = ssl_context.wrap_socket(httpd.socket, server_side=True)
    
    print(f"HTTPS server running on port {port}")
    httpd.serve_forever()


def main():
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    cert_file, key_file = generate_ssl_cert()
    if not cert_file:
        print("Failed to generate SSL certificate")
        sys.exit(1)
    
    ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ssl_context.load_cert_chain(cert_file, key_file)
    
    local_ip = get_local_ip()
    session_id = hashlib.md5(f"{local_ip}{time.time()}".encode()).hexdigest()[:8]
    
    print()
    print("=" * 65)
    print("  QR CODE DETECTOR - Phone + PC System")
    print("=" * 65)
    print()
    print("=" * 65)
    print("  STEP 1: Open PC Dashboard")
    print("=" * 65)
    print()
    print(f"    https://{local_ip}:{HTTP_PORT}/pc.html?session={session_id}")
    print()
    print("=" * 65)
    print("  STEP 2: Scan this QR or open on Phone")
    print("=" * 65)
    print()
    print(f"    https://{local_ip}:{HTTP_PORT}/phone.html?session={session_id}")
    print()
    print("=" * 65)
    print("  SECURITY WARNING")
    print("=" * 65)
    print()
    print("  You'll see a security warning (self-signed certificate).")
    print("  Click 'Advanced' -> 'Proceed' to continue.")
    print()
    print("=" * 65)
    print("  Press Ctrl+C to stop")
    print("=" * 65)
    print()
    
    # Start WebSocket server in a thread
    ws_handler = WebSocketHandler(WS_PORT, ssl_context)
    ws_thread = threading.Thread(target=ws_handler.start)
    ws_thread.daemon = True
    ws_thread.start()
    
    # Run HTTP server in main thread
    try:
        run_http_server(HTTP_PORT, ssl_context)
    except KeyboardInterrupt:
        print("\n\nServer stopped. Goodbye!")
        ws_handler.running = False


if __name__ == "__main__":
    main()
