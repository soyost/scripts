Save the file in your ~/.bashrc
`source ~/.bashrc`
## Usage
Where (mypod) substitute with actual full pod name
```bash
kdev         # switch to ibus-cloud-eng
kprod        # switch to ibus-cloud-prod
kall         # switch to all namespaces
kns          # show current namespace flag

kpod         # list pods
kpods app    # list pods matching "app"
kdes mypod   # describe pod
kwide nginx  # get wide pod output filtered by nginx

kpod         # list pods
kpods app    # list pods matching "app"
kdes mypod   # describe pod
kwide nginx  # get wide pod output filtered by nginx

kexec mypod              # exec into bash
kdump mypod              # pull heapdump
kldump mypod             # list dump directory
kimg mypod               # get image from pod
khost mypod              # get node name of pod
```
