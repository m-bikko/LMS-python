# LMS Project - Google Cloud Platform Deployment Guide

This guide provides step-by-step instructions for deploying the LMS project on Google Cloud Platform using a fresh Ubuntu 22.04 VM instance.

## 📋 Prerequisites

- Google Cloud Platform account with billing enabled
- Basic understanding of command line operations
- SSH key pair (will be created during setup)

## 🎯 Deployment Overview

This deployment uses:
- **Database**: SQLite (embedded, no external database needed)
- **Application**: Flask running via `app_simple.py`
- **Containerization**: Docker + Docker Compose
- **Platform**: Google Compute Engine VM (Ubuntu 22.04)
- **Port**: 5002

## 🚀 Step-by-Step Deployment Instructions

### Phase 1: Google Cloud Setup

#### 1.1 Create a Google Cloud Project
```bash
# Open Google Cloud Console in your browser
# Visit: https://console.cloud.google.com/

# Create a new project or select existing project
# Note down your PROJECT_ID for later use
```

#### 1.2 Enable Required APIs
```bash
# In Google Cloud Console, enable these APIs:
# - Compute Engine API
# - Cloud Resource Manager API
```

#### 1.3 Set up Google Cloud SDK (on your local machine)
```bash
# Install Google Cloud SDK
curl https://sdk.cloud.google.com | bash
exec -l $SHELL

# Initialize and authenticate
gcloud init
gcloud auth login

# Set your project
gcloud config set project YOUR_PROJECT_ID
```

### Phase 2: Create and Configure VM Instance

#### 2.1 Create VM Instance
```bash
# Create a VM instance with Ubuntu 22.04
gcloud compute instances create lms-server \
    --zone=us-central1-a \
    --machine-type=e2-medium \
    --network-tier=PREMIUM \
    --maintenance-policy=MIGRATE \
    --provisioning-model=STANDARD \
    --service-account=YOUR_PROJECT_NUMBER-compute@developer.gserviceaccount.com \
    --scopes=https://www.googleapis.com/auth/devstorage.read_only,https://www.googleapis.com/auth/logging.write,https://www.googleapis.com/auth/monitoring.write,https://www.googleapis.com/auth/servicecontrol,https://www.googleapis.com/auth/service.management.readonly,https://www.googleapis.com/auth/trace.append \
    --tags=lms-server \
    --create-disk=auto-delete=yes,boot=yes,device-name=lms-server,image=projects/ubuntu-os-cloud/global/images/ubuntu-2204-jammy-v20240319,mode=rw,size=20,type=projects/YOUR_PROJECT_ID/zones/us-central1-a/diskTypes/pd-balanced \
    --no-shielded-secure-boot \
    --shielded-vtpm \
    --shielded-integrity-monitoring \
    --labels=env=production,app=lms \
    --reservation-affinity=any
```

#### 2.2 Create Firewall Rules
```bash
# Allow HTTP traffic on port 5002
gcloud compute firewall-rules create allow-lms-port \
    --allow tcp:5002 \
    --source-ranges 0.0.0.0/0 \
    --target-tags lms-server \
    --description "Allow LMS application on port 5002"

# Allow SSH (if not already enabled)
gcloud compute firewall-rules create allow-ssh \
    --allow tcp:22 \
    --source-ranges 0.0.0.0/0 \
    --target-tags lms-server \
    --description "Allow SSH access"
```

#### 2.3 Get VM External IP
```bash
# Get the external IP of your VM
gcloud compute instances describe lms-server \
    --zone=us-central1-a \
    --format='get(networkInterfaces[0].accessConfigs[0].natIP)'

# Note down this IP address - you'll use it to access your application
```

### Phase 3: Connect to VM and Deploy

#### 3.1 Connect to VM
```bash
# SSH into your VM instance
gcloud compute ssh lms-server --zone=us-central1-a

# You are now connected to your Ubuntu 22.04 VM
```

#### 3.2 Option A: Automated Deployment (Recommended)
```bash
# Run the automated deployment script
curl -sSL https://raw.githubusercontent.com/m-bikko/LMS-python/main/deploy_gcp.sh | bash

# This script will:
# - Install Docker and Docker Compose
# - Clone the repository
# - Build and start the application
# - Show you the access URL and credentials
```

#### 3.3 Option B: Manual Deployment
```bash
# Update system packages
sudo apt update && sudo apt upgrade -y

# Install essential tools
sudo apt install -y curl wget git unzip software-properties-common apt-transport-https ca-certificates gnupg lsb-release

# Install Docker
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io
sudo systemctl start docker
sudo systemctl enable docker
sudo usermod -aG docker $USER
newgrp docker

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/download/v2.24.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
sudo ln -s /usr/local/bin/docker-compose /usr/bin/docker-compose

# Clone and deploy application
git clone https://github.com/m-bikko/LMS-python.git
cd LMS-python

# Create necessary directories
mkdir -p lms/static/uploads/course_images
mkdir -p lms/static/uploads/certificates
mkdir -p lms/static/uploads/payment_receipts
mkdir -p instance

# Create environment file
cat > .env << EOF
SECRET_KEY=$(openssl rand -hex 32)
DATABASE_URL=sqlite:///lms.db
ADMIN_EMAIL=admin@example.com
ADMIN_PASSWORD=admin123
GOOGLE_API_KEY=your-google-api-key-here
FLASK_APP=app_simple.py
EOF

# Build and start application
docker-compose build
docker-compose up -d
```

