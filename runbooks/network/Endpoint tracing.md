#### Use for: Interface flaps, Device outages, Broadcast equipment issues, DHCP troubleshooting, Unknown endpoint identification

### A: INTERFACE -> DEVICE

1. Identify the affected interface 

Monitor > Logs > System 

Example Filter: ( subtype eq port )

Example: ethernet1/2

2. Identify MAC addresses on the interface
CLI: 
```bash
show mac all
```
Example: 5c:77:57:00:d9:20 ethernet1/2

3. Identify endpoint 

Option A: Network > DHCP > DHCP Server > View Allocation 

Option B: DHCP Logs > Match MAC address. 

Example: 
MAC: 5c:77:57:00:d9:20 
IP: 10.77.250.8 
Hostname: PKITDEC02A




### B: IP -> INTERFACE

1. Locate IP
   - DHCP lease table
   - Traffic logs
   - DNS / hostname lookup
   - User-provided IP

2. Identify the gateway/SVI/router for that IP subnet
   - In our environment this is usually the Nexus core
   - Confirm the correct VRF/VLAN if applicable

3. From the gateway device, ping the endpoint to refresh ARP

```bash
   ping <ip> source <gateway-or-local-interface-ip> vrf <vrf>
```

   Example:
   ping 10.77.250.8 source 10.77.250.1 vrf ENG

4. Find the ARP entry

```bash
   show ip arp vrf <vrf> <ip>
```

   Example:
   show ip arp vrf ENG 10.77.250.8

5. Get the MAC address from ARP

   Example:
   10.77.250.8  5c77.5700.d920  Vlan250

6. Find where the MAC is learned

```bash
   show mac address-table address <mac>
``` 

   Example:
   show mac address-table address 5c77.5700.d920

7. Interpret the result
   - Access port = endpoint/interface found
   - Trunk or port-channel = use CDP/LLDP to find the downstream switch, then repeat the MAC lookup there