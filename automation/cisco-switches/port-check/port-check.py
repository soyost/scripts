# $language = "Python"
# $interface = "1.0"

def main():

    interface = crt.Dialog.Prompt(
        "Enter interface (example: Gi1/0/20):",
        "Port Connectivity Check",
        ""
    )

    # Cancel or blank entry
    if not interface:
        return

    commands = [
        "show interface {} status".format(interface),
        "show mac address-table interface {}".format(interface),
        "show authentication sessions interface {} details".format(interface)
    ]

    for command in commands:
        crt.Screen.Send(command + "\r")
        crt.Screen.WaitForCursor(1)
        crt.Screen.Send("\r\r")

main()