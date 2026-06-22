## Scope
This script is used to determine the expiration of hosts using OpenSSL command and a given list of hosts provided in hosts.txt. 

## Usage

1. Poplulate hosts.txt with the target urls.
2. Run

```bash
python ./cert-check.sh 
```

3. Output will be printed with the following columns

```bash
HOST:PORT   STATUS  DAYS  EXPIRES   ISSUER  VERIFY   
```
