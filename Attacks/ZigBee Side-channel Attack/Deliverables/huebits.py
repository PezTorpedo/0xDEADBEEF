import argparse
import json
from collections import Counter
from datetime import datetime, timedelta, time
from zoneinfo import ZoneInfo
import curses
import math

class Device:
    def __init__(self, address):
        self.address = address
        self.name = None

    def __str__(self):
        return f"Device ({self.address}): {self.name}"

class LightbulbToggle:
    def __init__(self, date):
        self.date = date
        self.type = None # True: 0 -> 1 (ON) | False: 1 -> 0 (OFF)

    def __str__(self):
        return f"[{self.date.strftime('%d/%m/%Y %H:%M:%S')}]: {'ON' if self.type else 'OFF'}"

    __repr__ = __str__

class Lightbulb(Device):
    def __init__(self, address):
        super().__init__(address)
        self.toggles = []

    def __str__(self):
        name = f" ({self.name})" if self.name else ""
        text = f"Lightbulb {self.address}{name} - {len(self.toggles)} Toggles\n"
        text += "\n".join(str(toggle) for toggle in self.toggles)
        return text

    __repr__ = __str__

ASCII_ART = [
    " _    _            _     _ _       ",
    "| |  | |          | |   (_) |      ",
    "| |__| |_   _  ___| |__  _| |_ ___ ",
    "|  __  | | | |/ _ \\ '_ \\| | __/ __|",
    "| |  | | |_| |  __/ |_) | | |_\\__ \\",
    "|_|  |_|\\__,_|\\___|_.__/|_|\\__|___/"
]

TAGLINE = "When lights speak, habits leak."

RESET  = "\033[0m"
RED    = "\033[31m"
GRAY   = "\033[90m"
BLUE   = "\033[38;5;027m"
CYAN   = "\033[38;5;037m"
GREEN  = "\033[38;5;071m"

TIMELINE_STEP_MINUTES = 10

def print_header():
    colors = ["\033[38;5;196m", "\033[38;5;202m", "\033[38;5;226m", "\033[38;5;082m", "\033[38;5;045m", "\033[38;5;027m"]
    print("".join(f"{color}{line}{RESET}\n" for color, line in zip(colors, ASCII_ART)), end="")
    print()
    print(f"{GRAY}{TAGLINE}{RESET}")
    print()
    print("\033[1m" + "A tool for deducing user habits from Philips Hue Zigbee traffic (.pcap)." + RESET)
    print("For educational and research purposes only. Developed by 0xDEADBEEF.")
    print()

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="huebits",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "example:\n  huebits -i capture.json\n"
            "\n"
            "The steps below describe how to capture and export the required JSON file:\n"
            "  1. Set up a Raspberry Pi (e.g., with Raspberry Pi OS Lite)\n"
            "  2. Install KillerBee (https://github.com/riverloopsec/killerbee.git)\n"
            "  3. Plug in a ZigBee sniffer dongle (e.g., CC2531)\n"
            "  4. Capture packets on the ZigBee channel used by Philips Hue:\n"
            "     - sudo zbdump -i 0 -c 15 -w capture.pcap\n"
            "     - If you don’t know the channel, try channels 11–26 until you see traffic\n"
            "  5. Let it run for the desired amount of time\n"
            "  6. Stop the capture with Ctrl+C\n"
            "  7. Open the .pcap file with Wireshark\n"
            "  8. (Optional) Apply the display filter: frame.len == 55\n"
            "  9. Export the capture as JSON: File > Export Packet Dissections > As JSON\n"
            "\n"
            "Note: filtering is optional but strongly recommended to reduce file size."
        ),
    )

    parser.add_argument(
        "-i", "--input",
        required=True,
        metavar="FILE",
        help="Input JSON file exported from a PCAP using Wireshark/tshark"
    )

    return parser

def parse_args(argv=None):
    return build_parser().parse_args(argv)

def load_json(filename):
    with open(filename, "r", encoding="utf-8") as f:
        data = json.load(f)

    return data

