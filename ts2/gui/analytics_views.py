#
#   Copyright (C) 2008-2015 by Nicolas Piganeau
#   npi@m4x.org
#
#   This program is free software; you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation; either version 2 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with this program; if not, write to the
#   Free Software Foundation, Inc.,
#   59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
#

from Qt import QtCore, QtWidgets, Qt, QtGui
import json
import os
import random
import math
from datetime import datetime, timedelta
from .charts import (SparklineChart, BarChart, LineChart, HeatmapChart, 
                    GaugeChart, KPITile, generateMockData)
from .railway_kpi_dashboard import RailwayKPIDashboard

# Use the new comprehensive KPI dashboard
KPIDashboardWidget = RailwayKPIDashboard


class WhatIfAnalysisWidget(QtWidgets.QWidget):
    """What-If Analysis simulation view"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.scenarios = []
        self.setupUI()
        
    def setupUI(self):
        """Setup what-if analysis UI with proper layout"""
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(15)
        
        # Header
        header = QtWidgets.QLabel("What-If Analysis Simulator")
        header.setStyleSheet("font-size: 18px; font-weight: bold; color: #495057; margin-bottom: 10px;")
        layout.addWidget(header)
        
        # Scenario setup
        setup_group = QtWidgets.QGroupBox("Scenario Setup")
        setup_layout = QtWidgets.QGridLayout(setup_group)
        
        # Section selection
        setup_layout.addWidget(QtWidgets.QLabel("Target Section:"), 0, 0)
        self.section_combo = QtWidgets.QComboBox()
        self.section_combo.addItems(["SEC_A - Central Junction", "SEC_B - Northern Platform", "SEC_C - Southern Freight"])
        setup_layout.addWidget(self.section_combo, 0, 1)
        
        # Train addition controls
        setup_layout.addWidget(QtWidgets.QLabel("Add Trains:"), 1, 0)
        
        train_controls = QtWidgets.QWidget()
        train_layout = QtWidgets.QHBoxLayout(train_controls)
        
        self.train_type_combo = QtWidgets.QComboBox()
        self.train_type_combo.addItems(["Express", "Regional", "Freight"])
        train_layout.addWidget(self.train_type_combo)
        
        self.train_count_spin = QtWidgets.QSpinBox()
        self.train_count_spin.setRange(1, 10)
        train_layout.addWidget(self.train_count_spin)
        
        self.add_train_btn = QtWidgets.QPushButton("Add Train")
        self.add_train_btn.clicked.connect(self.addTrainToScenario)
        train_layout.addWidget(self.add_train_btn)
        
        setup_layout.addWidget(train_controls, 1, 1)
        
        # Run simulation
        self.run_btn = QtWidgets.QPushButton("Run What-If Simulation")
        self.run_btn.clicked.connect(self.runSimulation)
        self.run_btn.setMinimumHeight(40)
        self.run_btn.setStyleSheet("QPushButton { font-weight: bold; background-color: #495057; color: white; }")
        setup_layout.addWidget(self.run_btn, 2, 0, 1, 2)
        
        layout.addWidget(setup_group)
        
        # Scenario trains list
        trains_group = QtWidgets.QGroupBox("Scenario Trains")
        trains_layout = QtWidgets.QVBoxLayout(trains_group)
        
        self.scenario_table = QtWidgets.QTableWidget()
        self.scenario_table.setColumnCount(4)
        self.scenario_table.setHorizontalHeaderLabels(["Type", "Speed", "Destination", "Actions"])
        trains_layout.addWidget(self.scenario_table)
        
        clear_btn = QtWidgets.QPushButton("Clear All")
        clear_btn.clicked.connect(self.clearScenario)
        trains_layout.addWidget(clear_btn)
        
        layout.addWidget(trains_group)
        
        # Results
        results_group = QtWidgets.QGroupBox("Predicted Results")
        results_layout = QtWidgets.QVBoxLayout(results_group)
        
        self.results_text = QtWidgets.QTextEdit()
        self.results_text.setMaximumHeight(150)
        self.results_text.setPlainText("Configure scenario and run simulation to see predicted KPI impacts...")
        results_layout.addWidget(self.results_text)
        
        layout.addWidget(results_group)
        
    def addTrainToScenario(self):
        """Add train to current scenario"""
        train_type = self.train_type_combo.currentText()
        count = self.train_count_spin.value()
        
        for i in range(count):
            train_data = {
                'type': train_type,
                'speed': 80 if train_type == 'Express' else 60 if train_type == 'Regional' else 40,
                'destination': f"Platform_{i+1}",
            }
            self.scenarios.append(train_data)
            
        self.updateScenarioTable()
        
    def updateScenarioTable(self):
        """Update the scenario trains table"""
        self.scenario_table.setRowCount(len(self.scenarios))
        
        for row, train in enumerate(self.scenarios):
            self.scenario_table.setItem(row, 0, QtWidgets.QTableWidgetItem(train['type']))
            self.scenario_table.setItem(row, 1, QtWidgets.QTableWidgetItem(f"{train['speed']} km/h"))
            self.scenario_table.setItem(row, 2, QtWidgets.QTableWidgetItem(train['destination']))
            
            # Actions
            remove_btn = QtWidgets.QPushButton("Remove")
            remove_btn.clicked.connect(lambda checked, r=row: self.removeTrainFromScenario(r))
            self.scenario_table.setCellWidget(row, 3, remove_btn)
            
        self.scenario_table.resizeColumnsToContents()
        
        # Fix right-side cropping - ensure table uses full width
        header = self.scenario_table.horizontalHeader()
        header.setStretchLastSection(True)
        header.setSectionResizeMode(QtWidgets.QHeaderView.Stretch)
        
    def removeTrainFromScenario(self, row):
        """Remove train from scenario"""
        if 0 <= row < len(self.scenarios):
            self.scenarios.pop(row)
            self.updateScenarioTable()
            
    def clearScenario(self):
        """Clear all scenario trains"""
        self.scenarios.clear()
        self.updateScenarioTable()
        
    def runSimulation(self):
        """Run the what-if simulation"""
        if not self.scenarios:
            QtWidgets.QMessageBox.warning(self, "No Scenario", "Please add some trains to the scenario first.")
            return
            
        # Simulate processing
        QtWidgets.QApplication.setOverrideCursor(Qt.WaitCursor)
        
        # Mock results calculation
        total_trains = len(self.scenarios)
        express_count = len([t for t in self.scenarios if t['type'] == 'Express'])
        regional_count = len([t for t in self.scenarios if t['type'] == 'Regional'])
        freight_count = len([t for t in self.scenarios if t['type'] == 'Freight'])
        
        # Predicted impact calculations (simplified)
        predicted_throughput = min(total_trains * 1.2, 300)  # Max capacity
        predicted_delay = max(0, (total_trains - 15) * 0.5)  # Delay increases with congestion
        predicted_utilization = min((total_trains / 20) * 100, 100)  # Max 100%
        
        # Handle recommendations separately to avoid f-string backslash issue
        if total_trains > 10:
            recommendations = "• Consider staggering train arrivals\n• Monitor signal timing\n• Prepare for delays"
        else:
            recommendations = "• Operations should run smoothly\n• No special measures needed"
            
        bottlenecks = "High congestion expected" if total_trains > 15 else "Normal operations"
        
        results = f"""Simulation Results for {total_trains} trains:

Train Composition:
• Express: {express_count} trains
• Regional: {regional_count} trains  
• Freight: {freight_count} trains

Predicted KPIs:
• Throughput: {predicted_throughput:.1f} trains/hour
• Average Delay: {predicted_delay:.1f} minutes
• Section Utilization: {predicted_utilization:.1f}%
• Estimated Bottlenecks: {bottlenecks}

Recommendations:
{recommendations}
        """
        
        self.results_text.setPlainText(results)
        QtWidgets.QApplication.restoreOverrideCursor()


class AuditLogsWidget(QtWidgets.QWidget):
    """Audit logs view with search, filter, and sort capabilities"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.logs_data = []
        self.filtered_logs = []
        self.setupUI()
        self.loadDummyData()
        
    def setupUI(self):
        """Setup audit logs UI with proper layout"""
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(15)
        
        # Header with search and filters
        header = QtWidgets.QWidget()
        header_layout = QtWidgets.QVBoxLayout(header)
        
        title = QtWidgets.QLabel("Audit Logs")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #495057; margin-bottom: 10px;")
        header_layout.addWidget(title)
        
        # Search and filter controls
        controls_frame = QtWidgets.QFrame()
        controls_frame.setFrameStyle(QtWidgets.QFrame.StyledPanel)
        controls_layout = QtWidgets.QGridLayout(controls_frame)
        
        # Search
        controls_layout.addWidget(QtWidgets.QLabel("Search:"), 0, 0)
        self.search_box = QtWidgets.QLineEdit()
        self.search_box.setPlaceholderText("Search in logs...")
        self.search_box.textChanged.connect(self.filterLogs)
        controls_layout.addWidget(self.search_box, 0, 1)
        
        # Severity filter
        controls_layout.addWidget(QtWidgets.QLabel("Severity:"), 0, 2)
        self.severity_combo = QtWidgets.QComboBox()
        self.severity_combo.addItems(["All", "INFO", "WARNING", "ERROR", "NOTICE"])
        self.severity_combo.currentTextChanged.connect(self.filterLogs)
        controls_layout.addWidget(self.severity_combo, 0, 3)
        
        # Time range
        controls_layout.addWidget(QtWidgets.QLabel("Time Range:"), 1, 0)
        self.time_range_combo = QtWidgets.QComboBox()
        self.time_range_combo.addItems(["All Time", "Last Hour", "Last 6 Hours", "Today", "Last 7 Days"])
        self.time_range_combo.currentTextChanged.connect(self.filterLogs)
        controls_layout.addWidget(self.time_range_combo, 1, 1)
        
        # Refresh button
        self.refresh_btn = QtWidgets.QPushButton("Refresh")
        self.refresh_btn.clicked.connect(self.refreshLogs)
        controls_layout.addWidget(self.refresh_btn, 1, 2)
        
        # Export button
        self.export_logs_btn = QtWidgets.QPushButton("Export Logs")
        self.export_logs_btn.clicked.connect(self.exportLogs)
        controls_layout.addWidget(self.export_logs_btn, 1, 3)
        
        header_layout.addWidget(controls_frame)
        layout.addWidget(header)
        
        # Logs table
        self.logs_table = QtWidgets.QTableWidget()
        self.logs_table.setColumnCount(4)
        self.logs_table.setHorizontalHeaderLabels(["Timestamp", "Action", "Details", "Severity"])
        self.logs_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.logs_table.setAlternatingRowColors(True)
        self.logs_table.setSortingEnabled(True)
        layout.addWidget(self.logs_table)
        
        # Status info
        self.status_label = QtWidgets.QLabel()
        self.status_label.setStyleSheet("color: #666666; font-size: 12px;")
        layout.addWidget(self.status_label)
        
    def loadDummyData(self):
        """Load dummy audit logs data"""
        try:
            data_file = os.path.join(os.path.dirname(__file__), '..', 'data', 'dummy_data.json')
            with open(data_file, 'r') as f:
                data = json.load(f)
                self.logs_data = data.get('auditLogs', [])
                
                # Add some more dummy logs for demonstration
                base_time = datetime.now()
                additional_logs = [
                    {
                        "timestamp": (base_time - timedelta(minutes=5)).isoformat(),
                        "action": "TRAIN_DEPARTED",
                        "details": "Train T003 departed from Station_A on schedule",
                        "user": "SYSTEM",
                        "severity": "INFO"
                    },
                    {
                        "timestamp": (base_time - timedelta(minutes=15)).isoformat(),
                        "action": "SIGNAL_MALFUNCTION",
                        "details": "Signal SIG_C1 reported communication error",
                        "user": "SYSTEM",
                        "severity": "ERROR"
                    },
                    {
                        "timestamp": (base_time - timedelta(minutes=30)).isoformat(),
                        "action": "USER_LOGIN",
                        "details": "User DISPATCHER_002 logged into the system",
                        "user": "DISPATCHER_002",
                        "severity": "INFO"
                    }
                ]
                
                self.logs_data.extend(additional_logs)
                self.filterLogs()
                
        except Exception as e:
            print(f"Error loading dummy data: {e}")
            
    def filterLogs(self):
        """Filter logs based on search criteria"""
        search_text = self.search_box.text().lower()
        severity_filter = self.severity_combo.currentText()
        
        self.filtered_logs = []
        
        for log in self.logs_data:
            # Search filter
            if search_text and search_text not in log['details'].lower() and search_text not in log['action'].lower():
                continue
                
            # Severity filter
            if severity_filter != "All" and log['severity'] != severity_filter:
                continue
                
            self.filtered_logs.append(log)
            
        self.updateLogsTable()
        
    def updateLogsTable(self):
        """Update the logs table display"""
        self.logs_table.setRowCount(len(self.filtered_logs))
        
        for row, log in enumerate(self.filtered_logs):
            # Timestamp
            timestamp = QtWidgets.QTableWidgetItem(log['timestamp'])
            self.logs_table.setItem(row, 0, timestamp)
            
            # Action
            action = QtWidgets.QTableWidgetItem(log['action'])
            self.logs_table.setItem(row, 1, action)
            
            # Details
            details = QtWidgets.QTableWidgetItem(log['details'])
            self.logs_table.setItem(row, 2, details)
            
            # Severity with color coding
            severity = QtWidgets.QTableWidgetItem(log['severity'])
            if log['severity'] == 'ERROR':
                severity.setBackground(QtGui.QColor(255, 200, 200))
            elif log['severity'] == 'WARNING':
                severity.setBackground(QtGui.QColor(255, 255, 200))
            elif log['severity'] == 'INFO':
                severity.setBackground(QtGui.QColor(200, 255, 200))
            elif log['severity'] == 'NOTICE':
                severity.setBackground(QtGui.QColor(220, 220, 255))
                
            self.logs_table.setItem(row, 3, severity)
            
        self.logs_table.resizeColumnsToContents()
        
        # Fix right-side cropping - ensure table uses full width
        header = self.logs_table.horizontalHeader()
        header.setStretchLastSection(True)
        header.setSectionResizeMode(QtWidgets.QHeaderView.Stretch)
        
        self.status_label.setText(f"Showing {len(self.filtered_logs)} of {len(self.logs_data)} log entries")
        
    def refreshLogs(self):
        """Refresh the logs data"""
        self.loadDummyData()
        
    def exportLogs(self):
        """Export filtered logs to CSV"""
        if not self.filtered_logs:
            QtWidgets.QMessageBox.warning(self, "No Data", "No logs to export.")
            return
            
        file_path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "Export Audit Logs",
            f"Audit_Logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            "CSV files (*.csv)"
        )
        
        if file_path:
            try:
                with open(file_path, 'w') as f:
                    f.write("Timestamp,Action,Details,User,Severity\n")
                    for log in self.filtered_logs:
                        timestamp = log["timestamp"]
                        action = log["action"]
                        details = log["details"]
                        user = log["user"]
                        severity = log["severity"]
                        f.write(f'"{timestamp}","{action}","{details}","{user}","{severity}"\n')
                
                QtWidgets.QMessageBox.information(self, "Export Complete", f"Logs exported to {file_path}")
            except Exception as e:
                QtWidgets.QMessageBox.critical(self, "Export Error", f"Failed to export logs: {str(e)}")
