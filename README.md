# QR Code Detector

Real-time QR code detection using your webcam. Detects and counts multiple QR codes simultaneously.

## Features

- 📷 Real-time webcam QR code detection
- 🔢 Counts multiple QR codes on screen
- 🏷️ Displays decoded QR data
- 📸 Screenshot capture functionality
- 🎨 Visual overlays with bounding boxes

## Installation

### Prerequisites

On macOS, you need to install `zbar` library first:

```bash
brew install zbar
```

On Ubuntu/Debian:

```bash
sudo apt-get install libzbar0
```

On Windows, `pyzbar` should work out of the box.

### Python Dependencies

```bash
pip install -r requirements.txt
```

## Usage

Run the detector:

```bash
python qr_detector.py
```

### Controls

- **Q** - Quit the application
- **S** - Save a screenshot

## How It Works

1. The program captures video from your webcam
2. Each frame is analyzed using the `pyzbar` library to detect QR codes
3. Detected QR codes are highlighted with green bounding boxes
4. The count of detected QR codes is displayed at the top
5. Decoded QR data is shown below each detected code

## Example

Show one or more QR codes to your webcam, and the program will:
- Draw a green box around each QR code
- Label each QR code (QR #1, QR #2, etc.)
- Display the total count at the top
- Show the decoded content of each QR code
