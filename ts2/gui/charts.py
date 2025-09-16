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
import random
import math
from datetime import datetime, timedelta


class SimpleChart(QtWidgets.QWidget):
    """Base class for simple chart widgets"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.data = []
        self.setMinimumSize(200, 100)
        
    def setData(self, data):
        """Set chart data"""
        self.data = data
        self.update()
        
    def paintEvent(self, event):
        """Override to draw chart"""
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        rect = self.rect()
        
        # Draw background
        painter.fillRect(rect, QtGui.QColor(250, 250, 250))
        painter.setPen(QtGui.QPen(QtGui.QColor(200, 200, 200), 1))
        painter.drawRect(rect)


class SparklineChart(SimpleChart):
    """Simple sparkline chart for trend visualization"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.color = QtGui.QColor(73, 80, 87)  # Dark gray
        self.setFixedHeight(30)
        
    def paintEvent(self, event):
        super().paintEvent(event)
        
        if not self.data or len(self.data) < 2:
            return
            
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        
        # Calculate bounds
        margin = 5
        rect = self.rect().adjusted(margin, margin, -margin, -margin)
        
        min_val = min(self.data)
        max_val = max(self.data)
        val_range = max_val - min_val if max_val != min_val else 1
        
        # Draw line
        painter.setPen(QtGui.QPen(self.color, 2))
        
        points = []
        for i, val in enumerate(self.data):
            x = rect.left() + (i / (len(self.data) - 1)) * rect.width()
            y = rect.bottom() - ((val - min_val) / val_range) * rect.height()
            points.append(QtCore.QPointF(x, y))
            
        if len(points) > 1:
            path = QtGui.QPainterPath()
            path.moveTo(points[0])
            for point in points[1:]:
                path.lineTo(point)
            painter.drawPath(path)


class BarChart(SimpleChart):
    """Simple bar chart"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.labels = []
        self.colors = [QtGui.QColor(73, 80, 87), QtGui.QColor(108, 117, 125), QtGui.QColor(134, 142, 150)]
        
    def setData(self, data, labels=None):
        """Set data with optional labels"""
        super().setData(data)
        self.labels = labels or [str(i) for i in range(len(data))]
        
    def paintEvent(self, event):
        super().paintEvent(event)
        
        if not self.data:
            return
            
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        
        # Calculate bounds
        margin = 20
        rect = self.rect().adjusted(margin, margin, -margin, -margin)
        
        max_val = max(self.data) if self.data else 1
        bar_width = rect.width() / len(self.data) * 0.8
        spacing = rect.width() / len(self.data) * 0.2
        
        # Draw bars
        for i, val in enumerate(self.data):
            color = self.colors[i % len(self.colors)]
            x = int(rect.left() + i * (bar_width + spacing))
            y = int(rect.bottom() - (val / max_val) * rect.height())
            w = int(bar_width)
            h = int((val / max_val) * rect.height())
            painter.fillRect(x, y, w, h, color)
            
        # Draw axis
        painter.setPen(QtGui.QPen(QtGui.QColor(100, 100, 100), 1))
        painter.drawLine(rect.bottomLeft(), rect.bottomRight())


class LineChart(SimpleChart):
    """Simple line chart with multiple series support"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.series = {}  # name: (data, color)
        self.show_grid = True
        
    def addSeries(self, name, data, color=None):
        """Add a data series"""
        if color is None:
            colors = [QtGui.QColor(73, 80, 87), QtGui.QColor(108, 117, 125), 
                     QtGui.QColor(134, 142, 150), QtGui.QColor(173, 181, 189)]
            color = colors[len(self.series) % len(colors)]
        self.series[name] = (data, color)
        self.update()
        
    def clearSeries(self):
        """Clear all series"""
        self.series.clear()
        self.update()
        
    def paintEvent(self, event):
        super().paintEvent(event)
        
        if not self.series:
            return
            
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        
        # Calculate bounds
        margin = 30
        rect = self.rect().adjusted(margin, margin, -margin, -margin)
        
        # Find data bounds
        all_data = []
        for data, _ in self.series.values():
            all_data.extend(data)
            
        if not all_data:
            return
            
        min_val = min(all_data)
        max_val = max(all_data)
        val_range = max_val - min_val if max_val != min_val else 1
        
        # Draw grid
        if self.show_grid:
            painter.setPen(QtGui.QPen(QtGui.QColor(230, 230, 230), 1))
            for i in range(5):
                y = int(rect.top() + (i / 4) * rect.height())
                painter.drawLine(rect.left(), y, rect.right(), y)
                
        # Draw series
        for name, (data, color) in self.series.items():
            if len(data) < 2:
                continue
                
            painter.setPen(QtGui.QPen(color, 2))
            
            points = []
            for i, val in enumerate(data):
                x = rect.left() + (i / (len(data) - 1)) * rect.width()
                y = rect.bottom() - ((val - min_val) / val_range) * rect.height()
                points.append(QtCore.QPointF(x, y))
                
            # Draw line
            if len(points) > 1:
                path = QtGui.QPainterPath()
                path.moveTo(points[0])
                for point in points[1:]:
                    path.lineTo(point)
                painter.drawPath(path)
                
        # Draw axes
        painter.setPen(QtGui.QPen(QtGui.QColor(100, 100, 100), 1))
        painter.drawLine(rect.bottomLeft(), rect.bottomRight())
        painter.drawLine(rect.bottomLeft(), rect.topLeft())