def discover_devices(frames):
    print(f"\n{BLUE}(1) DEVICES DISCOVERY {'=' * 89}{RESET}")
    print(f"{GRAY}Extracting 16-bit WPAN addresses from source/destination fields to enumerate active devices.{RESET}")
    print(f"{GRAY}The most frequent address is assumed to be the Hue Bridge (coordinator).{RESET}\n")

    devices_addresses = Counter()

    print("[*] Scanning for devices...", end="", flush=True)
    for frame in frames:
        wpan = frame["_source"]["layers"]["wpan"]
        devices_addresses[wpan["wpan.src16"]] += 1
        devices_addresses[wpan["wpan.dst16"]] += 1
    print(f" {len(devices_addresses)} found.")

    devices_addresses = devices_addresses.most_common() # The most frequent address is the Hue Bridge
    # print(devices_addresses)

    bridge = Device(devices_addresses[0][0])
    bridge.name = "Philips Hue Bridge"
    lightbulbs = [Lightbulb(device_address) for device_address, _ in devices_addresses[1:]]

    print(f"{GREEN}[+] Bridge: {bridge.address}×{devices_addresses[0][1]}{RESET}")
    print(f"{GREEN}[+] Lightbulbs: {len(lightbulbs)} ({', '.join(f'{device[0]}×{device[1]}' for device in devices_addresses[1:])}){RESET}")

    return bridge, lightbulbs

def infer_toggles(frames, bridge, lightbulbs):
    print(f"\n{BLUE}(2) FRAMES FILTERING {'=' * 90}{RESET}")
    print(f"{GRAY}Filtering for toggle frames using heuristics (frame length, source, and security counter).{RESET}")
    print(f"{GRAY}The ZigBee security counter is used to remove duplicates/retransmissions.{RESET}\n")

    frames.sort(key=lambda f: f["_source"]["layers"]["frame"]["frame.time_utc"])
    zbee_sec_counters = set()

    total_frames = len(frames)
    after_length_filter = 0
    after_source_filter = 0
    after_retransmission_filter = 0

    for frame in frames:
        layers = frame["_source"]["layers"]

        # Toggle frames are 55 bytes long
        frame_length = layers["frame"]["frame.len"]
        if frame_length != "55":
            continue
        after_length_filter += 1

        # Toggle commands are always initiated by the bridge
        src_address = layers["wpan"]["wpan.src16"]
        if src_address != bridge.address:
            continue
        after_source_filter += 1

        # The NWK address identifies the final target device, not the next-hop address (WPAN/MAC)
        dest_address = layers["zbee_nwk"]["zbee_nwk.dst"]

        # The ZigBee security counter uniquely identifies a secured frame, it can be used to detect duplicates or retransmissions
        zbee_sec_counter = frame["_source"]["layers"]["zbee_nwk"]['ZigBee Security Header']['zbee.sec.counter']
        if zbee_sec_counter in zbee_sec_counters:
            continue
        after_retransmission_filter += 1
        zbee_sec_counters.add(zbee_sec_counter)

        time = layers["frame"]["frame.time_utc"]
        date = datetime.fromisoformat(time[:26] + time[29:].replace("Z", "+00:00")).astimezone(ZoneInfo("Europe/Amsterdam")) # Truncate nanoseconds to microseconds

        lightbulb = next(lb for lb in lightbulbs if lb.address == dest_address)
        lightbulb.toggles.append(LightbulbToggle(date))

    print(f"[*] {'Frames total:':<50} {total_frames:>5}")
    print(f"[*] {'After length filter (55 B):':<50} {after_length_filter:>5} ({total_frames - after_length_filter:<3} removed)")
    print(f"[*] {'After source filter (bridge):':<50} {after_source_filter:>5} ({total_frames - after_source_filter:<3} removed)")
    print(f"[*] {'After retransmission filter (security counter):':<50} {after_retransmission_filter:>5} ({total_frames - after_retransmission_filter:<3} removed)")

    print(f"\n{BLUE}(3) TOGGLES ANALYSIS {'=' * 90}{RESET}")
    print(f"{GRAY}For each lightbulb, inferring toggle types (ON/OFF) based on the time spent in each state.{RESET}")
    print(f"{GRAY}The state with the longest total duration is assumed to be the OFF state.{RESET}\n")

    for lightbulb in lightbulbs:
        time_at_state_1 = timedelta(0)
        time_at_state_2 = timedelta(0)

        for idx, (prev_toggle, toggle) in enumerate(zip([None] + lightbulb.toggles[:-1], lightbulb.toggles)):
            duration = toggle.date - prev_toggle.date if prev_toggle else toggle.date - toggle.date.replace(hour=0, minute=0, second=0, microsecond=0)

            if idx % 2 == 0:
                time_at_state_1 += duration
            else:
                time_at_state_2 += duration

        state_1 = False if time_at_state_1 <= time_at_state_2 else True # The longer time corresponds to the OFF time
        for idx, toggle in enumerate(lightbulb.toggles):
            if idx % 2 == 0:
                toggle.type = state_1
            else:
                toggle.type = not state_1

        print(
            f"[*] Lightbulb {lightbulb.address} ({len(lightbulb.toggles):<3} toggles):    "
            f"{'OFF' if state_1 else 'ON'} {str(timedelta(seconds=int(time_at_state_1.total_seconds()))):<17}    "
            f"{'ON' if state_1 else 'OFF'} {str(timedelta(seconds=int(time_at_state_2.total_seconds()))):<17}"
        )

    print(f"\n{GREEN}[+] Toggles inferred: {sum(len(lightbulb.toggles) for lightbulb in lightbulbs)}{RESET}")

