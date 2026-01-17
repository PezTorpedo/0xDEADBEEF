from bridge import subprocess


class UbiError(Exception):
    pass


def ubi_attached(device: int) -> bool:
    # The reason we are not doing something like `stat` is
    # because ubi-simulator does not emulate `stat`, but
    # does `open`.
    try:
        with open(f"/sys/class/ubi/ubi{device}/mtd_num", "rt"):
            return True
    except OSError:
        return False


def ubi_assess(sysfs: dict):
    for key, value in sysfs.items():
        try:
            with open(key, "rt") as f:
                line = f.readline().strip()
                if line != value:
                    raise UbiError(f"Unexpected value of {key}: {line} (wanted {value})")
        except OSError as ose:
            raise UbiError(f"When reading {key}: {str(ose)}")  # pylint: disable=raise-missing-from


def ubi_detach(device: int):
    subprocess.run(f"ubidetach -d {device}")


def ubi_attach(device: int, mtd: str):
    subprocess.run(f"ubiattach -d {device} -p {mtd}")
