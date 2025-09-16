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
import random
from datetime import datetime


class AIHintsSystem(QtCore.QObject):
    """AI-powered hints system for train routing optimization"""
    
    # Signal emitted when new hints are available
    hintsUpdated = QtCore.pyqtSignal(list)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_hints = []
        self.hint_timer = QtCore.QTimer()
        self.hint_timer.timeout.connect(self.generateHints)
        self.hint_timer.setInterval(180000)  # 3 minutes
        
    def startHintGeneration(self):
        """Start automatic hint generation"""
        self.generateHints()  # Generate initial hints
        self.hint_timer.start()
        
    def stopHintGeneration(self):
        """Stop automatic hint generation"""
        self.hint_timer.stop()
        
    def generateHints(self):
        """Generate AI hints based on current simulation state"""
        # In a real implementation, this would analyze:
        # - Current traffic patterns
        # - Historical performance data
        # - Predicted bottlenecks
        # - Optimization opportunities
        
        # Mock AI hint generation
        hint_templates = [
            {
                "type": "OPTIMIZATION",
                "priority": "HIGH",
                "template": "Train {train_id} in section {section} should be rerouted via {alt_route} to avoid predicted 5-minute delay",
                "reasoning": "Current route shows congestion patterns. Alternative route has 85% efficiency and reduces overall system delay by 12%.",
                "action": "REROUTE"
            },
            {
                "type": "PREEMPTIVE",
                "priority": "MEDIUM", 
                "template": "Signal {signal_id} should switch to {new_state} in 2 minutes to optimize flow for incoming trains",
                "reasoning": "Predictive modeling shows 15% throughput improvement with preemptive signal timing adjustment.",
                "action": "SIGNAL_CHANGE"
            },
            {
                "type": "EFFICIENCY",
                "priority": "LOW",
                "template": "Platform {platform} can accommodate express train {train_id} instead of regional service for better utilization",
                "reasoning": "Platform optimization algorithm suggests 23% better passenger-per-minute ratio with this swap.",
                "action": "PLATFORM_SWAP"
            },
            {
                "type": "MAINTENANCE",
                "priority": "MEDIUM",
                "template": "Section {section} maintenance window optimal between {start_time}-{end_time} with minimal traffic impact",
                "reasoning": "Traffic analysis shows lowest utilization period. Estimated 3% total system impact vs 18% at peak hours.",
                "action": "SCHEDULE_MAINTENANCE"
            }
        ]
        
        new_hints = []
        
        # Generate 2-4 random hints
        num_hints = random.randint(2, 4)
        selected_templates = random.sample(hint_templates, min(num_hints, len(hint_templates)))
        
        for template in selected_templates:
            hint = self.generateSpecificHint(template)
            new_hints.append(hint)
            
        self.current_hints = new_hints
        self.hintsUpdated.emit(self.current_hints)
        
    def generateSpecificHint(self, template):
        """Generate a specific hint from template"""
        # Mock data for hint generation
        trains = ["T001", "T002", "T003", "T004", "T005"]
        sections = ["SEC_A", "SEC_B", "SEC_C"]
        signals = ["SIG_A1", "SIG_A2", "SIG_B1", "SIG_C1"]
        platforms = ["Platform_1", "Platform_2", "Platform_3"]
        routes = ["Route_North", "Route_South", "Route_Express"]
        signal_states = ["GREEN", "YELLOW", "RED"]
        
        hint = {
            "id": f"hint_{random.randint(1000, 9999)}",
            "type": template["type"],
            "priority": template["priority"],
            "timestamp": datetime.now().isoformat(),
            "confidence": random.randint(75, 95),
            "action": template["action"],
            "reasoning": template["reasoning"],
            "accepted": False,
            "dismissed": False
        }
        
        # Fill in template variables
        message = template["template"]
        message = message.replace("{train_id}", random.choice(trains))
        message = message.replace("{section}", random.choice(sections))
        message = message.replace("{signal_id}", random.choice(signals))
        message = message.replace("{platform}", random.choice(platforms))
        message = message.replace("{alt_route}", random.choice(routes))
        message = message.replace("{new_state}", random.choice(signal_states))
        message = message.replace("{start_time}", "14:30")
        message = message.replace("{end_time}", "15:15")
        
        hint["message"] = message
        
        return hint