def list_toggles(lightbulbs):
    print(f"\n{CYAN}List toggles (per lightbulb){RESET}")
    print("\n" + "\n\n".join(str(lightbulb) for lightbulb in lightbulbs))

def render_timeline(day, lightbulbs):
    lines = []

    slots_per_hour = 60 // TIMELINE_STEP_MINUTES
    slots = slots_per_hour * 24

    # Header
    lines.append("─" * 24 + ("┬" + "".join(["─" * (slots_per_hour - 1)])) * 24)

    labels = [" "] * slots
    for i in range(0, slots, slots_per_hour):
        hour = f"│{i // slots_per_hour:02d}:00"
        if i + len(hour) <= slots:
            labels[i:i + len(hour)] = hour
    lines.append(f" {day.strftime('%A %d %B'):<21}  " + "".join(labels))

    # Data
    on = "█"
    off = "░"

    lines.append("─" * 24 + ("┴" + "".join(["─" * (slots_per_hour - 1)])) * 24)

    for idx, lightbulb in enumerate(lightbulbs):
        row = [" "] * slots
        day_toggles = [toggle for toggle in lightbulb.toggles if toggle.date.date() == day.date()]

        for toggle in day_toggles:
            slot_index = (toggle.date.hour * 60 + toggle.date.minute) // TIMELINE_STEP_MINUTES
            row[slot_index] = "1" if not row[slot_index].isdigit() else str(int(row[slot_index]) + 1)

            if row[slot_index] == "1":
                last_slot_index = next(((i + 1) for i in range(slot_index - 1, -1, -1) if row[i].isdigit()), 0)
                if last_slot_index != slot_index:
                    row[last_slot_index:slot_index] = (off if toggle.type else on) * (slot_index - last_slot_index)

            if toggle == day_toggles[-1]:
                row[slot_index + 1:] = (on if toggle.type else off) * (slots - slot_index - 1)

        if not day_toggles:
            previous_toggle = next((t for t in reversed(lightbulb.toggles) if t.date < day), None)
            if previous_toggle:
                row = (on if previous_toggle.type else off) * slots
            else:
                next_toggle = next((t for t in lightbulb.toggles if t.date >= day + timedelta(days=1)), None)
                if next_toggle:
                    row = (off if next_toggle.type else on) * slots

        lines.append(f" {idx + 1:>02d}. {'Lightbulb ' + lightbulb.address if not lightbulb.name else lightbulb.name:<17}  " + "".join(row))
        lines.append("─" * (24 + slots))

    return lines

