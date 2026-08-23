import sys
import os
import time
import json
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QLabel, QPushButton, QStackedWidget, QProgressBar, QFrame)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont, QPixmap, QPainter, QLinearGradient, QColor, QIcon

# 模擬或真實的安裝背景執行緒
class InstallThread(QThread):
    progress_update = pyqtSignal(int, str, str)
    finished = pyqtSignal(bool, str)

    def run(self):
        try:
            import shutil
            import subprocess
            
            # 1. 目標資料夾設定在目前使用者的 AppData\Roaming 中 (不需要管理員權限)
            appdata_dir = os.path.join(os.environ.get('APPDATA', ''), 'GoHandwriting')
            if not os.path.exists(appdata_dir):
                os.makedirs(appdata_dir)
            
            # 2. 確認執行檔所在位置 (支援 PyInstaller 的打包虛擬環境 _MEIPASS)
            if hasattr(sys, '_MEIPASS'):
                base_path = sys._MEIPASS
            else:
                base_path = os.path.abspath(".")

            # 定義真實要安裝的程式 (請確保之後你有把 main.exe 打包進來)
            payload_name = "main.exe"
            source_payload = os.path.join(base_path, payload_name)
            target_payload = os.path.join(appdata_dir, payload_name)

            self.progress_update.emit(10, "正在準備安裝檔案...", "")
            time.sleep(0.5)

            # 3. 實際複製檔案 (真實安裝)
            if os.path.exists(source_payload):
                self.progress_update.emit(40, "正在複製核心程式...", f"複製: {payload_name}")
                shutil.copy2(source_payload, target_payload)
            else:
                # 測試環境下，先建立一個測試檔代替，確保安裝邏輯可以走通
                self.progress_update.emit(40, "【測試模式】未找到主程式，建立虛擬程式...", f"建立: {payload_name}")
                with open(target_payload, 'w', encoding='utf-8') as f:
                    f.write("此為安裝程式自動產生的測試檔案。")
                time.sleep(1)

            # 順便複製圖示，供捷徑使用
            icon_source = os.path.join(base_path, "icon.ico")
            icon_target = os.path.join(appdata_dir, "icon.ico")
            if os.path.exists(icon_source):
                shutil.copy2(icon_source, icon_target)

            # 4. 建立桌面捷徑 (使用 VBScript 腳本方式建立，不需要額外安裝第三方庫，也不需要管理員權限)
            self.progress_update.emit(70, "正在建立桌面捷徑...", "")
            desktop_dir = os.path.join(os.environ["USERPROFILE"], "Desktop")
            shortcut_path = os.path.join(desktop_dir, "去手寫.lnk")
            
            vbs_script = f'''
Set oWS = WScript.CreateObject("WScript.Shell")
Set oLink = oWS.CreateShortcut("{shortcut_path}")
oLink.TargetPath = "{target_payload}"
oLink.WorkingDirectory = "{appdata_dir}"
'''
            if os.path.exists(icon_target):
                vbs_script += f'oLink.IconLocation = "{icon_target}"\n'
            vbs_script += 'oLink.Save\n'

            vbs_path = os.path.join(os.environ['TEMP'], 'create_shortcut.vbs')
            with open(vbs_path, 'w', encoding='utf-8') as f:
                f.write(vbs_script)
            subprocess.call(['cscript.exe', '//Nologo', vbs_path])
            try:
                os.remove(vbs_path)
            except:
                pass

            # 5. 解鎖更多功能：寫入授權/設定檔
            self.progress_update.emit(85, "正在設定系統環境與解鎖功能...", "")
            time.sleep(0.5)
            unlock_file = os.path.join(appdata_dir, 'license_unlocked.json')
            with open(unlock_file, 'w', encoding='utf-8') as f:
                json.dump({
                    "is_pro_version": True, 
                    "unlocked_features": ["remove_watermark", "batch_processing", "high_res_export", "ai_enhance"],
                    "install_date": time.strftime("%Y-%m-%d %H:%M:%S")
                }, f, indent=4)
            
            self.progress_update.emit(100, "安裝完成！", "")
            time.sleep(0.5)
            self.finished.emit(True, "安裝成功")
        except Exception as e:
            self.finished.emit(False, str(e))

