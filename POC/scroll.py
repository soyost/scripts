#!/usr/bin/env python3
import random
import pygame

WIDTH, HEIGHT = 1200, 800
FONT_SIZE = 20
LINE_SPACING = 4
TITLE = "Cisco Catalyst Config Viewer"

BG = (10, 10, 10)
FG = (120, 255, 120)
DIM = (80, 160, 80)

HOSTNAME = "CATALYST-DEMO-01"
DOMAIN = "lab.local"

VLAN_NAMES = [
    "USERS", "VOICE", "PRINTERS", "WIFI", "GUEST",
    "SERVERS", "MGMT", "CAMERAS", "IOT", "TEST"
]

DESCRIPTIONS = [
    "User Access Port",
    "IP Phone + Workstation",
    "Printer",
    "Wireless AP",
    "Conference Room",
    "Spare Drop",
    "Camera",
    "Badge Reader",
    "Uplink Member",
    "Lab Device"
]

BANNERS = [
    "Authorized access only.",
    "Demo system for training use.",
    "All activity may be monitored.",
]

def rand_mac():
    return ".".join(
        "".join(random.choice("0123456789abcdef") for _ in range(4))
        for _ in range(3)
    )

def generate_global_config():
    mgmt_vlan = random.choice([10, 20, 99, 100, 150, 200])
    default_gw = f"10.1.{mgmt_vlan}.1"

    lines = [
        "!",
        "version 17.9",
        "service timestamps debug datetime msec",
        "service timestamps log datetime msec",
        "service password-encryption",
        "!",
        f"hostname {HOSTNAME}",
        f"ip domain-name {DOMAIN}",
        "!",
        f'banner motd ^C{random.choice(BANNERS)}^C',
        "!",
        "spanning-tree mode rapid-pvst",
        "spanning-tree extend system-id",
        "!",
        "vtp mode transparent",
        "!",
        "aaa new-model",
        "!",
        "ip routing",
        "!",
        "lldp run",
        "cdp run",
        "!",
        f"interface Vlan{mgmt_vlan}",
        f" ip address 10.1.{mgmt_vlan}.2 255.255.255.0",
        " no shutdown",
        "!",
        f"ip default-gateway {default_gw}",
        "!",
    ]

    vlan_ids = sorted(random.sample(range(10, 250), random.randint(6, 12)))
    for vlan_id in vlan_ids:
        lines.extend([
            f"vlan {vlan_id}",
            f" name {random.choice(VLAN_NAMES)}_{vlan_id}",
            "!"
        ])

    return lines, vlan_ids

def generate_interface_block(port_num, vlan_ids):
    iface = f"GigabitEthernet1/0/{port_num}"
    access_vlan = random.choice(vlan_ids)
    voice_vlan = random.choice(vlan_ids)
    trunk_native = random.choice(vlan_ids)
    allowed = ",".join(
        str(v) for v in sorted(random.sample(vlan_ids, min(len(vlan_ids), random.randint(3, 6))))
    )

    mode = random.choices(["access", "trunk", "shutdown"], weights=[70, 20, 10], k=1)[0]
    lines = [f"interface {iface}"]

    if mode == "access":
        lines.extend([
            f" description {random.choice(DESCRIPTIONS)}",
            " switchport mode access",
            f" switchport access vlan {access_vlan}",
        ])
        if random.random() < 0.35:
            lines.append(f" switchport voice vlan {voice_vlan}")
        lines.extend([
            " spanning-tree portfast",
            " spanning-tree bpduguard enable",
        ])
        if random.random() < 0.4:
            lines.append(" storm-control broadcast level 5.00")
        if random.random() < 0.5:
            lines.append(" authentication port-control auto")
        lines.append("!")
        return lines

    if mode == "trunk":
        lines.extend([
            " description Uplink/Trunk",
            " switchport trunk encapsulation dot1q",
            " switchport mode trunk",
            f" switchport trunk native vlan {trunk_native}",
            f" switchport trunk allowed vlan {allowed}",
            " spanning-tree link-type point-to-point",
            "!"
        ])
        return lines

    lines.extend([
        " description Unused Port",
        " switchport mode access",
        " shutdown",
        "!"
    ])
    return lines