def render_timeline_view(day, lightbulbs):
    lines = []

    # Header
    lines.extend(ASCII_ART)
    lines.append("")
    lines.append(TAGLINE)
    lines.append("")

    # Body
    lines.extend(render_timeline(day, lightbulbs))

    # Footer
    lines.append("")
    lines.append(f"Legend:  █ ON  |  ░ OFF  |  numbers = toggles per {TIMELINE_STEP_MINUTES}-minute slot")
    lines.append("")
    lines.append("[←/→] change day    [q] quit")

    return "\n".join(lines)

def visualize_lights_timeline(lightbulbs):
    start_date = min(toggle.date for lightbulb in lightbulbs for toggle in lightbulb.toggles).replace(hour=0, minute=0, second=0, microsecond=0)
    end_date = max(toggle.date for lightbulb in lightbulbs for toggle in lightbulb.toggles).replace(hour=0, minute=0, second=0, microsecond=0)
    day = start_date

    def _ui(stdscr):
        nonlocal day
        curses.curs_set(0)
        stdscr.keypad(True)

        while True:
            stdscr.erase()
            text = render_timeline_view(day, lightbulbs)
            h, w = stdscr.getmaxyx()

            for y, line in enumerate(text.splitlines()):
                if y >= h:
                    break
                stdscr.addnstr(y, 0, line, w - 1)
            stdscr.refresh()

            key = stdscr.getch()
            if key in (ord("q"), ord("Q")):
                break
            elif key == curses.KEY_RIGHT:
                next_day = day + timedelta(days=1)
                if next_day <= end_date:
                    day = next_day
            elif key == curses.KEY_LEFT:
                previous_day = day - timedelta(days=1)
                if previous_day >= start_date:
                    day = previous_day

    curses.wrapper(_ui)
    print(f"\n{CYAN}Visualize lights ON/OFF timeline{RESET}")
    print("\n".join(render_timeline(day, lightbulbs)))

def assign_lightbulb_names(lightbulbs):
    print(f"\n{CYAN}Assign lightbulb names{RESET}")

    current_mappings = ", ".join(f"{idx + 1}={lightbulb.name}" for idx, lightbulb in enumerate(lightbulbs) if lightbulb.name)
    mappings_info = f"Current mappings: {current_mappings}" if current_mappings else "Example: 1=Bathroom 1, 2=Bathroom 2, 3=Owl's Bedroom, 4=Dining Table 1, 5=Kitchen, 6=Dining Table 2, 7=Living Room, 8=Bird's Bedroom"

    light_name_mappings = input(
        f"Enter mappings as index=name (comma-separated), or press Enter to skip.\n"
        f"{GRAY}{mappings_info}{RESET}\n"
        "Mappings: "
    ).strip()

    valid_mappings = []

    for light_name in light_name_mappings.split(","):
        light_name = light_name.strip()
        if not light_name: continue

        if "=" not in light_name:
            print(f"{RED}[-] Invalid mapping (expected index=name): {light_name}{RESET}")
            continue

        idx, name = light_name.split("=", 1)
        idx = idx.strip()
        name = name.strip()

        if not idx.isdigit():
            print(f"{RED}[-] Invalid light number: {idx}{RESET}")
            continue

        idx = int(idx.strip()) - 1

        if not (0 <= idx < len(lightbulbs)):
            print(f"{RED}[-] Invalid light number: {idx + 1} (valid range 1-{len(lightbulbs)}){RESET}")
            continue

        if not name:
            print(f"{RED}[-] Invalid name (empty) for light {idx + 1}.{RESET}")
            continue

        lightbulbs[idx].name = name
        valid_mappings.append(f"{idx + 1}={name}")

    if valid_mappings:
        print(f"{GREEN}[+] Applied {len(valid_mappings)} mappings: {', '.join(valid_mappings)}{RESET}")

