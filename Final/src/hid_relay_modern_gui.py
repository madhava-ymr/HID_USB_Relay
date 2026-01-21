"""
HID USB Relay Control Dashboard - Modern GUI
Single file application with embedded relay control functionality
Developed by Madhava Reddy Yeruva
"""

import tkinter as tk
from tkinter import ttk, messagebox
import os
import sys
import platform
import subprocess
import threading
import time
from typing import Optional, List, Tuple


def get_resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller"""
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


class HIDRelayController:
    """Controller for HID USB Relay device"""
    
    def __init__(self):
        self.relay_executable = self.get_relay_executable()
        self.relay_count = 0
        self.device_id = None
        
    @staticmethod
    def get_platform_and_architecture() -> Tuple[str, str]:
        """Get the current system platform and architecture"""
        return platform.system().lower(), platform.architecture()[0].lower()
    
    def get_relay_executable(self) -> str:
        """Get the path to the relay command-line executable"""
        system, arch = self.get_platform_and_architecture()
        exe_name = "hidusb-relay-cmd.exe" if system == 'windows' else "hidusb-relay-cmd"
        
        # First, try PyInstaller bundled path
        bundled_path = get_resource_path(exe_name)
        if os.path.exists(bundled_path):
            print(f"Found bundled executable at: {bundled_path}")
            return bundled_path
        
        # Search in multiple locations
        search_paths = [
            # Same directory as script
            os.path.join(os.path.dirname(os.path.abspath(__file__)), exe_name),
            # Current working directory
            os.path.join(os.getcwd(), exe_name),
            # Just the executable name (will search in PATH)
            exe_name
        ]
        
        for exe_path in search_paths:
            if os.path.exists(exe_path):
                print(f"Found executable at: {exe_path}")
                return exe_path
        
        # If not found in specific paths, return just the name to try PATH
        print(f"Executable not found in local paths, will try system PATH: {exe_name}")
        return exe_name
    
    def run_command(self, command: List[str]) -> Optional[str]:
        """Run a command using subprocess and return its output"""
        try:
            print(f"Executing command: {' '.join(command)}")
            process = subprocess.run(
                command, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE, 
                universal_newlines=True,
                timeout=10
            )
            print(f"Return code: {process.returncode}")
            print(f"Output: {process.stdout.strip()}")
            if process.stderr:
                print(f"Error output: {process.stderr.strip()}")
            
            if process.returncode == 0:
                return process.stdout.strip()
            return None
        except FileNotFoundError:
            print(f"Error: Executable not found at {command[0]}")
            return None
        except subprocess.TimeoutExpired:
            print("Error: Command timeout")
            return None
        except Exception as e:
            print(f"Error executing command: {e}")
            return None
    
    def enumerate_devices(self) -> Optional[str]:
        """Get list of all connected relay devices"""
        return self.run_command([self.relay_executable, "ENUM"])
    
    def get_device_state(self) -> Optional[List[str]]:
        """Get the status of the relay device"""
        if self.device_id:
            output = self.run_command([self.relay_executable, f"id={self.device_id}", "STATUS"])
        else:
            output = self.run_command([self.relay_executable, "STATUS"])
        
        if output:
            # Parse output like "Device status: 1=OFF 2=OFF 3=OFF 4=OFF"
            status_part = output.split(':')[-1].strip()
            return status_part.split(' ')
        return None
    
    def set_relay_state(self, relay_number: str, state: str) -> bool:
        """Set the state of a specific relay (ON/OFF)"""
        if self.device_id:
            result = self.run_command([
                self.relay_executable, 
                f"id={self.device_id}", 
                state, 
                relay_number
            ])
        else:
            result = self.run_command([self.relay_executable, state, relay_number])
        return result is not None
    
    def set_all_relays(self, state: str) -> bool:
        """Set all relays to the same state (ON/OFF)"""
        if self.device_id:
            result = self.run_command([
                self.relay_executable, 
                f"id={self.device_id}", 
                state, 
                "ALL"
            ])
        else:
            result = self.run_command([self.relay_executable, state, "ALL"])
        return result is not None
    
    def detect_relay_count(self) -> int:
        """Detect how many relays are on the device"""
        states = self.get_device_state()
        return len(states) if states else 0


class ModernHIDRelayGUI:
    """Modern GUI for HID USB Relay Control"""
    
    # Modern color palette
    COLORS = {
        'bg': '#f0f2f5',
        'sidebar': '#2c3e50',
        'sidebar_hover': '#34495e',
        'card_bg': '#ffffff',
        'border': '#e1e8ed',
        'primary': '#3498db',
        'primary_dark': '#2980b9',
        'success': '#27ae60',
        'success_dark': '#229954',
        'danger': '#e74c3c',
        'danger_dark': '#c0392b',
        'warning': '#f39c12',
        'text_dark': '#2c3e50',
        'text_light': '#7f8c8d',
        'text_white': '#ffffff',
        'relay_on_bg': '#d5f4e6',
        'relay_on_border': '#27ae60',
        'relay_off_bg': '#fadbd8',
        'relay_off_border': '#e74c3c',
        'shadow': '#bdc3c7',
    }
    
    def __init__(self, root):
        self.root = root
        self.root.title("HID USB Relay Control - Modern")
        self.root.geometry("1100x700")
        self.root.configure(bg=self.COLORS['bg'])
        
        self.controller = HIDRelayController()
        self.relay_states = {}
        self.relay_cards = {}
        self.is_connected = False
        self.status_update_running = False
        self.relay_count = 0
        self.console_text = None
        
        self.setup_ui()
        self.log_console("Application started. Ready to detect device.")
    
    def log_console(self, message):
        """Log message to console with timestamp"""
        if self.console_text:
            import datetime
            timestamp = datetime.datetime.now().strftime("%H:%M:%S")
            self.console_text.insert(tk.END, f"[{timestamp}] {message}\n")
            self.console_text.see(tk.END)
            self.console_text.update()
        print(message)
    
    def clear_console(self):
        """Clear console log"""
        if self.console_text:
            self.console_text.delete(1.0, tk.END)
            self.log_console("Console cleared.")
        
    def setup_ui(self):
        """Setup the modern GUI layout"""
        
        # Main container
        main_container = tk.Frame(self.root, bg=self.COLORS['bg'])
        main_container.pack(fill=tk.BOTH, expand=True)
        
        # Left Sidebar
        self.create_sidebar(main_container)
        
        # Right Content Area
        self.create_content_area(main_container)
        
    def create_sidebar(self, parent):
        """Create left sidebar with connection settings"""
        sidebar = tk.Frame(parent, bg=self.COLORS['sidebar'], width=300)
        sidebar.pack(side=tk.LEFT, fill=tk.Y)
        sidebar.pack_propagate(False)
        
        # Logo/Title area
        title_frame = tk.Frame(sidebar, bg=self.COLORS['sidebar'])
        title_frame.pack(pady=30)
        
        tk.Label(
            title_frame,
            text="⚡",
            font=('Arial', 45),
            bg=self.COLORS['sidebar'],
            fg=self.COLORS['warning']
        ).pack()
        
        tk.Label(
            title_frame,
            text="HID USB Relay",
            font=('Arial', 20, 'bold'),
            bg=self.COLORS['sidebar'],
            fg=self.COLORS['text_white']
        ).pack()
        
        tk.Label(
            title_frame,
            text="Control Dashboard",
            font=('Arial', 11),
            bg=self.COLORS['sidebar'],
            fg=self.COLORS['text_light']
        ).pack()
        
        tk.Label(
            title_frame,
            text="by Madhava Reddy Yeruva",
            font=('Arial', 9),
            bg=self.COLORS['sidebar'],
            fg=self.COLORS['text_light']
        ).pack(pady=(10, 0))
        
        # Separator
        tk.Frame(sidebar, bg=self.COLORS['border'], height=1).pack(fill=tk.X, padx=20, pady=25)
        
        # Connection section
        conn_section = tk.Frame(sidebar, bg=self.COLORS['sidebar'])
        conn_section.pack(fill=tk.X, padx=20)
        
        tk.Label(
            conn_section,
            text="DEVICE CONNECTION",
            font=('Arial', 9, 'bold'),
            bg=self.COLORS['sidebar'],
            fg=self.COLORS['text_light']
        ).pack(anchor='w', pady=(0, 15))
        
        # Status indicator frame
        status_frame = tk.Frame(conn_section, bg=self.COLORS['sidebar_hover'], relief=tk.FLAT)
        status_frame.pack(fill=tk.X, pady=(0, 15))
        
        self.status_indicator = tk.Label(
            status_frame,
            text="●",
            font=('Arial', 18),
            bg=self.COLORS['sidebar_hover'],
            fg=self.COLORS['text_light']
        )
        self.status_indicator.pack(side=tk.LEFT, padx=(12, 8), pady=12)
        
        status_text_frame = tk.Frame(status_frame, bg=self.COLORS['sidebar_hover'])
        status_text_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, pady=12)
        
        self.status_text = tk.Label(
            status_text_frame,
            text="Disconnected",
            font=('Arial', 11, 'bold'),
            bg=self.COLORS['sidebar_hover'],
            fg=self.COLORS['text_white'],
            anchor='w'
        )
        self.status_text.pack(anchor='w')
        
        self.relay_count_label = tk.Label(
            status_text_frame,
            text="No device detected",
            font=('Arial', 9),
            bg=self.COLORS['sidebar_hover'],
            fg=self.COLORS['text_light'],
            anchor='w'
        )
        self.relay_count_label.pack(anchor='w')
        
        # Detect button
        self.detect_btn = tk.Button(
            conn_section,
            text="🔍 Detect Device",
            command=self.detect_device,
            font=('Arial', 11, 'bold'),
            bg=self.COLORS['primary'],
            fg=self.COLORS['text_white'],
            activebackground=self.COLORS['primary_dark'],
            activeforeground=self.COLORS['text_white'],
            relief=tk.FLAT,
            cursor='hand2',
            height=2,
            bd=0
        )
        self.detect_btn.pack(fill=tk.X, pady=(0, 10))
        
        # Connect button
        self.connect_btn = tk.Button(
            conn_section,
            text="Connect",
            command=self.toggle_connection,
            font=('Arial', 11, 'bold'),
            bg=self.COLORS['success'],
            fg=self.COLORS['text_white'],
            activebackground=self.COLORS['success_dark'],
            activeforeground=self.COLORS['text_white'],
            relief=tk.FLAT,
            cursor='hand2',
            height=2,
            bd=0,
            state=tk.DISABLED
        )
        self.connect_btn.pack(fill=tk.X)
        
        # Quick Actions section
        tk.Frame(sidebar, bg=self.COLORS['border'], height=1).pack(fill=tk.X, padx=20, pady=25)
        
        control_section = tk.Frame(sidebar, bg=self.COLORS['sidebar'])
        control_section.pack(fill=tk.X, padx=20)
        
        tk.Label(
            control_section,
            text="QUICK ACTIONS",
            font=('Arial', 9, 'bold'),
            bg=self.COLORS['sidebar'],
            fg=self.COLORS['text_light']
        ).pack(anchor='w', pady=(0, 15))
        
        self.all_on_btn = tk.Button(
            control_section,
            text="⚡ Turn All ON",
            command=self.turn_all_on,
            font=('Arial', 11, 'bold'),
            bg=self.COLORS['success'],
            fg=self.COLORS['text_white'],
            activebackground=self.COLORS['success_dark'],
            relief=tk.FLAT,
            cursor='hand2',
            height=2,
            bd=0,
            state=tk.DISABLED
        )
        self.all_on_btn.pack(fill=tk.X, pady=(0, 10))
        
        self.all_off_btn = tk.Button(
            control_section,
            text="✖ Turn All OFF",
            command=self.turn_all_off,
            font=('Arial', 11, 'bold'),
            bg=self.COLORS['danger'],
            fg=self.COLORS['text_white'],
            activebackground=self.COLORS['danger_dark'],
            relief=tk.FLAT,
            cursor='hand2',
            height=2,
            bd=0,
            state=tk.DISABLED
        )
        self.all_off_btn.pack(fill=tk.X)
        
        # Device info at bottom
        tk.Frame(sidebar, bg=self.COLORS['border'], height=1).pack(fill=tk.X, padx=20, pady=25)
        
        info_frame = tk.Frame(sidebar, bg=self.COLORS['sidebar'])
        info_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=20, pady=20)
        
        tk.Label(
            info_frame,
            text="💡 HID USB Relay",
            font=('Arial', 9),
            bg=self.COLORS['sidebar'],
            fg=self.COLORS['text_light']
        ).pack()
        
        tk.Label(
            info_frame,
            text="Version 1.0",
            font=('Arial', 8),
            bg=self.COLORS['sidebar'],
            fg=self.COLORS['text_light']
        ).pack()
        
    def create_content_area(self, parent):
        """Create right content area with relay controls"""
        content = tk.Frame(parent, bg=self.COLORS['bg'])
        content.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        # Header
        header = tk.Frame(content, bg=self.COLORS['bg'])
        header.pack(fill=tk.X, padx=35, pady=25)
        
        tk.Label(
            header,
            text="Relay Channels",
            font=('Arial', 24, 'bold'),
            bg=self.COLORS['bg'],
            fg=self.COLORS['text_dark']
        ).pack(anchor='w')
        
        tk.Label(
            header,
            text="Control individual relay channels on your HID USB device",
            font=('Arial', 11),
            bg=self.COLORS['bg'],
            fg=self.COLORS['text_light']
        ).pack(anchor='w', pady=(5, 0))
        
        # Relay cards container with scrollbar
        cards_frame = tk.Frame(content, bg=self.COLORS['bg'])
        cards_frame.pack(fill=tk.BOTH, expand=True, padx=35, pady=(0, 25))
        
        # Canvas for scrolling
        canvas = tk.Canvas(cards_frame, bg=self.COLORS['bg'], highlightthickness=0)
        scrollbar = ttk.Scrollbar(cards_frame, orient="vertical", command=canvas.yview)
        self.cards_container = tk.Frame(canvas, bg=self.COLORS['bg'])
        
        self.cards_container.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=self.cards_container, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Initial message
        self.no_device_label = tk.Label(
            self.cards_container,
            text="No device connected\n\nClick 'Detect Device' to find your HID USB Relay",
            font=('Arial', 14),
            bg=self.COLORS['bg'],
            fg=self.COLORS['text_light'],
            justify=tk.CENTER
        )
        self.no_device_label.pack(pady=100)
        
        # Console/Log section at bottom
        console_frame = tk.Frame(content, bg=self.COLORS['card_bg'], relief=tk.FLAT)
        console_frame.pack(fill=tk.BOTH, padx=35, pady=(0, 25))
        
        # Console header
        console_header = tk.Frame(console_frame, bg=self.COLORS['card_bg'])
        console_header.pack(fill=tk.X, padx=20, pady=(15, 5))
        
        tk.Label(
            console_header,
            text="📋 Console Log",
            font=('Arial', 12, 'bold'),
            bg=self.COLORS['card_bg'],
            fg=self.COLORS['text_dark']
        ).pack(side=tk.LEFT)
        
        clear_btn = tk.Button(
            console_header,
            text="Clear",
            command=self.clear_console,
            font=('Arial', 9),
            bg=self.COLORS['text_light'],
            fg=self.COLORS['text_white'],
            activebackground=self.COLORS['text_dark'],
            relief=tk.FLAT,
            cursor='hand2',
            padx=15,
            pady=3,
            bd=0
        )
        clear_btn.pack(side=tk.RIGHT)
        
        # Console text widget
        console_text_frame = tk.Frame(console_frame, bg=self.COLORS['card_bg'])
        console_text_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 15))
        
        console_scrollbar = ttk.Scrollbar(console_text_frame)
        console_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.console_text = tk.Text(
            console_text_frame,
            height=8,
            bg='#2c3e50',
            fg='#ecf0f1',
            font=('Consolas', 9),
            wrap=tk.WORD,
            relief=tk.FLAT,
            bd=0,
            yscrollcommand=console_scrollbar.set,
            padx=10,
            pady=10
        )
        self.console_text.pack(fill=tk.BOTH, expand=True)
        console_scrollbar.config(command=self.console_text.yview)
        
    def create_relay_card(self, relay_num):
        """Create a modern card for individual relay control"""
        # Card frame with shadow
        card_outer = tk.Frame(self.cards_container, bg=self.COLORS['shadow'])
        
        card = tk.Frame(
            card_outer,
            bg=self.COLORS['card_bg'],
            relief=tk.FLAT,
            bd=0
        )
        card.pack(padx=2, pady=2, fill=tk.BOTH, expand=True)
        
        # Left side - Info
        left_frame = tk.Frame(card, bg=self.COLORS['card_bg'])
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=30, pady=25)
        
        # Relay number and name
        name_frame = tk.Frame(left_frame, bg=self.COLORS['card_bg'])
        name_frame.pack(anchor='w')
        
        tk.Label(
            name_frame,
            text=f"Relay {relay_num}",
            font=('Arial', 18, 'bold'),
            bg=self.COLORS['card_bg'],
            fg=self.COLORS['text_dark']
        ).pack(side=tk.LEFT)
        
        # Status badge
        status_badge = tk.Label(
            name_frame,
            text="OFF",
            font=('Arial', 10, 'bold'),
            bg=self.COLORS['relay_off_bg'],
            fg=self.COLORS['danger'],
            padx=14,
            pady=6
        )
        status_badge.pack(side=tk.LEFT, padx=20)
        
        # Description
        tk.Label(
            left_frame,
            text=f"Channel #{relay_num} - HID USB Relay Output",
            font=('Arial', 10),
            bg=self.COLORS['card_bg'],
            fg=self.COLORS['text_light']
        ).pack(anchor='w', pady=(8, 0))
        
        # Right side - Controls
        right_frame = tk.Frame(card, bg=self.COLORS['card_bg'])
        right_frame.pack(side=tk.RIGHT, padx=30, pady=25)
        
        # Toggle button
        toggle_btn = tk.Button(
            right_frame,
            text="Turn ON",
            command=lambda: self.toggle_relay(relay_num),
            font=('Arial', 12, 'bold'),
            bg=self.COLORS['success'],
            fg=self.COLORS['text_white'],
            activebackground=self.COLORS['success_dark'],
            relief=tk.FLAT,
            cursor='hand2',
            width=14,
            height=2,
            bd=0
        )
        toggle_btn.pack()
        
        # Store references
        self.relay_cards[relay_num] = {
            'card': card_outer,
            'toggle_btn': toggle_btn,
            'status_badge': status_badge,
            'card_frame': card
        }
        
        return card_outer
        
    def detect_device(self):
        """Detect connected HID USB relay device"""
        self.log_console("Starting device detection...")
        self.detect_btn.config(state=tk.DISABLED, text="Detecting...")
        
        def detection_thread():
            # Check if executable is accessible
            exe_path = self.controller.relay_executable
            self.root.after(0, self.log_console, f"Using executable: {exe_path}")
            
            # Try to enumerate devices (will fail gracefully if exe not found)
            self.root.after(0, self.log_console, "Enumerating connected devices...")
            devices_info = self.controller.enumerate_devices()
            self.root.after(0, self.log_console, f"Device enumeration result: {devices_info if devices_info else 'None'}")
            
            if devices_info:
                # Any output means device is found, try to get relay count
                self.root.after(0, self.log_console, "Device found! Detecting relay channels...")
                self.relay_count = self.controller.detect_relay_count()
                self.root.after(0, self.log_console, f"Detected {self.relay_count} relay channels")
                
                if self.relay_count > 0:
                    self.root.after(0, self.on_device_detected)
                else:
                    # Even if we can't get count, still allow connection attempt
                    self.relay_count = 4  # Default to 4 channels
                    self.root.after(0, self.log_console, "Using default 4 channels")
                    self.root.after(0, self.on_device_detected)
            else:
                self.root.after(0, self.log_console, "ERROR: No device found")
                self.root.after(0, self.on_detection_failed, "No HID USB Relay device found.\n\nPlease ensure:\n1. Device is connected to USB\n2. Device drivers are installed\n3. 'hidusb-relay-cmd.exe' is in the same folder as this script\n4. No other program is using the device")
        
        threading.Thread(target=detection_thread, daemon=True).start()
    
    def on_device_detected(self):
        """Handle successful device detection"""
        self.detect_btn.config(state=tk.NORMAL, text="🔍 Detect Device")
        self.connect_btn.config(state=tk.NORMAL)
        self.relay_count_label.config(
            text=f"Found {self.relay_count} relay channels",
            fg=self.COLORS['success']
        )
    
    def on_detection_failed(self, error_msg):
        """Handle failed device detection"""
        self.detect_btn.config(state=tk.NORMAL, text="🔍 Detect Device")
        self.connect_btn.config(state=tk.DISABLED)
        messagebox.showerror("Detection Failed", error_msg)
    
    def toggle_connection(self):
        """Connect or disconnect from relay device"""
        if self.is_connected:
            self.disconnect()
        else:
            self.connect()
    
    def connect(self):
        """Connect to the relay device"""
        if self.relay_count == 0:
            messagebox.showerror("Error", "Please detect device first")
            return
        
        self.log_console(f"Connecting to device with {self.relay_count} channels...")
        
        try:
            # Initialize relay states
            for i in range(1, self.relay_count + 1):
                self.relay_states[i] = False
            
            # Update UI
            self.is_connected = True
            self.status_indicator.config(fg=self.COLORS['success'])
            self.status_text.config(text="Connected")
            self.connect_btn.config(
                text="Disconnect",
                bg=self.COLORS['danger'],
                activebackground=self.COLORS['danger_dark']
            )
            self.detect_btn.config(state=tk.DISABLED)
            
            # Enable controls
            self.all_on_btn.config(state=tk.NORMAL)
            self.all_off_btn.config(state=tk.NORMAL)
            
            # Remove no device label and create relay cards
            self.no_device_label.pack_forget()
            for i in range(1, self.relay_count + 1):
                card = self.create_relay_card(i)
                card.pack(fill=tk.X, pady=(0, 15))
            
            # Start status updates
            self.status_update_running = True
            threading.Thread(target=self.update_status_loop, daemon=True).start()
            
            self.log_console("✓ Successfully connected to device")
            self.log_console("Status monitoring started")
        except Exception as e:
            self.log_console(f"✗ Connection error: {str(e)}")
            messagebox.showerror("Connection Error", str(e))
    
    def disconnect(self):
        """Disconnect from relay device"""
        self.log_console("Disconnecting from device...")
        self.status_update_running = False
        self.is_connected = False
        
        # Update UI
        self.status_indicator.config(fg=self.COLORS['text_light'])
        self.status_text.config(text="Disconnected")
        self.connect_btn.config(
            text="Connect",
            bg=self.COLORS['success'],
            activebackground=self.COLORS['success_dark']
        )
        self.detect_btn.config(state=tk.NORMAL)
        
        # Disable controls
        self.all_on_btn.config(state=tk.DISABLED)
        self.all_off_btn.config(state=tk.DISABLED)
        
        # Clear relay cards
        for card_data in self.relay_cards.values():
            card_data['card'].destroy()
        self.relay_cards.clear()
        
        # Show no device label
        self.no_device_label.pack(pady=100)
    
    def toggle_relay(self, relay_num):
        """Toggle relay on/off"""
        if not self.is_connected:
            messagebox.showerror("Error", "Not connected to device")
            return
        
        current_state = self.relay_states.get(relay_num, False)
        new_state = "OFF" if current_state else "ON"
        
        self.log_console(f"Turning {new_state} relay {relay_num}...")
        if self.controller.set_relay_state(str(relay_num), new_state):
            self.relay_states[relay_num] = not current_state
            self.update_relay_ui(relay_num, not current_state)
            self.log_console(f"✓ Relay {relay_num} is now {new_state}")
        else:
            self.log_console(f"✗ Failed to toggle relay {relay_num}")
            messagebox.showerror("Error", f"Failed to toggle relay {relay_num}")
    
    def turn_all_on(self):
        """Turn on all relays"""
        self.log_console("Turning ON all relays...")
        if self.controller.set_all_relays("ON"):
            for i in range(1, self.relay_count + 1):
                self.relay_states[i] = True
                self.update_relay_ui(i, True)
            self.log_console("✓ All relays turned ON")
        else:
            self.log_console("✗ Failed to turn on all relays")
    
    def turn_all_off(self):
        """Turn off all relays"""
        self.log_console("Turning OFF all relays...")
        if self.controller.set_all_relays("OFF"):
            for i in range(1, self.relay_count + 1):
                self.relay_states[i] = False
                self.update_relay_ui(i, False)
            self.log_console("✓ All relays turned OFF")
        else:
            self.log_console("✗ Failed to turn off all relays")
    
    def update_relay_ui(self, relay_num, is_on):
        """Update UI for relay status"""
        if relay_num not in self.relay_cards:
            return
            
        card = self.relay_cards[relay_num]
        
        if is_on:
            # ON state
            card['status_badge'].config(
                text="ON",
                bg=self.COLORS['relay_on_bg'],
                fg=self.COLORS['success']
            )
            card['toggle_btn'].config(
                text="Turn OFF",
                bg=self.COLORS['danger'],
                activebackground=self.COLORS['danger_dark']
            )
            card['card_frame'].config(
                highlightbackground=self.COLORS['success'], 
                highlightthickness=3
            )
        else:
            # OFF state
            card['status_badge'].config(
                text="OFF",
                bg=self.COLORS['relay_off_bg'],
                fg=self.COLORS['danger']
            )
            card['toggle_btn'].config(
                text="Turn ON",
                bg=self.COLORS['success'],
                activebackground=self.COLORS['success_dark']
            )
            card['card_frame'].config(highlightthickness=0)
    
    def update_status_loop(self):
        """Continuously update relay status"""
        while self.status_update_running:
            if self.is_connected:
                try:
                    states = self.controller.get_device_state()
                    if states:
                        for i, state_str in enumerate(states, start=1):
                            # Parse "1=OFF" format
                            state = state_str.split('=')[-1]
                            is_on = state == "ON"
                            if i in self.relay_states and self.relay_states[i] != is_on:
                                self.relay_states[i] = is_on
                                self.root.after(0, self.update_relay_ui, i, is_on)
                except Exception:
                    pass
            time.sleep(1.5)
    
    def on_closing(self):
        """Handle window closing"""
        self.status_update_running = False
        if self.is_connected:
            self.disconnect()
        self.root.destroy()


def main():
    """Main entry point"""
    root = tk.Tk()
    app = ModernHIDRelayGUI(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()


if __name__ == "__main__":
    main()
