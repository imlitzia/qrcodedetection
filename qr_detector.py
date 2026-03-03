"""
QR Code Detection using Webcam
Detects and counts multiple QR codes in real-time from webcam feed.
Uses pyzbar for accurate detection.
"""

import cv2
import numpy as np
from datetime import datetime
import os

# Set the library path for zbar on macOS (Homebrew)
os.environ['DYLD_LIBRARY_PATH'] = '/opt/homebrew/opt/zbar/lib:' + os.environ.get('DYLD_LIBRARY_PATH', '')

# Try to import pyzbar, with fallback instructions
try:
    from pyzbar import pyzbar
    from pyzbar.pyzbar import ZBarSymbol
    USE_PYZBAR = True
    print("Using pyzbar (high accuracy mode)")
except ImportError:
    USE_PYZBAR = False
    print("pyzbar not available, using OpenCV detector")


class QRCodeDetector:
    """QR Code detector using pyzbar for high accuracy."""
    
    def __init__(self):
        if not USE_PYZBAR:
            self.cv_detector = cv2.QRCodeDetector()
        self.last_results = []
        self.frame_skip = 0
    
    def detect_pyzbar(self, frame):
        """Detect using pyzbar (more accurate)."""
        qr_codes = []
        
        # Try on grayscale
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # Detect QR codes
        decoded = pyzbar.decode(gray, symbols=[ZBarSymbol.QRCODE])
        
        for obj in decoded:
            # Get polygon points
            points = np.array(obj.polygon, dtype=np.float32)
            if len(points) == 4:
                data = obj.data.decode('utf-8')
                qr_codes.append((data, points))
        
        # If nothing found, try with enhanced contrast
        if not qr_codes:
            clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
            enhanced = clahe.apply(gray)
            decoded = pyzbar.decode(enhanced, symbols=[ZBarSymbol.QRCODE])
            
            for obj in decoded:
                points = np.array(obj.polygon, dtype=np.float32)
                if len(points) == 4:
                    data = obj.data.decode('utf-8')
                    qr_codes.append((data, points))
        
        # Try with thresholding if still nothing
        if not qr_codes:
            _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            decoded = pyzbar.decode(thresh, symbols=[ZBarSymbol.QRCODE])
            
            for obj in decoded:
                points = np.array(obj.polygon, dtype=np.float32)
                if len(points) == 4:
                    data = obj.data.decode('utf-8')
                    qr_codes.append((data, points))
        
        return qr_codes
    
    def detect_opencv(self, frame):
        """Fallback to OpenCV detector."""
        qr_codes = []
        try:
            retval, decoded_info, points, _ = self.cv_detector.detectAndDecodeMulti(frame)
            if retval and points is not None:
                for i, pts in enumerate(points):
                    data = decoded_info[i] if i < len(decoded_info) else ""
                    if pts is not None and len(pts) > 0:
                        qr_codes.append((data, pts))
        except:
            pass
        return qr_codes
    
    def detect(self, frame):
        """Detect QR codes in frame."""
        if USE_PYZBAR:
            qr_codes = self.detect_pyzbar(frame)
        else:
            qr_codes = self.detect_opencv(frame)
        
        # Cache results for smoother display
        if qr_codes:
            self.last_results = qr_codes
            self.frame_skip = 8
        elif self.frame_skip > 0:
            self.frame_skip -= 1
            return self.last_results
        else:
            self.last_results = []
        
        return qr_codes if qr_codes else self.last_results


def draw_qr_overlay(frame, qr_codes):
    """Draw bounding boxes and labels around detected QR codes."""
    for i, (data, points) in enumerate(qr_codes, 1):
        pts = points.astype(np.int32)
        if len(pts.shape) == 3:
            pts = pts.reshape(-1, 2)
        
        # Ensure we have 4 points
        if len(pts) != 4:
            continue
        
        # Draw filled polygon with transparency
        overlay = frame.copy()
        cv2.fillPoly(overlay, [pts], (0, 255, 180))
        cv2.addWeighted(overlay, 0.2, frame, 0.8, 0, frame)
        
        # Draw thick border
        cv2.polylines(frame, [pts], True, (0, 255, 180), 3)
        
        # Corner markers
        for point in pts:
            cv2.circle(frame, tuple(point), 10, (0, 200, 255), -1)
            cv2.circle(frame, tuple(point), 10, (0, 100, 150), 2)
        
        # Label background and text
        x, y = int(pts[0][0]), int(pts[0][1])
        label = f"QR #{i}"
        (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)
        label_y = max(35, y)
        cv2.rectangle(frame, (x, label_y - 32), (x + tw + 14, label_y + 4), (0, 255, 180), -1)
        cv2.putText(frame, label, (x + 7, label_y - 8), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)
        
        # QR data below the box
        if data:
            rect = cv2.boundingRect(pts)
            data_y = rect[1] + rect[3] + 25
            display_data = data[:45] + "..." if len(data) > 45 else data
            (dw, dh), _ = cv2.getTextSize(display_data, cv2.FONT_HERSHEY_SIMPLEX, 0.55, 1)
            cv2.rectangle(frame, (rect[0] - 4, data_y - dh - 8), 
                         (rect[0] + dw + 8, data_y + 8), (0, 0, 0), -1)
            cv2.putText(frame, display_data, (rect[0], data_y),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1)
    
    return frame