def analyze_patterns(lightbulbs):
    print(f"\n{CYAN}Analyze light usage patterns and infer habits{RESET}")

    # Routine Analysis

    def avg_time(times):
        if not times: return None
        a = [math.atan2(math.sin(2 * math.pi * (t.hour * 3600 + t.minute * 60 + t.second) / 86400), math.cos(2 * math.pi * (t.hour * 3600 + t.minute * 60 + t.second) / 86400)) for t in times]
        x = sum(math.cos(v) for v in a) / len(a)
        y = sum(math.sin(v) for v in a) / len(a)
        s = (math.atan2(y, x) * 86400 / (2 * math.pi)) % 86400
        return time(int(s // 3600), int(s % 3600 // 60), int(s % 60))

    MORNING_START = time(5, 0)
    MORNING_END = time(10, 30)
    NIGHT_START = time(21, 0)
    NIGHT_END = time(2, 0)

    morning_routine = []
    evening_routine = []

    for lightbulb in lightbulbs:
        daily_toggles = []

        current_day = None
        for toggle in lightbulb.toggles:
            if not (toggle.date.time() >= MORNING_START or toggle.date.time() <= NIGHT_END):
                continue

            adjusted_day = toggle.date.date() if toggle.date.time() >= MORNING_START else toggle.date.date() - timedelta(days=1)

            if adjusted_day != current_day:
                daily_toggles.append([])
                current_day = adjusted_day

            daily_toggles[-1].append(toggle)

        first_on_toggle_times = []
        last_off_toggle_times = []

        for day_toggles in daily_toggles:
            for toggle in day_toggles:
                if toggle.type is True and MORNING_START <= toggle.date.time() <= MORNING_END:
                    first_on_toggle_times.append(toggle.date.time())
                    break
            for toggle in reversed(day_toggles):
                if toggle.type is False and (NIGHT_START <= toggle.date.time() or toggle.date.time() <= NIGHT_END):
                    last_off_toggle_times.append(toggle.date.time())
                    break

        morning_routine.append((lightbulb, first_on_toggle_times))
        evening_routine.append((lightbulb, last_off_toggle_times))

    morning_routine = sorted(morning_routine, key=lambda t: (avg_time(t[1]).hour*3600 + avg_time(t[1]).minute*60 + avg_time(t[1]).second))
    evening_routine = sorted(evening_routine, key=lambda t: ((avg_time(t[1]).hour*3600 + avg_time(t[1]).minute*60 + avg_time(t[1]).second + 86400) if avg_time(t[1]) <= NIGHT_END else (avg_time(t[1]).hour*3600 + avg_time(t[1]).minute*60 + avg_time(t[1]).second)))

    print("Morning Routine (sorted by average first ON)")
    for lightbulb, first_on_toggle_times in morning_routine:
        lightbulb_name_text = f"{f' ({lightbulb.name}):':<18}" if lightbulb.name else ":"
        print(f"Lightbulb {lightbulb.address}{lightbulb_name_text} {avg_time(first_on_toggle_times)} ({len(first_on_toggle_times):02d} days)")

    print()

    print("Evening Routine (sorted by average last OFF)")
    for lightbulb, last_off_toggle_times in evening_routine:
        lightbulb_name_text = f"{f' ({lightbulb.name}):':<18}" if lightbulb.name else ":"
        print(f"Lightbulb {lightbulb.address}{lightbulb_name_text} {avg_time(last_off_toggle_times)} ({len(last_off_toggle_times):02d} days)")

def menu(lightbulbs):
    while True:
        print(f"\n{BLUE}(≡) MENU {'=' * 102}{RESET}")
        print("Select an action:")
        print("1) List toggles (per lightbulb)")
        print("2) Visualize lights ON/OFF timeline")
        print("3) Assign lightbulb names")
        print("4) Analyze light usage patterns and infer habits")
        print()
        choice = input("Choice: ").strip()

        if choice == "1":
            list_toggles(lightbulbs)
        elif choice == "2":
            visualize_lights_timeline(lightbulbs)
        elif choice == "3":
            assign_lightbulb_names(lightbulbs)
        elif choice == "4":
            analyze_patterns(lightbulbs)
        elif choice.lower() == "q":
            print("Exiting.\n")
            break
        else:
            print(f"{RED}[-] Invalid choice (valid: 1-4, q).{RESET}")


def main():
    print_header()

    filename = parse_args().input
    frames = load_json(filename)
    print(f"[*] File: {filename}")

    bridge, lightbulbs = discover_devices(frames)
    infer_toggles(frames, bridge, lightbulbs)

    menu(lightbulbs)

if __name__ == "__main__":
    main()