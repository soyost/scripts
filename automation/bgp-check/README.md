## Scope
This script is used to validate interface and BGP connection for a given circuit ID. 

## Note
This version of the script presumes the use of a vrf, in this case vrf OAM. 

## Usage

1. Ensure that the circuits.xlsx is present and up-to-date in the folder.

The circuit workbook must contain these logical columns (matching is flexible):
    Service/Circuit
    "A"-END-Router
    "Z"-END-Router

2. Find the circuit that is in question in the given alert or outage notification.
3. Run

```bash
python bgp_verify.py --circuit <circuit ID>
```

4. Output will be printed in bgp-verification-results.csv with raw data and in the command line:

```bash
SWITCH01: connecting
SWITCH02: connecting

==============================================================================
Circuit 4ABC12345 BGP verification
==============================================================================

A-END: SWITCH01 Eth1/46
  VRF OAM / Eth1/46.21
    Circuit in config: YES
    Interface: protocol-up/link-up/admin-up (YES)
    Local IP: 10.77.31.192/31
    Neighbor: 10.77.31.193
    Remote AS: 65079
    BGP state: Established
    BGP uptime: 06:14:27
    Prefixes received: 30
    InQ/OutQ: 0/0
    Peer seen on opposite endpoint: YES
    Result: PASS

Z-END: SWITCH02 Eth1/46
  VRF OAM / Eth1/46.21
    Circuit in config: YES
    Interface: protocol-up/link-up/admin-up (YES)
    Local IP: 10.77.31.193/31
    Neighbor: 10.77.31.192
    Remote AS: 65066
    BGP state: Established
    BGP uptime: 06:14:34
    Prefixes received: 47
    InQ/OutQ: 0/0
    Peer seen on opposite endpoint: YES
    Result: PASS

------------------------------------------------------------------------------
OVERALL RESULT: PASS
------------------------------------------------------------------------------

Results written to: bgp-verification-results.cs 
```
## Further exaplanation

This script automates the validation of a carrier circuit following an outage or maintenance event.

Given a circuit ID, the script:

Looks up the circuit in the circuit inventory spreadsheet (circuits.xlsx).
Identifies the A-end and Z-end Nexus switches and parent interfaces.
Connects to both switches using TACACS credentials.
Verifies that the circuit exists in the running configuration.
Identifies the associated Layer 3 subinterfaces.
Validates interface operational status.
Validates BGP neighbor state.
Correlates both ends of the circuit to ensure they are peering with one another.
Produces a PASS/FAIL summary and writes the results to a CSV file.
Verification Steps

The script performs the following verification on both endpoints.

3. Interface Discovery

Commands:

```bash
show ip interface brief vrf OAM
show ip interface brief vrf PROD
```
Purpose:

Finds Layer 3 subinterfaces associated with the documented parent interface.
Identifies the local IP address.
Determines interface operational status.


4. Interface Configuration

Command:

```bash
show running-config interface Ethernet1/XX.XX
```

Purpose:

Retrieves the configured IP address and prefix length.
Confirms the VRF assignment.
Calculates the expected BGP neighbor address.

Example:

ip address 10.77.31.192/31
vrf member OAM


5. BGP Verification

Command:

```bash
show bgp ipv4 unicast summary vrf <vrf>
```

Purpose:

Verifies:

Neighbor IP
Remote AS
Session state
Session uptime
Prefixes received
Input queue
Output queue

Example:

```bash
Neighbor        AS      Up/Down    State/PfxRcd

10.77.31.193    65079   06:14:27   30

The script interprets:

Numeric State/PfxRcd = BGP Established
Text (Idle, Active, Connect, etc.) = BGP not established
```

6. Endpoint Correlation

The script compares information collected from both switches.

It verifies:

Switch A's BGP neighbor matches Switch B's local interface IP.
Switch B's BGP neighbor matches Switch A's local interface IP.

This confirms that both devices are peering with one another rather than an unexpected device.

Example:

Peer IP validation: PASS
PASS Criteria

### Criteria
A circuit is considered PASS when:

Circuit ID exists in device configuration.
Interface is:
protocol-up/link-up/admin-up
BGP session is Established.
Input and Output queues are 0.
Neighbor IP matches the opposite endpoint.
Both switches successfully complete validation.
