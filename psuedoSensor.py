import sys
import random
import time
import sqlite3
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QPushButton, QLabel, QLineEdit, QMessageBox, QHBoxLayout
from PyQt5.QtCore import QTimer, QDateTime, QThread, pyqtSignal
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from PyQt5.QtGui import QFont

class PseudoSensor:
    # Define humidity and temperature ranges
    h_range = [0, 20, 20, 40, 40, 60, 60, 80, 80, 90, 70, 70, 50, 50, 30, 30, 10, 10]
    t_range = [-20, -10, 0, 10, 30, 50, 70, 80, 90, 80, 60, 40, 20, 10, 0, -10]
    h_range_index = 0
    t_range_index = 0
    humVal = 0
    tempVal = 0

    def __init__(self):
        # Initialize sensor values
        self.humVal = self.h_range[self.h_range_index]
        self.tempVal = self.t_range[self.t_range_index]

    def generate_values(self):
        # Generate pseudo-random sensor values
        self.humVal = self.h_range[self.h_range_index] + random.uniform(-1, 1)
        self.tempVal = self.t_range[self.t_range_index] + random.uniform(-1, 1)
        self.humVal = max(0, min(100, self.humVal))
        self.tempVal = max(-20, min(100, self.tempVal))
        self.h_range_index = (self.h_range_index + 1) % len(self.h_range)
        self.t_range_index = (self.t_range_index + 1) % len(self.t_range)
        return round(self.humVal, 2), round(self.tempVal, 2)

