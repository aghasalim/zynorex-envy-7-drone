# Zynorex Envy-7 — a custom long-endurance quadcopter

A from-scratch quadcopter build: powertrain sizing, frame, radio link, and a
measured flight-endurance result that beats a commercial reference of similar
weight. Built by a third-year Applied Computer Science (AI) student with
Çingiz Abdullazadə.

> Build log and engineering only. This documents the airframe, propulsion and
> control link — how it flies and how long. It is not a payload or security
> project.

## The result that matters

Against a commercial DJI-class drone of comparable weight:

| | this build | reference |
|---|---|---|
| all-up weight | **1382 g** | 1487 g |
| control range | **up to 1250 m** | up to 500 m |
| endurance | **46 min** | 27 min |

Lighter, longer range, and **70% more flight time** — the endurance came from
matching a low-kV motor to a 3S pack and a light carbon frame rather than from a
bigger battery.

## Powertrain

- **Motors** — 1400 kV brushless (×4). No-load speed scales as `kV × pack
  voltage`; on a 3S LiPo (11.1 V nominal, 12.6 V charged) that sets the usable
  rpm band. 1400 kV was chosen over a higher-kV motor because it draws less
  current for the same thrust, which is where the endurance comes from.
- **ESC** — 30 A brushless, SimonK firmware, one per motor. Sized above the
  motor's peak draw so it is never the thermal limit.
- **Battery** — 3S LiPo. Charge/utilisation window 12.6 V full → ~11.1 V nominal.
- **Frame & props** — carbon fibre: light, and stiff enough to hold prop
  alignment under load.

## Control link

- 2.4 GHz / 5 GHz radio, independent command to each motor.
- **ESP32 / ESP8266** on board for Wi-Fi telemetry — streaming flight state to a
  ground station. (Wi-Fi microcontroller as a telemetry radio; nothing more.)

## Status / what's here

- [ ] wiring diagram and parts list with part numbers
- [ ] thrust-vs-current bench measurements per motor
- [ ] the endurance test method (load, altitude, how the 46 min was timed)
- [ ] flight-controller firmware / PID tune
- [ ] photos of the built airframe

The specs above are from the design; the bench and flight numbers should be
filled in from the actual test logs so every figure here is one you measured.
