# DayZ Blackmarket Rotator v2.0

A complete solution for automatically rotating your DayZ blackmarket between different locations with Discord notifications and scheduling capabilities.

## 🚀 Features

- ✅ **Multi-Server Support** - Manage multiple DayZ servers from one configuration
- ✅ **Automated Scheduling** - Set up automatic rotations at specific times
- ✅ **Discord Integration** - Rich embed notifications with location images
- ✅ **Position Detection** - Automatically detects current blackmarket position
- ✅ **Configuration Validation** - Comprehensive validation with helpful error messages
- ✅ **Easy Setup** - Simple batch file interface for all operations

## 📁 Project Structure

```
Rotating_BM/
├── blackmarket_rotator_main.py    # Main script (all functionality)
├── blackmarket_rotator.bat        # Easy-to-use batch interface
├── config.json                    # Configuration file
├── README.md                      # This file
├── Examples/                      # Example files
│   └── Blackmarket.map
└── img/                          # Location images
    ├── BM_KRONA.png
    └── BM_ROG.png
```

## 🛠️ Quick Setup

### 1. Install Python
- Download from https://python.org
- **Important:** Check "Add Python to PATH" during installation

### 2. Configure Your Settings
Edit `config.json` with:
- Your server file paths
- Discord webhook URLs
- Blackmarket positions
- Scheduler settings

### 3. Run the Batch File
Double-click `blackmarket_rotator.bat` and choose from the menu:
- Install dependencies
- Rotate servers manually
- Start automated scheduler
- List configured servers

## ⚙️ Configuration

The `config.json` file contains all settings:

### Server Configuration
```json
{
  "servers": {
    "server1": {
      "name": "Main Server",
      "enabled": true,
      "blackmarket_map_path": "C:\\Path\\To\\Server\\Blackmarket.map",
      "blackmarket_trader_zone_path": "C:\\Path\\To\\Server\\Blackmarket.json",
      "discord_webhook_url": "https://discord.com/api/webhooks/YOUR_WEBHOOK"
    }
  }
}
```

### Position Configuration
```json
{
  "positions": [
    {
      "name": "Location Name",
      "Blackmarket_Vending_Classname": "Axios_Vending_Blackmarket",
      "Blackmarket_Vending_Coordinates": [11250.81, 292.80, 4282.29],
      "Blackmarket_Vending_Rotation": [154.67, 0.0, 0.0],
      "Blackmarket_Vehicle_Classname": "Axios_Vending_Car",
      "Blackmarket_Vehicle_Coordinates": [11251.73, 289.09, 4319.00],
      "Blackmarket_Vehicle_Rotation": [0.0, 0.0, 0.0],
      "img_path": "img/location.png"
    }
  ]
}
```

### Scheduler Configuration
```json
{
  "scheduler_settings": {
    "enabled": true,
    "rotation_times": ["04:00", "07:00", "10:00", "13:00", "16:00", "19:00", "22:00", "01:00"],
    "rotate_all_servers": true,
    "server_rotation_delay_seconds": 5,
    "check_interval_seconds": 60,
    "log_file": "blackmarket_scheduler.log"
  }
}
```

## 🖥️ Command Line Usage

You can also run the script directly from command line:

```bash
# Rotate all enabled servers
python blackmarket_rotator_main.py

# Rotate specific server
python blackmarket_rotator_main.py --server server1

# List configured servers
python blackmarket_rotator_main.py --list

# Run automated scheduler
python blackmarket_rotator_main.py --scheduler

# Use custom config file
python blackmarket_rotator_main.py --config custom.json

# Show help
python blackmarket_rotator_main.py --help
```

## 🔄 How It Works

1. **Position Detection**: Reads your current blackmarket coordinates from the map file
2. **Rotation Logic**: Moves to the next position in your configured list
3. **File Updates**: Updates both `.map` and trader zone `.json` files
4. **Discord Notification**: Sends rich embed with new location details and image
5. **Multi-Server**: Handles multiple servers with configurable delays

## 📋 Requirements

- **Python 3.6+** (with pip)
- **Internet connection** (for Discord notifications)
- **Write permissions** to your DayZ server directories

Dependencies are automatically installed via the batch file:
- `requests` (for Discord webhooks)
- `schedule` (for automated scheduling)

## 🚨 Important Notes

- **Always backup your server files** before first use
- **Restart your DayZ server** after rotation for changes to take effect
- The script preserves existing trader stock and settings
- Position tracking persists between script runs
- Configuration is validated on startup with helpful error messages

## 🛠️ Troubleshooting

### Common Issues

**"Python not found"**
- Ensure Python is installed and added to PATH
- Try running `python --version` in command prompt

**"Permission denied"**
- Run the batch file as administrator
- Check that server directories are writable

**"Configuration validation failed"**
- Review the error messages - they're detailed and helpful
- Check file paths use double backslashes: `C:\\Path\\To\\File`
- Verify Discord webhook URLs are correct

**"Discord notifications not working"**
- Verify webhook URL is correct and active
- Check internet connection
- Ensure webhook permissions in Discord

### Getting Help

1. Check the console output for detailed error messages
2. Verify all paths in `config.json` are correct
3. Test with a single server first before enabling multiple servers
4. Check the log file (`blackmarket_scheduler.log`) for scheduler issues

### Credits

- Jawshi
- Venom
- AI for optimizing code / comments and writing this readme (cuz im lazy af).