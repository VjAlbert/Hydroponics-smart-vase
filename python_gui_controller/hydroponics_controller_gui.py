import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, filedialog
import requests
import json
import time
import threading
import datetime
import csv

# --- Configuration ---
ESP_IP = None 
BASE_URL = None 

# --- Global GUI Variables ---
root = None
lbl_water_level_val = None
lbl_water_level_drops = None # Label for water droplets
lbl_soil_moisture_val = None
lbl_soil_moisture_drops = None # Label for soil moisture droplets
lbl_pump_status_val = None
lbl_cycle_status_val = None
entry_plant_name = None
entry_insert_date = None
entry_fertilizer = None # New field for fertilizer
entry_pump_on_min = None
entry_pump_off_min = None
db_listbox = None

current_db_data = [] 

# --- ESP Communication Functions (Only for data and cycle/pump control) ---
def get_esp_data():
    if not BASE_URL: return None
    try:
        response = requests.get(f"{BASE_URL}/data", timeout=5)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Data request error: {e}")
        return None

def set_irrigation_cycle(on_min, off_min):
    if not BASE_URL: return False
    payload = {"on_min": on_min, "off_min": off_min}
    try:
        response = requests.post(f"{BASE_URL}/set_cycle", json=payload, timeout=5)
        response.raise_for_status()
        messagebox.showinfo("Irrigation Cycle", f"Command sent to ESP.\nThe ESP will forward it to the UNO: {response.text}")
        return True
    except requests.exceptions.RequestException as e:
        messagebox.showerror("Error", f"Cycle setting error: {e}")
        return False

def control_pump(action): # "on" or "off"
    if not BASE_URL: return False
    endpoint = "/pump_on" if action == "on" else "/pump_off"
    try:
        response = requests.post(f"{BASE_URL}{endpoint}", timeout=5)
        response.raise_for_status()
        messagebox.showinfo("Pump Control", f"Pump {action.upper()} command sent to ESP.")
        return True
    except requests.exceptions.RequestException as e:
        messagebox.showerror("Error", f"Pump control error: {e}")
        return False

# --- GUI Functions ---
def get_droplet_indicator(percentage):
    """Converts a percentage into a droplet indicator (1-5)."""
    if percentage is None:
        return ""
    try:
        p = int(percentage)
        if p < 0: p = 0
        if p > 100: p = 100
        
        if p <= 5: return "◌ ◌ ◌ ◌ ◌ (Empty)" # Empty circles for near zero
        if p <= 20: return "💧 ◌ ◌ ◌ ◌"
        elif p <= 40: return "💧💧 ◌ ◌ ◌"
        elif p <= 60: return "💧💧💧 ◌ ◌"
        elif p <= 80: return "💧💧💧💧 ◌"
        else: return "💧💧💧💧💧 (Full)"
    except (ValueError, TypeError):
        return ""

def update_gui_data():
    global ESP_IP, BASE_URL
    if not ESP_IP: 
        # Do not attempt to fetch data if the IP is not set
        if lbl_water_level_val: lbl_water_level_val.config(text="Waiting for IP...")
        if lbl_water_level_drops: lbl_water_level_drops.config(text="")
        if lbl_soil_moisture_val: lbl_soil_moisture_val.config(text="")
        if lbl_soil_moisture_drops: lbl_soil_moisture_drops.config(text="")
        root.after(2000, update_gui_data) 
        return

    data = get_esp_data()
    if data:
        # Update the IP if provided and changed
        if "ip_address" in data and data["ip_address"] != "N/A" and ESP_IP != data["ip_address"]:
            ESP_IP = data["ip_address"]
            BASE_URL = f"http://{ESP_IP}" 
            root.title(f"Hydroponics Control - Connected to {ESP_IP}")

        water_pct = data.get('water_level')
        soil_pct = data.get('soil_moisture')

        lbl_water_level_val.config(text=f"{water_pct}%" if water_pct is not None else "N/A")
        lbl_water_level_drops.config(text=get_droplet_indicator(water_pct))
        
        lbl_soil_moisture_val.config(text=f"{soil_pct}%" if soil_pct is not None else "N/A")
        lbl_soil_moisture_drops.config(text=get_droplet_indicator(soil_pct))
        
        pump_stat = "ON" if data.get('pump_status') else "OFF"
        lbl_pump_status_val.config(text=pump_stat)
        
        cycle_stat = "ACTIVE" if data.get('cycle_active') else "INACTIVE"
        on_m = data.get('pump_on_min', 0)
        off_m = data.get('pump_off_min', 0)
        if data.get('cycle_active'):
            cycle_stat += f" ({on_m}min ON / {off_m}min OFF)"
        lbl_cycle_status_val.config(text=cycle_stat)

    else:
        lbl_water_level_val.config(text="Error")
        lbl_water_level_drops.config(text="")
        lbl_soil_moisture_val.config(text="Error")
        lbl_soil_moisture_drops.config(text="")
        lbl_pump_status_val.config(text="Error")
        lbl_cycle_status_val.config(text="Error")

    root.after(2000, update_gui_data)

