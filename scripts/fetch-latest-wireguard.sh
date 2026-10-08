#!/bin/bash
set -e
USER_AGENT="WireGuard-AndroidROMBuild/0.3 ($(uname -a))"

exec 9>.wireguard-fetch-lock
flock -n 9 || exit 0

[[ $(( $(date +%s) - $(stat -c %Y "net/wireguard/.check" 2>/dev/null || echo 0) )) -gt 86400 ]] || exit 0

if [[ -f net/wireguard/Kconfig && -f net/wireguard/version.h ]]; then
	touch net/wireguard/.check
	exit 0
fi

rm -rf net/wireguard
mkdir -p net/wireguard

if ! (curl -A "$USER_AGENT" -LsS --connect-timeout 10 "https://git.zx2c4.com/wireguard-linux-compat/snapshot/wireguard-linux-compat-1.0.20220627.tar.xz" | tar -C "net/wireguard" -xJf - --strip-components=2 "wireguard-linux-compat-1.0.20220627/src" 2>/dev/null); then
	echo "git.zx2c4.com failed, falling back to GitHub..."
	rm -rf /tmp/wg_tmp net/wireguard
	git clone --depth 1 https://github.com/WireGuard/wireguard-linux-compat.git /tmp/wg_tmp
	cp -r /tmp/wg_tmp/src net/wireguard
	rm -rf /tmp/wg_tmp
fi

sed -i 's/tristate/bool/;s/default m/default y/;' net/wireguard/Kconfig
touch net/wireguard/.check