def generate_misc_section(vlan_ids):
    return [
        "line con 0",
        " logging synchronous",
        " stopbits 1",
        "!",
        "line vty 0 4",
        " transport input ssh",
        " login local",
        "!",
        "ip ssh version 2",
        "!",
        "snmp-server community DEMO ro",
        f"snmp-server location IDF-{random.randint(1, 12)}",
        f"snmp-server contact netops@{DOMAIN}",
        "!",
        "logging trap warnings",
        "!",
        "archive",
        " log config",
        "  logging enable",
        "!",
        "end",
        ""
    ]

def build_big_config(target_lines=5000):
    all_lines = []
    while len(all_lines) < target_lines:
        global_lines, vlan_ids = generate_global_config()
        all_lines.extend(global_lines)

        port_count = random.randint(24, 48)
        for port in range(1, port_count + 1):
            all_lines.extend(generate_interface_block(port, vlan_ids))
            if random.random() < 0.12:
                po = random.randint(1, 8)
                all_lines.extend([
                    f"interface Port-channel{po}",
                    " description Aggregated Uplink",
                    " switchport mode trunk",
                    "!"
                ])
            if random.random() < 0.08:
                all_lines.extend([
                    f"mac address-table static {rand_mac()} vlan {random.choice(vlan_ids)} interface GigabitEthernet1/0/{port}",
                    "!"
                ])

        all_lines.extend(generate_misc_section(vlan_ids))
    return all_lines

def render(screen, font, lines, scroll_y, auto_scroll, paused):
    screen.fill(BG)
    x = 20
    y = 20 - scroll_y
    line_height = FONT_SIZE + LINE_SPACING

    for line in lines:
        if y > HEIGHT:
            break
        if y >= -line_height:
            color = FG if line.strip() != "!" else DIM
            surf = font.render(line, True, color)
            screen.blit(surf, (x, y))
        y += line_height

    status = "PAUSED" if paused else ("AUTO" if auto_scroll else "MANUAL")
    help_text = f"Wheel: scroll | A: auto | SPACE: pause | R: regenerate | Esc/Q: quit | Mode: {status}"
    help_surf = font.render(help_text, True, DIM)
    screen.blit(help_surf, (20, HEIGHT - 30))

def next_scroll_delay():
    return random.randint(150, 1600)

def next_scroll_step(line_height):
    roll = random.random()
    if roll < 0.70:
        return line_height
    if roll < 0.93:
        return line_height * 2
    return line_height * 3

def main():
    pygame.init()
    pygame.display.set_caption(TITLE)
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    font = pygame.font.SysFont("couriernew", FONT_SIZE)

    lines = build_big_config()
    line_height = FONT_SIZE + LINE_SPACING
    total_height = len(lines) * line_height
    max_scroll = max(0, total_height - (HEIGHT - 40))
    scroll_y = 0

    auto_scroll = False
    paused = False

    last_auto = pygame.time.get_ticks()
    auto_scroll_delay_ms = next_scroll_delay()

    clock = pygame.time.Clock()
    running = True

    while running:
        now = pygame.time.get_ticks()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.MOUSEWHEEL:
                scroll_y -= event.y * line_height * 2
                scroll_y = max(0, min(scroll_y, max_scroll))

            elif event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_ESCAPE, pygame.K_q):
                    running = False
                elif event.key == pygame.K_a:
                    auto_scroll = not auto_scroll
                    last_auto = now
                    auto_scroll_delay_ms = next_scroll_delay()
                elif event.key == pygame.K_SPACE:
                    paused = not paused
                elif event.key == pygame.K_r:
                    lines = build_big_config()
                    total_height = len(lines) * line_height
                    max_scroll = max(0, total_height - (HEIGHT - 40))
                    scroll_y = 0
                    last_auto = now
                    auto_scroll_delay_ms = next_scroll_delay()

        if auto_scroll and not paused and now - last_auto >= auto_scroll_delay_ms:
            scroll_y += next_scroll_step(line_height)
            if scroll_y >= max_scroll:
                lines = build_big_config()
                total_height = len(lines) * line_height
                max_scroll = max(0, total_height - (HEIGHT - 40))
                scroll_y = 0
            last_auto = now
            auto_scroll_delay_ms = next_scroll_delay()

        render(screen, font, lines, scroll_y, auto_scroll, paused)
        pygame.display.flip()
        clock.tick(60)

    pygame.quit()

if __name__ == "__main__":
    main()