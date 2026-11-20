#!/usr/bin/env python3
"""FPP Robot Voice: separate, live mono USB-mic -> USB-output DSP engine.

No FPP show, playlist, recording, socket or network service is required.
Only stdlib and NumPy are imported for offline DSP testing; sounddevice
(PortAudio) is imported when an audio device must be opened.
"""
from __future__ import annotations

import argparse
import json
import logging
from logging.handlers import WatchedFileHandler
import math
import os
from pathlib import Path
import signal
import sys
import time
from typing import Any

import numpy as np

VERSION = "0.2.0-local"
DATADIR = Path(os.environ.get("ROBOTVOICE_DATADIR", "/home/fpp/media/plugindata/fpp-RobotVoice"))
LOGDIR = Path(os.environ.get("LOGDIR", "/home/fpp/media/logs"))
DEFAULT_CONFIG = {
    "enabled": False, "input_device": "", "output_device": "",
    "sample_rate": 48000, "blocksize": 256, "preset": "clean",
    "mic_gain": 1.0, "output_gain": 0.30, "noise_gate": 0.02,
    "pitch_ratio": 1.0, "metallic": 0.0, "metallic_hz": 65.0,
    "distortion": 0.0, "echo_ms": 0,
}
PRESETS = {
    "clean":   {"pitch_ratio": 1.00, "metallic": 0.00, "metallic_hz": 65, "distortion": 0.00, "echo_ms": 0},
    "classic": {"pitch_ratio": 0.95, "metallic": 0.52, "metallic_hz": 68, "distortion": 0.13, "echo_ms": 0},
    "deep":    {"pitch_ratio": 0.72, "metallic": 0.20, "metallic_hz": 45, "distortion": 0.23, "echo_ms": 0},
    "dalek":   {"pitch_ratio": 0.88, "metallic": 0.76, "metallic_hz": 89, "distortion": 0.35, "echo_ms": 58},
    "cartoon": {"pitch_ratio": 1.50, "metallic": 0.00, "metallic_hz": 65, "distortion": 0.00, "echo_ms": 0},
    "chipmunk": {"pitch_ratio": 1.85, "metallic": 0.00, "metallic_hz": 65, "distortion": 0.00, "echo_ms": 0},
}


def clamp_number(value: Any, lo: float, hi: float, default: float) -> float:
    try:
        result = float(value)
    except (ValueError, TypeError, OverflowError):
        return default
    return max(lo, min(hi, result)) if math.isfinite(result) else default


def normalize(raw: Any) -> dict[str, Any]:
    """Treat config as untrusted: strict bounds protect output/CPU."""
    value = raw if isinstance(raw, dict) else {}
    c = DEFAULT_CONFIG.copy()
    c["enabled"] = value.get("enabled") is True
    for key in ("input_device", "output_device"):
        c[key] = str(value.get(key, ""))[:120].strip()
    c["preset"] = value.get("preset") if value.get("preset") in PRESETS else "clean"
    c["sample_rate"] = 44100 if str(value.get("sample_rate", 48000)) == "44100" else 48000
    c["blocksize"] = 512 if str(value.get("blocksize", 256)) == "512" else 256
    for key, lo, hi in (
        ("mic_gain", 0, 4), ("output_gain", 0, 1), ("noise_gate", 0, .10),
        ("pitch_ratio", .60, 2.00), ("metallic", 0, 1),
        ("metallic_hz", 20, 180), ("distortion", 0, 1),
        ("echo_ms", 0, 200),
    ):
        c[key] = clamp_number(value.get(key, c[key]), lo, hi, float(c[key]))
    c["echo_ms"] = int(c["echo_ms"])
    return c


def load_config(filename: Path) -> dict[str, Any]:
    try:
        return normalize(json.loads(filename.read_text(encoding="utf-8")))
    except (OSError, ValueError, UnicodeError) as ex:
        logging.warning("Configuration missing or invalid (%s); disabling audio", ex)
        return normalize({})


