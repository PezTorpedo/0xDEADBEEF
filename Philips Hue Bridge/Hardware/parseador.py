import re
from binascii import unhexlify

out = open("dump_clean.bin", "wb")

with open("potentialfw.txt", "r", errors="ignore") as f:
    for line in f:
        # Busca patrón: dirección + ':' + hasta 4 grupos de 8 hex
        m = re.match(r'^[0-9a-fA-F]{8}:\s+([0-9a-fA-F]{8}\s+){1,4}', line)
        if not m:
            continue

        # Extrae todos los bloques de 8 hex de la línea
        blocks = re.findall(r'([0-9a-fA-F]{8})', line)
        for b in blocks:
            try:
                out.write(unhexlify(b))
            except Exception:
                # Si hay algo raro (no 8 hex válidos), lo saltamos
                pass

out.close()

