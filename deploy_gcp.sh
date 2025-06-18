#!/bin/bash

# LMS Project - GCP Deployment Quick Start Script
# This script automates the Docker deployment on a fresh Ubuntu 22.04 VM

set -e

echo "🚀 Starting LMS Deployment on Google Cloud Platform..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running as root
if [ "$EUID" -eq 0 ]; then 
    print_error "Please do not run this script as root"
    exit 1
fi

# Update system
print_status "Updating system packages..."
sudo apt update && sudo apt upgrade -y

# Install essential tools
print_status "Installing essential tools..."
sudo apt install -y curl wget git unzip software-properties-common apt-transport-https ca-certificates gnupg lsb-release

# Install Docker
print_status "Installing Docker..."
if ! command -v docker &> /dev/null; then
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
    sudo apt update
    sudo apt install -y docker-ce docker-ce-cli containerd.io
    sudo systemctl start docker
    sudo systemctl enable docker
    sudo usermod -aG docker $USER
    print_success "Docker installed successfully"
else
    print_warning "Docker is already installed"
fi

# Install Docker Compose
print_status "Installing Docker Compose..."
if ! command -v docker-compose &> /dev/null; then
    sudo curl -L "https://github.com/docker/compose/releases/download/v2.24.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    sudo chmod +x /usr/local/bin/docker-compose
    sudo ln -s /usr/local/bin/docker-compose /usr/bin/docker-compose
    print_success "Docker Compose installed successfully"
else
    print_warning "Docker Compose is already installed"
fi

# Verify Docker installation
print_status "Verifying Docker installation..."
if ! docker --version &> /dev/null; then
    print_error "Docker installation failed"
    exit 1
fi

if ! docker-compose --version &> /dev/null; then
    print_error "Docker Compose installation failed"
    exit 1
fi

print_success "Docker and Docker Compose are ready!"

# Clone repository if not exists
if [ ! -d "LMS-python" ]; then
    print_status "Cloning LMS repository..."
    git clone https://github.com/m-bikko/LMS-python.git
    print_success "Repository cloned successfully"
else
    print_warning "Repository already exists, pulling latest changes..."
    cd LMS-python
    git pull
    cd ..
fi

# Navigate to project directory
cd LMS-python

# Create required directories
print_status "Creating required directories..."
mkdir -p lms/static/uploads/course_images
mkdir -p lms/static/uploads/certificates
mkdir -p lms/static/uploads/payment_receipts
mkdir -p instance

# Set proper permissions
chmod -R 755 lms/static/uploads
chmod -R 755 instance

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    print_status "Creating environment configuration..."
    cat > .env << EOF
SECRET_KEY=$(openssl rand -hex 32)
DATABASE_URL=sqlite:///lms.db
ADMIN_EMAIL=admin@example.com
ADMIN_PASSWORD=admin123
GOOGLE_API_KEY=your-google-api-key-here
FLASK_APP=app_simple.py
EOF
    print_success ".env file created with default values"
    print_warning "Please edit .env file to customize your configuration!"
else
    print_warning ".env file already exists"
fi

# Build Docker image
print_status "Building Docker image..."
if newgrp docker <<EOF
docker-compose build
EOF
then
    print_success "Docker image built successfully"
else
    print_error "Failed to build Docker image"
    exit 1
fi

# Start the application
print_status "Starting LMS application..."
if newgrp docker <<EOF
docker-compose up -d
EOF
then
    print_success "LMS application started successfully"
else
    print_error "Failed to start LMS application"
    exit 1
fi

# Wait a moment for the application to start
sleep 10

# Check if application is running
print_status "Checking application status..."
if docker-compose ps | grep -q "Up"; then
    print_success "✅ LMS application is running!"
    
    # Get external IP (works on GCP)
    EXTERNAL_IP=$(curl -s -H "Metadata-Flavor: Google" http://metadata.google.internal/computeMetadata/v1/instance/network-interfaces/0/access-configs/0/external-ip 2>/dev/null || echo "localhost")
    
    echo ""
    echo "🎉 Deployment completed successfully!"
    echo ""
    echo "📊 Application Information:"
    echo "   🌐 URL: http://${EXTERNAL_IP}:5002"
    echo "   📧 Admin Email: $(grep ADMIN_EMAIL .env | cut -d'=' -f2)"
    echo "   🔑 Admin Password: $(grep ADMIN_PASSWORD .env | cut -d'=' -f2)"
    echo ""
    echo "🔧 Management Commands:"
    echo "   View logs: docker-compose logs -f web"
    echo "   Restart: docker-compose restart web"
    echo "   Stop: docker-compose down"
    echo "   Update: git pull && docker-compose build && docker-compose up -d"
    echo ""
    print_warning "Important: Please edit .env file to set secure passwords and API keys!"
    print_warning "For production use, consider setting up SSL certificates."
    
else
    print_error "Application failed to start properly"
    echo "Check logs with: docker-compose logs web"
    exit 1
fi

print_success "🚀 LMS deployment script completed!" 