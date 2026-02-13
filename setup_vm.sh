#!/bin/bash
# VM Setup Script for Google Cloud Platform
# This script installs all required dependencies for running the batch processing script

set -e  # Exit on error

echo "🚀 Setting up VM for tattoo artist batch processing..."
echo "=================================================="

# Update system packages
echo "📦 Updating system packages..."
sudo apt-get update
sudo apt-get upgrade -y

# Install Python 3 and pip if not already installed
echo "🐍 Installing Python 3 and pip..."
sudo apt-get install -y python3 python3-pip python3-venv

# Install Google Chrome
echo "🌐 Installing Google Chrome..."
wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | sudo apt-key add -
sudo sh -c 'echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google-chrome.list'
sudo apt-get update
sudo apt-get install -y google-chrome-stable

# Verify Chrome installation
CHROME_VERSION=$(google-chrome --version)
echo "✅ Installed: $CHROME_VERSION"

# Install ChromeDriver
echo "🔧 Installing ChromeDriver..."
# Method 1: Try using apt (may not have latest version)
if ! command -v chromedriver &> /dev/null; then
    echo "   Installing via apt..."
    sudo apt-get install -y chromium-chromedriver || true
fi

# Method 2: Install via webdriver-manager (recommended, handled by Python)
echo "   ChromeDriver will be managed automatically by webdriver-manager"

# Install system dependencies for Chrome
echo "📚 Installing system dependencies..."
sudo apt-get install -y \
    libnss3 \
    libatk-bridge2.0-0 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    libxshmfence1 \
    libxss1

# Create virtual environment (optional but recommended)
echo "🔨 Setting up Python virtual environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Upgrade pip
echo "⬆️  Upgrading pip..."
pip install --upgrade pip

# Install Python dependencies
echo "📥 Installing Python dependencies..."
pip install -r requirements.txt

# Install webdriver-manager for automatic ChromeDriver management
echo "📥 Installing webdriver-manager..."
pip install webdriver-manager

# Verify installation
echo ""
echo "✅ Setup complete!"
echo ""
echo "Verifying installations..."
python3 -c "import selenium; print(f'✅ Selenium: {selenium.__version__}')"
python3 -c "import requests; print(f'✅ Requests: {requests.__version__}')"
python3 -c "import bs4; print(f'✅ BeautifulSoup4: {bs4.__version__}')"
python3 -c "from webdriver_manager.chrome import ChromeDriverManager; print('✅ WebDriver Manager: OK')" || echo "⚠️  WebDriver Manager: Not installed (will use system ChromeDriver)"

echo ""
echo "=================================================="
echo "🎉 VM is ready for batch processing!"
echo ""
echo "To start processing artists:"
echo "  source venv/bin/activate  # If using virtual environment"
echo "  python3 batch_process_artists.py --limit 10  # Test with 10 artists first"
echo ""
echo "For full processing:"
echo "  python3 batch_process_artists.py"
echo ""
echo "To monitor progress:"
echo "  tail -f batch_progress.json"
echo "=================================================="