class HeatmapChart(SimpleChart):
    """Simple heatmap chart"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.matrix_data = []
        self.row_labels = []
        self.col_labels = []
        
    def setData(self, matrix_data, row_labels=None, col_labels=None):
        """Set matrix data with optional labels"""
        self.matrix_data = matrix_data
        self.row_labels = row_labels or []
        self.col_labels = col_labels or []
        self.update()
        
    def paintEvent(self, event):
        super().paintEvent(event)
        
        if not self.matrix_data:
            return
            
        painter = QtGui.QPainter(self)
        
        rows = len(self.matrix_data)
        cols = len(self.matrix_data[0]) if rows > 0 else 0
        
        if rows == 0 or cols == 0:
            return
            
        # Calculate cell size
        margin = 20
        rect = self.rect().adjusted(margin, margin, -margin, -margin)
        
        cell_width = rect.width() / cols
        cell_height = rect.height() / rows
        
        # Find data bounds for color mapping
        all_values = [val for row in self.matrix_data for val in row]
        min_val = min(all_values) if all_values else 0
        max_val = max(all_values) if all_values else 1
        val_range = max_val - min_val if max_val != min_val else 1
        
        # Draw cells
        for i, row in enumerate(self.matrix_data):
            for j, val in enumerate(row):
                # Color intensity based on value
                intensity = (val - min_val) / val_range
                color = QtGui.QColor(255, int(255 - 155 * intensity), int(255 - 155 * intensity))
                
                painter.fillRect(
                    int(rect.left() + j * cell_width),
                    int(rect.top() + i * cell_height),
                    int(cell_width),
                    int(cell_height),
                    color
                )
                
                # Draw cell border
                painter.setPen(QtGui.QPen(QtGui.QColor(200, 200, 200), 1))
                painter.drawRect(
                    int(rect.left() + j * cell_width),
                    int(rect.top() + i * cell_height),
                    int(cell_width),
                    int(cell_height)
                )


class GaugeChart(SimpleChart):
    """Simple gauge/dial chart"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.value = 0
        self.min_value = 0
        self.max_value = 100
        self.setFixedSize(100, 100)
        
    def setValue(self, value):
        """Set gauge value"""
        self.value = max(self.min_value, min(self.max_value, value))
        self.update()
        
    def setRange(self, min_val, max_val):
        """Set gauge range"""
        self.min_value = min_val
        self.max_value = max_val
        self.update()
        
    def paintEvent(self, event):
        super().paintEvent(event)
        
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        
        rect = self.rect()
        center = rect.center()
        radius = min(rect.width(), rect.height()) // 2 - 10
        
        # Draw gauge background
        painter.setPen(QtGui.QPen(QtGui.QColor(200, 200, 200), 8))
        painter.drawArc(int(center.x() - radius), int(center.y() - radius), 
                       int(radius * 2), int(radius * 2), 
                       45 * 16, 270 * 16)
        
        # Draw gauge value
        if self.max_value > self.min_value:
            ratio = (self.value - self.min_value) / (self.max_value - self.min_value)
            angle = int(270 * ratio)
            
            # Color based on value - minimal gray scale
            if ratio < 0.5:
                color = QtGui.QColor(73, 80, 87)  # Dark gray
            elif ratio < 0.8:
                color = QtGui.QColor(108, 117, 125)  # Medium gray
            else:
                color = QtGui.QColor(134, 142, 150)  # Light gray
                
            painter.setPen(QtGui.QPen(color, 8))
            painter.drawArc(int(center.x() - radius), int(center.y() - radius), 
                           int(radius * 2), int(radius * 2), 
                           45 * 16, angle * 16)
        
        # Draw value text
        painter.setPen(QtGui.QPen(QtGui.QColor(50, 50, 50), 1))
        font = painter.font()
        font.setPointSize(12)
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(rect, Qt.AlignCenter, str(int(self.value)))


