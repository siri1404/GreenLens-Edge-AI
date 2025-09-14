#!/usr/bin/env python3
"""
Install required dependencies for the EcoCopilot app
"""
import subprocess
import sys

def install_package(package):
    """Install a package using pip"""
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])
        print(f"✅ Successfully installed {package}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install {package}: {e}")
        return False

def main():
    """Install all required dependencies"""
    print("🔧 Installing dependencies for EcoCopilot app...")
    print("=" * 50)
    
    # List of required packages
    packages = [
        "opencv-python>=4.8.0",
        "onnxruntime>=1.16.0", 
        "PyQt5>=5.15.0",
        "PyQtWebEngine>=5.15.0",
        "requests>=2.31.0",
        "httpx>=0.24.0",
        "pyyaml>=6.0",
        "numpy>=1.24.0",
        "easyocr>=1.7.0",
        "gradio>=4.0.0",
        "SpeechRecognition>=3.10.0",
        "pyttsx3>=2.90",
        "PyAudio>=0.2.11"
    ]
    
    success_count = 0
    total_count = len(packages)
    
    for package in packages:
        if install_package(package):
            success_count += 1
    
    print("=" * 50)
    print(f"📊 Installation Summary: {success_count}/{total_count} packages installed successfully")
    
    if success_count == total_count:
        print("🎉 All dependencies installed successfully!")
        print("💡 You can now run: python src/ecocopilot_app.py")
    else:
        print("⚠️ Some packages failed to install. Please check the errors above.")
        print("💡 You may need to install them manually or check your Python environment.")

if __name__ == "__main__":
    main()
