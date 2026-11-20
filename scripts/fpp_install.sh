#!/bin/bash
# Local FPP plugin install/update. FPP runs official install hooks as root;
# for manual installation call this script using sudo from an SSH shell.
set -e
: "${FPPDIR:=/opt/fpp}"
. "${FPPDIR}/scripts/common"
PLUGIN_DIR="${MEDIADIR}/plugins/fpp-RobotVoice"
DATA_DIR="${MEDIADIR}/plugindata/fpp-RobotVoice"
if [ ! -f "${PLUGIN_DIR}/robot_voice.py" ]; then
  echo "Missing ${PLUGIN_DIR}/robot_voice.py" >&2
  exit 1
fi
# Use OS packages; no pip, external script download, or FPP core modifications.
DEBIAN_FRONTEND=noninteractive apt-get install -y python3-numpy python3-sounddevice libportaudio2
install -d -m 0750 -o fpp -g fpp "${DATA_DIR}"
if [ ! -f "${DATA_DIR}/config.json" ]; then
  install -m 0640 -o fpp -g fpp "${PLUGIN_DIR}/default-config.json" "${DATA_DIR}/config.json"
fi
# Preserve user settings across updates; keep both paths inside FPP's media tree.
cat > /etc/systemd/system/fpp-robotvoice.service <<EOF
[Unit]
Description=FPP Robot Voice - dedicated live microphone effects
After=sound.target

[Service]
Type=simple
User=fpp
Group=fpp
SupplementaryGroups=audio
WorkingDirectory=${PLUGIN_DIR}
Environment=ROBOTVOICE_DATADIR=${DATA_DIR}
Environment=LOGDIR=${LOGDIR}
ExecStart=/usr/bin/python3 ${PLUGIN_DIR}/robot_voice.py run --config ${DATA_DIR}/config.json
Restart=on-failure
RestartSec=3
NoNewPrivileges=true
ProtectSystem=full
StandardOutput=null
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF
systemctl daemon-reload
systemctl enable --now fpp-robotvoice.service
# An update should restart this plugin's own service, never fppd.
systemctl try-restart fpp-robotvoice.service
printf 'Robot Voice installed. Visit FPP > Status/Control > Robot Voice.\n'
