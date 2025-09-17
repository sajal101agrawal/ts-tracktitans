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
from .analytics_provider import AuditLogsProvider

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
        self._provider = AuditLogsProvider()
        self._provider.itemsAdded.connect(self.onItemsAdded)
        self._provider.itemReceived.connect(self.onItemReceived)
        self._provider.streamStatusChanged.connect(self.onStreamStatus)
        self._provider.errorOccurred.connect(self.onProviderError)
        self._last_id = 0
        self.setupUI()
        # Kick off initial backfill + live stream
        QtCore.QTimer.singleShot(0, lambda: self._provider.start(since_id=self._last_id, limit=500))
        
    def setupUI(self):
        """Setup modern audit logs UI matching KPI dashboard design"""
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # Set modern background
        self.setStyleSheet("""
            QWidget {
                background-color: #f8fafc;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            }
        """)

        # Scrollable container
        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QtWidgets.QFrame.NoFrame)
        scroll.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: #f8fafc;
            }
            QScrollBar:vertical {
                background: #e2e8f0;
                width: 8px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background: #cbd5e1;
                border-radius: 4px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background: #94a3b8;
            }
        """)
        
        content = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(content)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)
        
        # Modern controls row
        controls_row = QtWidgets.QHBoxLayout()
        
        # Search box
        search_label = QtWidgets.QLabel("Search")
        search_label.setStyleSheet("color: #64748b; font-weight: 500; font-size: 14px;")
        controls_row.addWidget(search_label)
        
        self.search_box = QtWidgets.QLineEdit()
        self.search_box.setPlaceholderText("Search in logs...")
        self.search_box.setStyleSheet("""
            QLineEdit {
                padding: 10px 16px;
                border: 2px solid #e5e7eb;
                border-radius: 10px;
                background-color: white;
                font-size: 14px;
                font-weight: 500;
                color: #1f2937;
                min-width: 200px;
            }
            QLineEdit:hover {
                border-color: #3b82f6;
                background-color: #f8fafc;
            }
            QLineEdit:focus {
                border-color: #3b82f6;
                background-color: white;
                box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
                outline: none;
            }
        """)
        self.search_box.textChanged.connect(self.filterLogs)
        controls_row.addWidget(self.search_box)
        
        controls_row.addSpacing(20)
        
        # Severity filter
        severity_label = QtWidgets.QLabel("Severity")
        severity_label.setStyleSheet("color: #64748b; font-weight: 500; font-size: 14px;")
        controls_row.addWidget(severity_label)
        
        self.severity_combo = QtWidgets.QComboBox()
        self.severity_combo.addItems(["All", "INFO", "WARNING", "ERROR", "NOTICE"])
        self.severity_combo.setStyleSheet(self._getMinimalComboBoxStyle("#ef4444"))
        self.severity_combo.currentTextChanged.connect(self.filterLogs)
        controls_row.addWidget(self.severity_combo)
        
        controls_row.addSpacing(20)
        
        # Category filter
        category_label = QtWidgets.QLabel("Category")
        category_label.setStyleSheet("color: #64748b; font-weight: 500; font-size: 14px;")
        controls_row.addWidget(category_label)
        
        self.category_combo = QtWidgets.QComboBox()
        self.category_combo.addItems(["All", "route", "signal", "train", "system"])
        self.category_combo.setStyleSheet(self._getMinimalComboBoxStyle("#8b5cf6"))
        self.category_combo.currentTextChanged.connect(self.filterLogs)
        controls_row.addWidget(self.category_combo)
        
        controls_row.addSpacing(20)
        
        # Time range
        time_label = QtWidgets.QLabel("Time Range")
        time_label.setStyleSheet("color: #64748b; font-weight: 500; font-size: 14px;")
        controls_row.addWidget(time_label)
        
        self.time_range_combo = QtWidgets.QComboBox()
        self.time_range_combo.addItems(["All Time", "Last Hour", "Last 6 Hours", "Today", "Last 7 Days"])
        self.time_range_combo.setStyleSheet(self._getMinimalComboBoxStyle("#10b981"))
        self.time_range_combo.currentTextChanged.connect(self.filterLogs)
        controls_row.addWidget(self.time_range_combo)
        
        controls_row.addStretch()
        
        # Action buttons
        self.refresh_btn = QtWidgets.QPushButton("Refresh")
        self.refresh_btn.clicked.connect(self.refreshLogs)
        self.refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: #f3f4f6;
                color: #374151;
                border: 1px solid #d1d5db;
                padding: 8px 16px;
                border-radius: 8px;
                font-weight: 500;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #e5e7eb;
            }
            QPushButton:pressed {
                background-color: #d1d5db;
            }
        """)
        controls_row.addWidget(self.refresh_btn)
        
        self.export_logs_btn = QtWidgets.QPushButton("Export")
        self.export_logs_btn.clicked.connect(self.exportLogs)
        self.export_logs_btn.setStyleSheet("""
            QPushButton {
                background-color: #3b82f6;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 8px;
                font-weight: 600;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #2563eb;
            }
            QPushButton:pressed {
                background-color: #1d4ed8;
            }
        """)
        controls_row.addWidget(self.export_logs_btn)
        
        layout.addLayout(controls_row)
        
        # Modern table container
        table_container = QtWidgets.QWidget()
        table_container.setStyleSheet("""
            QWidget {
                background-color: white;
                border-radius: 12px;
                border: 1px solid #e5e7eb;
            }
        """)
        table_layout = QtWidgets.QVBoxLayout(table_container)
        table_layout.setContentsMargins(0, 0, 0, 0)
        
        # Modern table
        self.logs_table = QtWidgets.QTableWidget()
        self.logs_table.setColumnCount(6)
        self.logs_table.setHorizontalHeaderLabels(["Timestamp", "Event", "Category", "Object", "Details", "Severity"])
        self.logs_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.logs_table.setAlternatingRowColors(True)
        self.logs_table.setSortingEnabled(True)
        self.logs_table.setStyleSheet("""
            QTableWidget {
                border: none;
                border-radius: 12px;
                background-color: white;
                gridline-color: #f1f5f9;
                font-size: 13px;
            }
            QTableWidget::item {
                padding: 8px;
                border-bottom: 1px solid #f1f5f9;
            }
            QTableWidget::item:selected {
                background-color: #eff6ff;
                color: #1e40af;
            }
            QHeaderView::section {
                background-color: #f8fafc;
                padding: 12px 8px;
                border: none;
                border-bottom: 2px solid #e5e7eb;
                font-weight: 600;
                color: #374151;
            }
            QTableWidget::item:alternate {
                background-color: #f9fafb;
            }
        """)
        table_layout.addWidget(self.logs_table)
        
        layout.addWidget(table_container)
        
        # Modern status info
        self.status_label = QtWidgets.QLabel()
        self.status_label.setStyleSheet("""
            color: #9ca3af; 
            font-size: 13px;
            font-weight: 500;
            padding: 8px 0;
        """)
        layout.addWidget(self.status_label)
        
        scroll.setWidget(content)
        main_layout.addWidget(scroll)
        
    def _getMinimalComboBoxStyle(self, accent_color="#374151"):
        """Get ultra-minimal combo box styling with no margins/padding"""
        return f"""
            QComboBox {{
                padding: 4px 20px 4px 8px;
                border: 1px solid #d1d5db;
                border-radius: 0;
                background-color: white;
                font-size: 13px;
                color: #374151;
                min-width: 80px;
                min-height: 24px;
            }}
            QComboBox:hover {{
                border-color: {accent_color};
            }}
            QComboBox:focus {{
                border-color: {accent_color};
                outline: none;
            }}
            QComboBox::drop-down {{
                subcontrol-origin: padding;
                subcontrol-position: center right;
                width: 16px;
                border: none;
                background-color: transparent;
            }}
            QComboBox::down-arrow {{
                image: none;
                width: 0;
                height: 0;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 6px solid #6b7280;
                margin: 0;
            }}
            QComboBox:hover::down-arrow {{
                border-top-color: {accent_color};
            }}
            QComboBox:open::down-arrow {{
                border-top: none;
                border-bottom: 6px solid {accent_color};
            }}
            QComboBox QAbstractItemView {{
                border: 1px solid #d1d5db;
                background-color: white;
                selection-background-color: {accent_color};
                selection-color: white;
                padding: 0;
                margin: 0;
                outline: none;
            }}
            QComboBox QAbstractItemView::item {{
                padding: 4px 8px;
                margin: 0;
                border: none;
                color: #374151;
                font-size: 13px;
            }}
            QComboBox QAbstractItemView::item:hover {{
                background-color: #f3f4f6;
                color: #374151;
            }}
            QComboBox QAbstractItemView::item:selected {{
                background-color: {accent_color};
                color: white;
            }}
        """
        
    def onItemsAdded(self, items):
        # Normalize to our in-memory representation and append
        changed = False
        for it in items:
            entry = self._map_api_item(it)
            if entry is not None:
                self.logs_data.append(entry)
                # track last id
                try:
                    n = int(it.get('id', 0))
                    if n > self._last_id:
                        self._last_id = n
                except Exception:
                    pass
                changed = True
        if changed:
            self.filterLogs()

    def onItemReceived(self, it):
        entry = self._map_api_item(it)
        if entry is not None:
            self.logs_data.append(entry)
            try:
                n = int(it.get('id', 0))
                if n > self._last_id:
                    self._last_id = n
            except Exception:
                pass
            self.filterLogs()

    def onStreamStatus(self, connected):
        self._setStatus(connected=connected)

    def onProviderError(self, message):
        self._setStatus(error=message)
            
    def filterLogs(self):
        """Filter logs based on search criteria"""
        search_text = self.search_box.text().lower()
        severity_filter = self.severity_combo.currentText()
        category_filter = self.category_combo.currentText()
        
        self.filtered_logs = []
        
        for log in self.logs_data:
            # Search filter: include event, details, category, object string
            hay = f"{log.get('event','')} {log.get('details','')} {log.get('category','')} {log.get('object','')}".lower()
            if search_text and search_text not in hay:
                continue

            # Severity filter
            if severity_filter != "All" and log.get('severity') != severity_filter:
                continue

            # Category filter
            if category_filter != "All" and log.get('category') != category_filter:
                continue

            self.filtered_logs.append(log)
            
        self.updateLogsTable()
        
    def updateLogsTable(self):
        """Update the logs table display"""
        self.logs_table.setRowCount(len(self.filtered_logs))

        for row, log in enumerate(self.filtered_logs):
            # Timestamp
            ts_text = log.get('timestamp', '')
            timestamp = QtWidgets.QTableWidgetItem(ts_text)
            self.logs_table.setItem(row, 0, timestamp)

            # Event
            event_text = log.get('event', '')
            self.logs_table.setItem(row, 1, QtWidgets.QTableWidgetItem(event_text))

            # Category
            cat_text = log.get('category', '')
            self.logs_table.setItem(row, 2, QtWidgets.QTableWidgetItem(cat_text))

            # Object (compact)
            obj_text = log.get('object', '')
            self.logs_table.setItem(row, 3, QtWidgets.QTableWidgetItem(obj_text))

            # Details (pretty)
            det_text = log.get('details', '')
            self.logs_table.setItem(row, 4, QtWidgets.QTableWidgetItem(det_text))

            # Severity with color coding
            sev = (log.get('severity') or '').upper()
            severity_item = QtWidgets.QTableWidgetItem(sev)
            if sev == 'ERROR':
                severity_item.setBackground(QtGui.QColor(255, 200, 200))
            elif sev == 'WARNING' or sev == 'WARN':
                severity_item.setBackground(QtGui.QColor(255, 255, 200))
            elif sev == 'INFO':
                severity_item.setBackground(QtGui.QColor(200, 255, 200))
            elif sev == 'NOTICE':
                severity_item.setBackground(QtGui.QColor(220, 220, 255))
            self.logs_table.setItem(row, 5, severity_item)
            
        self.logs_table.resizeColumnsToContents()
        
        # Fix right-side cropping - ensure table uses full width
        header = self.logs_table.horizontalHeader()
        header.setStretchLastSection(True)
        header.setSectionResizeMode(QtWidgets.QHeaderView.Stretch)
        
        self.status_label.setText(f"Showing {len(self.filtered_logs)} of {len(self.logs_data)} log entries")
        
    def refreshLogs(self):
        """Refresh the logs data from server (HTTP backfill)."""
        self._provider.backfill(limit=500)
        
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
                    f.write("id,timestamp,event,category,severity,object,details\n")
                    for log in self.filtered_logs:
                        id_ = log.get("id", "")
                        timestamp = log.get("timestamp", "")
                        event = log.get("event", "")
                        category = log.get("category", "")
                        severity = log.get("severity", "")
                        obj = log.get("object", "")
                        details = log.get("details", "").replace('\n', ' ')
                        f.write(f'"{id_}","{timestamp}","{event}","{category}","{severity}","{obj}","{details}"\n')
                
                QtWidgets.QMessageBox.information(self, "Export Complete", f"Logs exported to {file_path}")
            except Exception as e:
                QtWidgets.QMessageBox.critical(self, "Export Error", f"Failed to export logs: {str(e)}")

    def _map_api_item(self, it):
        # Expect shape per new API; map to flattened strings for table
        if not isinstance(it, dict):
            return None
        obj = it.get('object') or {}
        obj_str_parts = []
        if isinstance(obj, dict):
            if obj.get('type'):
                obj_str_parts.append(str(obj.get('type')))
            if obj.get('id'):
                obj_str_parts.append(str(obj.get('id')))
            if obj.get('serviceCode'):
                obj_str_parts.append(str(obj.get('serviceCode')))
        obj_str = " / ".join(obj_str_parts)

        details = it.get('details')
        if isinstance(details, dict):
            try:
                # Compact JSON for display
                details_str = json.dumps(details, separators=(",", ":"))
            except Exception:
                details_str = str(details)
        else:
            details_str = str(details) if details is not None else ""

        entry = {
            "id": it.get('id', ''),
            "timestamp": it.get('timestamp', ''),
            "event": it.get('event', ''),
            "category": it.get('category', ''),
            "severity": it.get('severity', ''),
            "object": obj_str,
            "details": details_str,
        }
        return entry

    def _setStatus(self, connected=None, error=None):
        # Update status footer text
        parts = [f"Showing {len(self.filtered_logs)} of {len(self.logs_data)} log entries"]
        if connected is not None:
            parts.append("Live: ON" if connected else "Live: OFF")
        if error:
            parts.append(f"Error: {error}")
        self.status_label.setText(" | ".join(parts))
