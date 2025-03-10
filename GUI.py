import tkinter as tk
from tkinter import ttk
from tkinter import scrolledtext
import serial.tools.list_ports
from serial import Serial
import threading
import datetime
import time
import csv

NUM_MODULES = 8
NUM_CELLS_PER_MODULE = 12

NUM_COLUMNS = NUM_MODULES
NUM_ROWS = NUM_CELLS_PER_MODULE

INSTANTANEOUS_CELL_VOLTAGE = "Instantaneous Cell Voltage"
INTERNAL_RESISTANCE = "Internal Resistance"
OPEN_CIRCUIT_VOLTAGE = "Open Circuit Voltage"

class SerialMonitor:
    def __init__(self, master):
        self.master = master
        self.window_width = self.master.winfo_screenwidth()  # Use full screen width
        self.window_height = self.master.winfo_screenheight()  # Use full screen height
        self.master.geometry(f'{self.window_width}x{self.window_height}')  # Set the window to full screen
        self.master.title("Serial Monitor")
        self.master.state('zoomed')  # Open in maximized state

        self.create_widgets()  # Call method to create widgets

        self.mode = self.meas_combobox.get()

        self.connection_active = False  # Flag to track connection state

    def create_widgets(self):
        # Port ComboBox Label
        self.port_combobox_label = ttk.Label(self.master, text="Select Port:")
        self.port_combobox_label.grid(row=0, column=0, padx=10, pady=10)

        # Populate available ports into the ComboBox
        self.populate_ports()

        # Baud ComboBox Label
        self.baud_combobox_label = ttk.Label(self.master, text="Select Baud Rate:")
        self.baud_combobox_label.grid(row=0, column=1, padx=10, pady=10)

        # Combobox with predefined baud rates
        self.baud_combobox = ttk.Combobox(self.master, values=["2400","4800","9600","14400", "115200"], state="readonly")
        self.baud_combobox.set("9600")  # Default to 9600 baud rate
        self.baud_combobox.grid(row=0, column=2, padx=10, pady=10)

        # Connect Button
        self.connect_button = ttk.Button(self.master, text="Connect", command=self.connect)
        self.connect_button.grid(row=0, column=3, padx=10, pady=10)

        # Disconnect Button
        self.disconnect_button = ttk.Button(self.master, text="Disconnect", command=self.disconnect, state=tk.DISABLED)
        self.disconnect_button.grid(row=0, column=4, padx=10, pady=10)

        # Export CSV Button
        self.export_csv_button = ttk.Button(self.master, text="Export as CSV", command=self.export_csv, state=tk.DISABLED)
        self.export_csv_button.grid(row=1, column=5, padx=10, pady=10)

        # User Input Entry Box
        self.text_entry_label = ttk.Label(self.master, text="Enter Text:")
        self.text_entry_label.grid(row=1, column=0, padx=10, pady=10)

        self.text_entry = ttk.Entry(self.master, width=30)  # Adjust width as needed
        self.text_entry.grid(row=1, column=1, padx=10, pady=10)

        self.meas_combobox_label = ttk.Label(self.master, text="Select Measurement Quantity:")
        self.meas_combobox_label.grid(row=0, column=6, padx=10, pady=10)

        self.meas_combobox = ttk.Combobox(self.master, values=[INSTANTANEOUS_CELL_VOLTAGE, INTERNAL_RESISTANCE, OPEN_CIRCUIT_VOLTAGE], state="readonly")
        self.meas_combobox.set(INSTANTANEOUS_CELL_VOLTAGE)  # Default
        self.meas_combobox.grid(row=0, column=7, padx=10, pady=10)

        # Start Recording Button
        self.start_recording_button = ttk.Button(self.master, text="Start Recording", command=self.toggle_recording)
        self.start_recording_button.grid(row=1, column=6, padx=10, pady=10)

    # Initialize recording flag
        self.recording_active = False
        self.recording_thread = None

        # Scrolled Text Area for logs
        self.log_text = scrolledtext.ScrolledText(self.master, wrap=tk.WORD, height=40, width = 150)
        self.log_text.grid(row=2, column=0, columnspan=18, padx=10, pady=10)

    def populate_ports(self):
        ports = [port.device for port in serial.tools.list_ports.comports()]
        self.port_combobox = ttk.Combobox(self.master, values=ports, state="readonly")
        self.port_combobox.grid(row=0, column=0, padx=10, pady=10)

    def connect(self):
        port = self.port_combobox.get()  # Get selected port
        baud = int(self.baud_combobox.get())  # Get selected baud rate
        try:
            self.ser = Serial(port, baud, timeout=1)  # Open serial connection
            self.connection_active = True

            # Change button states after successful connection
            self.disconnect_button["state"] = tk.NORMAL
            self.connect_button["state"] = tk.DISABLED
            #self.export_txt_button["state"] = tk.NORMAL
            self.export_csv_button["state"] = tk.NORMAL

            # Start a new thread to read data from the serial port
            self.thread = threading.Thread(target=self.read_from_port)
            self.thread.start()

        except Exception as e:
            self.log_text.insert(tk.END, f"Error: {str(e)}\n")

    def disconnect(self):
        self.connection_active = False  # Stop data reading
        if hasattr(self, 'ser') and self.ser.is_open:
            self.ser.close()  # Close serial port connection
        self.connect_button["state"] = tk.NORMAL
        self.disconnect_button["state"] = tk.DISABLED
        self.export_csv_button["state"] = tk.DISABLED
        self.log_text.insert(tk.END, "Disconnected\n")

    def clear_matrix(self):
        self.matrix = [["NA"] * NUM_COLUMNS for _ in range(NUM_ROWS)]

    def read_from_port(self):
        columns = [f"Module {i + 1}" for i in range(NUM_COLUMNS)]  # Define columns
        self.tree = ttk.Treeview(self.master, columns=columns, show="headings")
        self.tree.grid(row=2, column=0, columnspan=8, sticky="nsew")

        # Define columns
        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, stretch=False, anchor="center", width = int(self.window_width / NUM_COLUMNS))

        self.clear_matrix()  # Initialize matrix

        # Insert empty rows into the Treeview
        for row in self.matrix:
            self.tree.insert("", tk.END, values=row)

        phrase = "t0368".encode()  # Marker phrase to look for in serial data

        while self.connection_active:

            #If measurement mode changes, clear grid, update mode
            if self.mode != self.meas_combobox.get():
                self.clear_matrix()
                self.mode = self.meas_combobox.get()

            if self.ser.in_waiting > 0: #If there are unread bytes
                data = self.ser.read(self.ser.in_waiting)  # Read all available data

                end_index = 0

                for i in range(data.count(phrase)):

                    phrase_start_index = data.find(phrase, end_index)

                    cell_id_hex = data[phrase_start_index + len(phrase): phrase_start_index + len(phrase) + 2]
                    cell_id_decimal = int(cell_id_hex, 16)

                    # Calculate row and column indices
                    row_index = cell_id_decimal % NUM_ROWS
                    column_index = cell_id_decimal // NUM_ROWS

                    if self.mode == INSTANTANEOUS_CELL_VOLTAGE:
                        icv_hex = data[phrase_start_index + len(phrase) + 2: phrase_start_index + len(phrase) + 6]
                        icv_decimal = int(icv_hex, 16)
                        icv_converted = round(((icv_decimal + 10000) * .00015), 3)
                        dipslayed_value = icv_converted
                    elif self.mode == INTERNAL_RESISTANCE:
                        res_hex = data[phrase_start_index + len(phrase) + 6: phrase_start_index + len(phrase) + 10]
                        res_decimal = int(res_hex, 16)
                        #Need proper conversion
                        res_converted = res_decimal
                        dipslayed_value = res_converted
                    elif self.mode == OPEN_CIRCUIT_VOLTAGE:
                        ocv_hex = data[phrase_start_index + len(phrase) + 10: phrase_start_index + len(phrase) + 14]
                        ocv_decimal = int(ocv_hex, 16)
                        #Need proper conversion
                        ocv_converted = ocv_decimal
                        dipslayed_value = ocv_converted

                    end_index = phrase_start_index + len(phrase) + 14

                    # Update matrix and Treeview
                    if self.matrix[row_index][column_index] != dipslayed_value:
                        self.matrix[row_index][column_index] = dipslayed_value
                        self.update_cell(row_index, self.matrix[row_index])

            time.sleep(0.01)  # Small delay to reduce CPU usage

    def update_cell(self, row_index, row_values):
        """Update a specific row in the Treeview."""
        item_id = self.tree.get_children()[row_index]
        self.tree.item(item_id, values=row_values)
        #data = np.array(self.matrix)
        average = 20
        self.average_entry = ttk.Label(self.master, text= str(average))
        self.average_entry.grid(row = 1, column = 2, padx = 10, pady = 10)

    def toggle_recording(self):
        """Toggles data recording on/off."""
        if not self.recording_active:
            self.recording_active = True
            self.start_recording_button.config(text="Stop Recording")
            self.log_text.insert(tk.END, "Recording started...\n")

            # Start the recording thread
            self.recording_thread = threading.Thread(target=self.record_data, daemon=True)
            self.recording_thread.start()
        else:
            self.recording_active = False
            self.start_recording_button.config(text="Start Recording")
            self.log_text.insert(tk.END, "Recording stopped.\n")

    def record_data(self):
        """Continuously writes data to a CSV file while recording is active."""
        filename = f"data_recording_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}.csv"
    
        with open(filename, "w", newline="") as file:
            writer = csv.writer(file)

            # Write headers (including Time as the first column)
            headers = ["Time"] + [self.tree.heading(col)["text"] for col in self.tree["columns"]]
            writer.writerow(headers)

            while self.recording_active:
                current_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
                # Get all data rows from the Treeview
                for row in self.tree.get_children():
                    row_data = self.tree.item(row)["values"]
                    writer.writerow([current_time] + row_data)

                time.sleep(1)  # Log data every second

        self.log_text.insert(tk.END, f"Recording saved as: {filename}\n")
    
    def export_csv(self):
        filename = f"serial_log_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}.csv"
        with open(filename, "w", newline="") as file:
            writer = csv.writer(file)

        # Write headers (including 'Time' as the first column)
        headers = ["Time"] + [self.tree.heading(col)["text"] for col in self.tree["columns"]]
        writer.writerow(headers)

        # Write the data from the Treeview (matrix values) with a timestamp
        for row in self.tree.get_children():
            row_data = self.tree.item(row)["values"]
            current_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            writer.writerow([current_time] + row_data)  # Add the current time at the beginning of each row

        self.log_text.insert(tk.END, f"Log exported as CSV: {filename}\n")

# Main block
if __name__ == "__main__":
    root = tk.Tk()
    app = SerialMonitor(root)
    root.mainloop()
