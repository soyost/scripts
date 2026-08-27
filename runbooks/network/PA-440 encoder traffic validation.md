# note at the time writing this, the focus is more on the 440 to validate encoder is passing traffic. 

# pre-reqs: ipsec tunnels are are connected. working admin session to the firewall device

1. Network > DHCP > DHCP Allocation
   - Identify encoder IP
   - Confirm lease is active
   - Note encoder hostname if available

   Example:
   **<img src="../../images/dhcp-allocation.png" width="800" alt="DHCP Allocation">**

2. Monitor > Session Browser
   - Filter:
     (source eq '<encoder-ip>')
   - Locate haivision-srt session
   - Expand session details

   Example:
   <img src="../../images/session-id-browser.png" width="800" alt="Session Browser">

3. Verify in Session Browser
   - State = ACTIVE
   - Application = haivision-srt
   - Source = Encoder IP
   - Destination = Remote decoder IP
   - Traverse Tunnel = True
   - Security Rule = VLAN_IPSEC-HAIVISION
   - Session ID = <number>

4. (Optional) CLI deep-dive
   show session id <number>

   Example:
   <img src="../../images/show-session-id.png" width="800" alt="CLI">

5. Verify
   - Start Time
   - Total Bytes
   - Packet Counts
   - Egress Interface = tunnel.x
   - Session traverses tunnel = True

6. Re-check later
   - Confirm packet and byte counts are increasing

   