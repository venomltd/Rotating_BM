import json
import os
import requests
import argparse
import time
import schedule
import logging
from datetime import datetime
from urllib.parse import urlparse

# ============================================================================
# CONFIGURATION VALIDATION
# ============================================================================

class ConfigValidator:
    """Validates configuration file structure and content"""
    
    def __init__(self):
        self.errors = []
        self.warnings = []
    
    def validate_config(self, config):
        """Main validation method"""
        self.errors = []
        self.warnings = []
        
        # Validate top-level structure
        self._validate_top_level_structure(config)
        
        # Validate individual sections
        if 'servers' in config:
            self._validate_servers(config['servers'])
        
        if 'global_settings' in config:
            self._validate_global_settings(config['global_settings'])
        
        if 'scheduler_settings' in config:
            self._validate_scheduler_settings(config['scheduler_settings'])
        
        if 'positions' in config:
            self._validate_positions(config['positions'])
        
        # Report results
        if self.errors:
            error_msg = "Configuration validation failed:\n" + "\n".join([f"  - {error}" for error in self.errors])
            if self.warnings:
                error_msg += "\n\nWarnings:\n" + "\n".join([f"  - {warning}" for warning in self.warnings])
            raise ValueError(error_msg)
        
        if self.warnings:
            print("Configuration warnings:")
            for warning in self.warnings:
                print(f"  - {warning}")
        
        return True
    
    def _validate_top_level_structure(self, config):
        """Validate required top-level keys"""
        required_keys = ['servers', 'global_settings', 'scheduler_settings', 'positions']
        
        for key in required_keys:
            if key not in config:
                self.errors.append(f"Missing required top-level key: '{key}'")
            elif not isinstance(config[key], (dict, list)):
                if key == 'positions' and not isinstance(config[key], list):
                    self.errors.append(f"'{key}' must be a list")
                elif key != 'positions' and not isinstance(config[key], dict):
                    self.errors.append(f"'{key}' must be an object")
    
    def _validate_servers(self, servers):
        """Validate servers configuration"""
        if not servers:
            self.errors.append("At least one server must be configured")
            return
        
        enabled_count = 0
        for server_id, server_config in servers.items():
            if not isinstance(server_config, dict):
                self.errors.append(f"Server '{server_id}' configuration must be an object")
                continue
            
            # Check required server fields
            required_fields = ['name', 'blackmarket_map_path', 'blackmarket_trader_zone_path']
            for field in required_fields:
                if field not in server_config:
                    self.errors.append(f"Server '{server_id}' missing required field: '{field}'")
                elif not isinstance(server_config[field], str) or not server_config[field].strip():
                    self.errors.append(f"Server '{server_id}' field '{field}' must be a non-empty string")
            
            # Validate file paths
            if 'blackmarket_map_path' in server_config:
                self._validate_file_path(server_config['blackmarket_map_path'], f"Server '{server_id}' map file")
            
            if 'blackmarket_trader_zone_path' in server_config:
                self._validate_file_path(server_config['blackmarket_trader_zone_path'], f"Server '{server_id}' trader zone file")
            
            # Validate Discord webhook URL
            if 'discord_webhook_url' in server_config:
                self._validate_discord_webhook(server_config['discord_webhook_url'], f"Server '{server_id}'")
            
            # Check if server is enabled
            if server_config.get('enabled', True):
                enabled_count += 1
        
        if enabled_count == 0:
            self.warnings.append("No servers are enabled - scheduler will have nothing to do")
    
    def _validate_global_settings(self, global_settings):
        """Validate global settings"""
        # Validate Discord username
        if 'discord_username' not in global_settings:
            self.warnings.append("No discord_username specified, using default")
        elif not isinstance(global_settings['discord_username'], str):
            self.errors.append("discord_username must be a string")
        
        # Validate Discord embed color
        if 'discord_embed_color' not in global_settings:
            self.warnings.append("No discord_embed_color specified, using default")
        elif not isinstance(global_settings['discord_embed_color'], str):
            self.errors.append("discord_embed_color must be a string")
        else:
            color = global_settings['discord_embed_color']
            if not (color.startswith('0x') or color.startswith('#')):
                self.errors.append("discord_embed_color must start with '0x' or '#'")
            else:
                try:
                    int(color.replace('#', '0x'), 16)
                except ValueError:
                    self.errors.append("discord_embed_color is not a valid hex color")
    
    def _validate_scheduler_settings(self, scheduler_settings):
        """Validate scheduler settings"""
        # Validate rotation times
        if 'rotation_times' in scheduler_settings:
            if not isinstance(scheduler_settings['rotation_times'], list):
                self.errors.append("rotation_times must be a list")
            else:
                for i, time_str in enumerate(scheduler_settings['rotation_times']):
                    if not isinstance(time_str, str):
                        self.errors.append(f"rotation_times[{i}] must be a string")
                        continue
                    
                    # Validate time format (HH:MM)
                    try:
                        time_parts = time_str.split(':')
                        if len(time_parts) != 2:
                            raise ValueError()
                        
                        hour = int(time_parts[0])
                        minute = int(time_parts[1])
                        
                        if not (0 <= hour <= 23):
                            raise ValueError("Hour must be 0-23")
                        if not (0 <= minute <= 59):
                            raise ValueError("Minute must be 0-59")
                    except ValueError as e:
                        self.errors.append(f"rotation_times[{i}] '{time_str}' is not a valid time format (HH:MM): {e}")
        
        # Validate numeric settings
        numeric_settings = {
            'check_interval_seconds': (1, 3600, "Check interval must be between 1 and 3600 seconds"),
            'server_rotation_delay_seconds': (0, 300, "Server rotation delay must be between 0 and 300 seconds")
        }
        
        for setting, (min_val, max_val, error_msg) in numeric_settings.items():
            if setting in scheduler_settings:
                if not isinstance(scheduler_settings[setting], (int, float)):
                    self.errors.append(f"{setting} must be a number")
                elif not (min_val <= scheduler_settings[setting] <= max_val):
                    self.errors.append(error_msg)
        
        # Validate boolean settings
        boolean_settings = ['enabled', 'rotate_all_servers']
        for setting in boolean_settings:
            if setting in scheduler_settings and not isinstance(scheduler_settings[setting], bool):
                self.errors.append(f"{setting} must be a boolean (true/false)")
        
        # Validate log file
        if 'log_file' in scheduler_settings:
            if not isinstance(scheduler_settings['log_file'], str):
                self.errors.append("log_file must be a string")
            elif not scheduler_settings['log_file'].strip():
                self.errors.append("log_file cannot be empty")
    
    def _validate_positions(self, positions):
        """Validate position configurations"""
        if not positions:
            self.errors.append("At least one position must be configured")
            return
        
        if not isinstance(positions, list):
            self.errors.append("positions must be a list")
            return
        
        # Check if any position has vehicle data to determine if vehicles are used
        has_vehicle_data = any(
            'Blackmarket_Vehicle_Classname' in pos or 'Blackmarket_Vehicle_Coordinates' in pos 
            for pos in positions if isinstance(pos, dict)
        )
        
        # If any position has vehicle data, all positions must have complete vehicle data
        vehicle_required = has_vehicle_data
        
        for i, position in enumerate(positions):
            if not isinstance(position, dict):
                self.errors.append(f"Position {i} must be an object")
                continue
            
            # Required fields for vending machine (always required)
            required_fields = [
                'name',
                'Blackmarket_Vending_Classname',
                'Blackmarket_Vending_Coordinates'
            ]
            
            # Add vehicle fields if any position uses vehicles
            if vehicle_required:
                required_fields.extend([
                    'Blackmarket_Vehicle_Classname',
                    'Blackmarket_Vehicle_Coordinates'
                ])
            
            for field in required_fields:
                if field not in position:
                    self.errors.append(f"Position {i} ('{position.get('name', 'unnamed')}') missing required field: '{field}'")
            
            # Validate coordinates (vending always required)
            coord_fields = ['Blackmarket_Vending_Coordinates']
            if vehicle_required:
                coord_fields.append('Blackmarket_Vehicle_Coordinates')
                
            for field in coord_fields:
                if field in position:
                    self._validate_coordinates(position[field], f"Position {i} {field}")
            
            # Validate rotation fields (optional)
            rotation_fields = ['Blackmarket_Vending_Rotation']
            if vehicle_required:
                rotation_fields.append('Blackmarket_Vehicle_Rotation')
                
            for field in rotation_fields:
                if field in position:
                    self._validate_coordinates(position[field], f"Position {i} {field}")
            
            # Validate classnames
            classname_fields = ['Blackmarket_Vending_Classname']
            if vehicle_required:
                classname_fields.append('Blackmarket_Vehicle_Classname')
                
            for field in classname_fields:
                if field in position:
                    if not isinstance(position[field], str) or not position[field].strip():
                        self.errors.append(f"Position {i} {field} must be a non-empty string")
            
            # Validate image path (optional)
            if 'img_path' in position:
                if not isinstance(position['img_path'], str):
                    self.errors.append(f"Position {i} img_path must be a string")
                elif position['img_path'] and not os.path.exists(position['img_path']):
                    self.warnings.append(f"Position {i} image file not found: {position['img_path']}")
        
        # Log whether vehicles are enabled
        if not has_vehicle_data:
            self.warnings.append("No vehicle trader data found in positions - vehicle trader functionality will be disabled")
    
    def _validate_coordinates(self, coords, field_name):
        """Validate coordinate arrays"""
        if not isinstance(coords, list):
            self.errors.append(f"{field_name} must be a list")
            return
        
        if len(coords) != 3:
            self.errors.append(f"{field_name} must have exactly 3 values [X, Y, Z]")
            return
        
        for i, coord in enumerate(coords):
            if not isinstance(coord, (int, float)):
                self.errors.append(f"{field_name}[{i}] must be a number")
    
    def _validate_file_path(self, path, description):
        """Validate file paths"""
        if not isinstance(path, str):
            self.errors.append(f"{description} path must be a string")
            return
        
        if not path.strip():
            self.errors.append(f"{description} path cannot be empty")
            return
        
        # Check if directory exists (file might not exist yet)
        directory = os.path.dirname(path)
        if directory and not os.path.exists(directory):
            self.warnings.append(f"{description} directory does not exist: {directory}")
    
    def _validate_discord_webhook(self, webhook_url, description):
        """Validate Discord webhook URLs"""
        if not isinstance(webhook_url, str):
            self.errors.append(f"{description} Discord webhook URL must be a string")
            return
        
        if not webhook_url.strip():
            self.warnings.append(f"{description} has empty Discord webhook URL - notifications will be disabled")
            return
        
        try:
            parsed = urlparse(webhook_url)
            if not parsed.scheme or not parsed.netloc:
                raise ValueError("Invalid URL format")
            
            if 'discord.com' not in parsed.netloc and 'discordapp.com' not in parsed.netloc:
                self.warnings.append(f"{description} webhook URL doesn't appear to be a Discord URL")
            
            if '/api/webhooks/' not in webhook_url:
                self.warnings.append(f"{description} URL doesn't appear to be a webhook URL")
                
        except Exception as e:
            self.errors.append(f"{description} webhook URL is invalid: {e}")

