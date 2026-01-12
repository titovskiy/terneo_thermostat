# Terneo/Welrok Thermostat Integration for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/custom-components/hacs)

Custom component for Home Assistant to control Terneo/Welrok thermostats via local API.

## Supported Devices

This integration supports both old and new versions of Welrok/Terneo thermostats:

- **Old version (OZ without air sensor)** - devices manufactured before June 2025
- **New version (OZ with air sensor / AZ)** - devices manufactured from June 2025

The integration automatically detects the device version during setup.

## Features

### Climate Entity
- Turn on/off
- Set target temperature
- Switch between heating/cooling modes
- Schedule (AUTO) and manual (HEAT/COOL) modes
- Preset modes: Schedule, Manual

### Sensors
- Floor temperature
- Air temperature (new version only)
- Target temperature
- Connected power (W)
- Hysteresis
- Sensor corrections

### Switches
- Power on/off
- Children lock
- Cooling mode (vs heating)
- Pre-heating
- Night brightness mode
- Window open detection (new version only)

### Number Controls
- Display brightness (0-9)
- Hysteresis setting

### Select Controls
- Control type:
  - Floor sensor
  - Air sensor (new version only)
  - Air with floor limit (new version only)

### Services
- `terneo.set_floor_limits` - Set min/max floor temperature limits
- `terneo.set_air_limits` - Set min/max air temperature limits (new version only)

## Installation

### HACS (Recommended)

1. Open HACS in Home Assistant
2. Go to "Integrations"
3. Click the three dots menu and select "Custom repositories"
4. Add this repository URL with category "Integration"
5. Install "Terneo Thermostat"
6. Restart Home Assistant

### Manual Installation

1. Copy the `custom_components/terneo` folder to your `config/custom_components` directory
2. Restart Home Assistant

## Configuration

### GUI Configuration (Recommended)

1. Go to **Settings** → **Devices & Services**
2. Click **+ Add Integration**
3. Search for "Terneo"
4. Enter the IP address of your thermostat
5. The integration will automatically detect the device and its version

### Configuration Options

After adding the integration, you can configure:

- **Update interval** - How often to poll the device (10-300 seconds, default: 30)
- **Show advanced sensors** - Enable additional diagnostic sensors

## API Documentation

This integration uses the Welrok Local API:

- [New version (OZ with air sensor)](https://welrok-local-api.readthedocs.io/en/latest/OZ/en/parameters.html)
- [Old version (OZ without air sensor)](https://welrok-local-api.readthedocs.io/en/latest/Old/en/parameters.html)

### Security Note

By default, local API control without a security token is blocked on the device for security reasons. To enable local control, set the `bLc` parameter to `oFF` on your thermostat.

- [New version (OZ with air sensor)](https://welrok-local-api.readthedocs.io/en/latest/OZ/en/safety.html)
- [Old version (OZ without air sensor)](https://welrok-local-api.readthedocs.io/en/latest/Old/en/safety.html)

## Parameters Supported

### Common Parameters (both versions)
| Parameter | Description |
|-----------|-------------|
| mode | Operation mode: schedule=0, manual=3 |
| controlType | Control: floor=0, air=1, air with floor limit=2 |
| manualFloorTemperature | Manual mode floor setpoint |
| awayFloorTemperature | Away mode floor setpoint |
| hysteresis | Temperature hysteresis |
| brightness | Display brightness (0-9) |
| upperLimit / lowerLimit | Floor temperature limits |
| powerOff | Device power state |
| childrenLock | Children lock |
| coolingControlWay | Heating=0, Cooling=1 |
| preControl | Pre-heating mode |
| useNightBright | Night brightness mode |

### New Version Only
| Parameter | Description |
|-----------|-------------|
| manualAir | Manual mode air setpoint |
| awayAir | Away mode air setpoint |
| upperAirLimit / lowerAirLimit | Air temperature limits |
| minTempAdvancedMode / maxTempAdvancedMode | Floor limits in air control mode |
| airCorrection | Air sensor correction |
| bleSensorInterval | Wireless sensor poll interval |
| windowOpenControl | Window open detection |

## Troubleshooting

### Cannot connect to device
- Ensure the thermostat is connected to your network
- Check that the IP address is correct
- Verify that local API is enabled (`bLc` = `oFF`)

### Commands not working
- Check if `lanBlock` (parameter 114) is disabled
- Ensure the device is not in cloud-only mode

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License.

## Credits

- Original integration by [@Makave1i](https://github.com/Makave1i)
- Extended by [@DevRedOWL](https://github.com/DevRedOWL)