def draw_status_panel(frame, qr_count, fps):
    """Draw status panel."""
    height, width = frame.shape[:2]
    
    # Top panel
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, 0), (width, 70), (25, 25, 25), -1)
    cv2.addWeighted(overlay, 0.75, frame, 0.25, 0, frame)
    
    # Title
    cv2.putText(frame, "QR CODE DETECTOR", (20, 30),
               cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 180), 2)
    
    # Detection mode
    mode = "pyzbar" if USE_PYZBAR else "OpenCV"
    cv2.putText(frame, f"Mode: {mode}", (20, 55),
               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (150, 150, 150), 1)
    
    # Count
    count_text = f"Detected: {qr_count}"
    count_color = (0, 255, 180) if qr_count > 0 else (120, 120, 120)
    cv2.putText(frame, count_text, (width - 150, 30),
               cv2.FONT_HERSHEY_SIMPLEX, 0.65, count_color, 2)
    
    # FPS
    cv2.putText(frame, f"FPS: {fps:.0f}", (width - 150, 55),
               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (150, 150, 150), 1)
    
    # Bottom bar
    overlay2 = frame.copy()
    cv2.rectangle(overlay2, (0, height - 40), (width, height), (25, 25, 25), -1)
    cv2.addWeighted(overlay2, 0.75, frame, 0.25, 0, frame)
    cv2.putText(frame, "Q: Quit | S: Screenshot | Hold QR codes steady for best results",
               (20, height - 14), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (140, 140, 140), 1)
    
    return frame


def main():
    print("=" * 55)
    print("  QR CODE DETECTOR - High Accuracy Mode")
    print("=" * 55)
    print("\nStarting webcam...")
    
    cap = cv2.VideoCapture(0)
    
    if not cap.isOpened():
        print("Error: Could not open webcam.")
        return
    
    # Camera settings
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    cap.set(cv2.CAP_PROP_FPS, 30)
    cap.set(cv2.CAP_PROP_AUTOFOCUS, 1)
    
    qr_detector = QRCodeDetector()
    
    print("Webcam started!")
    print("\nControls: Q = Quit, S = Screenshot")
    print("Tip: Hold QR codes steady and ensure good lighting.\n")
    
    fps = 0
    prev_time = datetime.now()
    frame_count = 0
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        frame = cv2.flip(frame, 1)
        
        # Detect
        qr_codes = qr_detector.detect(frame)
        qr_count = len(qr_codes)
        
        # FPS
        frame_count += 1
        now = datetime.now()
        elapsed = (now - prev_time).total_seconds()
        if elapsed >= 0.5:
            fps = frame_count / elapsed
            frame_count = 0
            prev_time = now
        
        # Draw
        frame = draw_qr_overlay(frame, qr_codes)
        frame = draw_status_panel(frame, qr_count, fps)
        
        # Console
        if qr_count > 0:
            info = f"\r[{now.strftime('%H:%M:%S')}] {qr_count} QR"
            for i, (data, _) in enumerate(qr_codes[:3], 1):
                if data:
                    info += f" | #{i}: {data[:20]}..."
            print(info + "      ", end="", flush=True)
        
        cv2.imshow("QR Code Detector", frame)
        
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q') or key == ord('Q'):
            break
        elif key == ord('s') or key == ord('S'):
            filename = f"qr_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            cv2.imwrite(filename, frame)
            print(f"\nSaved: {filename}")
    
    cap.release()
    cv2.destroyAllWindows()
    print("\n\nGoodbye!")


if __name__ == "__main__":
    main()
