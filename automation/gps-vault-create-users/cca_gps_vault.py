import os
import subprocess
import shutil
from pathlib import Path

def run_command(command):
    """Run a shell command and print its output."""
    result = subprocess.run(command, shell=True, text=True, capture_output=True)
    print(result.stdout)
    print(result.stderr)
    return result

def main():
    facility = input("Enter the facility (e.g., lcox_mo_bcca): ")

    # Change to the appliance_mapping directory
    os.chdir(os.path.expanduser("~/git/appliance_mapping"))

    # Run the gen_local_users command
    gen_command = f"bin/gen user gen_local_users {facility}"
    print(f"Running: {gen_command}")
    run_command(gen_command)

    # Cat the passphrase files and pause to put them in Vault
    print("Displaying contents of passphrase files:")
    for passphrase_file in Path('.').glob("*.etsops.passphrase"):
        with open(passphrase_file, 'r') as file:
            print(file.read())
    for passphrase_file in Path('.').glob("*.etsnxp.passphrase"):
        with open(passphrase_file, 'r') as file:
            print(file.read())

    input("Press Enter to continue...")

    # Create chef.cerner directories
    gps_vault_path = Path(f"~/git/gps-vault/chef.cerner.com/cho.prod/{facility}").expanduser()
    gps_vault_path.mkdir(parents=True, exist_ok=True)
    print(f"Created directory: {gps_vault_path}")

    # Copy the password and pem files
    src_path = Path(f"~/git/appliance_mapping/generated/{facility}").expanduser()
    for file in src_path.glob("*.password"):
        shutil.copy(file, gps_vault_path)
        print(f"Copied {file} to {gps_vault_path}")
    for file in src_path.glob("*.pem"):
        shutil.copy(file, gps_vault_path)
        print(f"Copied {file} to {gps_vault_path}")

    # Create data bags directories
    backup_accounts_path = Path(f"~/git/gps-roles/chef.cerner.com/cho_prod/data_bags/{facility}-backup_accounts").expanduser()
    backup_accounts_path.mkdir(parents=True, exist_ok=True)
    print(f"Created directory: {backup_accounts_path}")

    ets_users_path = Path(f"~/git/gps-roles/chef.cerner.com/cho_prod/data_bags/{facility}-ets_users").expanduser()
    ets_users_path.mkdir(parents=True, exist_ok=True)
    print(f"Created directory: {ets_users_path}")

    # Copy files to new directories
    gabor_backup_src = Path(f"~/git/appliance_mapping/generated/data_bags/{facility}-ets_users/gabor_backup.json").expanduser()
    gabor_backup_dest = backup_accounts_path / "gabor_backup.json"
    shutil.copy(gabor_backup_src, gabor_backup_dest)
    print(f"Copied {gabor_backup_src} to {gabor_backup_dest}")

    for file in Path(f"~/git/appliance_mapping/generated/data_bags/{facility}-ets_users").expanduser().glob("*.*"):
        shutil.copy(file, ets_users_path)
        print(f"Copied {file} to {ets_users_path}")

    # Copy the roles file
    roles_src = Path(f"~/git/appliance_mapping/generated/roles/{facility}/{facility}-local_users.json").expanduser()
    roles_dest = Path(f"~/git/gps-roles/chef.cerner.com/cho_prod/roles/{facility}-local_users.json").expanduser()
    shutil.copy(roles_src, roles_dest)
    print(f"Copied {roles_src} to {roles_dest}")

    print("Task Completed")

if __name__ == "__main__":
    main()
