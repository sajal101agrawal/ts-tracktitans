#!/usr/bin/python3
"""
TS2 Client Auto-Connect

This script automatically connects the TS2 client to a running server.
It's a wrapper around start-ts2.py that bypasses the connection dialog.
"""

import sys
import os
import time
from pathlib import Path

# Add the current directory to sys.path so we can import ts2 modules
sys.path.insert(0, str(Path(__file__).parent))

try:
    from Qt import QtWidgets, QtCore, QtGui
    import ts2.application
    import ts2.mainwindow
    from ts2.xobjects import xsettings
    from ts2 import __APP_SHORT__, __VERSION__
except ImportError as e:
    print(f"❌ Error importing TS2 modules: {e}")
    print("Make sure you're running this from the TS2 project directory")
    sys.exit(1)

def connect_to_server_automatically(host="localhost", port="22222"):
    """Create a main window and automatically connect to the server"""
    
    # Create a mock args object similar to what start-ts2.py creates
    class MockArgs:
        def __init__(self):
            self.server = None
            self.debug = False
            self.edit = False
            self.file = None
    
    args = MockArgs()
    
    # Create the main window with proper args
    main_window = ts2.mainwindow.MainWindow(args=args)
    
    # Directly connect to the server instead of showing open dialog
    print(f"🔗 Connecting to server at {host}:{port}...")
    
    def on_connection_ready():
        print("✅ Successfully connected to simulation server!")
        main_window.show()
    
    def on_connection_failed():
        print("❌ Failed to connect to server. Make sure the server is running.")
        QtWidgets.QApplication.quit()
    
    # Connect the signals
    main_window.connectToServer(host, port)
    
    # We need to handle the connection result
    if hasattr(main_window, 'webSocket'):
        main_window.webSocket.connectionReady.connect(on_connection_ready)
        # Note: There's no direct connectionFailed signal, but we can use a timer as fallback
        QtCore.QTimer.singleShot(5000, lambda: check_connection(main_window))
    else:
        on_connection_failed()
    
    return main_window

def check_connection(main_window):
    """Check if connection was successful after timeout"""
    if not main_window.isVisible():  # If window isn't shown yet, connection likely failed
        print("⚠️  Connection timeout. Make sure the server is running on localhost:22222")
        QtWidgets.QApplication.quit()

def main():
    """Main entry point"""
    if not sys.version_info >= (3, 0, 0):
        sys.exit("ERROR: TS2 requires Python3")
    
    app = QtWidgets.QApplication(sys.argv)
    app.setApplicationName(__APP_SHORT__)
    app.setApplicationVersion(__VERSION__)
    app.setWindowIcon(QtGui.QIcon(QtGui.QPixmap(":/ts2.png")))
    
    # Set up translation (similar to original start-ts2.py)
    qtTranslator = QtCore.QTranslator()
    qtTranslator.load("qt_" + QtCore.QLocale.system().name(),
                      QtCore.QLibraryInfo.location(
                                      QtCore.QLibraryInfo.TranslationsPath))
    app.installTranslator(qtTranslator)
    ts2Translator = QtCore.QTranslator()
    ts2Translator.load(QtCore.QLocale.system(), "ts2", "_", "i18n", ".qm")
    app.installTranslator(ts2Translator)
    
    # Set up settings
    settings = xsettings.XSettings()
    settings.setDebug(False)
    
    try:
        # Create and connect the main window
        main_window = connect_to_server_automatically()
        
        # Start the application event loop
        return app.exec_()
        
    except Exception as e:
        print(f"❌ Error starting client: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
