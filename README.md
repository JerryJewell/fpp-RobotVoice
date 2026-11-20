# FPP Robot Voice
Live robotic microphone effects for a dedicated Raspberry Pi running FPP 10.

**Experimental. Audio quality, latency, USB audio and installation on Pi/FPP have not yet been verified on hardware.**

## Install from the FPP Plugins page
1. In FPP Settings set UI Level to Developer.
2. Open Content Setup → Plugins (Plugin Manager).
3. Paste https://github.com/JerryJewell/fpp-RobotVoice into Find a Plugin.
4. Load the plugin details, review the disclosure and click Install.
5. When installation finishes, open Status/Control → Robot Voice. Alternatively:
   `http://YOUR_FPP_IP/plugin.php?plugin=fpp-RobotVoice&page=control.php`

This repository must be published first. It is not automatically included in FPP's community catalog.

## Wiring
Existing microphone → USB sound adapter mic input → Raspberry Pi → USB adapter 3.5 mm output → amplifier.
Microphone, adapter and amplifier are required and not included. The Pi's onboard 3.5 mm jack is output only.
Use an adapter with real microphone input and simultaneous input/output support.
Keep amplifier volume low while setting up.
Set FPP's own audio output to a different unused device (such as HDMI) to avoid competing for the USB adapter.

## First sound
Select the detected input and output device names.
Choose Clean / test; microphone gain 1, output gain 0.30, noise gate 0.
Enable live microphone processing and save settings.
After clean speech works, select Classic robot, Deep robot or Dalek-style and click Load preset values and save.
The preset selector alone does not reset sliders.

Settings are preserved across updates. The engine starts at boot, with audio disabled until enabled in the controls.
No playlist, show or sequence is needed.

## Troubleshooting
If the controls do not appear, refresh FPP and use the direct page URL above.
The install log should show whether OS audio dependencies installed successfully.
If installation cannot find OS packages, check FPP's internet connection and package indexes.
If audio is busy, ensure FPP playback does not own the USB adapter.
If sound stutters, try 512 frames; if the sample rate fails, try 44100 Hz.
Turn off Enable live microphone processing to stop audio.

Diagnostic commands, only if needed:
```sh
systemctl status fpp-robotvoice.service --no-pager
python3 /home/fpp/media/plugins/fpp-RobotVoice/robot_voice.py devices
tail -n 50 /home/fpp/media/logs/plugin-fpp-RobotVoice.log
```

## Data and system changes
Audio is processed in memory, not recorded or sent online.
Configuration and device status: /home/fpp/media/plugindata/fpp-RobotVoice/
Diagnostic log: /home/fpp/media/logs/plugin-fpp-RobotVoice.log
Installs Debian NumPy, sounddevice and PortAudio packages and a systemd service.
Does not modify FPP's audio routing.
Uninstall using FPP's Plugin Manager; the uninstall hook removes the service and plugin settings unless FPP requests preservation for reinstall.

## Validation
The original package reported offline DSP tests. This repository packaging update does not establish Pi hardware compatibility.
Before relying on it, test clean speech, all four presets, settings persistence, reboot recovery, adapter reconnect and acceptable latency.
