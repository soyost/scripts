## Instructions

Save 
```bash
/etc/systemd/system/caption-viewer.service
```



Create service account

```bash
sudo useradd -r -s /sbin/nologin captionviewer
```

Create app directory

```bash
sudo mkdir -p /opt/caption-viewer
```

Copy your script here:

```bash
/opt/caption-viewer/caption_viewer.py
```

Permissions:

sudo chown -R captionviewer:captionviewer /opt/caption-viewer
sudo chmod +x /opt/caption-viewer/caption_viewer.py


Reload systemd:

sudo systemctl daemon-reload


Enable at boot:

sudo systemctl enable caption-viewer


Start service

sudo systemctl start caption-viewer


Check status

sudo systemctl status caption-viewer


Watch logs live

This becomes your main troubleshooting tool:

sudo journalctl -u caption-viewer -f

You’ll see things like:

TCP listener started on 0.0.0.0:5000
Web server started on 0.0.0.0:8080
CC device connected from x.x.x.x



Test locally on server:


curl http://localhost:8080
curl http://localhost:8080/caption


Open from workstation


http://<server-ip>:8080