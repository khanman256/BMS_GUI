# BMS_GUI
This Python-based script provides a user-friendly interface for reading and logging serial data, designed for battery management system (BMS) monitoring, based heavily off of the Orion BMS software. The GUI is built using Tkinter and supports real-time data visualization, logging, and CSV export.

**Features**
* Serial Port Selection: Choose from available serial ports and configure baud rate.
* Live Data Display: Monitors and updates cell voltage, internal resistance, and open circuit voltage in a grid format.
* Data Logging: Record serial data in real-time and export logs as CSV.
* User Input & Control: Send commands, start/stop recording, and toggle measurement modes.
* Threaded Serial Communication: Runs serial reading in a background thread to ensure smooth UI performance.

**Usage**
* Select the desired serial port and baud rate.
* Click Connect to establish communication.
* Choose a measurement mode from the dropdown menu.
* Data updates in real time as it's received from the serial device.
     * If no data is being received, the table in the GUI will be filled with "NA"
* Use Start Recording to log data and Export CSV to save it and log when the data was added into the table
* Click Disconnect to safely stop communication.
     * If Disconnect is not pressed and the code is closed, it can cause the terminal to be stuck
 
NOTE: Code is tuned specifically to receive specific messages
