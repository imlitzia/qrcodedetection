"""
HTTPS server for QR code detector web app.
Uses a self-signed certificate for camera access on mobile.
"""

import http.server
import ssl
import socket
import os
import subprocess
import sys

PORT = 8443

class NoCacheHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    """HTTP handler that prevents caching"""
    
    def end_headers(self):
        # Add headers to prevent caching
        self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate, max-age=0')
        self.send_header('Pragma', 'no-cache')
        self.send_header('Expires', '0')
        super().end_headers()

def get_local_ip():
    """Get the local IP address of this machine."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "localhost"

def generate_ssl_cert():
    """Generate a self-signed SSL certificate."""
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
    except subprocess.CalledProcessError as e:
        print(f"Error generating certificate: {e}")
        return None, None
    except FileNotFoundError:
        print("Error: openssl not found. Please install openssl.")
        return None, None

def main():
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    cert_file, key_file = generate_ssl_cert()
    
    if not cert_file or not key_file:
        print("Failed to generate SSL certificate. Exiting.")
        sys.exit(1)
    
    local_ip = get_local_ip()
    
    print()
    print("=" * 65)
    print("  QR CODE DETECTOR - HTTPS Server (No Cache)")
    print("=" * 65)
    print()
    print("=" * 65)
    print("  ACCESS URL (use this on your phone):")
    print("=" * 65)
    print()
    print(f"    https://{local_ip}:{PORT}")
    print()
    print("  TIP: If page doesn't update, add ?v=2 to the URL:")
    print(f"    https://{local_ip}:{PORT}?v=2")
    print()
    print("=" * 65)
    print("  IMPORTANT - First time setup:")
    print("=" * 65)
    print()
    print("  When you open the URL, you'll see a security warning.")
    print("  This is normal for self-signed certificates.")
    print()
    print("  On iPhone (Safari):")
    print("    1. Tap 'Show Details'")
    print("    2. Tap 'visit this website'")
    print("    3. Tap 'Visit Website'")
    print()
    print("  On Android (Chrome):")
    print("    1. Tap 'Advanced'")
    print("    2. Tap 'Proceed to [IP] (unsafe)'")
    print()
    print("=" * 65)
    print("  Press Ctrl+C to stop")
    print("=" * 65)
    print()
    
    try:
        httpd = http.server.HTTPServer(("0.0.0.0", PORT), NoCacheHTTPRequestHandler)
        
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(cert_file, key_file)
        httpd.socket = context.wrap_socket(httpd.socket, server_side=True)
        
        print(f"HTTPS Server running on port {PORT}...")
        print("Caching is DISABLED - changes will show immediately")
        print("Waiting for connections...")
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
