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
    """Advanced What-If Analysis simulation view with modern UI"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.scenario_data = {
            'trains': [],
            'modifications': []
        }
        self.current_results = None
        self.setupUI()
        
    def setupUI(self):
        """Setup modern, clean what-if analysis UI"""
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # Modern base styling with minimal accent
        self.setStyleSheet("""
            QWidget {
                background-color: #fafbfc;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, system-ui, sans-serif;
            }
        """)
        
        # Scrollable container
        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QtWidgets.QFrame.NoFrame)
        scroll.setStyleSheet(self._getScrollAreaStyle())
        
        content = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(content)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        
        # Header section with actions
        self._setupHeaderSection(layout)
        
        # Main content in two-column layout
        content_layout = QtWidgets.QHBoxLayout()
        content_layout.setSpacing(10)
        
        # Left column - Configuration
        left_column = QtWidgets.QVBoxLayout()
        left_column.setSpacing(8)
        self._setupConfigurationSection(left_column)
        self._setupScenarioBuilder(left_column)
        
        left_widget = QtWidgets.QWidget()
        left_widget.setLayout(left_column)
        content_layout.addWidget(left_widget)
        
        # Right column - Results and Visualization
        right_column = QtWidgets.QVBoxLayout()
        right_column.setSpacing(8)
        self._setupResultsSection(right_column)
        
        right_widget = QtWidgets.QWidget()
        right_widget.setLayout(right_column)
        content_layout.addWidget(right_widget, stretch=1)
        
        layout.addLayout(content_layout)
        
        scroll.setWidget(content)
        main_layout.addWidget(scroll)
        
    def _setupHeaderSection(self, parent_layout):
        """Setup modern header with title and main actions"""
        header_widget = QtWidgets.QWidget()
        header_layout = QtWidgets.QHBoxLayout(header_widget)
        header_layout.setContentsMargins(0, 0, 0, 0)
        
        # Title and description
        title_layout = QtWidgets.QVBoxLayout()
        title_layout.setSpacing(4)
        
        title = QtWidgets.QLabel("What If Analysis")
        title.setStyleSheet("""
            font-size: 28px; 
            font-weight: 700; 
            color: #0f172a;
            margin: 0;
        """)
        title_layout.addWidget(title)
        
        subtitle = QtWidgets.QLabel("Model operational scenarios and predict system impacts")
        subtitle.setStyleSheet("""
            font-size: 16px; 
            color: #6b7280; 
            font-weight: 400;
            margin: 0;
        """)
        title_layout.addWidget(subtitle)
        header_layout.addLayout(title_layout)
        
        header_layout.addStretch()
        
        # Main action button
        actions_layout = QtWidgets.QHBoxLayout()
        actions_layout.setSpacing(12)
        
        self.run_analysis_btn = QtWidgets.QPushButton("Run Analysis")
        self.run_analysis_btn.clicked.connect(self.runAnalysis)
        self.run_analysis_btn.setStyleSheet(self._getPrimaryButtonStyle())
        actions_layout.addWidget(self.run_analysis_btn)
        
        header_layout.addLayout(actions_layout)
        parent_layout.addWidget(header_widget)
        
    def _setupConfigurationSection(self, parent_layout):
        """Setup scenario configuration section"""
        config_card = self._createCard("Configuration", "Set analysis parameters")
        config_layout = config_card.layout()
        
        # Time parameters only
        time_row = self._createFormRow("Analysis Period", 
            "Duration to simulate")
        self.duration_spin = QtWidgets.QSpinBox()
        self.duration_spin.setRange(30, 480)
        self.duration_spin.setValue(120)
        self.duration_spin.setSuffix(" min")
        self.duration_spin.setStyleSheet(self._getInputStyle())
        time_row.addWidget(self.duration_spin)
        config_layout.addLayout(time_row)
        
        parent_layout.addWidget(config_card)
        
    def _setupScenarioBuilder(self, parent_layout):
        """Setup the scenario builder section"""
        builder_card = self._createCard("Scenario Builder", "Add trains and modifications to test")
        builder_layout = builder_card.layout()
        
        # Tabs for different scenario elements
        tabs = QtWidgets.QTabWidget()
        tabs.setStyleSheet(self._getTabStyle())
        
        # Train Additions tab
        train_tab = QtWidgets.QWidget()
        train_layout = QtWidgets.QVBoxLayout(train_tab)
        train_layout.setSpacing(12)
        
        # Train addition form
        train_form = QtWidgets.QGridLayout()
        train_form.setVerticalSpacing(8)
        train_form.setHorizontalSpacing(12)
        
        train_form.addWidget(QtWidgets.QLabel("Type"), 0, 0)
        
        # Train type buttons
        type_widget = QtWidgets.QWidget()
        type_layout = QtWidgets.QHBoxLayout(type_widget)
        type_layout.setContentsMargins(0, 0, 0, 0)
        type_layout.setSpacing(6)
        
        self.train_type_group = QtWidgets.QButtonGroup()
        train_types = ["Express", "Regional", "Freight", "Maintenance"]
        self.train_type_buttons = {}
        
        for i, train_type in enumerate(train_types):
            btn = QtWidgets.QRadioButton(train_type)
            btn.setStyleSheet(self._getRadioButtonStyle())
            if i == 0:  # Select first by default
                btn.setChecked(True)
            self.train_type_group.addButton(btn, i)
            self.train_type_buttons[train_type] = btn
            type_layout.addWidget(btn)
            
        train_form.addWidget(type_widget, 0, 1, 1, 3)
        
        train_form.addWidget(QtWidgets.QLabel("Speed"), 1, 0)
        self.train_speed_spin = QtWidgets.QSpinBox()
        self.train_speed_spin.setRange(20, 200)
        self.train_speed_spin.setValue(80)
        self.train_speed_spin.setSuffix(" km/h")
        self.train_speed_spin.setStyleSheet(self._getInputStyle())
        train_form.addWidget(self.train_speed_spin, 1, 1)
        
        train_form.addWidget(QtWidgets.QLabel("Destination"), 1, 2)
        self.destination_input = QtWidgets.QLineEdit()
        self.destination_input.setPlaceholderText("e.g., Platform_1")
        self.destination_input.setText("Platform_1")
        self.destination_input.setStyleSheet(self._getInputStyle())
        train_form.addWidget(self.destination_input, 1, 3)
        
        train_form.addWidget(QtWidgets.QLabel("Arrival"), 2, 0)
        self.arrival_time = QtWidgets.QTimeEdit()
        self.arrival_time.setTime(QtCore.QTime.currentTime().addSecs(3600))
        self.arrival_time.setStyleSheet(self._getInputStyle())
        train_form.addWidget(self.arrival_time, 2, 1)
        
        train_layout.addLayout(train_form)
        
        # Add train button
        add_train_btn = QtWidgets.QPushButton("Add Train to Scenario")
        add_train_btn.clicked.connect(self.addTrainToScenario)
        add_train_btn.setStyleSheet(self._getSecondaryButtonStyle())
        train_layout.addWidget(add_train_btn)
        
        # Current trains list
        self.trains_list = QtWidgets.QListWidget()
        self.trains_list.setStyleSheet(self._getListStyle())
        # Improve text handling to avoid cropping
        self.trains_list.setWordWrap(True)
        self.trains_list.setTextElideMode(Qt.ElideRight)
        self.trains_list.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        train_layout.addWidget(self.trains_list)
        
        tabs.addTab(train_tab, "Trains")
        
        # Signal Modifications tab
        signal_tab = QtWidgets.QWidget()
        signal_layout = QtWidgets.QVBoxLayout(signal_tab)
        
        signal_form = QtWidgets.QVBoxLayout()
        signal_form.setSpacing(10)
        
        # Signal ID input
        id_row = QtWidgets.QHBoxLayout()
        id_row.addWidget(QtWidgets.QLabel("Signal ID:"))
        self.signal_id_input = QtWidgets.QLineEdit()
        self.signal_id_input.setPlaceholderText("e.g., SIG_A1")
        self.signal_id_input.setText("SIG_A1")
        self.signal_id_input.setStyleSheet(self._getInputStyle())
        id_row.addWidget(self.signal_id_input)
        signal_form.addLayout(id_row)
        
        # Signal status buttons
        status_label = QtWidgets.QLabel("New Status:")
        signal_form.addWidget(status_label)
        
        status_widget = QtWidgets.QWidget()
        status_layout = QtWidgets.QHBoxLayout(status_widget)
        status_layout.setContentsMargins(0, 0, 0, 0)
        status_layout.setSpacing(8)
        
        self.signal_status_group = QtWidgets.QButtonGroup()
        signal_statuses = ["GREEN", "YELLOW", "RED", "FLASHING"]
        self.signal_status_buttons = {}
        
        for i, status in enumerate(signal_statuses):
            btn = QtWidgets.QRadioButton(status)
            btn.setStyleSheet(self._getRadioButtonStyle())
            if i == 0:  # Select first by default
                btn.setChecked(True)
            self.signal_status_group.addButton(btn, i)
            self.signal_status_buttons[status] = btn
            status_layout.addWidget(btn)
            
        signal_form.addWidget(status_widget)
        
        signal_layout.addLayout(signal_form)
        
        add_signal_btn = QtWidgets.QPushButton("Add Signal Modification")
        add_signal_btn.clicked.connect(self.addSignalModification)
        add_signal_btn.setStyleSheet(self._getSecondaryButtonStyle())
        signal_layout.addWidget(add_signal_btn)
        
        self.modifications_list = QtWidgets.QListWidget()
        self.modifications_list.setStyleSheet(self._getListStyle())
        signal_layout.addWidget(self.modifications_list)
        
        tabs.addTab(signal_tab, "Signals")
        
        builder_layout.addWidget(tabs)
        parent_layout.addWidget(builder_card)
        
    def _setupResultsSection(self, parent_layout):
        """Setup the results visualization section"""
        results_card = self._createCard("Analysis Results", "Predicted impacts and recommendations")
        results_layout = results_card.layout()
        
        # Results tabs
        self.results_tabs = QtWidgets.QTabWidget()
        self.results_tabs.setStyleSheet(self._getTabStyle())
        
        # Metrics Overview
        metrics_widget = QtWidgets.QWidget()
        metrics_layout = QtWidgets.QGridLayout(metrics_widget)
        metrics_layout.setSpacing(16)
        
        self.throughput_card = self._createMetricCard("Throughput", "--", "trains/hour")
        self.delay_card = self._createMetricCard("Avg Delay", "--", "minutes")
        self.utilization_card = self._createMetricCard("Utilization", "--", "%")
        self.efficiency_card = self._createMetricCard("Efficiency", "--", "%")
        
        metrics_layout.addWidget(self.throughput_card, 0, 0)
        metrics_layout.addWidget(self.delay_card, 0, 1)
        metrics_layout.addWidget(self.utilization_card, 1, 0)
        metrics_layout.addWidget(self.efficiency_card, 1, 1)
        
        self.results_tabs.addTab(metrics_widget, "Metrics")
        
        # Recommendations
        recommendations_widget = QtWidgets.QWidget()
        recommendations_layout = QtWidgets.QVBoxLayout(recommendations_widget)
        
        self.recommendations_list = QtWidgets.QListWidget()
        self.recommendations_list.setStyleSheet(self._getRecommendationsStyle())
        self.recommendations_list.setWordWrap(True)
        self.recommendations_list.setTextElideMode(Qt.ElideRight)
        self.recommendations_list.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        recommendations_layout.addWidget(self.recommendations_list)
        
        self.results_tabs.addTab(recommendations_widget, "Suggestions")
        
        # Bottlenecks
        bottlenecks_widget = QtWidgets.QWidget()
        bottlenecks_layout = QtWidgets.QVBoxLayout(bottlenecks_widget)
        
        self.bottlenecks_list = QtWidgets.QListWidget()
        self.bottlenecks_list.setStyleSheet(self._getListStyle())
        self.bottlenecks_list.setWordWrap(True)
        self.bottlenecks_list.setTextElideMode(Qt.ElideRight)
        self.bottlenecks_list.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        bottlenecks_layout.addWidget(self.bottlenecks_list)
        
        self.results_tabs.addTab(bottlenecks_widget, "Threats")
        
        results_layout.addWidget(self.results_tabs)
        parent_layout.addWidget(results_card)
        
    
    # Helper methods for modern UI styling
    def _getScrollAreaStyle(self):
        """Modern scroll area styling"""
        return """
            QScrollArea {
                border: none;
                background-color: #fafbfc;
            }
            QScrollBar:vertical {
                background: transparent;
                width: 6px;
                border-radius: 3px;
            }
            QScrollBar::handle:vertical {
                background: #d1d5db;
                border-radius: 3px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background: #6b7280;
            }
        """
    
    def _createCard(self, title, subtitle=""):
        """Create a modern card widget with title"""
        card = QtWidgets.QWidget()
        card.setStyleSheet("""
            QWidget {
                background-color: white;
                border-radius: 12px;
                border: none;
            }
        """)
        
        layout = QtWidgets.QVBoxLayout(card)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)
        
        # Card header
        header_layout = QtWidgets.QVBoxLayout()
        header_layout.setSpacing(4)
        
        title_label = QtWidgets.QLabel(title)
        title_label.setStyleSheet("""
            font-size: 18px; 
            font-weight: 600; 
            color: #1e293b;
            margin: 0;
        """)
        header_layout.addWidget(title_label)
        
        if subtitle:
            subtitle_label = QtWidgets.QLabel(subtitle)
            subtitle_label.setStyleSheet("""
                font-size: 14px; 
                color: #64748b; 
                font-weight: 400;
                margin: 0;
            """)
            header_layout.addWidget(subtitle_label)
        
        layout.addLayout(header_layout)
        return card
    
    def _createFormRow(self, label_text, help_text=""):
        """Create a form row with label and help text"""
        row_layout = QtWidgets.QVBoxLayout()
        row_layout.setSpacing(6)
        
        label_layout = QtWidgets.QHBoxLayout()
        label = QtWidgets.QLabel(label_text)
        label.setStyleSheet("""
            font-size: 14px;
                font-weight: 500;
            color: #374151;
            margin: 0;
        """)
        label_layout.addWidget(label)
        label_layout.addStretch()
        
        if help_text:
            help_label = QtWidgets.QLabel(help_text)
            help_label.setStyleSheet("""
                font-size: 12px;
                color: #9ca3af;
                font-weight: 400;
            """)
            label_layout.addWidget(help_label)
        
        row_layout.addLayout(label_layout)
        return row_layout
    
    def _createMetricCard(self, title, value, unit=""):
        """Create a metric display card"""
        card = QtWidgets.QWidget()
        card.setStyleSheet("""
            QWidget {
                background-color: #f9fafb;
                border-radius: 10px;
                border: none;
                padding: 12px;
            }
        """)
        
        layout = QtWidgets.QVBoxLayout(card)
        layout.setSpacing(6)
        layout.setContentsMargins(8, 8, 8, 8)
        
        title_label = QtWidgets.QLabel(title)
        title_label.setStyleSheet("""
                font-size: 13px;
            font-weight: 500;
            color: #64748b;
            margin: 0;
        """)
        layout.addWidget(title_label)
        
        value_container = QtWidgets.QHBoxLayout()
        value_container.setSpacing(4)
        
        value_label = QtWidgets.QLabel(value)
        value_label.setStyleSheet("""
            font-size: 24px;
            font-weight: 700;
            color: #0f172a;
            margin: 0;
        """)
        value_container.addWidget(value_label)
        
        if unit:
            unit_label = QtWidgets.QLabel(unit)
            unit_label.setStyleSheet("""
                font-size: 14px;
                font-weight: 500;
                color: #64748b;
                margin: 0;
            """)
            value_container.addWidget(unit_label)
        
        value_container.addStretch()
        layout.addLayout(value_container)
        
        # Store references for updating
        setattr(card, 'value_label', value_label)
        setattr(card, 'unit_label', unit_label if unit else None)
        
        return card
    
    def _getInputStyle(self):
        """Modern input field styling"""
        return """
            QLineEdit, QSpinBox, QTimeEdit {
                padding: 8px 10px;
                border: none;
                border-radius: 8px;
                background-color: #f1f3f4;
                font-size: 14px;
                font-weight: 500;
                color: #1f2937;
                min-height: 18px;
            }
            QLineEdit:hover, QSpinBox:hover, QTimeEdit:hover {
                background-color: #e8eaed;
            }
            QLineEdit:focus, QSpinBox:focus, QTimeEdit:focus {
                background-color: #f9fafb;
                border: 2px solid #6b7280;
                outline: none;
            }
        """
    
    def _getRadioButtonStyle(self):
        """Modern radio button styling"""
        return """
            QRadioButton {
                font-size: 13px;
                font-weight: 500;
                color: #374151;
                spacing: 4px;
                padding: 4px 8px;
                border-radius: 4px;
                background-color: #f9fafb;
                border: 1px solid #e5e7eb;
            }
            QRadioButton:hover {
                background-color: #f3f4f6;
                border-color: #d1d5db;
            }
            QRadioButton:checked {
                background-color: #374151;
                color: white;
                border-color: #374151;
            }
            QRadioButton::indicator {
                width: 0px;
                height: 0px;
            }
        """
    
    def _getPrimaryButtonStyle(self):
        """Primary action button styling"""
        return """
            QPushButton {
                background-color: #374151;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 6px;
                font-weight: 600;
                font-size: 14px;
                min-width: 120px;
            }
            QPushButton:hover {
                background-color: #1f2937;
            }
            QPushButton:pressed {
                background-color: #111827;
            }
        """
    
    def _getSecondaryButtonStyle(self):
        """Secondary action button styling"""
        return """
            QPushButton {
                background-color: #f1f3f4;
                color: #374151;
                border: none;
                padding: 6px 12px;
                border-radius: 6px;
                font-weight: 500;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #e8eaed;
                color: #1f2937;
            }
            QPushButton:pressed {
                background-color: #dadce0;
            }
        """
    
    def _getTabStyle(self):
        """Modern tab widget styling"""
        return """
            QTabWidget::pane {
                border: none;
                border-radius: 10px;
                background-color: #fafbfc;
                padding: 8px;
            }
            QTabBar::tab {
                background-color: transparent;
                color: #6b7280;
                padding: 6px 12px;
                border: none;
                border-radius: 4px;
                font-weight: 500;
                margin-right: 3px;
                margin-bottom: 4px;
            }
            QTabBar::tab:selected {
                background-color: #374151;
                color: white;
            }
            QTabBar::tab:hover:!selected {
                background-color: #f1f3f4;
                color: #374151;
            }
        """
    
    def _getListStyle(self):
        """Modern list widget styling"""
        return """
            QListWidget {
                border: none;
                border-radius: 8px;
                background-color: #fafbfc;
                font-size: 14px;
                padding: 4px;
            }
            QListWidget::item {
                padding: 8px 10px;
                border: none;
                border-radius: 4px;
                margin: 1px 0;
                background-color: white;
            }
            QListWidget::item:hover {
                background-color: #f1f3f4;
            }
            QListWidget::item:selected {
                background-color: #374151;
                color: white;
            }
        """
    
    def _getRecommendationsStyle(self):
        """Special styling for recommendations list"""
        return """
            QListWidget {
                border: none;
                border-radius: 8px;
                background-color: #fafbfc;
                font-size: 14px;
                padding: 4px;
            }
            QListWidget::item {
                padding: 10px;
                border: none;
                border-radius: 4px;
                margin: 2px 0;
                background-color: #f6f6f7;
                color: #374151;
                font-weight: 500;
            }
            QListWidget::item:hover {
                background-color: #ededed;
            }
        """
    
    # Core functionality methods
        
    def addTrainToScenario(self):
        """Add train to current scenario"""
        # Get selected train type from radio buttons
        selected_type = "Express"  # default
        for train_type, button in self.train_type_buttons.items():
            if button.isChecked():
                selected_type = train_type
                break
        # Build train data after selection is resolved
        train_data = {
            'type': selected_type,
            'speed': self.train_speed_spin.value(),
            'destination': self.destination_input.text() or "Platform_1",
            'arrivalTime': self.arrival_time.time().toString("HH:mm:ss")
        }

        self.scenario_data['trains'].append(train_data)
        self._updateTrainsList()
        
    def addSignalModification(self):
        """Add signal modification to scenario"""
        # Get selected signal status from radio buttons
        selected_status = "GREEN"  # default
        for status, button in self.signal_status_buttons.items():
            if button.isChecked():
                selected_status = status
                break
        
        modification = {
            'type': 'SIGNAL_CHANGE',
            'signalId': self.signal_id_input.text() or "SIG_A1",
            'newStatus': selected_status
        }
        
        self.scenario_data['modifications'].append(modification)
        self._updateModificationsList()
        
    def _updateTrainsList(self):
        """Update the trains list display"""
        self.trains_list.clear()
        for i, train in enumerate(self.scenario_data['trains']):
            item_text = f"{train['type']} - {train['speed']}km/h to {train['destination']} at {train['arrivalTime']}"
            item = QtWidgets.QListWidgetItem(item_text)
            item.setData(QtCore.Qt.UserRole, i)
            self.trains_list.addItem(item)
            
    def _updateModificationsList(self):
        """Update the modifications list display"""
        self.modifications_list.clear()
        for i, mod in enumerate(self.scenario_data['modifications']):
            item_text = f"Set {mod['signalId']} to {mod['newStatus']}"
            item = QtWidgets.QListWidgetItem(item_text)
            item.setData(QtCore.Qt.UserRole, i)
            self.modifications_list.addItem(item)
            
    def newScenario(self):
        """Create a new scenario"""
        self.scenario_data = {
            'trains': [],
            'modifications': []
        }
        self.current_results = None
        self._updateTrainsList()
        self._updateModificationsList()
        self._clearResults()
        
    def runAnalysis(self):
        """Run the comprehensive what-if analysis"""
        if not self.scenario_data['trains'] and not self.scenario_data['modifications']:
            QtWidgets.QMessageBox.information(self, "Empty Scenario", 
                "Please add trains or signal modifications to analyze.")
            return
            
        QtWidgets.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)
        
        try:
            # Enhanced simulation logic
            results = self._calculatePredictedResults()
            self.current_results = results
            self._displayResults(results)
            
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Analysis Error", f"Failed to run analysis: {str(e)}")
        finally:
            QtWidgets.QApplication.restoreOverrideCursor()
            
    def _calculatePredictedResults(self):
        """Calculate predicted results with enhanced logic"""
        trains = self.scenario_data['trains']
        modifications = self.scenario_data['modifications']
        duration = self.duration_spin.value()
        
        # Train type analysis
        train_counts = {'Express': 0, 'Regional': 0, 'Freight': 0, 'Maintenance': 0}
        total_speed = 0
        for train in trains:
            train_counts[train['type']] += 1
            total_speed += train['speed']
            
        total_trains = len(trains)
        avg_speed = total_speed / total_trains if total_trains > 0 else 0
        
        # Signal impact analysis
        signal_delays = len([m for m in modifications if m['newStatus'] in ['RED', 'YELLOW']]) * 0.5
        signal_improvements = len([m for m in modifications if m['newStatus'] == 'GREEN']) * -0.2
        
        # Predicted metrics calculation
        base_throughput = min(total_trains * (avg_speed / 80) * 1.5, 300)
        predicted_throughput = max(0, base_throughput - signal_delays * 10 + signal_improvements * 5)
        
        congestion_factor = max(0, (total_trains - 10) * 0.3)
        predicted_delay = max(0, congestion_factor + signal_delays - signal_improvements)
        
        predicted_utilization = min((total_trains / 15) * 100, 100)
        predicted_efficiency = max(0, 95 - congestion_factor * 2 - signal_delays * 3)
        
        # Generate recommendations
        recommendations = []
        bottlenecks = []
        
        if total_trains > 12:
            recommendations.append("Consider reducing train frequency during peak times")
            bottlenecks.append("High train density may cause congestion")
            
        if train_counts['Express'] > train_counts['Regional']:
            recommendations.append("Balance express and regional services")
            
        if signal_delays > 0:
            recommendations.append("Review signal timing to minimize delays")
            bottlenecks.append("Signal restrictions creating bottlenecks")
        else:
            recommendations.append("Signal configuration appears optimal")
            
        if predicted_delay < 2:
            recommendations.append("Operations should run smoothly with this configuration")
        elif predicted_delay > 5:
            recommendations.append("Consider staggering arrivals to reduce delays")
            
        return {
            'throughput': predicted_throughput,
            'delay': predicted_delay,
            'utilization': predicted_utilization,
            'efficiency': predicted_efficiency,
            'recommendations': recommendations,
            'bottlenecks': bottlenecks,
            'train_counts': train_counts,
            'confidence': 0.85
        }
        
    def _displayResults(self, results):
        """Display results in the modern UI"""
        # Update metric cards
        self.throughput_card.value_label.setText(f"{results['throughput']:.1f}")
        self.delay_card.value_label.setText(f"{results['delay']:.1f}")
        self.utilization_card.value_label.setText(f"{results['utilization']:.1f}")
        self.efficiency_card.value_label.setText(f"{results['efficiency']:.1f}")
        
        # Update recommendations
        self.recommendations_list.clear()
        for rec in results['recommendations']:
            item = QtWidgets.QListWidgetItem(rec)
            self.recommendations_list.addItem(item)
            
        # Update bottlenecks
        self.bottlenecks_list.clear()
        for bottleneck in results['bottlenecks']:
            item = QtWidgets.QListWidgetItem(bottleneck)
            self.bottlenecks_list.addItem(item)
            
    def _clearResults(self):
        """Clear all results displays"""
        self.throughput_card.value_label.setText("--")
        self.delay_card.value_label.setText("--")
        self.utilization_card.value_label.setText("--")
        self.efficiency_card.value_label.setText("--")
        
        self.recommendations_list.clear()
        self.bottlenecks_list.clear()
        


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
        self.severity_combo.setStyleSheet(self._getComboBoxStyle("#ef4444"))  # Red theme
        self.severity_combo.currentTextChanged.connect(self.filterLogs)
        controls_row.addWidget(self.severity_combo)
        
        controls_row.addSpacing(20)
        
        # Category filter
        category_label = QtWidgets.QLabel("Category")
        category_label.setStyleSheet("color: #64748b; font-weight: 500; font-size: 14px;")
        controls_row.addWidget(category_label)
        
        self.category_combo = QtWidgets.QComboBox()
        self.category_combo.addItems(["All", "route", "signal", "train", "system"])
        self.category_combo.setStyleSheet(self._getComboBoxStyle("#8b5cf6"))  # Purple theme
        self.category_combo.currentTextChanged.connect(self.filterLogs)
        controls_row.addWidget(self.category_combo)
        
        controls_row.addSpacing(20)
        
        # Time range
        time_label = QtWidgets.QLabel("Time Range")
        time_label.setStyleSheet("color: #64748b; font-weight: 500; font-size: 14px;")
        controls_row.addWidget(time_label)
        
        self.time_range_combo = QtWidgets.QComboBox()
        self.time_range_combo.addItems(["All Time", "Last Hour", "Last 6 Hours", "Today", "Last 7 Days"])
        self.time_range_combo.setStyleSheet(self._getComboBoxStyle("#10b981"))  # Green theme
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
        self.logs_table.setColumnCount(7)
        self.logs_table.setHorizontalHeaderLabels(["ID", "Timestamp", "Event", "Category", "Object", "Details", "Severity"])
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
                background-color: #e5e7eb;
                color: #111827;
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
        
    def _getComboBoxStyle(self, accent_color):
        """Get consistent combo box styling with accent color"""
        return f"""
            QComboBox {{
                padding: 8px 12px;
                border: 2px solid #e5e7eb;
                border-radius: 8px;
                background-color: white;
                font-size: 14px;
                font-weight: 500;
                color: #1f2937;
                min-width: 100px;
            }}
            QComboBox:hover {{
                border-color: {accent_color};
                background-color: #f8fafc;
            }}
            QComboBox:focus {{
                border-color: {accent_color};
                background-color: white;
            }}
            QComboBox QAbstractItemView {{
                border: 2px solid #e5e7eb;
                border-radius: 8px;
                background-color: white;
                selection-background-color: {accent_color};
                selection-color: white;
                padding: 4px;
            }}
            QComboBox QAbstractItemView::item {{
                padding: 8px 12px;
                border-radius: 4px;
                margin: 2px;
            }}
            QComboBox QAbstractItemView::item:hover {{
                background-color: #f1f5f9;
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
            # ID (serial number)
            id_text = log.get('id', '') or str(row + 1)
            id_item = QtWidgets.QTableWidgetItem(id_text)
            id_item.setFont(QtGui.QFont("monospace", 10))
            id_item.setTextAlignment(Qt.AlignCenter)
            id_item.setForeground(QtGui.QColor("#6b7280"))
            self.logs_table.setItem(row, 0, id_item)

            # Timestamp
            ts_text = log.get('timestamp', '')
            timestamp = QtWidgets.QTableWidgetItem(ts_text)
            self.logs_table.setItem(row, 1, timestamp)

            # Event
            event_text = log.get('event', '')
            self.logs_table.setItem(row, 2, QtWidgets.QTableWidgetItem(event_text))

            # Category
            cat_text = log.get('category', '')
            self.logs_table.setItem(row, 3, QtWidgets.QTableWidgetItem(cat_text))

            # Object (compact)
            obj_text = log.get('object', '')
            self.logs_table.setItem(row, 4, QtWidgets.QTableWidgetItem(obj_text))

            # Details (pretty)
            det_text = log.get('details', '')
            self.logs_table.setItem(row, 5, QtWidgets.QTableWidgetItem(det_text))

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
            self.logs_table.setItem(row, 6, severity_item)
            
        self.logs_table.resizeColumnsToContents()
        
        # Set specific column sizing for better visibility
        header = self.logs_table.horizontalHeader()
        
        # ID column - fixed narrow width
        header.setSectionResizeMode(0, QtWidgets.QHeaderView.Fixed)
        self.logs_table.setColumnWidth(0, 60)
        
        # Timestamp - fixed reasonable width
        header.setSectionResizeMode(1, QtWidgets.QHeaderView.Fixed)
        self.logs_table.setColumnWidth(1, 150)
        
        # Event - resize to contents
        header.setSectionResizeMode(2, QtWidgets.QHeaderView.ResizeToContents)
        
        # Category - resize to contents
        header.setSectionResizeMode(3, QtWidgets.QHeaderView.ResizeToContents)
        
        # Object - resize to contents
        header.setSectionResizeMode(4, QtWidgets.QHeaderView.ResizeToContents)
        
        # Details - stretch to fill remaining space
        header.setSectionResizeMode(5, QtWidgets.QHeaderView.Stretch)
        
        # Severity - fixed compact width
        header.setSectionResizeMode(6, QtWidgets.QHeaderView.Fixed)
        self.logs_table.setColumnWidth(6, 80)
        
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
                    f.write("id,timestamp,event,category,object,details,severity\n")
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
        # Map API response to flattened strings for table display
        if not isinstance(it, dict):
            return None
            
        # Handle both API formats: server API uses 'action', dummy data might use 'event'
        event = it.get('action') or it.get('event', '')
        
        # Extract object information from metadata field
        metadata = it.get('metadata') or {}
        obj_str_parts = []
        if isinstance(metadata, dict):
            # Extract train information
            if metadata.get('trainId'):
                obj_str_parts.append(f"Train:{metadata.get('trainId')}")
            # Extract signal information  
            if metadata.get('signalId'):
                obj_str_parts.append(f"Signal:{metadata.get('signalId')}")
            # Extract section information
            if metadata.get('section'):
                obj_str_parts.append(f"Section:{metadata.get('section')}")
            # Add any other relevant context
            if metadata.get('serviceCode'):
                obj_str_parts.append(f"Service:{metadata.get('serviceCode')}")
        obj_str = " / ".join(obj_str_parts)
        
        # Determine category based on action/event type
        category = ""
        if event:
            if "TRAIN" in event.upper():
                category = "Train Operations"
            elif "SIGNAL" in event.upper():
                category = "Signal Control"
            elif "MAINTENANCE" in event.upper():
                category = "Maintenance"
            elif "MANUAL" in event.upper() or "OVERRIDE" in event.upper():
                category = "Manual Operations"
            else:
                category = "System"

        # Handle details field
        details = it.get('details')
        if isinstance(details, dict):
            try:
                # Compact JSON for display
                details_str = json.dumps(details, separators=(",", ":"))
            except Exception:
                details_str = str(details)
        else:
            details_str = str(details) if details is not None else ""

        # Handle user field - API uses 'userId', dummy data uses 'user'
        user_id = it.get('userId') or it.get('user', '')

        entry = {
            "id": it.get('id', ''),
            "timestamp": it.get('timestamp', ''),
            "event": event,
            "category": category,
            "severity": it.get('severity', ''),
            "object": obj_str,
            "details": details_str,
            "userId": user_id,
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
