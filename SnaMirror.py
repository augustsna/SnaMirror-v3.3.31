import sys
import subprocess
import time
import ctypes
from subprocess import CREATE_NO_WINDOW
from PyQt5.QtWidgets import (
    QApplication, QWidget, QPushButton, QVBoxLayout, QHBoxLayout,
    QListWidget, QMessageBox, QButtonGroup, QSplashScreen
)
from PyQt5.QtGui import QIcon, QFont, QPixmap
from PyQt5.QtCore import Qt

# Windows taskbar icon support
myappid = 'mycompany.myproduct.subproduct.version'
ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)

def get_device_name(device_id):
    try:
        result = subprocess.run(
            ['adb', '-s', device_id, 'shell', 'settings', 'get', 'global', 'device_name'],
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL
        )
        name = result.stdout.decode().strip()
        if not name or name == 'null':
            result = subprocess.run(
                ['adb', '-s', device_id, 'shell', 'getprop', 'net.hostname'],
                stdout=subprocess.PIPE, stderr=subprocess.DEVNULL
            )
            name = result.stdout.decode().strip()
        return name if name else "Unknown"
    except Exception:
        return "Unknown"

def get_connected_devices_with_names():
    result = subprocess.run(['adb', 'devices'], stdout=subprocess.PIPE)
    lines = result.stdout.decode().splitlines()[1:]
    devices = [line.split()[0] for line in lines if "device" in line]
    return [(d, get_device_name(d)) for d in devices]