class KPITile(QtWidgets.QWidget):
    """KPI tile with value, trend, and sparkline"""
    
    def __init__(self, title, value="--", unit="", parent=None):
        super().__init__(parent)
        self.title = title
        self.value = value
        self.unit = unit
        self.trend_data = []
        self.delta = None
        self.setupUI()
        
    def setupUI(self):
        """Setup the tile UI"""
        self.setFixedSize(200, 120)
        self.setStyleSheet("""
            KPITile {
                background-color: white;
                border: 1px solid #e0e0e0;
                border-radius: 4px;
            }
            KPITile:hover {
                border-color: #495057;
            }
        """)
        
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        
        # Title
        title_label = QtWidgets.QLabel(self.title)
        title_label.setStyleSheet("font-size: 11px; color: #666; font-weight: bold;")
        layout.addWidget(title_label)
        
        # Value and unit
        value_container = QtWidgets.QHBoxLayout()
        
        self.value_label = QtWidgets.QLabel(str(self.value))
        self.value_label.setStyleSheet("font-size: 24px; font-weight: bold; color: #495057;")
        value_container.addWidget(self.value_label)
        
        self.unit_label = QtWidgets.QLabel(self.unit)
        self.unit_label.setStyleSheet("font-size: 12px; color: #666; margin-left: 4px;")
        value_container.addWidget(self.unit_label)
        
        value_container.addStretch()
        layout.addLayout(value_container)
        
        # Delta and sparkline
        bottom_container = QtWidgets.QHBoxLayout()
        
        self.delta_label = QtWidgets.QLabel("")
        self.delta_label.setStyleSheet("font-size: 10px;")
        bottom_container.addWidget(self.delta_label)
        
        bottom_container.addStretch()
        
        self.sparkline = SparklineChart()
        self.sparkline.setFixedSize(60, 20)
        bottom_container.addWidget(self.sparkline)
        
        layout.addLayout(bottom_container)
        
    def updateValue(self, value, delta=None, trend_data=None):
        """Update tile value and trend"""
        self.value = value
        self.value_label.setText(str(value))
        
        # Update delta
        if delta is not None:
            self.delta = delta
            delta_text = f"{'▲' if delta > 0 else '▼'} {abs(delta):.1f}"
            color = "#495057" if delta > 0 else "#6c757d"
            self.delta_label.setText(delta_text)
            self.delta_label.setStyleSheet(f"font-size: 10px; color: {color};")
        
        # Update sparkline
        if trend_data:
            self.trend_data = trend_data
            self.sparkline.setData(trend_data)
            
    def setValueColor(self, color):
        """Set value label color based on threshold"""
        self.value_label.setStyleSheet(f"font-size: 24px; font-weight: bold; color: {color};")


def generateMockData():
    """Generate mock data for testing charts"""
    return {
        'rtp_hourly': [random.uniform(75, 95) for _ in range(24)],
        'delay_trend': [random.uniform(2, 12) for _ in range(60)],
        'throughput_data': [(random.randint(15, 25), random.randint(12, 20)) for _ in range(24)],
        'conflict_funnel': [45, 38, 32, 30],
        'platform_heatmap': [[random.randint(0, 100) for _ in range(24)] for _ in range(8)],
        'headway_data': [random.uniform(2.5, 4.0) for _ in range(100)]
    }