def on_set_cycle_click():
    try:
        on_min = int(entry_pump_on_min.get())
        off_min = int(entry_pump_off_min.get())
        if on_min <= 0 or off_min <= 0:
            messagebox.showerror("Error", "Cycle minutes must be positive.")
            return
        set_irrigation_cycle(on_min, off_min)
    except ValueError:
        messagebox.showerror("Error", "Enter valid numbers for cycle minutes.")

def populate_db_listbox():
    db_listbox.delete(0, tk.END)
    for i, record in enumerate(current_db_data):
        plant_name = record.get("plant_name", "N/A")
        insert_date = record.get("insert_date", "N/A")
        fertilizer = record.get("fertilizer", "-") # Show "-" if not specified
        on_min = record.get("cycle_on_min", "N/A")
        off_min = record.get("cycle_off_min", "N/A")
        db_listbox.insert(tk.END, f"{i+1}. Plant: {plant_name}, Date: {insert_date}, Fert: {fertilizer}, Cycle: {on_min}on/{off_min}off")

def add_to_db():
    name = entry_plant_name.get()
    date = entry_insert_date.get()
    fertilizer_val = entry_fertilizer.get() # Read the fertilizer field
    try:
        on_min_str = entry_pump_on_min.get()
        off_min_str = entry_pump_off_min.get()
        on_min = int(on_min_str) if on_min_str else 0 
        off_min = int(off_min_str) if off_min_str else 0
    except ValueError:
        messagebox.showerror("Data Error", "ON/OFF minutes must be valid numbers or left empty.")
        return

    if not name or not date:
        messagebox.showerror("Data Error", "Plant name and insertion date are mandatory.")
        return

    record = {
        "plant_name": name,
        "insert_date": date,
        "fertilizer": fertilizer_val, # Save the fertilizer
        "cycle_on_min": on_min,
        "cycle_off_min": off_min
    }
    current_db_data.append(record)
    populate_db_listbox()
    entry_plant_name.delete(0, tk.END) 
    entry_fertilizer.delete(0, tk.END) # Clear fertilizer field

def load_selected_db_entry():
    selected_indices = db_listbox.curselection()
    if not selected_indices:
        messagebox.showwarning("Selection", "No record selected from the database.")
        return
    
    selected_index = selected_indices[0]
    record = current_db_data[selected_index]

    entry_plant_name.delete(0, tk.END)
    entry_plant_name.insert(0, record.get("plant_name", ""))
    
    entry_insert_date.delete(0, tk.END)
    entry_insert_date.insert(0, record.get("insert_date", ""))

    entry_fertilizer.delete(0, tk.END)
    entry_fertilizer.insert(0, record.get("fertilizer", "")) # Load fertilizer

    entry_pump_on_min.delete(0, tk.END)
    entry_pump_on_min.insert(0, str(record.get("cycle_on_min", "")))

    entry_pump_off_min.delete(0, tk.END)
    entry_pump_off_min.insert(0, str(record.get("cycle_off_min", "")))
    
    # Apply the cycle to Arduino if valid
    on_min_val = record.get("cycle_on_min", 0)
    off_min_val = record.get("cycle_off_min", 0)
    if isinstance(on_min_val, int) and isinstance(off_min_val, int) and on_min_val > 0 and off_min_val > 0:
        if messagebox.askyesno("Apply Cycle", "Do you want to apply this irrigation cycle to the Arduino?"):
            set_irrigation_cycle(on_min_val, off_min_val) # Use the direct function
    elif on_min_val or off_min_val: # If at least one is specified but they don't form a valid cycle
        messagebox.showinfo("Cycle Info", "Invalid cycle (ON and OFF must be > 0) for this record. Not applied.")