class ScrcpyManager(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('SNA Phone Mirror')
        self.setWindowIcon(QIcon("icon.ico"))
        self.resize(280, 300)
        self.selected_size = "800"

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(16, 16, 16, 16)
        self.layout.setSpacing(10)

        self.device_list = QListWidget()
        self.device_list.setStyleSheet("padding: 6px; border-radius: 6px;")
        self.device_list.itemDoubleClicked.connect(self.launch_scrcpy_for_item)
        self.layout.addWidget(self.device_list)

        self.control_row1 = QHBoxLayout()
        self.control_row1.addStretch()

        self.kill_btn = QPushButton('🚩')
        self.restart_btn = QPushButton('🔁')
        for btn in [self.kill_btn, self.restart_btn]:
            btn.setFixedSize(32, 30)
            btn.setStyleSheet("""
                QPushButton {
                    border-radius: 6px;
                    font-size: 13px;
                    border: 1.2px solid #555;
                    background-color: transparent;
                }
                QPushButton:hover {
                    background-color: #f0f0f0;
                }
            """)
            self.control_row1.addWidget(btn)

        self.small_btn = QPushButton("S")
        self.medium_btn = QPushButton("M")
        self.max_btn = QPushButton("L")
        for btn in [self.small_btn, self.medium_btn, self.max_btn]:
            btn.setCheckable(True)
            btn.setFixedSize(32, 30)
            btn.setStyleSheet("""
                QPushButton {
                    border-radius: 15px;
                    font-size: 12px;
                    border: 1.2px solid #555;
                    background-color: transparent;
                }
                QPushButton:checked {
                    background-color: #d0e0ff;
                    border: 1.2px solid #6090ff;
                }
            """)
            self.control_row1.addWidget(btn)

        self.control_row1.addStretch()

        self.size_group = QButtonGroup()
        self.size_group.addButton(self.small_btn)
        self.size_group.addButton(self.medium_btn)
        self.size_group.addButton(self.max_btn)
        self.medium_btn.setChecked(True)

        self.small_btn.clicked.connect(lambda: self.set_size("600"))
        self.medium_btn.clicked.connect(lambda: self.set_size("800"))
        self.max_btn.clicked.connect(lambda: self.set_size("1080"))

        self.layout.addLayout(self.control_row1)

        self.control_row2 = QHBoxLayout()
        self.control_row2.addStretch()

        self.refresh_btn = QPushButton('🔄 Refresh')
        self.connect_btn = QPushButton('🚀 Connect')
        for btn in [self.refresh_btn, self.connect_btn]:
            btn.setFixedHeight(30)
            btn.setFixedWidth(84)
            btn.setStyleSheet("""
                QPushButton {
                    font-size: 11.5px;
                    border-radius: 6px;
                    border: 1.2px solid #555;
                    background-color: transparent;
                }
                QPushButton:hover {
                    background-color: #f0f0f0;
                }
            """)
            self.control_row2.addWidget(btn)

        self.control_row2.addStretch()
        self.layout.addLayout(self.control_row2)

        self.refresh_btn.clicked.connect(self.refresh_devices)
        self.connect_btn.clicked.connect(self.connect_devices)
        self.kill_btn.clicked.connect(self.kill_adb_server)
        self.restart_btn.clicked.connect(self.restart_adb_server)

        self.device_id_map = {}
        self.refresh_devices()

    def keyPressEvent(self, event):
        if event.modifiers() == Qt.ControlModifier and event.key() == Qt.Key_W:
            self.close()

    def set_size(self, size):
        self.selected_size = size

    def refresh_devices(self):
        self.device_list.clear()
        self.device_id_map.clear()
        devices = get_connected_devices_with_names()
        if not devices:
            QMessageBox.warning(self, 'Warning', 'No devices found!')
            return
        for device_id, device_name in devices:
            self.device_list.addItem(device_name)
            self.device_id_map[device_name] = device_id
        if self.device_list.count() > 0:
            self.device_list.setCurrentRow(0)

    def connect_devices(self):
        selected = self.device_list.selectedItems()
        if not selected:
            QMessageBox.information(self, 'Info', 'Please select at least one device.')
            return
        for item in selected:
            name = item.text()
            device_id = self.device_id_map.get(name)
            if device_id:
                subprocess.Popen(
                    ['scrcpy', '-s', device_id, '--max-size', self.selected_size],
                    creationflags=CREATE_NO_WINDOW
                )

    def launch_scrcpy_for_item(self, item):
        name = item.text()
        device_id = self.device_id_map.get(name)
        if device_id:
            subprocess.Popen(
                ['scrcpy', '-s', device_id, '--max-size', self.selected_size],
                creationflags=CREATE_NO_WINDOW
            )

    def show_wait_message(self, text):
        msg = QMessageBox(self)
        msg.setWindowTitle("ADB")
        msg.setStyleSheet("""
            QLabel {
                qproperty-alignment: AlignLeft;
                min-width: 240px;
                font-size: 12px;
            }
        """)
        msg.setText(text)
        msg.setStandardButtons(QMessageBox.NoButton)
        msg.setFixedSize(280, 120)
        msg.setWindowModality(Qt.ApplicationModal)
        msg.show()
        QApplication.processEvents()
        return msg

    def show_done_message(self, text):
        msg = QMessageBox(self)
        msg.setWindowTitle("ADB")
        msg.setStyleSheet("""
            QLabel {
                qproperty-alignment: AlignLeft;
                min-width: 240px;
                font-size: 12px;
            }
            QPushButton {
                min-width: 80px;
                max-width: 80px;
                border: 1.2px solid #555;
                border-radius: 4px;
                padding: 4px 8px;
            }
            QPushButton:hover {
                background-color: #f0f0f0;
            }
        """)
        msg.setText(text)
        msg.setStandardButtons(QMessageBox.Ok)
        ok_btn = msg.button(QMessageBox.Ok)
        ok_btn.setFixedSize(80, 28)
        msg.setFixedSize(280, 120)
        msg.exec_()

    def kill_adb_server(self):
        msg = self.show_wait_message("Killing ADB server...")
        subprocess.run(['adb', 'kill-server'])
        msg.done(0)
        self.show_done_message("✅ ADB server killed.")

    def restart_adb_server(self):
        msg = self.show_wait_message("Restarting ADB server...")
        subprocess.run(['adb', 'kill-server'])
        subprocess.run(['adb', 'start-server'])
        msg.done(0)
        self.show_done_message("✅ ADB server restarted.")
        self.refresh_devices()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setFont(QFont("Segoe UI", 10))

    # --- Splash screen ---
    splash_pix = QPixmap("splash.png").scaled(400, 300, Qt.KeepAspectRatio, Qt.SmoothTransformation)
    splash = QSplashScreen(splash_pix, Qt.WindowStaysOnTopHint)
    splash.showMessage("Loading...", Qt.AlignBottom | Qt.AlignCenter, Qt.white)
    splash.show()
    app.processEvents()
    time.sleep(1.5)
    # ---------------------

    window = ScrcpyManager()
    window.show()
    splash.finish(window)

    sys.exit(app.exec_())