class VoiceDSP:
    """Stateful, single-channel per-block voice effects; runs on a NumPy array."""

    def __init__(self, sample_rate: int):
        self.sample_rate = sample_rate
        self.pitch_history = np.zeros(16384, dtype=np.float32)
        self.pitch_write = 0
        self.pitch_phase = 0.0
        self.metal_phase = 0.0
        self.echo_history = np.zeros(32768, dtype=np.float32)
        self.echo_write = 0
        self.gate_value = 0.0

    def _pitch_shift(self, x: np.ndarray, ratio: float) -> np.ndarray:
        """Dual, cross-faded variable delay heads; preserves real-time duration.

        Approximate pitch shifter, not formant-preserving or studio quality.
        Minimum 1024-frame delay ensures read samples are from earlier blocks.
        """
        n = len(x)
        idx = np.arange(n)
        ring = self.pitch_history
        ring_size = len(ring)
        ring[(self.pitch_write + idx) % ring_size] = x
        start = self.pitch_write
        self.pitch_write = (self.pitch_write + n) % ring_size
        if abs(ratio - 1.0) < .005:
            return x.copy()
        span = 3072.0
        phase = (self.pitch_phase + idx * (1.0 - ratio) / span) % 1.0
        self.pitch_phase = (self.pitch_phase + n * (1.0 - ratio) / span) % 1.0

        def tap(delay: np.ndarray) -> np.ndarray:
            position = ((start + idx).astype(np.float64) - delay) % ring_size
            a = position.astype(np.int64)
            fract = position - a
            return ring[a] * (1.0 - fract) + ring[(a + 1) % ring_size] * fract

        d1 = 1024.0 + span * phase
        d2 = 1024.0 + span * ((phase + .5) % 1.0)
        w = np.sin(np.pi * phase) ** 2
        return (tap(d1) * w + tap(d2) * (1.0 - w)).astype(np.float32)

    def process(self, input_samples: np.ndarray, config: dict[str, Any]) -> np.ndarray:
        cfg = config  # main thread swaps a fully normalized dict atomically
        x = np.nan_to_num(np.asarray(input_samples, dtype=np.float32).flatten(),
                          nan=0.0, posinf=0.0, neginf=0.0).copy()
        if len(x) == 0:
            return x
        if len(x) > 512:
            # Keep pitch minimum delay > processed block size even with host jitter.
            return np.concatenate([self.process(z, cfg) for z in np.array_split(x, math.ceil(len(x) / 512))])
        x *= cfg["mic_gain"]
        rms = float(np.sqrt(np.mean(x * x)))
        gate_target = 1.0 if cfg["noise_gate"] == 0 or rms > cfg["noise_gate"] else 0.0
        # Avoid hard gate switching (short fade between blocks).
        fade = np.linspace(self.gate_value, gate_target, len(x), dtype=np.float32)
        self.gate_value = gate_target
        x *= fade
        y = self._pitch_shift(x, cfg["pitch_ratio"])
        metallic = cfg["metallic"]
        if metallic > 0:
            t = np.arange(len(y), dtype=np.float64)
            theta = self.metal_phase + (2 * np.pi * cfg["metallic_hz"] / self.sample_rate) * t
            osc = np.sin(theta).astype(np.float32)
            self.metal_phase = float((theta[-1] + 2 * np.pi * cfg["metallic_hz"] / self.sample_rate) % (2 * np.pi))
            y *= (1.0 - metallic) + metallic * osc
        if cfg["distortion"] > 0:
            drive = 1.0 + 9.0 * cfg["distortion"]
            y = (np.tanh(y * drive) / np.tanh(drive)).astype(np.float32)
        delay = int(cfg["echo_ms"] * self.sample_rate / 1000)
        if delay > 0:
            # A short echo at 20% wet. Feedback limited to 0.17.
            for i in range(len(y)):
                earlier = self.echo_history[(self.echo_write - delay) % len(self.echo_history)]
                sample = float(y[i])
                self.echo_history[self.echo_write] = sample + .17 * earlier
                y[i] = sample + .20 * earlier
                self.echo_write = (self.echo_write + 1) % len(self.echo_history)
        y *= cfg["output_gain"]
        return np.clip(y, -0.95, 0.95).astype(np.float32)


def describe_devices(sd: Any) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    hosts = sd.query_hostapis()
    for index, device in enumerate(sd.query_devices()):
        has_in = int(device["max_input_channels"]) > 0
        has_out = int(device["max_output_channels"]) > 0
        if has_in or has_out:
            entries.append({"index": index, "name": device["name"],
                            "hostapi": hosts[device["hostapi"]]["name"],
                            "input": has_in, "output": has_out})
    return entries


def select_device(devices: list[dict[str, Any]], name: str, direction: str) -> int:
    """Prefer exact names; require unique substring match to avoid wrong mic."""
    if not name:
        raise ValueError(f"Select a {direction} device in the FPP Robot Voice page")
    eligible = [d for d in devices if d[direction]]
    exact = [d for d in eligible if d["name"].casefold() == name.casefold()]
    matches = exact or [d for d in eligible if name.casefold() in d["name"].casefold()]
    # Prefer ALSA if the same name is visible under several host APIs.
    alsa = [d for d in matches if d["hostapi"].casefold() == "alsa"]
    matches = alsa if alsa else matches
    if len(matches) != 1:
        raise ValueError(f"{direction.title()} device '{name}' found {len(matches)} times; "
                         "choose a unique device name from the device list")
    return int(matches[0]["index"])


def atomic_json(path: Path, data: dict[str, Any]) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def configure_logging() -> None:
    LOGDIR.mkdir(parents=True, exist_ok=True)
    handler = WatchedFileHandler(LOGDIR / "plugin-fpp-RobotVoice.log")
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(message)s",
                        handlers=[handler])


