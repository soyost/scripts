Copy to file
```bash
chmod +x
```
Update location of the ssh keys used for Bastion connections here
`PRIVATE_KEY=(location of your private key`
# Tip
I have found that using the id_rsa.pub for bastion creation and the id_rsa for the private key helps streamline other tools, like tunapoke at the same time.

## usage
./bastion-session.connect.sh '(paste ssh command from OCI bastion here)'
