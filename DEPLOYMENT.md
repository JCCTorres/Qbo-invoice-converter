# QBO Invoice Converter - Server Deployment Guide

This guide provides instructions for deploying the QBO Invoice Converter application on a Virtual Private Server (VPS).

## Prerequisites

- A VPS running Ubuntu 20.04 LTS or later
- SSH access to your VPS
- A domain name (optional but recommended)
- Basic familiarity with Linux command line

## Deployment Steps

### 1. Set Up the Server

Update the system and install required packages:

```bash
sudo apt update
sudo apt upgrade -y
sudo apt install -y python3 python3-pip python3-venv nginx
```

### 2. Create a User for the Application

```bash
sudo adduser qboapp
sudo usermod -aG sudo qboapp
```

### 3. Transfer the Application Files

Option 1: Use SCP to transfer files from your local machine:

```bash
scp -r /path/to/qbo-invoice-converter/ qboapp@your-server-ip:/home/qboapp/
```

Option 2: Clone from Git repository (if you've set up a repository):

```bash
sudo -u qboapp git clone https://github.com/yourusername/qbo-invoice-converter.git /home/qboapp/qbo-invoice-converter
```

### 4. Set Up Python Environment and Install Dependencies

```bash
sudo -u qboapp bash -c "cd /home/qboapp/qbo-invoice-converter && python3 -m venv venv"
sudo -u qboapp bash -c "cd /home/qboapp/qbo-invoice-converter && source venv/bin/activate && pip install -r requirements.txt"
```

### 5. Set Up Gunicorn as a System Service

Create a systemd service file:

```bash
sudo nano /etc/systemd/system/qbo-converter.service
```

Add the following content:

```ini
[Unit]
Description=QBO Invoice Converter
After=network.target

[Service]
User=qboapp
Group=www-data
WorkingDirectory=/home/qboapp/qbo-invoice-converter
Environment="PATH=/home/qboapp/qbo-invoice-converter/venv/bin"
ExecStart=/home/qboapp/qbo-invoice-converter/venv/bin/gunicorn --workers 3 --bind 127.0.0.1:8000 app:app
Restart=always

[Install]
WantedBy=multi-user.target
```

### 6. Start and Enable the Service

```bash
sudo systemctl start qbo-converter
sudo systemctl enable qbo-converter
sudo systemctl status qbo-converter
```

### 7. Configure Nginx as a Reverse Proxy

Create an Nginx configuration file:

```bash
sudo nano /etc/nginx/sites-available/qbo-converter
```

Add the following content:

```nginx
server {
    listen 80;
    server_name your-domain.com; # Replace with your domain or server IP

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /static {
        alias /home/qboapp/qbo-invoice-converter/static;
    }
}
```

Enable the site and restart Nginx:

```bash
sudo ln -s /etc/nginx/sites-available/qbo-converter /etc/nginx/sites-enabled
sudo nginx -t
sudo systemctl restart nginx
```

### 8. Set Up SSL with Let's Encrypt (Optional but Recommended)

Install Certbot:

```bash
sudo apt install -y certbot python3-certbot-nginx
```

Obtain SSL certificate:

```bash
sudo certbot --nginx -d your-domain.com
```

Follow the prompts to complete the setup.

### 9. Set Up Firewall (Optional but Recommended)

```bash
sudo ufw allow 'Nginx Full'
sudo ufw allow ssh
sudo ufw enable
```

### 10. Configure Automatic Updates for Security (Optional but Recommended)

```bash
sudo apt install -y unattended-upgrades
sudo dpkg-reconfigure -plow unattended-upgrades
```

## Maintenance and Monitoring

### Viewing Application Logs

```bash
sudo journalctl -u qbo-converter.service
```

### Restarting the Application After Updates

```bash
# After updating application files
sudo systemctl restart qbo-converter
```

### Backing Up Data

```bash
# Back up the entire application directory
sudo -u qboapp tar -czvf /home/qboapp/qbo-backup-$(date +%Y%m%d).tar.gz -C /home/qboapp qbo-invoice-converter
```

## Security Considerations

1. **Secure User Uploads**: The application stores uploaded files temporarily. Consider setting up a cron job to clean old files.

2. **Access Restrictions**: You might want to restrict access to the application using basic authentication or an IP whitelist.

3. **Regular Updates**: Keep the system and dependencies updated regularly for security.

## Troubleshooting

- **Application not starting**: Check the logs with `sudo journalctl -u qbo-converter.service`
  
- **Nginx not serving the application**: Verify Nginx configuration with `sudo nginx -t`

- **Permission issues**: Ensure the qboapp user has proper permissions to all application files

## Scaling Considerations

For increased traffic or load:

1. Increase the number of Gunicorn workers in the service file
2. Consider adding a load balancer if deploying across multiple servers
3. Optimize database operations for larger datasets

## References

- [Flask Deployment Options](https://flask.palletsprojects.com/en/2.0.x/deploying/)
- [Gunicorn Configuration](https://docs.gunicorn.org/en/stable/configure.html)
- [Nginx Documentation](https://nginx.org/en/docs/)
- [Let's Encrypt Documentation](https://letsencrypt.org/docs/) 