def remove_selected_db_entry():
    selected_indices = db_listbox.curselection()
    if not selected_indices:
        messagebox.showwarning("Selection", "No record selected to remove.")
        return
    
    selected_index = selected_indices[0]
    if messagebox.askyesno("Remove Record", f"Are you sure you want to remove the local record:\n{db_listbox.get(selected_index)}?"):
        current_db_data.pop(selected_index)
        populate_db_listbox()

def export_db_csv():
    if not current_db_data:
        messagebox.showinfo("Export CSV", "The local database is empty. Nothing to export.")
        return
    
    filepath = filedialog.asksaveasfilename(
        defaultextension=".csv",
        filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
        title="Save Local Database as CSV"
    )
    if not filepath:
        return

    try:
        with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
            # Define fieldnames to include the new 'fertilizer' field and ensure order
            fieldnames = ["plant_name", "insert_date", "fertilizer", "cycle_on_min", "cycle_off_min"]
            
            # Collect all possible keys if records are not uniform (optional but more robust)
            # all_keys = set()
            # for record in current_db_data:
            #    all_keys.update(record.keys())
            # fieldnames = sorted(list(all_keys)) # Use this if fieldnames are not fixed

            writer = csv.DictWriter(csvfile, fieldnames=fieldnames, extrasaction='ignore')
            writer.writeheader()
            for record in current_db_data:
                # Ensure all fieldnames are present in the record to write, otherwise add empty value
                row_to_write = {key: record.get(key, "") for key in fieldnames}
                writer.writerow(row_to_write)
        messagebox.showinfo("Export CSV", f"Local database successfully exported to {filepath}")
    except Exception as e:
        messagebox.showerror("Export Error", f"Error during CSV export: {e}")

def import_db_csv():
    global current_db_data
    filepath = filedialog.askopenfilename(
        filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
        title="Import Local Database from CSV"
    )
    if not filepath:
        return

    try:
        new_data = []
        with open(filepath, 'r', newline='', encoding='utf-8-sig') as csvfile: 
            reader = csv.DictReader(csvfile)
            for row in reader:
                # Convert numerical values if necessary, handling empty or missing strings
                cycle_on_min_str = row.get('cycle_on_min', '0')
                cycle_off_min_str = row.get('cycle_off_min', '0')
                
                row['cycle_on_min'] = int(cycle_on_min_str) if cycle_on_min_str and cycle_on_min_str.strip() else 0
                row['cycle_off_min'] = int(cycle_off_min_str) if cycle_off_min_str and cycle_off_min_str.strip() else 0
                
                # The fertilizer field is read as is; if not present in CSV, .get will return None
                if 'fertilizer' not in row:
                    row['fertilizer'] = "" # Add a default value if missing

                new_data.append(row)
        
        if messagebox.askyesno("Import CSV", "Do you want to replace the current local database with the data imported from the CSV?"):
            current_db_data = new_data
            populate_db_listbox()
            messagebox.showinfo("Import CSV", "Local database successfully updated from CSV.")
            
    except FileNotFoundError:
        messagebox.showerror("Import Error", f"File not found: {filepath}")
    except ValueError as e:
        messagebox.showerror("Import Error", f"Error in data conversion in CSV (e.g., non-numeric minutes): {e}")
    except Exception as e:
        messagebox.showerror("Import Error", f"Error during CSV import: {e}")

def ask_esp_ip():
    global ESP_IP, BASE_URL
    ip = simpledialog.askstring("ESP IP Address", "Enter the IP address of the ESP8266 module:", parent=root)
    if ip:
        ESP_IP = ip
        BASE_URL = f"http://{ESP_IP}"
        root.title(f"Hydroponics Control - Attempting connection to {ESP_IP}")
        update_gui_data() # Start the sensor data update cycle
    else:
        messagebox.showwarning("Missing IP", "Without an IP, communication with the ESP is not possible.")
        root.title("Hydroponics Control - IP not set")