### Phase 4: Access Your Application

#### 4.1 Get Your Application URL
```bash
# Your application will be available at:
# http://YOUR_VM_EXTERNAL_IP:5002

# Get the external IP
beimbet_m0434@lms:~/LMS-python$ docker-compose up -d
[+] Running 2/2
 ✔ Network lms-python_default  Created                                                                                                                                                                             0.1s 
 ✔ Container lms-python-web-1  Started                                                                                                                                                                             0.1s 
beimbet_m0434@lms:~/LMS-python$ curl -s -H "Metadata-Flavor: Google" http://metadata.google.internal/computeMetadata/v1/instance/network-interfaces/0/access-configs/0/external-ip
34.118.8.14beimbet_m0434@lms:~/LMS-python$ sudo docker ps
CONTAINER ID   IMAGE            COMMAND                  CREATED          STATUS          PORTS                                         NAMES
7e3b90faf6cf   lms-python-web   "/usr/local/bin/dock…"   17 seconds ago   Up 17 seconds   0.0.0.0:5002->5002/tcp, [::]:5002->5002/tcp   lms-python-web-1
beimbet_m0434@lms:~/LMS-python$ 
```

#### 4.2 Initial Login
```bash
# Use the admin credentials:
# Email: admin@example.com
# Password: admin123 (or whatever you set in .env)
```

## 🔧 Management Commands

### View Application Status
```bash
# Check running containers
docker-compose ps

# View real-time logs
docker-compose logs -f web

# Check system resources
docker stats
```

### Application Management
```bash
# Restart application
docker-compose restart web

# Stop application
docker-compose down

# Update application
git pull origin main
docker-compose build
docker-compose up -d

# Backup database
cp lms.db lms_backup_$(date +%Y%m%d_%H%M%S).db
```

### System Monitoring
```bash
# Check disk usage
df -h

# Check memory usage
free -h

# Check system processes
htop
```

## 🛡️ Security Considerations

### 1. Change Default Credentials
```bash
# Edit the .env file to change default passwords
nano .env

# Update these values:
# SECRET_KEY=your-unique-secret-key
# ADMIN_EMAIL=your-email@domain.com
# ADMIN_PASSWORD=your-secure-password

# Restart application after changes
docker-compose restart web
```

### 2. Firewall Security
```bash
# Restrict SSH access to your IP only
gcloud compute firewall-rules update allow-ssh \
    --source-ranges YOUR_IP/32

# For production, consider using Cloud IAP for SSH access
```

### 3. SSL Certificate (Recommended for Production)
```bash
# Install certbot for Let's Encrypt
sudo apt install -y certbot

# You'll need a domain name pointing to your VM's IP
# Follow standard certbot procedures for nginx/apache
```

## 🔍 Troubleshooting

### Common Issues

#### Application Won't Start
```bash
# Check container logs
docker-compose logs web

# Check if port is in use
sudo netstat -tlnp | grep 5002

# Restart Docker service
sudo systemctl restart docker
```

#### Can't Access from Browser
```bash
# Verify firewall rules
gcloud compute firewall-rules list | grep lms

# Check application is binding to all interfaces
docker-compose logs web | grep "Starting LMS"
```

#### Database Issues
```bash
# Check database file permissions
ls -la lms.db

# Reset database (WARNING: Deletes all data)
docker-compose down
rm lms.db
docker-compose up -d
```

#### Build Failures
```bash
# Clean Docker cache and rebuild
docker system prune -f
docker-compose build --no-cache
docker-compose up -d
```

## 📊 Monitoring and Maintenance

### Automated Backups
```bash
# Create backup script
cat > backup_script.sh << 'EOF'
#!/bin/bash
BACKUP_DIR="/home/$USER/backups"
mkdir -p $BACKUP_DIR
cp lms.db $BACKUP_DIR/lms_backup_$(date +%Y%m%d_%H%M%S).db
find $BACKUP_DIR -name "lms_backup_*.db" -mtime +7 -delete
EOF

chmod +x backup_script.sh

# Add to crontab for daily backups at 2 AM
(crontab -l 2>/dev/null; echo "0 2 * * * $PWD/backup_script.sh") | crontab -
```

### Log Management
```bash
# Configure Docker log rotation
sudo tee /etc/docker/daemon.json << EOF
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  }
}
EOF

sudo systemctl restart docker
docker-compose up -d
```

## 🎉 Success!

Your LMS application should now be running successfully on Google Cloud Platform!

- **Application URL**: `http://YOUR_VM_EXTERNAL_IP:5002`
- **Admin Access**: Use your configured credentials
- **Database**: SQLite (automatically managed)
- **Persistent Storage**: Docker volumes for uploads and database

For production environments, consider implementing:
- SSL certificates
- Regular automated backups
- Monitoring and alerting
- Load balancing for high availability

## 📞 Support

If you encounter issues:

1. Check the troubleshooting section above
2. Review container logs: `docker-compose logs web`
3. Verify firewall and network settings
4. Ensure all environment variables are properly configured

Good luck with your LMS deployment! 🚀 