# ============================================================================
# BLACK MARKET ROTATOR
# ============================================================================

class BlackmarketRotator:
    def __init__(self, config_path='./config.json', server_id=None):
        # Load configuration
        self.config = self.load_config(config_path)
        self.server_id = server_id
        
        # If no server specified, use the first enabled server
        if not server_id:
            enabled_servers = [sid for sid, sconfig in self.config['servers'].items() if sconfig.get('enabled', True)]
            if not enabled_servers:
                raise ValueError("No enabled servers found in configuration!")
            self.server_id = enabled_servers[0]
            print(f"No server specified, using: {self.server_id}")
        
        # Validate server exists
        if self.server_id not in self.config['servers']:
            available_servers = list(self.config['servers'].keys())
            raise ValueError(f"Server '{self.server_id}' not found. Available servers: {available_servers}")
        
        self.server_config = self.config['servers'][self.server_id]
        self.server_name = self.server_config['name']
        
        # Set up paths from config
        self.blackmarket_map_path = self.server_config['blackmarket_map_path']
        self.blackmarket_trader_zone_path = self.server_config['blackmarket_trader_zone_path']
        self.discord_webhook_url = self.server_config['discord_webhook_url']
        
        # Load positions from config
        self.positions = self.config.get('positions', [])
        
        # Check if vehicles are enabled based on position data
        self.vehicles_enabled = self.check_vehicles_enabled()
        if not self.vehicles_enabled:
            print("🚗 Vehicle trader functionality disabled - no vehicle data found in positions")
        
        self.current_index = self.get_current_position_from_map()
    
    def check_vehicles_enabled(self):
        """Check if any position has vehicle data to determine if vehicles are enabled"""
        return any(
            'Blackmarket_Vehicle_Classname' in pos or 'Blackmarket_Vehicle_Coordinates' in pos 
            for pos in self.positions if isinstance(pos, dict)
        )
    
    def load_config(self, config_path):
        """Load and validate configuration from JSON file"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
        except FileNotFoundError:
            print(f"Error: Configuration file {config_path} not found!")
            raise
        except json.JSONDecodeError as e:
            print(f"Error: Invalid JSON in {config_path}: {e}")
            raise
        
        # Validate configuration
        validator = ConfigValidator()
        try:
            validator.validate_config(config)
            print("✅ Configuration validation passed")
        except ValueError as e:
            print(f"❌ Configuration validation failed:")
            print(str(e))
            raise
        
        return config
    
    def get_current_position_from_map(self):
        """Determine current position by reading coordinates from map file"""
        try:
            with open(self.blackmarket_map_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            # Find the vending machine line
            current_coords = None
            for line in lines:
                if '.Blackmarket|' in line and not '.Blackmarket_Vehicles|' in line:
                    # Extract coordinates from map line format: "classname.Blackmarket|X Y Z|rotation"
                    parts = line.strip().split('|')
                    if len(parts) >= 2:
                        coord_parts = parts[1].split()
                        if len(coord_parts) >= 3:
                            current_coords = [float(coord_parts[0]), float(coord_parts[1]), float(coord_parts[2])]
                            break
            
            if not current_coords:
                print("No blackmarket coordinates found in map file, starting from position 0")
                return 0
            
            # Match coordinates to position index
            for i, position in enumerate(self.positions):
                pos_coords = position['Blackmarket_Vending_Coordinates']
                # Check if coordinates match (with small tolerance for floating point differences)
                if (abs(current_coords[0] - pos_coords[0]) < 0.1 and 
                    abs(current_coords[1] - pos_coords[1]) < 0.1 and 
                    abs(current_coords[2] - pos_coords[2]) < 0.1):
                    print(f"Current position detected: {position['name']} (index {i})")
                    return i
            
            print(f"Current coordinates {current_coords} don't match any configured position, starting from position 0")
            return 0
            
        except FileNotFoundError:
            print(f"Map file not found: {self.blackmarket_map_path}, starting from position 0")
            return 0
        except Exception as e:
            print(f"Error reading map file: {e}, starting from position 0")
            return 0
    
    def get_next_position(self):
        """Get the next position in rotation"""
        if not self.positions:
            return None
        
        # Move to next position (rotate back to 0 if at end)
        next_index = (self.current_index + 1) % len(self.positions)
        
        return self.positions[next_index]
    
    def update_map_file(self, position):
        """Update existing .map file with new coordinates"""
        vending_coords = position['Blackmarket_Vending_Coordinates']
        vending_classname = position['Blackmarket_Vending_Classname']
        
        # Get rotation if available, otherwise use default
        vending_rotation = position.get('Blackmarket_Vending_Rotation', [0.0, 0.0, 0.0])
        
        # Format the vending machine line
        new_vending_line = f"{vending_classname}.Blackmarket|{vending_coords[0]} {vending_coords[1]} {vending_coords[2]}|{vending_rotation[0]} {vending_rotation[1]} {vending_rotation[2]}"
        
        # Prepare vehicle line if vehicles are enabled
        new_vehicle_line = None
        if self.vehicles_enabled:
            vehicle_coords = position['Blackmarket_Vehicle_Coordinates']
            vehicle_classname = position['Blackmarket_Vehicle_Classname']
            vehicle_rotation = position.get('Blackmarket_Vehicle_Rotation', [0.0, 0.0, 0.0])
            new_vehicle_line = f"{vehicle_classname}.Blackmarket_Vehicles|{vehicle_coords[0]} {vehicle_coords[1]} {vehicle_coords[2]}|{vehicle_rotation[0]} {vehicle_rotation[1]} {vehicle_rotation[2]}"
        
        # Read existing map file
        with open(self.blackmarket_map_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # Remove trailing newlines and whitespace
        lines = [line.rstrip() for line in lines]
        
        # Find and update blackmarket lines
        updated_lines = []
        vending_updated = False
        vehicle_updated = False
        
        for line in lines:
            if line.strip():  # Skip empty lines
                if '.Blackmarket|' in line and not '.Blackmarket_Vehicles|' in line:
                    # This is a vending machine line
                    updated_lines.append(new_vending_line)
                    vending_updated = True
                    print(f"Updated vending line: {new_vending_line}")
                elif '.Blackmarket_Vehicles|' in line:
                    # This is a vehicle trader line
                    if self.vehicles_enabled and new_vehicle_line:
                        updated_lines.append(new_vehicle_line)
                        vehicle_updated = True
                        print(f"Updated vehicle line: {new_vehicle_line}")
                    else:
                        # Remove vehicle line if vehicles are disabled
                        print(f"Removed vehicle line (vehicles disabled): {line}")
                else:
                    # Keep other lines unchanged
                    updated_lines.append(line)
        
        # Add lines if they weren't found in the file
        if not vending_updated:
            updated_lines.append(new_vending_line)
            print(f"Added new vending line: {new_vending_line}")
        
        if self.vehicles_enabled and not vehicle_updated and new_vehicle_line:
            updated_lines.append(new_vehicle_line)
            print(f"Added new vehicle line: {new_vehicle_line}")
        
        # Join lines with newlines
        map_content = '\n'.join(updated_lines) + '\n'
        
        return map_content
    
    def update_trader_zone_file(self, position):
        """Update coordinates in existing trader zone JSON file"""
        vending_coords = position['Blackmarket_Vending_Coordinates']
        
        # Read existing trader zone file
        with open(self.blackmarket_trader_zone_path, 'r', encoding='utf-8') as f:
            trader_zone = json.load(f)
        
        # Update only the position coordinates
        old_coords = trader_zone.get('Position', [0, 0, 0])
        trader_zone['Position'] = vending_coords
        
        print(f"Updated trader zone coordinates:")
        print(f"  Old: {old_coords}")
        print(f"  New: {vending_coords}")
        
        # Preserve all other settings (Stock, BuyPricePercent, etc.)
        return trader_zone
    
    def update_files(self, position):
        """Update the blackmarket files with new position"""
        try:
            # Update map file
            map_content = self.update_map_file(position)
            os.makedirs(os.path.dirname(self.blackmarket_map_path), exist_ok=True)
            with open(self.blackmarket_map_path, 'w', encoding='utf-8') as f:
                f.write(map_content)
            print(f"Updated map file: {self.blackmarket_map_path}")
            
            # Update trader zone file
            trader_zone = self.update_trader_zone_file(position)
            os.makedirs(os.path.dirname(self.blackmarket_trader_zone_path), exist_ok=True)
            with open(self.blackmarket_trader_zone_path, 'w', encoding='utf-8') as f:
                json.dump(trader_zone, f, indent=4)
            print(f"Updated trader zone file: {self.blackmarket_trader_zone_path}")
            
            return True
        except Exception as e:
            print(f"Error updating files: {e}")
            return False
    
    def send_discord_notification(self, position):
        """Send Discord webhook notification with image attachment"""
        if not self.discord_webhook_url:
            print("No Discord webhook URL configured")
            return
        
        coords = position['Blackmarket_Vending_Coordinates']
        
        embed_color = int(self.config['global_settings']['discord_embed_color'], 16)
        
        embed = {
            "title": f"🔄 {self.server_name} - Black Market Rotated!",
            "description": f"The Black Market has moved to **{position['name']}**!",
            "color": embed_color,
            "fields": [
                {
                    "name": "🗺️ Coordinates",
                    "value": f"X: {coords[0]:.1f}\nY: {coords[1]:.1f}\nZ: {coords[2]:.1f}",
                    "inline": True
                }
            ],
            "timestamp": datetime.now().isoformat()
        }
        
        # Check if image exists and attach it
        img_path = position.get('img_path')
        files = None
        
        if img_path and os.path.exists(img_path):
            try:
                # Read the image file
                with open(img_path, 'rb') as f:
                    image_data = f.read()
                
                # Get the filename for the attachment
                filename = os.path.basename(img_path)
                
                # Set up the attachment
                files = {
                    'file': (filename, image_data, 'image/png')
                }
                
                # Reference the attachment in the embed
                embed["image"] = {"url": f"attachment://{filename}"}
                
                print(f"Attaching image: {img_path}")
                
            except Exception as e:
                print(f"Warning: Could not attach image {img_path}: {e}")
        elif img_path:
            print(f"Warning: Image file not found: {img_path}")
        
        payload = {
            "embeds": [embed],
            "username": self.config['global_settings']['discord_username']
        }
        
        try:
            if files:
                # Send with file attachment
                response = requests.post(
                    self.discord_webhook_url, 
                    data={"payload_json": json.dumps(payload)},
                    files=files
                )
            else:
                # Send without file attachment
                response = requests.post(self.discord_webhook_url, json=payload)
            
            if response.status_code == 204:
                print("Discord notification sent successfully!")
            else:
                print(f"Failed to send Discord notification: {response.status_code}")
                print(f"Response: {response.text}")
        except Exception as e:
            print(f"Error sending Discord notification: {e}")
    
    def rotate(self):
        """Main method to rotate blackmarket to next position"""
        if not self.positions:
            print("No positions available for rotation!")
            return False
        
        if len(self.positions) == 1:
            print("Only one position available, no rotation needed")
            return True
        
        # Get next position
        next_position = self.get_next_position()
        if not next_position:
            print("Failed to get next position")
            return False
        
        print(f"[{self.server_name}] Rotating blackmarket to: {next_position['name']}")
        print(f"[{self.server_name}] Position {self.current_index + 1} of {len(self.positions)}")
        
        # Update files
        if not self.update_files(next_position):
            print("Failed to update files")
            return False
        
        # Send Discord notification
        self.send_discord_notification(next_position)
        
        print("Blackmarket rotation completed successfully!")
        return True
    
    def get_current_position_info(self):
        """Get information about current position"""
        if not self.positions:
            return None
        
        current_pos = self.positions[self.current_index]
        return {
            "position": current_pos,
            "index": self.current_index,
            "total": len(self.positions)
        }

# ============================================================================
# MULTI-SERVER FUNCTIONS
# ============================================================================

def rotate_server(server_id, config_path='./config.json'):
    """Rotate blackmarket for a specific server"""
    try:
        rotator = BlackmarketRotator(config_path, server_id)
        
        # Show current position info
        current_info = rotator.get_current_position_info()
        if current_info:
            print(f"[{rotator.server_name}] Current position: {current_info['position']['name']} ({current_info['index'] + 1}/{current_info['total']})")
        
        # Perform rotation
        success = rotator.rotate()
        
        if success:
            print(f"[{rotator.server_name}] Rotation completed successfully!")
            return True
        else:
            print(f"[{rotator.server_name}] Rotation failed!")
            return False
            
    except Exception as e:
        print(f"Error rotating server '{server_id}': {e}")
        return False

def rotate_all_servers(config_path='./config.json'):
    """Rotate blackmarket for all enabled servers"""
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
    except Exception as e:
        print(f"Error loading config: {e}")
        return False
    
    enabled_servers = [sid for sid, sconfig in config['servers'].items() if sconfig.get('enabled', True)]
    
    if not enabled_servers:
        print("No enabled servers found!")
        return False
    
    print(f"Rotating blackmarket for {len(enabled_servers)} servers...")
    
    success_count = 0
    delay = config['scheduler_settings'].get('server_rotation_delay_seconds', 5)
    
    for i, server_id in enumerate(enabled_servers):
        if i > 0:
            print(f"Waiting {delay} seconds before next server...")
            time.sleep(delay)
        
        if rotate_server(server_id, config_path):
            success_count += 1
    
    print(f"Multi-Server Rotation Complete: {success_count}/{len(enabled_servers)} servers")
    print("Don't forget to restart your DayZ servers for changes to take effect.")
    
    return success_count == len(enabled_servers)

def list_servers(config_path='./config.json'):
    """List all configured servers"""
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
    except Exception as e:
        print(f"Error loading config: {e}")
        return
    
    print("Configured servers:")
    for server_id, server_config in config['servers'].items():
        status = "✅ Enabled" if server_config.get('enabled', True) else "❌ Disabled"
        print(f"  {server_id}: {server_config['name']} - {status}")

# ============================================================================
# SCHEDULER FUNCTIONALITY
# ============================================================================

def load_scheduler_config(config_path='./config.json'):
    """Load and validate configuration for scheduler"""
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
    except FileNotFoundError:
        print(f"Error: Configuration file {config_path} not found!")
        raise
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in {config_path}: {e}")
        raise
    
    # Validate configuration
    validator = ConfigValidator()
    try:
        validator.validate_config(config)
        logging.info("✅ Configuration validation passed")
    except ValueError as e:
        logging.error(f"❌ Configuration validation failed:")
        logging.error(str(e))
        raise
    
    return config

def run_rotation(config):
    """Run the blackmarket rotation"""
    try:
        logging.info("Starting scheduled blackmarket rotation...")
        
        if config['scheduler_settings'].get('rotate_all_servers', True):
            # Rotate all enabled servers
            success = rotate_all_servers('./config.json')
            if success:
                logging.info("Multi-server rotation completed successfully!")
                logging.info("Don't forget to restart your DayZ servers for changes to take effect.")
            else:
                logging.error("Multi-server rotation failed!")
        else:
            # Rotate only the first enabled server (legacy behavior)
            enabled_servers = [sid for sid, sconfig in config['servers'].items() if sconfig.get('enabled', True)]
            if enabled_servers:
                server_id = enabled_servers[0]
                success = rotate_server(server_id, './config.json')
                if success:
                    logging.info(f"Rotation completed successfully for server: {server_id}")
                    logging.info("Don't forget to restart your DayZ server for changes to take effect.")
                else:
                    logging.error(f"Rotation failed for server: {server_id}")
            else:
                logging.error("No enabled servers found!")
                
    except Exception as e:
        logging.error(f"Error during rotation: {e}")

def run_scheduler():
    """Run the automated scheduler"""
    # Load configuration
    config = load_scheduler_config()
    
    if not config['scheduler_settings']['enabled']:
        logging.info("Scheduler is disabled in configuration")
        return
    
    rotation_times = config['scheduler_settings']['rotation_times']
    check_interval = config['scheduler_settings']['check_interval_seconds']
    
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(config['scheduler_settings']['log_file']),
            logging.StreamHandler()
        ]
    )
    
    logging.info("Starting Blackmarket Rotation Scheduler...")
    logging.info(f"Scheduled times: {', '.join(rotation_times)}")
    
    # Schedule the rotations at configured times
    for time_str in rotation_times:
        schedule.every().day.at(time_str).do(run_rotation, config)
        logging.info(f"Scheduled rotation at {time_str}")
    
    logging.info("Scheduler started. Waiting for scheduled times...")
    
    # Keep the script running
    while True:
        try:
            schedule.run_pending()
            time.sleep(check_interval)
        except KeyboardInterrupt:
            logging.info("Scheduler stopped by user")
            break
        except Exception as e:
            logging.error(f"Scheduler error: {e}")
            time.sleep(check_interval)

# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description='DayZ Blackmarket Rotator - Complete Solution',
        epilog='''
Examples:
  %(prog)s                          # Rotate all enabled servers
  %(prog)s --server server1         # Rotate specific server
  %(prog)s --list                   # List all configured servers  
  %(prog)s --scheduler              # Run automated scheduler
  %(prog)s --config custom.json     # Use custom config file
        ''',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument('--server', '-s', help='Specific server ID to rotate (default: rotate all enabled servers)')
    parser.add_argument('--list', '-l', action='store_true', help='List all configured servers')
    parser.add_argument('--scheduler', action='store_true', help='Run automated scheduler')
    parser.add_argument('--config', '-c', default='./config.json', help='Path to config file (default: ./config.json)')
    parser.add_argument('--version', '-v', action='version', version='DayZ Blackmarket Rotator v2.0.0')
    
    args = parser.parse_args()
    
    if args.list:
        list_servers(args.config)
        return 0
    
    if args.scheduler:
        run_scheduler()
        return 0
    
    if args.server:
        # Rotate specific server
        success = rotate_server(args.server, args.config)
        if success:
            print("Don't forget to restart your DayZ server for changes to take effect.")
            return 0
        else:
            return 1
    else:
        # Rotate all enabled servers
        success = rotate_all_servers(args.config)
        return 0 if success else 1

if __name__ == "__main__":
    exit(main())