class AIHintsWidget(QtWidgets.QWidget):
    """Widget to display and manage AI hints"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.ai_system = AIHintsSystem(self)
        self.ai_system.hintsUpdated.connect(self.updateHints)
        self.hint_widgets = []
        self.setupUI()
        
    def setupUI(self):
        """Setup the AI hints UI"""
        layout = QtWidgets.QVBoxLayout(self)
        
        # Header
        header = QtWidgets.QWidget()
        header_layout = QtWidgets.QHBoxLayout(header)
        
        title = QtWidgets.QLabel("AI Routing Hints")
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #495057;")
        header_layout.addWidget(title)
        
        header_layout.addStretch()
        
        # Controls
        self.auto_hint_cb = QtWidgets.QCheckBox("Auto-generate (3 min)")
        self.auto_hint_cb.setChecked(True)
        self.auto_hint_cb.toggled.connect(self.toggleAutoHints)
        header_layout.addWidget(self.auto_hint_cb)
        
        self.manual_hint_btn = QtWidgets.QPushButton("Generate Now")
        self.manual_hint_btn.clicked.connect(self.ai_system.generateHints)
        header_layout.addWidget(self.manual_hint_btn)
        
        layout.addWidget(header)
        
        # Hints container
        self.hints_scroll = QtWidgets.QScrollArea()
        self.hints_scroll.setWidgetResizable(True)
        self.hints_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        self.hints_container = QtWidgets.QWidget()
        self.hints_layout = QtWidgets.QVBoxLayout(self.hints_container)
        self.hints_layout.setContentsMargins(5, 5, 5, 5)
        self.hints_layout.setSpacing(10)
        
        self.hints_scroll.setWidget(self.hints_container)
        layout.addWidget(self.hints_scroll)
        
        # Start AI system
        self.ai_system.startHintGeneration()
        
    def toggleAutoHints(self, enabled):
        """Toggle automatic hint generation"""
        if enabled:
            self.ai_system.startHintGeneration()
        else:
            self.ai_system.stopHintGeneration()
            
    def updateHints(self, hints):
        """Update the hints display"""
        # Clear existing hint widgets
        for widget in self.hint_widgets:
            widget.deleteLater()
        self.hint_widgets.clear()
        
        # Add new hint widgets
        for hint in hints:
            hint_widget = self.createHintWidget(hint)
            self.hint_widgets.append(hint_widget)
            self.hints_layout.addWidget(hint_widget)
            
        # Add stretch at the end
        self.hints_layout.addStretch()
        
    def createHintWidget(self, hint):
        """Create a widget for a single hint"""
        widget = QtWidgets.QFrame()
        widget.setFrameStyle(QtWidgets.QFrame.StyledPanel)
        
        # Color code by priority
        if hint["priority"] == "HIGH":
            border_color = "#868e96"
            bg_color = "#ffebee"
        elif hint["priority"] == "MEDIUM":
            border_color = "#6c757d" 
            bg_color = "#fff3e0"
        else:
            border_color = "#495057"
            bg_color = "#e8f5e9"
            
        widget.setStyleSheet(f"""
            QFrame {{
                border: 2px solid {border_color};
                border-radius: 8px;
                background-color: {bg_color};
                margin: 2px;
                padding: 5px;
            }}
        """)
        
        layout = QtWidgets.QVBoxLayout(widget)
        
        # Header with priority and confidence
        header_layout = QtWidgets.QHBoxLayout()
        
        priority_label = QtWidgets.QLabel(f"{hint['priority']} PRIORITY")
        priority_label.setStyleSheet(f"color: {border_color}; font-weight: bold; font-size: 12px;")
        header_layout.addWidget(priority_label)
        
        header_layout.addStretch()
        
        confidence_label = QtWidgets.QLabel(f"Confidence: {hint['confidence']}%")
        confidence_label.setStyleSheet("font-size: 11px; color: #666666;")
        header_layout.addWidget(confidence_label)
        
        layout.addLayout(header_layout)
        
        # Message
        message_label = QtWidgets.QLabel(hint["message"])
        message_label.setWordWrap(True)
        message_label.setStyleSheet("font-size: 13px; color: #333333; margin: 5px 0;")
        layout.addWidget(message_label)
        
        # Reasoning
        reasoning_label = QtWidgets.QLabel(f"Reasoning: {hint['reasoning']}")
        reasoning_label.setWordWrap(True)
        reasoning_label.setStyleSheet("font-size: 11px; color: #555555; font-style: italic;")
        layout.addWidget(reasoning_label)
        
        # Action buttons
        buttons_layout = QtWidgets.QHBoxLayout()
        
        accept_btn = QtWidgets.QPushButton("Accept")
        accept_btn.setStyleSheet("QPushButton { background-color: #495057; color: white; font-weight: bold; padding: 6px 12px; }")
        accept_btn.clicked.connect(lambda: self.acceptHint(hint, widget))
        buttons_layout.addWidget(accept_btn)
        
        dismiss_btn = QtWidgets.QPushButton("Dismiss")
        dismiss_btn.setStyleSheet("QPushButton { background-color: #6c757d; color: white; padding: 6px 12px; }")
        dismiss_btn.clicked.connect(lambda: self.dismissHint(hint, widget))
        buttons_layout.addWidget(dismiss_btn)
        
        override_btn = QtWidgets.QPushButton("Override")
        override_btn.setStyleSheet("QPushButton { padding: 6px 12px; }")
        override_btn.clicked.connect(lambda: self.overrideHint(hint))
        buttons_layout.addWidget(override_btn)
        
        buttons_layout.addStretch()
        
        timestamp_label = QtWidgets.QLabel(hint["timestamp"][:19])
        timestamp_label.setStyleSheet("font-size: 10px; color: #888888;")
        buttons_layout.addWidget(timestamp_label)
        
        layout.addLayout(buttons_layout)
        
        return widget
        
    def acceptHint(self, hint, widget):
        """Accept an AI hint and execute the action"""
        # In a real implementation, this would:
        # - Execute the suggested action
        # - Log the acceptance
        # - Update the simulation state
        
        QtWidgets.QMessageBox.information(
            self, "Hint Accepted", 
            f"AI hint accepted and action executed:\n\n{hint['message']}"
        )
        
        # Mark as accepted and hide
        hint["accepted"] = True
        widget.setVisible(False)
        
    def dismissHint(self, hint, widget):
        """Dismiss an AI hint"""
        hint["dismissed"] = True
        widget.setVisible(False)
        
    def overrideHint(self, hint):
        """Show dialog to override/modify the AI hint"""
        dialog = QtWidgets.QDialog(self)
        dialog.setWindowTitle("Override AI Hint")
        dialog.setMinimumSize(500, 300)
        
        layout = QtWidgets.QVBoxLayout(dialog)
        
        # Original hint
        layout.addWidget(QtWidgets.QLabel("Original AI Suggestion:"))
        original_text = QtWidgets.QTextEdit()
        original_text.setPlainText(hint["message"])
        original_text.setReadOnly(True)
        original_text.setMaximumHeight(80)
        layout.addWidget(original_text)
        
        # Override input
        layout.addWidget(QtWidgets.QLabel("Your Override:"))
        override_text = QtWidgets.QTextEdit()
        override_text.setPlaceholderText("Enter your alternative action or reasoning...")
        layout.addWidget(override_text)
        
        # Buttons
        button_box = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)
        layout.addWidget(button_box)
        
        if dialog.exec_() == QtWidgets.QDialog.Accepted:
            override_content = override_text.toPlainText()
            if override_content.strip():
                QtWidgets.QMessageBox.information(
                    self, "Override Recorded",
                    f"Your override has been recorded and will be executed:\n\n{override_content}"
                )
            else:
                QtWidgets.QMessageBox.warning(self, "No Override", "Please enter an override action.")


class AIHintsDockWidget(QtWidgets.QDockWidget):
    """Dock widget container for AI hints"""
    
    def __init__(self, parent=None):
        super().__init__("AI Routing Hints", parent)
        
        self.hints_widget = AIHintsWidget(self)
        self.setWidget(self.hints_widget)
        
        # Configure dock widget
        self.setFeatures(
            QtWidgets.QDockWidget.DockWidgetMovable |
            QtWidgets.QDockWidget.DockWidgetFloatable
        )
        # Ensure dock widget cannot be closed accidentally
        self.setFeatures(self.features() & ~QtWidgets.QDockWidget.DockWidgetClosable)
        self.setMinimumWidth(300)
        self.setMaximumWidth(500)