# --- GUI Creation ---
def create_main_window():
    global root, lbl_water_level_val, lbl_water_level_drops, lbl_soil_moisture_val, lbl_soil_moisture_drops
    global lbl_pump_status_val, lbl_cycle_status_val, entry_plant_name, entry_insert_date
    global entry_fertilizer, entry_pump_on_min, entry_pump_off_min, db_listbox

    root = tk.Tk()
    root.title("Hydroponics Control")
    root.geometry("750x700") 

    # Frame for sensor data
    sensor_frame = ttk.LabelFrame(root, text="Sensor Data", padding=10)
    sensor_frame.pack(padx=10, pady=10, fill="x")

    ttk.Label(sensor_frame, text="Water Level:").grid(row=0, column=0, sticky="w", padx=5, pady=2)
    lbl_water_level_val = ttk.Label(sensor_frame, text="N/A", font=("Arial", 12, "bold"))
    lbl_water_level_val.grid(row=0, column=1, sticky="w", padx=5, pady=2)
    lbl_water_level_drops = ttk.Label(sensor_frame, text="", font=("Arial", 12))
    lbl_water_level_drops.grid(row=0, column=2, sticky="w", padx=10, pady=2)

    ttk.Label(sensor_frame, text="Soil Moisture:").grid(row=1, column=0, sticky="w", padx=5, pady=2)
    lbl_soil_moisture_val = ttk.Label(sensor_frame, text="N/A", font=("Arial", 12, "bold"))
    lbl_soil_moisture_val.grid(row=1, column=1, sticky="w", padx=5, pady=2)
    lbl_soil_moisture_drops = ttk.Label(sensor_frame, text="", font=("Arial", 12))
    lbl_soil_moisture_drops.grid(row=1, column=2, sticky="w", padx=10, pady=2)

    ttk.Label(sensor_frame, text="Pump Status:").grid(row=2, column=0, sticky="w", padx=5, pady=2)
    lbl_pump_status_val = ttk.Label(sensor_frame, text="N/A", font=("Arial", 12, "bold"))
    lbl_pump_status_val.grid(row=2, column=1, sticky="w", padx=5, pady=2)

    ttk.Label(sensor_frame, text="Irrigation Cycle ESP/UNO:").grid(row=3, column=0, sticky="w", padx=5, pady=2)
    lbl_cycle_status_val = ttk.Label(sensor_frame, text="N/A", font=("Arial", 10))
    lbl_cycle_status_val.grid(row=3, column=1, sticky="w", padx=5, pady=2, columnspan=2)

    # Frame for manual pump control
    manual_pump_frame = ttk.LabelFrame(root, text="Manual Pump Control (via ESP)", padding=10)
    manual_pump_frame.pack(padx=10, pady=5, fill="x")
    btn_pump_on_manual = ttk.Button(manual_pump_frame, text="TURN ON Pump", command=lambda: control_pump("on"))
    btn_pump_on_manual.pack(side="left", padx=5, pady=5, expand=True, fill="x")
    btn_pump_off_manual = ttk.Button(manual_pump_frame, text="TURN OFF Pump", command=lambda: control_pump("off"))
    btn_pump_off_manual.pack(side="left", padx=5, pady=5, expand=True, fill="x")

    # Frame for DB and cycle management
    db_cycle_frame = ttk.LabelFrame(root, text="Local Plant Database and Irrigation Cycle Management", padding=10)
    db_cycle_frame.pack(padx=10, pady=10, fill="both", expand=True)

    input_fields_frame = ttk.Frame(db_cycle_frame)
    input_fields_frame.pack(fill="x", pady=5)

    ttk.Label(input_fields_frame, text="Plant Name:").grid(row=0, column=0, sticky="w", padx=5, pady=2)
    entry_plant_name = ttk.Entry(input_fields_frame, width=30)
    entry_plant_name.grid(row=0, column=1, sticky="ew", padx=5, pady=2, columnspan=2)

    ttk.Label(input_fields_frame, text="Insertion Date (YYYY-MM-DD):").grid(row=1, column=0, sticky="w", padx=5, pady=2)
    entry_insert_date = ttk.Entry(input_fields_frame, width=30)
    entry_insert_date.grid(row=1, column=1, sticky="ew", padx=5, pady=2, columnspan=2)
    entry_insert_date.insert(0, datetime.date.today().strftime("%Y-%m-%d"))

    ttk.Label(input_fields_frame, text="Fertilizer:").grid(row=2, column=0, sticky="w", padx=5, pady=2)
    entry_fertilizer = ttk.Entry(input_fields_frame, width=30)
    entry_fertilizer.grid(row=2, column=1, sticky="ew", padx=5, pady=2, columnspan=2)

    ttk.Label(input_fields_frame, text="Cycle: Pump ON (minutes):").grid(row=3, column=0, sticky="w", padx=5, pady=2)
    entry_pump_on_min = ttk.Entry(input_fields_frame, width=10)
    entry_pump_on_min.grid(row=3, column=1, sticky="w", padx=5, pady=2)

    ttk.Label(input_fields_frame, text="Cycle: Every (minutes elapsed):").grid(row=4, column=0, sticky="w", padx=5, pady=2)
    entry_pump_off_min = ttk.Entry(input_fields_frame, width=10)
    entry_pump_off_min.grid(row=4, column=1, sticky="w", padx=5, pady=2)
    
    input_fields_frame.columnconfigure(1, weight=1) 

    btn_set_cycle = ttk.Button(input_fields_frame, text="Set Cycle on ESP/Arduino (from fields above)", command=on_set_cycle_click)
    btn_set_cycle.grid(row=5, column=0, columnspan=3, pady=10, sticky="ew")

    db_list_frame = ttk.Frame(db_cycle_frame)
    db_list_frame.pack(fill="both", expand=True, pady=5)
    
    db_listbox = tk.Listbox(db_list_frame, height=7)
    db_listbox.pack(side="left", fill="both", expand=True)
    scrollbar = ttk.Scrollbar(db_list_frame, orient="vertical", command=db_listbox.yview)
    scrollbar.pack(side="right", fill="y")
    db_listbox.config(yscrollcommand=scrollbar.set)

    db_buttons_frame_row1 = ttk.Frame(db_cycle_frame)
    db_buttons_frame_row1.pack(fill="x", pady=2)
    btn_add_db = ttk.Button(db_buttons_frame_row1, text="Add to Local DB", command=add_to_db)
    btn_add_db.pack(side="left", padx=2, pady=2, expand=True, fill="x")
    btn_load_selected = ttk.Button(db_buttons_frame_row1, text="Load Selected & Apply Cycle", command=load_selected_db_entry)
    btn_load_selected.pack(side="left", padx=2, pady=2, expand=True, fill="x")
    
    db_buttons_frame_row2 = ttk.Frame(db_cycle_frame)
    db_buttons_frame_row2.pack(fill="x", pady=2)
    btn_remove_db = ttk.Button(db_buttons_frame_row2, text="Remove Selected from Local DB", command=remove_selected_db_entry)
    btn_remove_db.pack(side="left", padx=2, pady=2, expand=True, fill="x")
    
    csv_buttons_frame = ttk.Frame(db_cycle_frame)
    csv_buttons_frame.pack(fill="x", pady=(5,2)) 
    btn_export_csv = ttk.Button(csv_buttons_frame, text="Export Local DB (CSV)", command=export_db_csv)
    btn_export_csv.pack(side="left", padx=2, pady=2, expand=True, fill="x")
    btn_import_csv = ttk.Button(csv_buttons_frame, text="Import DB from CSV (to Local)", command=import_db_csv)
    btn_import_csv.pack(side="left", padx=2, pady=2, expand=True, fill="x")

    menubar = tk.Menu(root)
    config_menu = tk.Menu(menubar, tearoff=0)
    config_menu.add_command(label="Set ESP8266 IP", command=ask_esp_ip)
    menubar.add_cascade(label="Configuration", menu=config_menu)
    root.config(menu=menubar)

    if not ESP_IP:
        root.after(100, ask_esp_ip) 
    else:
        update_gui_data()

    root.mainloop()

if __name__ == "__main__":
    create_main_window()
