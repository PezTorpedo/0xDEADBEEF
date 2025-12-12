#!/bin/sh

DNSMASQ_FILTER_AAAA=1
DNSMASQ_FILTER_A=0
DNSMASQ_CACHESIZE=1000
DNSMASQ_EDNSPACKET_MAX=1232

[   "$(uci -q get dhcp.@dnsmasq[0].filter_aaaa)" = "${DNSMASQ_FILTER_AAAA}" ] && \
  [ "$(uci -q get dhcp.@dnsmasq[0].filter_a)" = "${DNSMASQ_FILTER_A}" ] && \
  [ "$(uci -q get dhcp.@dnsmasq[0].cachesize)" = "${DNSMASQ_CACHESIZE}" ] && \
  [ "$(uci -q get dhcp.@dnsmasq[0].ednspacket_max)" = "${DNSMASQ_EDNSPACKET_MAX}" ] && \
        exit 0

uci -q batch <<-EOF >/dev/null
        set dhcp.@dnsmasq[0].filter_aaaa=${DNSMASQ_FILTER_AAAA}
        set dhcp.@dnsmasq[0].filter_a=${DNSMASQ_FILTER_A}
        set dhcp.@dnsmasq[0].cachesize=${DNSMASQ_CACHESIZE}
        set dhcp.@dnsmasq[0].ednspacket_max=${DNSMASQ_EDNSPACKET_MAX}
        commit dhcp
EOF

exit 0
