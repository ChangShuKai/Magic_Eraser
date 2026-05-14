import sys
import os
import cv2
import numpy as np
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QLabel, QFileDialog, 
                             QRadioButton, QButtonGroup, QCheckBox, 
                             QGroupBox, QMessageBox, QScrollArea, QFrame, QSizePolicy,
                             QGraphicsDropShadowEffect, QProgressBar)
from PyQt6.QtCore import Qt, QSize, QThread, pyqtSignal, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QImage, QPixmap, QPainter, QIcon, QPalette, QBrush, QColor, QFont

from image_processor import process_image, enhance_text, whiten_background

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def create_shadow(blur=20, offset=(0, 10), color=QColor(0, 0, 0, 40)):
    shadow = QGraphicsDropShadowEffect()
    shadow.setBlurRadius(blur)
    shadow.setXOffset(offset[0])
    shadow.setYOffset(offset[1])
    shadow.setColor(color)
    return shadow

class ModernButton(QPushButton):
    """具有懸停效果的現代按鈕"""
    def __init__(self, text, parent=None, primary=False):
        super().__init__(text, parent)
        self.primary = primary
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(45)
        self.update_style()

    def update_style(self, hover=False):
        if self.primary:
            bg = "rgba(0, 122, 255, 0.9)" if not hover else "rgba(0, 122, 255, 1.0)"
            color = "white"
        else:
            bg = "rgba(255, 255, 255, 0.6)" if not hover else "rgba(255, 255, 255, 0.8)"
            color = "#333"
        
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {bg};
                border: 1px solid rgba(255, 255, 255, 0.5);
                border-radius: 12px;
                color: {color};
                font-weight: bold;
                font-size: 14px;
                padding: 0 20px;
            }}
            QPushButton:disabled {{
                background-color: rgba(200, 200, 200, 0.3);
                color: #888;
                border: 1px solid rgba(255, 255, 255, 0.2);
            }}
        """)

    def enterEvent(self, event):
        self.update_style(True)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.update_style(False)
        super().leaveEvent(event)

class ResponsiveImageLabel(QLabel):
    def __init__(self, text=""):
        super().__init__(text)
        self.original_pixmap = None
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet("""
            ResponsiveImageLabel {
                background-color: rgba(0, 0, 0, 0.05);
                border: 1px solid rgba(255, 255, 255, 0.3);
                border-radius: 10px;
                color: #666;
            }
        """)
        self.setMinimumSize(150, 150)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        
    def set_image(self, img_array):
        if img_array is None:
            return
        img_rgb = cv2.cvtColor(img_array, cv2.COLOR_BGR2RGB)
        h, w, ch = img_rgb.shape
        bytes_per_line = ch * w
        qt_img = QImage(img_rgb.data, w, h, bytes_per_line, QImage.Format.Format_RGB888).copy()
        self.original_pixmap = QPixmap.fromImage(qt_img)
        self.update()
        
    def paintEvent(self, event):
        super().paintEvent(event)
        if self.original_pixmap and not self.original_pixmap.isNull():
            painter = QPainter(self)
            painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
            scaled = self.original_pixmap.scaled(
                self.size(), 
                Qt.AspectRatioMode.KeepAspectRatio, 
                Qt.TransformationMode.SmoothTransformation
            )
            x = (self.width() - scaled.width()) // 2
            y = (self.height() - scaled.height()) // 2
            painter.drawPixmap(x, y, scaled)

class ImageRow(QFrame):
    def __init__(self, file_path, original_image, parent_window):
        super().__init__()
        self.file_path = file_path
        self.filename = os.path.basename(file_path)
        self.original_image = original_image
        self.processed_image = None
        self.parent_window = parent_window

        self.setStyleSheet("""
            ImageRow { 
                background-color: rgba(255, 255, 255, 0.5); 
                margin: 5px 10px; 
                border-radius: 20px; 
                border: 1px solid rgba(255, 255, 255, 0.6);
            }
        """)
        self.setMinimumHeight(240)
        self.setGraphicsEffect(create_shadow(15, (0, 5)))

        layout = QHBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(15)

        # 資訊區
        info_layout = QVBoxLayout()
        name_label = QLabel(self.filename)
        name_label.setFixedWidth(140)
        name_label.setWordWrap(True)
        name_label.setStyleSheet("color: #222; font-weight: 800; font-size: 13px; background: transparent;")
        info_layout.addWidget(name_label)
        info_layout.addStretch()
        
        self.btn_save = ModernButton("💾 儲存", primary=True)
        self.btn_save.setFixedWidth(100)
        self.btn_save.setFixedHeight(35)
        self.btn_save.setEnabled(False)
        self.btn_save.clicked.connect(self.save_individual)
        info_layout.addWidget(self.btn_save)
        layout.addLayout(info_layout)

        # 預覽區
        preview_layout = QHBoxLayout()
        self.orig_preview = ResponsiveImageLabel("原圖")
        self.proc_preview = ResponsiveImageLabel("等待處理...")
        preview_layout.addWidget(self.orig_preview, 1)
        
        arrow_label = QLabel("➜")
        arrow_label.setStyleSheet("font-size: 24px; color: #999;")
        preview_layout.addWidget(arrow_label)
        
        preview_layout.addWidget(self.proc_preview, 1)
        layout.addLayout(preview_layout, 1)

        self.orig_preview.set_image(self.original_image)

    def set_processed_image(self, img):
        self.processed_image = img
        self.proc_preview.set_image(self.processed_image)
        self.btn_save.setEnabled(True)

    def save_individual(self):
        if self.processed_image is not None:
            name, ext = os.path.splitext(self.filename)
            default_name = f"{name}_processed{ext}"
            file_name, _ = QFileDialog.getSaveFileName(self, "儲存圖片", default_name, "Images (*.jpg *.png)")
            if file_name:
                is_success, im_buf_arr = cv2.imencode(file_name[-4:], self.processed_image)
                if is_success:
                    im_buf_arr.tofile(file_name)
                    QMessageBox.information(self, "成功", f"圖片 {self.filename} 已儲存。")
                else:
                    QMessageBox.warning(self, "錯誤", f"無法儲存圖片 {self.filename}。")

class ProcessWorker(QThread):
    progress = pyqtSignal(int)
    finished_row = pyqtSignal(int, object)
    all_done = pyqtSignal()
    error = pyqtSignal(str)

    def __init__(self, image_rows, color_type, tolerance, fill_method, enhance):
        super().__init__()
        self.image_rows = image_rows
        self.color_type = color_type
        self.tolerance = tolerance
        self.fill_method = fill_method
        self.enhance = enhance

    def run(self):
        try:
            for i, row in enumerate(self.image_rows):
                processed = process_image(row.original_image, self.color_type, self.tolerance, self.fill_method)
                if self.enhance:
                    processed = enhance_text(processed)
                self.finished_row.emit(i, processed)
                self.progress.emit(int((i + 1) / len(self.image_rows) * 100))
            self.all_done.emit()
        except Exception as e:
            self.error.emit(str(e))

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Magic Eraser 專業版")
        self.resize(1280, 850)
        
        icon_path = resource_path("icon.png")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
            
        self.image_rows = []
        self.setup_ui()
        self.apply_theme()

    def apply_theme(self):
        bg_path = resource_path("bg.png")
        if os.path.exists(bg_path):
            bg_image = QPixmap(bg_path)
            palette = QPalette()
            palette.setBrush(QPalette.ColorRole.Window, QBrush(bg_image.scaled(self.size(), Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation)))
            self.setPalette(palette)
            self.setAutoFillBackground(True)

        self.setStyleSheet("""
            QMainWindow { background-color: #f0f2f5; }
            QGroupBox {
                background-color: rgba(255, 255, 255, 0.4);
                border: 1px solid rgba(255, 255, 255, 0.6);
                border-radius: 15px;
                margin-top: 15px;
                font-weight: bold;
                padding-top: 10px;
                color: #444;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 15px;
                color: #222;
                font-size: 14px;
            }
            QRadioButton, QCheckBox, QLabel {
                color: #333;
                background: transparent;
                font-size: 13px;
            }
            QRadioButton::indicator, QCheckBox::indicator {
                width: 18px;
                height: 18px;
            }
            QScrollArea {
                background-color: transparent;
                border: none;
            }
            QScrollBar:vertical {
                border: none;
                background: rgba(0,0,0,0.05);
                width: 10px;
                border-radius: 5px;
            }
            QScrollBar::handle:vertical {
                background: rgba(0,0,0,0.1);
                min-height: 20px;
                border-radius: 5px;
            }
        """)

    def setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # --- 左側側邊欄 ---
        sidebar = QFrame()
        sidebar.setFixedWidth(320)
        sidebar.setStyleSheet("""
            QFrame {
                background-color: rgba(255, 255, 255, 0.7);
                border-right: 1px solid rgba(0, 0, 0, 0.1);
            }
        """)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(20, 30, 20, 20)
        sidebar_layout.setSpacing(20)

        # 標題
        title_label = QLabel("Magic Eraser")
        title_label.setStyleSheet("font-size: 28px; font-weight: 900; color: #1a73e8;")
        subtitle_label = QLabel("考卷手寫筆記清除專家")
        subtitle_label.setStyleSheet("font-size: 13px; color: #666; margin-bottom: 20px;")
        sidebar_layout.addWidget(title_label)
        sidebar_layout.addWidget(subtitle_label)

        # 檔案區
        file_group = QGroupBox("1. 檔案管理")
        file_vbox = QVBoxLayout(file_group)
        self.btn_load = ModernButton("📂 載入圖片 (多選)")
        self.btn_load.clicked.connect(self.load_images)
        self.btn_save_all = ModernButton("💾 全部儲存", primary=True)
        self.btn_save_all.clicked.connect(self.save_all)
        self.btn_save_all.setEnabled(False)
        file_vbox.addWidget(self.btn_load)
        file_vbox.addWidget(self.btn_save_all)
        sidebar_layout.addWidget(file_group)

        # 設定區
        settings_group = QGroupBox("2. 處理設定")
        settings_vbox = QVBoxLayout(settings_group)
        
        settings_vbox.addWidget(QLabel("移除模式:"))
        self.radio_both = QRadioButton("紅 + 藍 (快速)")
        self.radio_red = QRadioButton("僅紅色")
        self.radio_blue = QRadioButton("僅藍色")
        self.radio_ai_all = QRadioButton("AI 全能 (含黑字)")
        self.radio_ai_all.setStyleSheet("color: #d93025; font-weight: bold;")
        self.radio_both.setChecked(True)
        
        self.color_group = QButtonGroup()
        for rb in [self.radio_both, self.radio_red, self.radio_blue, self.radio_ai_all]:
            self.color_group.addButton(rb)
            settings_vbox.addWidget(rb)

        settings_vbox.addSpacing(10)
        settings_vbox.addWidget(QLabel("進階功能:"))
        self.cb_enhance = QCheckBox("增強黑白對比")
        self.cb_ai_fill = QCheckBox("AI 神經修補 (RTX)")
        self.cb_ai_fill.setStyleSheet("color: #188038; font-weight: bold;")
        self.cb_inpaint = QCheckBox("傳統修補")
        
        # 預設非 AI
        self.cb_ai_fill.setChecked(False) 
        self.cb_enhance.setChecked(True)

        settings_vbox.addWidget(self.cb_enhance)
        settings_vbox.addWidget(self.cb_ai_fill)
        settings_vbox.addWidget(self.cb_inpaint)
        sidebar_layout.addWidget(settings_group)

        # 執行按鈕
        sidebar_layout.addStretch()
        self.btn_process_all = ModernButton("✨ 開始轉換 ✨", primary=True)
        self.btn_process_all.setFixedHeight(55)
        self.btn_process_all.setStyleSheet(self.btn_process_all.styleSheet() + "font-size: 18px;")
        self.btn_process_all.clicked.connect(self.process_all)
        self.btn_process_all.setEnabled(False)
        sidebar_layout.addWidget(self.btn_process_all)

        main_layout.addWidget(sidebar)

        # --- 右側主顯示區 ---
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(10, 10, 10, 10)

        # 進度條
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(6)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar { background: rgba(0,0,0,0.05); border: none; border-radius: 3px; }
            QProgressBar::chunk { background: #1a73e8; border-radius: 3px; }
        """)
        self.progress_bar.hide()
        right_layout.addWidget(self.progress_bar)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_content = QWidget()
        self.list_layout = QVBoxLayout(self.scroll_content)
        self.list_layout.setContentsMargins(10, 10, 10, 10)
        self.list_layout.setSpacing(5)
        self.list_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.scroll_area.setWidget(self.scroll_content)
        right_layout.addWidget(self.scroll_area)

        # 初始提示
        self.empty_label = QLabel("請點擊左側「載入圖片」開始使用")
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_label.setStyleSheet("color: #999; font-size: 18px;")
        self.list_layout.addWidget(self.empty_label)

        main_layout.addWidget(right_panel, 1)

    def load_images(self):
        file_names, _ = QFileDialog.getOpenFileNames(self, "開啟圖片 (可多選)", "", "Images (*.png *.jpg *.jpeg *.bmp)")
        if not file_names: return
        self.clear_list()
        self.empty_label.hide()
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        for file_name in file_names:
            QApplication.processEvents()
            img = cv2.imdecode(np.fromfile(file_name, dtype=np.uint8), cv2.IMREAD_COLOR)
            if img is not None:
                img = whiten_background(img)
                row_widget = ImageRow(file_name, img, self)
                self.image_rows.append(row_widget)
                self.list_layout.addWidget(row_widget)
        QApplication.restoreOverrideCursor()
        if self.image_rows:
            self.btn_process_all.setEnabled(True)
        else:
            self.empty_label.show()

    def clear_list(self):
        for i in reversed(range(self.list_layout.count())): 
            widget = self.list_layout.itemAt(i).widget()
            if widget is not None and widget != self.empty_label:
                widget.setParent(None)
                widget.deleteLater()
        self.image_rows.clear()
        self.btn_process_all.setEnabled(False)
        self.btn_save_all.setEnabled(False)

    def process_all(self):
        if not self.image_rows: return
        self.btn_process_all.setEnabled(False)
        self.btn_load.setEnabled(False)
        self.progress_bar.show()
        self.progress_bar.setValue(0)
        
        if self.radio_ai_all.isChecked(): color_type = 'ai_all'
        elif self.radio_both.isChecked(): color_type = 'both'
        elif self.radio_red.isChecked(): color_type = 'red'
        else: color_type = 'blue'
            
        if self.cb_ai_fill.isChecked(): fill_method = 'ai'
        elif self.cb_inpaint.isChecked(): fill_method = 'inpaint'
        else: fill_method = 'white'
        
        self.worker = ProcessWorker(self.image_rows, color_type, 0, fill_method, self.cb_enhance.isChecked())
        self.worker.finished_row.connect(self.on_row_finished)
        self.worker.progress.connect(self.progress_bar.setValue)
        self.worker.all_done.connect(self.on_process_finished)
        self.worker.error.connect(self.on_process_error)
        self.worker.start()

    def on_row_finished(self, index, processed_image):
        self.image_rows[index].set_processed_image(processed_image)

    def on_process_finished(self):
        self.btn_save_all.setEnabled(True)
        self.btn_process_all.setEnabled(True)
        self.btn_load.setEnabled(True)
        self.progress_bar.hide()
        QMessageBox.information(self, "完成", "所有圖片處理完成！")

    def on_process_error(self, msg):
        self.progress_bar.hide()
        self.btn_process_all.setEnabled(True)
        self.btn_load.setEnabled(True)
        QMessageBox.critical(self, "錯誤", f"處理失敗: {msg}")

    def save_all(self):
        dir_path = QFileDialog.getExistingDirectory(self, "選擇儲存資料夾")
        if not dir_path: return
        success = 0
        for row in self.image_rows:
            if row.processed_image is not None:
                name, ext = os.path.splitext(row.filename)
                save_path = os.path.join(dir_path, f"{name}_processed{ext or '.jpg'}")
                is_success, buf = cv2.imencode(ext or '.jpg', row.processed_image)
                if is_success:
                    buf.tofile(save_path)
                    success += 1
        QMessageBox.information(self, "完成", f"成功儲存 {success} 張圖片。")

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.apply_theme()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
