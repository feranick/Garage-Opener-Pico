import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import os
import sys
import tomli
import tomli_w

# --- Configuration Constants ---
CONFIG_FILENAME = "settings.toml"

# --- Sensor and Boolean Choices ---
SENSOR_CHOICES = [
    "AHT21",
    "MCP9808",
    "MAX31865",
    "BME280",
    "BME680",
    "ENS160_AHT21"
]

# Standard choices for all boolean fields
BOOLEAN_CHOICES = ["True", "False"]

# --- Default Settings Structure (Updated with new keys) ---
DEFAULT_SETTINGS = {
    'wifi': {
        'ssid': 'ssid_name',
        'password': 'password'
    },
    'web_api': {
        'instance_name': 'PicoGarageOpener',
        'api_password': 'passw0rd',
        'api_port': 205
    },
    'sonar': {
        'triggerDistance': '20'
    },
    'sensors': {
        # Sensor names are now selected from the list above
        'sensor1_name': 'BME280',
        'sensor1_pins': '10,11,8,9',
        'sensor1_correct_temp': True,
        'sensorURL': '192.168.1.206'
    },
    'database': {
        'station': 'kbos',
        'zipcode': '02139',
        'country': 'US',
        'ow_api_key': 'YOUR_API_KEY',
    },
}

class ConfigApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("LabMonitor settings.toml Editor")
        self.geometry("600x900")
        
        self.circuitpy_path = tk.StringVar(self, value="<Select CIRCUITPY Drive Path>")
        self.entries = {}
        # Using a slightly smaller default font to ensure it fits well
        self.font_style = ('Helvetica', 14)
        
        self.create_widgets()
        self.auto_detect_circuitpy()

    def create_widgets(self):
        """Builds the UI elements including path selector, actions, and config fields."""
        
        # --- Configure grid for the main 'self' window ---
        self.grid_rowconfigure(0, weight=0) # path_frame
        self.grid_rowconfigure(1, weight=0) # action_frame
        self.grid_rowconfigure(2, weight=1) # canvas_frame (expandable)
        self.grid_rowconfigure(3, weight=0) # path_footer
        self.grid_columnconfigure(0, weight=1) # All content in one column

        # 1. Path Selector Frame (Stays at top)
        path_frame = tk.Frame(self, padx=10, pady=10, relief=tk.GROOVE, bd=1)
        path_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=5)

        tk.Label(path_frame, text="CIRCUITPY Path:", font=self.font_style).pack(side=tk.LEFT, padx=5)
        tk.Entry(path_frame, textvariable=self.circuitpy_path, state='readonly', 
                 width=30, font=self.font_style).pack(side=tk.LEFT, fill='x', expand=True, padx=5)
        
        tk.Button(path_frame, text="Select Drive", command=self.select_circuitpy_path).pack(side=tk.LEFT, padx=5)

        # 2. Action Buttons Frame (Stays at top)
        action_frame = tk.Frame(self)
        action_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 10))
        
        tk.Button(action_frame, text="Load Config", command=self.load_config).pack(side=tk.LEFT, padx=(0, 5))
        
        tk.Button(action_frame, text="Save to Device", command=self.save_config).pack(side=tk.LEFT, padx=5)


        # 3. Config Fields Frame (Using a canvas for scrollability)
        canvas_frame = tk.Frame(self)
        canvas_frame.grid(row=2, column=0, sticky="nsew", padx=10, pady=(0, 10))
        canvas_frame.grid_rowconfigure(0, weight=1)
        canvas_frame.grid_columnconfigure(0, weight=1)
        canvas_frame.grid_columnconfigure(1, weight=0)

        canvas = tk.Canvas(canvas_frame)
        scrollbar = tk.Scrollbar(canvas_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, padx=10, pady=10)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(
                scrollregion=canvas.bbox("all")
            )
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")
        
        scrollable_frame.grid_columnconfigure(0, weight=1)
        scrollable_frame.grid_columnconfigure(1, weight=2)
        
        row_idx = 0
        
        for section, defaults in DEFAULT_SETTINGS.items():
            # Section Header
            tk.Label(scrollable_frame, text=f"[{section}]", font=('Helvetica', 14, 'bold'), fg="#1a5a9c").grid(
                row=row_idx, column=0, columnspan=2, sticky="w", pady=(15, 5), padx=5)
            row_idx += 1
            
            self.entries[section] = {}
            for key, default_val in defaults.items():
                # Key Label
                label_text = key.replace('_', ' ').title()
                
                tk.Label(scrollable_frame, text=f"{label_text}:", font=self.font_style).grid(
                    row=row_idx, column=0, sticky="w", padx=10, pady=2)
                
                # We store the value as a string in the UI, we'll cast on save/load
                var = tk.StringVar(self, value=str(default_val)) 
                
                widget = None
                
                if section == 'sensors' and key.endswith('_name'):
                    # Sensor Name Dropdown
                    initial_choice = str(default_val) if str(default_val) in SENSOR_CHOICES else SENSOR_CHOICES[0]
                    var.set(initial_choice)
                    widget = tk.OptionMenu(scrollable_frame, var, *SENSOR_CHOICES)
                    # Note: tk.OptionMenu must still use .config() for size/font
                    widget.config(width=37, font=self.font_style) 
                
                elif isinstance(default_val, bool):
                    # Boolean Dropdown (for any field defined as True/False in DEFAULT_SETTINGS)
                    initial_choice = "True" if str(default_val).lower() == 'true' else "False"
                    var.set(initial_choice)
                    widget = tk.OptionMenu(scrollable_frame, var, *BOOLEAN_CHOICES)
                    widget.config(width=37, font=self.font_style)
                
                if widget:
                    widget.grid(row=row_idx, column=1, sticky="ew", padx=10, pady=2)
                    self.entries[section][key] = var
                else:
                    # Default to standard Entry field
                    entry = tk.Entry(scrollable_frame, textvariable=var, width=40, font=self.font_style)
                    entry.grid(row=row_idx, column=1, sticky="ew", padx=10, pady=2)
                    self.entries[section][key] = var
                
                row_idx += 1
                
        path_footer = tk.Frame(self, padx=10, pady=10, relief=tk.GROOVE, bd=1)
        path_footer.grid(row=3, column=0, sticky="ew", padx=10, pady=5)
        
        # --- Configure footer grid for two columns ---
        path_footer.grid_columnconfigure(0, weight=1)
        path_footer.grid_columnconfigure(1, weight=1)
        
        footer_label_left = tk.Label(path_footer, text="Pins format for SPI:\n"+ \
                                             "SCK, MOSI, MISO, OUT\n" + \
                                             "CLK, SDI, SDO, CS\n" + \
                                             "CLK, SDA, SDO, CS\n",
                                             fg="gray60",
                                             font=('Helvetica', 12, 'italic'),
                                             justify='left')
        footer_label_left.grid(row=0, column=0, sticky="w", padx=10, pady=(0, 5))

        # --- Add a second label to the right column ---
        footer_label_right = tk.Label(path_footer, text="Pins format for I2C\n"+ \
                                            "SCL, SDA.",
                                             fg="gray60",
                                             font=('Helvetica', 12, 'italic'),
                                             justify='left')
        footer_label_right.grid(row=0, column=1, sticky="w", padx=10, pady=(0, 5))
        
    # --- Utility Functions ---

    def _is_circuitpy_device(self, path):
        """Checks if a given path looks like a CIRCUITPY device."""
        return os.path.exists(os.path.join(path, 'boot_out.txt'))

    def auto_detect_circuitpy(self):
        """Tries to find the CIRCUITPY drive based on common OS paths."""
        common_paths = []
        if sys.platform.startswith('darwin'):  # macOS
            common_paths.append('/Volumes/CIRCUITPY')
        elif sys.platform.startswith('linux'): # Linux
            user = os.getenv('USER')
            if user:
                common_paths.append(f'/media/{user}/CIRCUITPY')
            common_paths.append('/media/CIRCUITPY')
        elif sys.platform.startswith('win'): # Windows
            import string
            for letter in string.ascii_uppercase:
                path = f'{letter}:\\'
                if os.path.isdir(path) and self._is_circuitpy_device(path):
                    common_paths.append(path)
                    break 

        for path in common_paths:
            if os.path.exists(path) and self._is_circuitpy_device(path):
                self.circuitpy_path.set(path)
                return
    
    def select_circuitpy_path(self):
        """Opens a dialog to select the CIRCUITPY drive."""
        initial_dir = self.circuitpy_path.get() if os.path.exists(self.circuitpy_path.get()) else os.path.expanduser("~")
        directory = filedialog.askdirectory(
            initialdir=initial_dir,
            title="Select the CIRCUITPY drive (or folder)"
        )
        if directory:
            if not self._is_circuitpy_device(directory):
                messagebox.showwarning("Device Warning", 
                                       "The selected folder does not appear to be a CIRCUITPY device (missing boot_out.txt). Proceed with caution.")
            self.circuitpy_path.set(directory)
            self.load_config()

    # --- Load/Save Handlers using tomli/tomli_w ---

    def load_config(self):
        """Loads settings.toml using tomli and updates the UI."""
        path = self.circuitpy_path.get()
        toml_path = os.path.join(path, CONFIG_FILENAME)
        
        if not os.path.exists(toml_path):
            messagebox.showinfo("File Not Found", f"{CONFIG_FILENAME} not found. Using default settings.")
            return

        try:
            # tomli requires 'rb' (read binary) mode
            with open(toml_path, 'rb') as f: 
                loaded_data = tomli.load(f)
            
            # Update UI entries with loaded data, converting values back to string
            for section, keys in self.entries.items():
                if section in loaded_data:
                    for key, var in keys.items():
                        if key in loaded_data[section]:
                            # Convert any loaded value (int, float, str, bool) to string for the StringVar
                            var.set(str(loaded_data[section][key]))
                                    
            messagebox.showinfo("Load Success", f"Configuration loaded from {CONFIG_FILENAME} on the device.")

        except tomli.TOMLDecodeError as e:
            messagebox.showerror("Load Error", f"Error decoding TOML file (syntax error): {e}")
            print(f"TOML Decode Error: {e}")
        except Exception as e:
            messagebox.showerror("Load Error", f"Error reading config file: {e}")
            print(f"Error loading config: {e}")

    def save_config(self):
        """Saves current UI values to settings.toml using tomli_w."""
        path = self.circuitpy_path.get()
        if not os.path.exists(path) or not self._is_circuitpy_device(path):
            messagebox.showwarning("Save Error", "Please select a valid CIRCUITPY device path first.")
            return

        toml_path = os.path.join(path, CONFIG_FILENAME)

        try:
            # 1. Collect data from UI and cast back to their original types (bool, int, float, str)
            data_to_save = {}
            for section, defaults in DEFAULT_SETTINGS.items():
                data_to_save[section] = {}
                for key, default_val in defaults.items():
                    ui_value = self.entries[section][key].get().strip()
                    
                    # --- Type Casting and Validation ---
                    if isinstance(default_val, bool):
                        lower_value = ui_value.lower()
                        if lower_value == 'true':
                            data_to_save[section][key] = True
                        elif lower_value == 'false':
                            data_to_save[section][key] = False
                        else:
                            # Added validation for boolean inputs
                            raise ValueError(f"Value for '{key}' must be 'True' or 'False' (case-insensitive). Found: '{ui_value}'")
                    
                    elif isinstance(default_val, int):
                        try:
                            data_to_save[section][key] = int(ui_value)
                        except ValueError:
                            raise ValueError(f"Value for '{key}' must be an integer (e.g., 205). Found: '{ui_value}'")
                    
                    elif isinstance(default_val, float):
                        try:
                            data_to_save[section][key] = float(ui_value)
                        except ValueError:
                            raise ValueError(f"Value for '{key}' must be a decimal number (e.g., 0.5). Found: '{ui_value}'")
                    
                    else:
                        # Keep as string for everything else (SSID, passwords, URLs, pins, sensor names)
                        data_to_save[section][key] = ui_value
            
            # 2. Write to file using tomli_w. It requires 'wb' (write binary) mode
            with open(toml_path, 'wb') as f: 
                tomli_w.dump(data_to_save, f)
                
            messagebox.showinfo("Save Success", f"Configuration successfully saved to:\n{toml_path}")

        except ValueError as e:
            messagebox.showerror("Validation Error", str(e))
        except Exception as e:
            messagebox.showerror("Save Error", f"Error saving config file. Is the drive writeable?\n{e}")
            print(f"Error saving config: {e}")

if __name__ == "__main__":
    app = ConfigApp()
    app.mainloop()
