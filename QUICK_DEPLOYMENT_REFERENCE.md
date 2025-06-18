# LMS Quick Deployment Reference

## 🚀 One-Command Deployment

For fresh Ubuntu 22.04 VM on Google Cloud Platform:

```bash
curl -sSL https://raw.githubusercontent.com/m-bikko/LMS-python/main/deploy_gcp.sh | bash
```

Or manual approach:

```bash
git clone https://github.com/m-bikko/LMS-python.git
cd LMS-python
chmod +x deploy_gcp.sh
./deploy_gcp.sh
```

## ⚡ Manual Docker Commands

```bash
# Clone and setup
git clone https://github.com/m-bikko/LMS-python.git
cd LMS-python

# Build and run
docker-compose build
docker-compose up -d

# View logs
docker-compose logs -f web

# Stop
docker-compose down
```

## 🔧 Google Cloud VM Setup

```bash
# Create VM instance
gcloud compute instances create lms-server \
    --zone=us-central1-a \
    --machine-type=e2-medium \
    --image-family=ubuntu-2204-lts \
    --image-project=ubuntu-os-cloud \
    --boot-disk-size=20GB \
    --tags=lms-server

# Create firewall rule
gcloud compute firewall-rules create allow-lms-port \
    --allow tcp:5002 \
    --source-ranges 0.0.0.0/0 \
    --target-tags lms-server

# SSH to VM
gcloud compute ssh lms-server --zone=us-central1-a
```

## 📊 Application Access

- **URL**: `http://YOUR_VM_EXTERNAL_IP:5002`
- **Default Admin**: `admin@example.com` / `admin123`
- **Database**: SQLite (no external DB needed)

## 🛠️ Troubleshooting

```bash
# Check container status
docker-compose ps

# View application logs
docker-compose logs web

# Restart application
docker-compose restart web

# Rebuild after code changes
docker-compose down
docker-compose build --no-cache
docker-compose up -d

# Check system resources
docker stats
```

## 🔒 Security Notes

- Change default admin password in `.env`
- Update `SECRET_KEY` in `.env` 
- Consider SSL certificate for production
- Restrict firewall rules to specific IPs if needed

## 📁 Important Files

- `Dockerfile` - Container configuration
- `docker-compose.yml` - Service orchestration  
- `app_simple.py` - Main application entry point
- `.env` - Environment variables
- `requirements.txt` - Python dependencies 