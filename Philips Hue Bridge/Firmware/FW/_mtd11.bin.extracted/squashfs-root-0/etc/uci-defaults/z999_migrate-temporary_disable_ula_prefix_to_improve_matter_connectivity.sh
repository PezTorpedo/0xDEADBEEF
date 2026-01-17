#!/bin/sh

uci -q batch <<-EOF >/dev/null
	delete network.globals.ula_prefix
	commit network
EOF

exit 0