class SensorApp(QWidget):
    def __init__(self):
        super().__init__()
        self.alarm_temp = 100
        self.alarm_hum = 100
        self.temp_unit = 'F'
        self.sensor = PseudoSensor()
        self.conn = sqlite3.connect('sensor_data.db')
        self.create_table()
        self.initUI()

    def initUI(self):
        # Initialize the user interface
        self.layout = QVBoxLayout()
        
        # Create a font for the temperature and humidity labels
        label_font = QFont()
        label_font.setPointSize(14)
        label_font.setBold(True)
        
        self.temp_label = QLabel(f'Temperature: 0.00°{self.temp_unit}')
        self.temp_label.setFont(label_font)
        self.hum_label = QLabel('Humidity: 0.00%')
        self.hum_label.setFont(label_font)
        self.alarm_temp_input = QLineEdit(str(self.alarm_temp))
        self.alarm_hum_input = QLineEdit(str(self.alarm_hum))
        
        # Create buttons with larger font size
        button_font = QFont()
        button_font.setPointSize(12)
        
        self.single_read_button = QPushButton('Read Single Value')
        self.single_read_button.setFont(button_font)
        self.single_read_button.clicked.connect(self.read_single_value)
        
        self.read_10_button = QPushButton('Read 10 Values')
        self.read_10_button.setFont(button_font)
        self.read_10_button.clicked.connect(self.read_10_values)
        
        self.calc_stats_button = QPushButton('Calculate Stats')
        self.calc_stats_button.setFont(button_font)
        self.calc_stats_button.clicked.connect(self.calculate_stats)
        
        self.clear_data_button = QPushButton('Clear Data')
        self.clear_data_button.setFont(button_font)
        self.clear_data_button.clicked.connect(self.clear_data)
        
        self.show_graph_button = QPushButton('Show Graphs')
        self.show_graph_button.setFont(button_font)
        self.show_graph_button.clicked.connect(self.show_graphs)
        
        self.toggle_unit_button = QPushButton('Toggle °C/°F')
        self.toggle_unit_button.setFont(button_font)
        self.toggle_unit_button.clicked.connect(self.toggle_temp_unit)
        
        self.close_button = QPushButton('Close')
        self.close_button.setFont(button_font)
        self.close_button.clicked.connect(self.close_app)
        
        self.layout.addWidget(self.temp_label)
        self.layout.addWidget(self.hum_label)
        self.layout.addWidget(QLabel('Temperature Alarm:'))
        self.layout.addWidget(self.alarm_temp_input)
        self.layout.addWidget(QLabel('Humidity Alarm:'))
        self.layout.addWidget(self.alarm_hum_input)
        self.layout.addWidget(self.single_read_button)
        self.layout.addWidget(self.read_10_button)
        self.layout.addWidget(self.calc_stats_button)
        self.layout.addWidget(self.clear_data_button)
        self.layout.addWidget(self.show_graph_button)
        self.layout.addWidget(self.toggle_unit_button)
        self.layout.addWidget(self.close_button)
        self.setLayout(self.layout)
        
        self.temp_canvas = FigureCanvas(Figure())
        self.hum_canvas = FigureCanvas(Figure())
        
        self.graph_layout = QHBoxLayout()
        self.graph_layout.addWidget(self.temp_canvas)
        self.graph_layout.addWidget(self.hum_canvas)
        
        self.layout.addLayout(self.graph_layout)
        
    def read_single_value(self):
        hum, temp = self.sensor.generate_values()
        self.save_data_to_db(hum, temp)
        self.update_labels(temp, hum)
        self.check_alarms(temp, hum)
        
    def read_10_values(self):
        for _ in range(10):
            self.read_single_value()
            time.sleep(1)
        QMessageBox.information(self, 'Read 10 Values', 'Successfully read 10 values.')
        
    def calculate_stats(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT temperature, humidity FROM sensor_data ORDER BY timestamp DESC LIMIT 10")
        rows = cursor.fetchall()
        if rows:
            temps = [row[0] for row in rows]
            hums = [row[1] for row in rows]
            min_temp, max_temp, avg_temp = min(temps), max(temps), sum(temps) / len(temps)
            min_hum, max_hum, avg_hum = min(hums), max(hums), sum(hums) / len(hums)
            QMessageBox.information(self, 'Stats', f'Temperature - Min: {min_temp}, Max: {max_temp}, Avg: {avg_temp}\n'
                                                   f'Humidity - Min: {min_hum}, Max: {max_hum}, Avg: {avg_hum}')
        
    def save_data_to_db(self, hum, temp):
        cursor = self.conn.cursor()
        cursor.execute("INSERT INTO sensor_data (timestamp, temperature, humidity) VALUES (?, ?, ?)",
                       (QDateTime.currentDateTime().toString(), temp, hum))
        self.conn.commit()
        
    def update_labels(self, temp, hum):
        self.temp_label.setText(f'Temperature: {temp:.2f}°{self.temp_unit}')
        self.hum_label.setText(f'Humidity: {hum:.2f}%')
        
    def check_alarms(self, temp, hum):
        alarm_temp = float(self.alarm_temp_input.text())
        alarm_hum = float(self.alarm_hum_input.text())
        if temp > alarm_temp or hum > alarm_hum:
            QMessageBox.warning(self, 'Alarm', 'Temperature or Humidity exceeded alarm values!')
        
    def clear_data(self):
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM sensor_data")
        self.conn.commit()
        QMessageBox.information(self, 'Data Cleared', 'All data has been cleared from the database.')
        
    def show_graphs(self):
        # Display graphs of the sensor data
        cursor = self.conn.cursor()
        cursor.execute("SELECT temperature, humidity FROM sensor_data")
        rows = cursor.fetchall()
        if rows:
            temps = [row[0] for row in rows]
            hums = [row[1] for row in rows]
            readings = list(range(1, len(rows) + 1))
            
            self.temp_canvas.figure.clear()
            self.hum_canvas.figure.clear()
            
            temp_ax = self.temp_canvas.figure.add_subplot(111)
            hum_ax = self.hum_canvas.figure.add_subplot(111)
            
            temp_ax.plot(readings, temps, label=f'Temperature (°{self.temp_unit})')
            hum_ax.plot(readings, hums, label='Humidity (%)')
            
            temp_ax.legend()
            hum_ax.legend()
            
            self.temp_canvas.draw()
            self.hum_canvas.draw()
        
    def toggle_temp_unit(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT timestamp, temperature, humidity FROM sensor_data")
        rows = cursor.fetchall()
        if rows:
            if self.temp_unit == 'C':
                self.temp_unit = 'F'
                for row in rows:
                    new_temp = (row[1] * 9/5) + 32
                    cursor.execute("UPDATE sensor_data SET temperature = ? WHERE timestamp = ?", (new_temp, row[0]))
            else:
                self.temp_unit = 'C'
                for row in rows:
                    new_temp = (row[1] - 32) * 5/9
                    cursor.execute("UPDATE sensor_data SET temperature = ? WHERE timestamp = ?", (new_temp, row[0]))
            self.conn.commit()
            self.show_graphs()
            self.update_labels(self.sensor.tempVal, self.sensor.humVal)
        
    def create_table(self):
        cursor = self.conn.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS sensor_data
                          (timestamp TEXT, temperature REAL, humidity REAL)''')
        self.conn.commit()
        
    def close_app(self):
        self.conn.close()
        self.close()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = SensorApp()
    ex.show()
    sys.exit(app.exec_())