## This allows for monitoring this dashboard via mobile phone using the url on the same network as the computer running the script
### Usage
1. You will need both file locally. Run the following command for Prod dashboard
```bash
/run_dashboard.sh mobilerabbittop.py -p
```

2. Go to http://127.0.0.1:8051/ on your local device

3. Find the IP of your local device, using something like ifconfig

4. Go to http://<*IP of your computer*>:8051 on your phone from whatever browser. 

## Note
This only works if all devices are on the same network
