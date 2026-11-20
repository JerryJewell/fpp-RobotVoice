#!/bin/bash
# Safe to run multiple times; FPP removes the plugin directory after this.
set -e
: "${FPPDIR:=/opt/fpp}"
. "${FPPDIR}/scripts/common"
systemctl disable --now fpp-robotvoice.service 2>/dev/null || true
rm -f /etc/systemd/system/fpp-robotvoice.service
systemctl daemon-reload
# FPP 10.4+ reinstate keeps settings; a real uninstall deletes plugin data.
if [ "${FPP_PLUGIN_REINSTALL:-0}" != "1" ]; then
  rm -rf "${MEDIADIR}/plugindata/fpp-RobotVoice"
fi
printf 'Robot Voice removed.\n'
