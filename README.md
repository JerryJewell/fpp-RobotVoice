# Chad's Voice Changer
Live robotic microphone effects for a dedicated Raspberry Pi running FPP 10.

**Beta for FPP 10.x.** FPP can play a sequence soundtrack while this plugin processes the microphone. Simultaneous FPP audio and live voice worked through the same output on one Pi; shared-output compatibility depends on your audio setup. The new Status-page controls still need a hardware test.

## Install from the FPP Plugins page
1. In FPP Settings set UI Level to Developer.
2. Open Content Setup → Plugins (Plugin Manager).
3. Paste the [direct plugin manifest](https://raw.githubusercontent.com/JerryJewell/fpp-RobotVoice/refs/heads/main/pluginInfo.json) into Find a Plugin.
4. Load the plugin details, review the disclosure and click Install.
5. When installation finishes, open Status/Control → Chad's Voice Changer. Alternatively:
   `http://YOUR_FPP_IP/plugin.php?plugin=fpp-RobotVoice&page=control.php`

This plugin is not automatically included in FPP's community catalog.

## Wiring
Existing microphone → USB sound adapter mic input → Raspberry Pi → USB adapter 3.5 mm output → amplifier.
Microphone, adapter and amplifier are required and not included. The Pi's onboard 3.5 mm jack is output only.
Use an adapter with real microphone input and simultaneous input/output support.
Keep amplifier volume low while setting up.
If the two audio streams compete for an output, test them on separate devices. On one Pi, the live voice and FPP media worked on the same output.

## First sound
Select the detected input and output device names.
Choose Clean / test; microphone gain 1, output gain 0.30, noise gate 0.
Save the device settings, then use **Voice On** on the FPP Status page.
After clean speech works, select Classic robot, Deep robot or Dalek-style or one of the experimental cartoon voices.
Changing the preset applies and saves its effect values immediately. Manual adjustments still need **Save settings**.

Settings are preserved across updates. The **Voice On / Voice Off** buttons affect only the mic and do not alter the playlist or the **Start voice processing at boot** preference. Uncheck the boot preference if you want the mic off after a reboot.
No playlist, show or sequence is needed.

## Troubleshooting
If the controls do not appear, refresh FPP and use the direct page URL above.
The install log should show whether OS audio dependencies installed successfully.
If installation cannot find OS packages, check FPP's internet connection and package indexes.
If audio is busy, ensure FPP playback does not own the USB adapter.
If sound stutters, try 512 frames; if the sample rate fails, try 44100 Hz.
Click **Voice Off** on the FPP Status page to stop live voice processing.

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
Installs NumPy and PortAudio from the OS repositories, sounddevice 0.5.3 via the FPP Python dependency mechanism, and a systemd service.
Does not modify FPP's audio routing.
Uninstall using FPP's Plugin Manager; the uninstall hook removes the service and plugin settings unless FPP requests preservation for reinstall.

## Validation
The original package reported offline DSP tests. This update has not been tested on Pi hardware.
Before relying on it, test clean speech, all four presets, settings persistence, reboot recovery, adapter reconnect and acceptable latency.
