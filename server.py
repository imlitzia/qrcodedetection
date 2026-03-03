"""
Simple HTTPS server for QR code detector.
Serves the phone scanner and PC dashboard pages.
"""

import http.server
import ssl
import socket
import os
import subprocess
import sys
import hashlib
import time

PORT = 8443

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

def main():
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    cert_file, key_file = generate_ssl_cert()
    if not cert_file:
        print("Failed to generate SSL certificate")
        sys.exit(1)
    
    local_ip = get_local_ip()
    session_id = hashlib.md5(f"{local_ip}{time.time()}".encode()).hexdigest()[:8]
    
    print()
    print("=" * 65)
    print("  QR CODE DETECTOR - Phone + PC System")
    print("=" * 65)
    print()
    print("=" * 65)
    print("  STEP 1: Open PC Dashboard on this computer")
    print("=" * 65)
    print()
    print(f"    https://localhost:{PORT}/pc.html")
    print()
    print("=" * 65)
    print("  STEP 2: Open Phone Scanner on your mobile")
    print("=" * 65)
    print()
    print(f"    https://{local_ip}:{PORT}/phone.html")
    print()
    print("=" * 65)
    print("  SECURITY WARNING")
    print("=" * 65)
    print()
    print("  You'll see a security warning (self-signed certificate).")
    print("  - Chrome: Click 'Advanced' -> 'Proceed to site'")
    print("  - Safari: Click 'Show Details' -> 'visit this website'")
    print()
    print("=" * 65)
    print("  Press Ctrl+C to stop")
    print("=" * 65)
    print()
    
    handler = http.server.SimpleHTTPRequestHandler
    
    try:
        httpd = http.server.HTTPServer(("0.0.0.0", PORT), handler)
        
        ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ssl_context.load_cert_chain(cert_file, key_file)
        httpd.socket = ssl_context.wrap_socket(httpd.socket, server_side=True)
        
        print(f"Server running on port {PORT}...")
        print()
        httpd.serve_forever()
    except OSError as e:
        if "Address already in use" in str(e):
            print(f"ERROR: Port {PORT} is already in use!")
            print("Stop the other server first (Ctrl+C) and try again.")
        else:
            print(f"ERROR: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n\nServer stopped. Goodbye!")

if __name__ == "__main__":
    main()