class ModernInstaller(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("去手寫 - 專業安裝程式")
        self.setFixedSize(620, 420)
        
        # 嘗試載入圖示
        if os.path.exists("icon.ico"):
            self.setWindowIcon(QIcon("icon.ico"))
        
        # 全局 QSS 樣式：追求精美、現代感
        self.setStyleSheet("""
            QMainWindow {
                background-color: #FFFFFF;
            }
            QLabel {
                font-family: 'Microsoft JhengHei', 'Segoe UI', Arial;
                color: #222222;
            }
            QPushButton {
                font-family: 'Microsoft JhengHei', 'Segoe UI';
                font-size: 13px;
                background-color: #F8F8F8;
                border: 1px solid #D0D0D0;
                padding: 6px 18px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #EEEEEE;
                border: 1px solid #B0B0B0;
            }
            QPushButton:pressed {
                background-color: #E0E0E0;
            }
            QPushButton#primaryButton {
                background-color: #0066CC;
                color: white;
                border: 1px solid #005BB5;
            }
            QPushButton#primaryButton:hover {
                background-color: #0073E6;
                border: 1px solid #0066CC;
            }
            QPushButton#primaryButton:pressed {
                background-color: #0052A3;
            }
            QPushButton:disabled {
                background-color: #F5F5F5;
                color: #A0A0A0;
                border: 1px solid #DDDDDD;
            }
            QProgressBar {
                border: 1px solid #CCCCCC;
                border-radius: 3px;
                background-color: #EFEFEF;
                text-align: center;
                color: transparent; /* 隱藏數字 */
                height: 18px;
            }
            QProgressBar::chunk {
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #06B025, stop:1 #1AD03A);
                border-radius: 2px;
            }
        """)

        # 主佈局
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 上半部：切換頁面區塊
        self.stacked_widget = QStackedWidget()
        main_layout.addWidget(self.stacked_widget)

        # 建立各頁面
        self.init_welcome_page()
        self.init_progress_page()
        self.init_finish_page()

        # 下半部：控制列區塊
        bottom_bar = QWidget()
        bottom_bar.setFixedHeight(55)
        bottom_bar.setStyleSheet("background-color: #F3F3F3; border-top: 1px solid #DCDCDC;")
        bottom_layout = QHBoxLayout(bottom_bar)
        bottom_layout.setContentsMargins(20, 0, 20, 0)
        
        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.clicked.connect(self.close)
        
        self.back_btn = QPushButton("< 上一步")
        self.back_btn.setEnabled(False)
        
        self.next_btn = QPushButton("下一步(N) >")
        self.next_btn.setObjectName("primaryButton")
        self.next_btn.clicked.connect(self.next_page)

        bottom_layout.addStretch()
        bottom_layout.addWidget(self.back_btn)
        bottom_layout.addSpacing(5)
        bottom_layout.addWidget(self.next_btn)
        bottom_layout.addSpacing(20)
        bottom_layout.addWidget(self.cancel_btn)

        main_layout.addWidget(bottom_bar)

    def create_sidebar(self):
        """建立精美的左側邊欄，使用深藍色漸層模擬經典安裝程式風格"""
        class SidebarWidget(QWidget):
            def paintEvent(self, event):
                painter = QPainter(self)
                gradient = QLinearGradient(0, 0, self.width(), self.height())
                gradient.setColorAt(0, QColor(0, 10, 60))
                gradient.setColorAt(1, QColor(0, 30, 120))
                painter.fillRect(self.rect(), gradient)
                
                # 如果有 bg.png 或是 icon.ico 可以在這裡繪製裝飾
                if os.path.exists("icon.ico"):
                    pixmap = QPixmap("icon.ico").scaled(80, 80, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                    painter.drawPixmap(50, 40, pixmap)

        sidebar = SidebarWidget()
        sidebar.setFixedWidth(180)
        return sidebar

    def init_welcome_page(self):
        page = QWidget()
        layout = QHBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        layout.addWidget(self.create_sidebar())

        content = QWidget()
        content.setStyleSheet("background-color: #FFFFFF;")
        vbox = QVBoxLayout(content)
        vbox.setContentsMargins(35, 40, 35, 40)

        title = QLabel("歡迎使用 去手寫 安裝程式")
        title.setFont(QFont("Microsoft JhengHei", 18, QFont.Weight.Bold))
        title.setStyleSheet("color: #000000;")
        vbox.addWidget(title)
        vbox.addSpacing(20)

        desc1 = QLabel("這個安裝程式將會安裝「去手寫」到您的電腦，\n並為您將系統設定寫入 AppData 解鎖專業功能。")
        desc1.setFont(QFont("Microsoft JhengHei", 11))
        desc1.setWordWrap(True)
        vbox.addWidget(desc1)
        vbox.addSpacing(15)

        desc2 = QLabel("我們強烈建議您在安裝過程中關閉其它的應用程式，以避免\n與安裝程式發生衝突。")
        desc2.setFont(QFont("Microsoft JhengHei", 11))
        desc2.setWordWrap(True)
        vbox.addWidget(desc2)
        vbox.addSpacing(15)

        desc3 = QLabel("按 [下一步] 繼續安裝，或按 [取消] 結束安裝程式。")
        desc3.setFont(QFont("Microsoft JhengHei", 11))
        vbox.addWidget(desc3)
        vbox.addStretch()

        layout.addWidget(content)
        self.stacked_widget.addWidget(page)

    def init_progress_page(self):
        page = QWidget()
        page.setStyleSheet("background-color: #FFFFFF;")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(35, 30, 35, 30)

        title = QLabel("正在安裝")
        title.setFont(QFont("Microsoft JhengHei", 14, QFont.Weight.Bold))
        layout.addWidget(title)
        layout.addSpacing(5)
        
        subtitle = QLabel("請稍候，正在安裝檔案與解鎖功能...")
        subtitle.setFont(QFont("Microsoft JhengHei", 10))
        layout.addWidget(subtitle)
        layout.addSpacing(30)

        self.status_label = QLabel("準備中...")
        self.status_label.setFont(QFont("Microsoft JhengHei", 10))
        layout.addWidget(self.status_label)
        layout.addSpacing(5)

        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)
        layout.addSpacing(5)

        self.file_label = QLabel("")
        self.file_label.setFont(QFont("Microsoft JhengHei", 9))
        self.file_label.setStyleSheet("color: #777777;")
        layout.addWidget(self.file_label)
        
        layout.addStretch()
        
        # 模擬圖片中的 Stop backup 按鈕，放在進度條下方右側
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        self.stop_btn = QPushButton("停止安裝")
        self.stop_btn.clicked.connect(self.close)
        btn_layout.addWidget(self.stop_btn)
        
        # layout.addLayout(btn_layout) # 如果需要可以取消註解顯示停止按鈕
        
        self.stacked_widget.addWidget(page)

    def init_finish_page(self):
        page = QWidget()
        layout = QHBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        layout.addWidget(self.create_sidebar())

        content = QWidget()
        content.setStyleSheet("background-color: #FFFFFF;")
        vbox = QVBoxLayout(content)
        vbox.setContentsMargins(35, 40, 35, 40)

        title = QLabel("安裝完成")
        title.setFont(QFont("Microsoft JhengHei", 18, QFont.Weight.Bold))
        title.setStyleSheet("color: #000000;")
        vbox.addWidget(title)
        vbox.addSpacing(20)

        desc1 = QLabel("「去手寫」已成功安裝在您的電腦上！\n\n您的高級功能已成功解鎖，設定已寫入系統 AppData 資料夾。")
        desc1.setFont(QFont("Microsoft JhengHei", 11))
        desc1.setWordWrap(True)
        vbox.addWidget(desc1)
        
        vbox.addSpacing(30)
        
        # 加上一個勾選框 (用 QLabel + 按鈕 或 QCheckBox)
        self.run_checkbox = QPushButton("☑ 執行 去手寫")
        self.run_checkbox.setCheckable(True)
        self.run_checkbox.setChecked(True)
        self.run_checkbox.setStyleSheet("""
            QPushButton { text-align: left; background: none; border: none; font-size: 13px; color: #222222; }
            QPushButton:checked { color: #0066CC; font-weight: bold; }
        """)
        vbox.addWidget(self.run_checkbox)

        vbox.addStretch()

        layout.addWidget(content)
        self.stacked_widget.addWidget(page)

    def closeEvent(self, event):
        # 如果在完成頁面關閉，且勾選了執行程式，則啟動主程式
        if self.stacked_widget.currentIndex() == 2 and self.run_checkbox.isChecked():
            appdata_dir = os.path.join(os.environ.get('APPDATA', ''), 'GoHandwriting')
            target_payload = os.path.join(appdata_dir, 'main.exe')
            if os.path.exists(target_payload):
                try:
                    os.startfile(target_payload)
                except:
                    pass
        super().closeEvent(event)

    def next_page(self):
        current = self.stacked_widget.currentIndex()
        if current == 0:
            # 切換到安裝進度頁面
            self.stacked_widget.setCurrentIndex(1)
            self.next_btn.setEnabled(False)
            self.cancel_btn.setEnabled(False)
            self.back_btn.setEnabled(False)
            self.start_installation()
        elif current == 2:
            # 完成並關閉
            self.close()

    def start_installation(self):
        self.install_thread = InstallThread()
        self.install_thread.progress_update.connect(self.update_progress)
        self.install_thread.finished.connect(self.install_finished)
        self.install_thread.start()

    def update_progress(self, val, status_text, file_text):
        self.progress_bar.setValue(val)
        self.status_label.setText(status_text)
        self.file_label.setText(file_text)

    def install_finished(self, success, msg):
        if success:
            self.stacked_widget.setCurrentIndex(2)
            self.next_btn.setEnabled(True)
            self.next_btn.setText("完成")
            self.cancel_btn.setEnabled(False)
            self.back_btn.setEnabled(False)
        else:
            self.status_label.setText("安裝失敗：" + msg)
            self.cancel_btn.setEnabled(True)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ModernInstaller()
    window.show()
    sys.exit(app.exec())