def run_forever(config_path: Path) -> None:
    import sounddevice as sd  # only needed on an installed Pi
    running = True

    def shutdown(_sig: int, _frame: Any) -> None:
        nonlocal running
        running = False

    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)
    logging.info("Robot Voice %s started (disabled until configured)", VERSION)
    current: dict[str, Any] = {}
    cfg = load_config(config_path)
    audio_key: tuple[Any, ...] | None = None
    stream: Any = None
    dsp: VoiceDSP | None = None
    status_text = "disabled"
    last_error = ""
    xruns = [0]
    dsp_errors = [0]
    last_status = 0.0
    last_attempt = 0.0
    last_devices_scan = 0.0
    devices: list[dict[str, Any]] = []
    try:
        while running:
            now = time.monotonic()
            if now - last_devices_scan >= 15 or not devices:
                try:
                    devices = describe_devices(sd)
                except Exception as exc:
                    devices = []
                    logging.warning("Device discovery: %s", exc)
                last_devices_scan = now
            cfg = load_config(config_path)
            desired_key = (cfg["input_device"], cfg["output_device"],
                           cfg["sample_rate"], cfg["blocksize"]) if cfg["enabled"] else None
            if desired_key != audio_key or (cfg["enabled"] and stream is None and now - last_attempt >= 10):
                last_attempt = now
                if stream is not None:
                    stream.stop()
                    stream.close()
                    stream = None
                audio_key = desired_key
                if desired_key is None:
                    status_text = "disabled"
                    last_error = ""
                else:
                    try:
                        input_idx = select_device(devices, cfg["input_device"], "input")
                        output_idx = select_device(devices, cfg["output_device"], "output")
                        sd.check_input_settings(device=input_idx, channels=1, samplerate=cfg["sample_rate"])
                        sd.check_output_settings(device=output_idx, channels=1, samplerate=cfg["sample_rate"])
                        dsp = VoiceDSP(cfg["sample_rate"])
                        # Reference to config replaced by main loop; read only in callback.
                        current = cfg

                        def callback(indata: np.ndarray, outdata: np.ndarray,
                                     frames: int, time_info: Any, flags: Any) -> None:
                            if flags:
                                xruns[0] += 1
                            try:
                                assert dsp is not None
                                outdata[:, 0] = dsp.process(indata[:, 0], current)
                            except Exception:
                                dsp_errors[0] += 1
                                outdata.fill(0)

                        stream = sd.Stream(samplerate=cfg["sample_rate"],
                                           blocksize=cfg["blocksize"],
                                           dtype="float32", channels=(1, 1),
                                           device=(input_idx, output_idx),
                                           latency="low", callback=callback)
                        stream.start()
                        status_text = "running"
                        last_error = ""
                        logging.info("Audio running: input %s (%s), output %s (%s), %s Hz",
                                     cfg["input_device"], input_idx,
                                     cfg["output_device"], output_idx, cfg["sample_rate"])
                    except Exception as exc:
                        last_error = str(exc)
                        status_text = "error"
                        if stream is not None:
                            try:
                                stream.close()
                            except Exception:
                                pass
                        stream = None
                        logging.warning("Audio unavailable: %s", exc)
            if stream is not None:
                current = cfg  # apply changed effects without opening a new stream
                if not stream.active:
                    last_error = "Audio stream stopped; retrying"
                    status_text = "error"
                    stream.close()
                    stream = None
                    logging.warning(last_error)
            if now - last_status > 10 or desired_key != audio_key:
                atomic_json(DATADIR / "status.json", {
                    "time": int(time.time()), "version": VERSION,
                    "state": status_text, "error": last_error,
                    "xruns": xruns[0], "processing_errors": dsp_errors[0],
                    "devices": devices,
                })
                last_status = now
            time.sleep(1.0 if stream is not None or not cfg["enabled"] else 3.0)
    finally:
        if stream is not None:
            stream.stop()
            stream.close()
        atomic_json(DATADIR / "status.json", {
            "time": int(time.time()), "state": "stopped", "version": VERSION,
            "error": "", "xruns": xruns[0], "processing_errors": dsp_errors[0],
            "devices": devices,
        })
        logging.info("Robot Voice stopped")


def main() -> int:
    ap = argparse.ArgumentParser(description="FPP Robot Voice DSP engine")
    ap.add_argument("action", choices=["run", "devices", "self-test"])
    ap.add_argument("--config", default=str(DATADIR / "config.json"))
    opts = ap.parse_args()
    if opts.action == "devices":
        import sounddevice as sd
        print(json.dumps(describe_devices(sd), indent=2))
        return 0
    if opts.action == "self-test":
        c = normalize({"mic_gain": 1, "output_gain": .5,
                       "pitch_ratio": .72, "metallic": .5, "distortion": .25})
        dsp = VoiceDSP(48000)
        for i in range(100):
            t = (np.arange(256) + i * 256) / 48000
            samples = np.sin(2 * np.pi * 190 * t).astype(np.float32) * .2
            out = dsp.process(samples, c)
            assert len(out) == 256 and np.all(np.isfinite(out)) and np.max(np.abs(out)) <= .95
        print("DSP self-test passed (no microphone/adapter required)")
        return 0
    DATADIR.mkdir(parents=True, exist_ok=True)
    configure_logging()
    run_forever(Path(opts.config))
    return 0


if __name__ == "__main__":
    sys.exit(main())
