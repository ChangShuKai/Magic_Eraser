import sys
import os
import cv2
import numpy as np
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QLabel, QFileDialog, 
                             QRadioButton, QButtonGroup, QCheckBox, 
                             QGroupBox, QMessageBox, QScrollArea, QFrame, QSizePolicy,
                             QGraphicsDropShadowEffect, QProgressBar, QDialog)
from PyQt6.QtCore import Qt, QSize, QThread, pyqtSignal
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
    def __init__(self, text, parent=None, color_type="default"):
        super().__init__(text, parent)
        self.color_type = color_type
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.update_style()

    def update_style(self, hover=False):
        if self.color_type == "save":
            bg = "rgba(33, 150, 243, 0.7)" if not hover else "rgba(33, 150, 243, 0.9)"
            color = "white"
        elif self.color_type == "load":
            bg = "rgba(255, 255, 255, 0.6)" if not hover else "rgba(255, 255, 255, 0.8)"
            color = "#333"
        elif self.color_type == "process":
            bg = "rgba(76, 175, 80, 0.7)" if not hover else "rgba(76, 175, 80, 0.9)"
            color = "white"
        else:
            bg = "rgba(255, 255, 255, 0.4)" if not hover else "rgba(255, 255, 255, 0.6)"
            color = "#222"
        
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {bg};
                border: 1px solid rgba(255, 255, 255, 0.4);
                border-radius: 10px;
                color: {color};
                font-weight: bold;
                font-size: 14px;
                padding: 10px 20px;
            }}
            QPushButton:disabled {{
                background-color: rgba(200, 200, 200, 0.2);
                color: #999;
            }}
        """)

    def enterEvent(self, event):
        self.update_style(True)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.update_style(False)
        super().leaveEvent(event)

class ImageDialog(QDialog):
    """點擊圖片後彈出的放大預覽視窗"""
    def __init__(self, pixmap, title="圖片預覽", parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumSize(800, 600)
        self.resize(1200, 900)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # 使用滾動區域來容納大圖片
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("background-color: #1a1a1a; border: none;")
        
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # 根據視窗大小縮放圖片，但保持原圖細節（可以稍微大一點）
        self.pixmap = pixmap
        self.image_label.setPixmap(self.pixmap)
        
        scroll.setWidget(self.image_label)
        layout.addWidget(scroll)
        
        # 加上按鍵說明或關閉按鈕的提示
        self.setStyleSheet("QDialog { background-color: #1a1a1a; }")

class ResponsiveImageLabel(QLabel):
    def __init__(self, text=""):
        super().__init__(text)
        self.original_pixmap = None
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet("background-color: rgba(255, 255, 255, 0.1); border-radius: 10px; color: #fff;")
        self.setMinimumSize(100, 100)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip("點擊可放大觀看")
        
    def set_image(self, img_array):
        if img_array is None: return
        img_rgb = cv2.cvtColor(img_array, cv2.COLOR_BGR2RGB)
        h, w, ch = img_rgb.shape
        qt_img = QImage(img_rgb.data, w, h, ch * w, QImage.Format.Format_RGB888).copy()
        self.original_pixmap = QPixmap.fromImage(qt_img)
        self.update()
        
    def paintEvent(self, event):
        super().paintEvent(event)
        if self.original_pixmap and not self.original_pixmap.isNull():
            painter = QPainter(self)
            painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
            scaled = self.original_pixmap.scaled(self.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            x = (self.width() - scaled.width()) // 2
            y = (self.height() - scaled.height()) // 2
            painter.drawPixmap(x, y, scaled)

    def mousePressEvent(self, event):
        """點擊事件：彈出放大視窗"""
        if self.original_pixmap and not self.original_pixmap.isNull():
            dialog = ImageDialog(self.original_pixmap, "放大觀看", self.window())
            dialog.exec()
        super().mousePressEvent(event)

class ImageRow(QFrame):
    def __init__(self, file_path, original_image, parent_window):
        super().__init__()
        self.file_path = file_path
        self.filename = os.path.basename(file_path)
        self.original_image = original_image
        self.processed_image = None
        self.setStyleSheet("background-color: rgba(255, 255, 255, 0.2); border-radius: 15px; border: 1px solid rgba(255, 255, 255, 0.3);")
        self.setMinimumHeight(200)

        layout = QHBoxLayout(self)
        
        info_layout = QVBoxLayout()
        name_label = QLabel(self.filename)
        name_label.setStyleSheet("color: #fff; font-weight: bold; background: transparent;")
        info_layout.addWidget(name_label)
        self.btn_save = ModernButton("💾 儲存", color_type="save")
        self.btn_save.setEnabled(False)
        self.btn_save.clicked.connect(self.save_individual)
        info_layout.addWidget(self.btn_save)
        layout.addLayout(info_layout)

        self.orig_preview = ResponsiveImageLabel("原圖")
        self.proc_preview = ResponsiveImageLabel("處理後")
        layout.addWidget(self.orig_preview, 1)
        layout.addWidget(self.proc_preview, 1)

        self.orig_preview.set_image(self.original_image)

    def set_processed_image(self, img):
        self.processed_image = img
        self.proc_preview.set_image(self.processed_image)
        self.btn_save.setEnabled(True)

    def save_individual(self):
        if self.processed_image is not None:
            name, ext = os.path.splitext(self.filename)
            file_name, _ = QFileDialog.getSaveFileName(self, "儲存圖片", f"{name}_clean{ext}", "Images (*.jpg *.png)")
            if file_name:
                cv2.imencode(file_name[-4:], self.processed_image)[1].tofile(file_name)
                QMessageBox.information(self, "成功", "已儲存。")

class ProcessWorker(QThread):
    progress = pyqtSignal(int)
    finished_row = pyqtSignal(int, object)
    all_done = pyqtSignal()

    def __init__(self, image_rows, color_type, fill_method, enhance):
        super().__init__()
        self.image_rows = image_rows
        self.color_type = color_type
        self.fill_method = fill_method
        self.enhance = enhance

    def run(self):
        for i, row in enumerate(self.image_rows):
            processed = process_image(row.original_image, self.color_type, 50, self.fill_method)
            if self.enhance: processed = enhance_text(processed)
            self.finished_row.emit(i, processed)
            self.progress.emit(int((i + 1) / len(self.image_rows) * 100))
        self.all_done.emit()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Magic Eraser - 考卷手寫筆記去除工具")
        self.resize(1100, 800)
        self.image_rows = []
        self.setup_ui()
        self.apply_theme()

    def apply_theme(self):
        bg_path = resource_path("bg.png")
        if os.path.exists(bg_path):
            bg_pixmap = QPixmap(bg_path)
            palette = QPalette()
            palette.setBrush(QPalette.ColorRole.Window, QBrush(bg_pixmap.scaled(self.size(), Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation)))
            self.setPalette(palette)
            self.setAutoFillBackground(True)

    def setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(10)

        # --- 上方控制面板 (橫向) ---
        control_panel = QHBoxLayout()
        
        # 檔案操作
        file_group = QGroupBox("檔案操作")
        file_group.setStyleSheet("QGroupBox { background-color: rgba(255, 255, 255, 0.3); border: 1px solid rgba(255, 255, 255, 0.4); border-radius: 15px; padding-top: 20px; font-weight: bold; color: #333; } QGroupBox::title { subcontrol-origin: margin; subcontrol-position: top center; padding: 0 10px; }")
        file_layout = QHBoxLayout(file_group)
        self.btn_save_all = ModernButton("💾 全部儲存", color_type="save")
        self.btn_save_all.setEnabled(False)
        self.btn_save_all.clicked.connect(self.save_all)
        self.btn_load = ModernButton("📂 載入圖片 (支援多選)", color_type="load")
        self.btn_load.clicked.connect(self.load_images)
        file_layout.addWidget(self.btn_save_all)
        file_layout.addWidget(self.btn_load)
        control_panel.addWidget(file_group)

        # 處理設定
        settings_group = QGroupBox("處理設定")
        settings_group.setStyleSheet("QGroupBox { background-color: rgba(255, 255, 255, 0.3); border: 1px solid rgba(255, 255, 255, 0.4); border-radius: 15px; padding-top: 20px; font-weight: bold; color: #333; } QGroupBox::title { subcontrol-origin: margin; subcontrol-position: top center; padding: 0 10px; }")
        settings_layout = QHBoxLayout(settings_group)

        settings_group2 = QGroupBox("說明")
        settings_group2.setStyleSheet("QGroupBox { background-color: rgba(255, 255, 255, 0.3); border: 1px solid rgba(255, 255, 255, 0.4); border-radius: 15px; padding-top: 20px; font-weight: bold; color: #333; } QGroupBox::title { subcontrol-origin: margin; subcontrol-position: top center; padding: 0 10px; }")
        settings_layout2 = QVBoxLayout(settings_group2)
        
        l1=QLabel("1. 先選取要清除手寫筆記的圖片")
        l2=QLabel("2. 設定要清洗的顏色")
        l3=QLabel("3. 按下「清除手寫筆記」按鈕")
        l4=QLabel("4. 觀看處理結果(或直接下載)")
        l5=QLabel("5. 按下「全部儲存」按鈕儲存所有圖片或單張圖片")

        settings_layout2.addWidget(l1)
        settings_layout2.addWidget(l2)
        settings_layout2.addWidget(l3)
        settings_layout2.addWidget(l4)
        settings_layout2.addWidget(l5)

        settings_group3 = QGroupBox("開發者")
        settings_group3.setStyleSheet("QGroupBox { background-color: rgba(255, 255, 255, 0.3); border: 1px solid rgba(255, 255, 255, 0.4); border-radius: 10px; padding-top: 20px; font-weight: bold; color: #333; } QGroupBox::title { subcontrol-origin: margin; subcontrol-position: top center; padding: 0 10px; }")
        settings_layout3 = QVBoxLayout(settings_group3)
        settings_layout3.setSpacing(1)

        settings_layout3.addStretch()

        De = QLabel("Developer : ChangShuKai")
        De2 = QLabel("Create by : Six Star Culture")
        De.setStyleSheet("""
            font-size: 20px; 
            font-weight: bold; 
            color: #333;
            qproperty-alignment: 'AlignCenter';
        """)
        De2.setStyleSheet("""
            font-size: 20px; 
            font-weight: bold; 
            color: #333;
            qproperty-alignment: 'AlignCenter';
        """)
        settings_layout3.addWidget(De)
        settings_layout3.addWidget(De2)
        settings_layout3.addStretch()

        # 左側選項
        options_vbox = QVBoxLayout()
        
        # 顏色行
        color_row = QHBoxLayout()
        color_row.addWidget(QLabel("要去除的顏色:"))
        self.radio_red = QRadioButton("紅色")
        self.radio_blue = QRadioButton("藍色")
        self.radio_both = QRadioButton("紅+藍皆去除")
        self.radio_both.setChecked(True)
        self.color_group = QButtonGroup()
        for r in [self.radio_red, self.radio_blue, self.radio_both]:
            self.color_group.addButton(r)
            color_row.addWidget(r)
        options_vbox.addLayout(color_row)

        # 勾選行
        check_row = QHBoxLayout()
        self.cb_inpaint = QCheckBox("使用智慧修補 (修補殘留網點)")
        self.cb_enhance = QCheckBox("增強黑白對比")
        self.cb_enhance.setChecked(True)
        check_row.addWidget(self.cb_inpaint)
        check_row.addWidget(self.cb_enhance)
        options_vbox.addLayout(check_row)
        
        settings_layout.addLayout(options_vbox)
        settings_layout.addStretch()

        # 執行按鈕
        self.btn_process_all = ModernButton("✨ 清除手寫筆記 ✨", color_type="process")
        self.btn_process_all.setMinimumHeight(60)
        self.btn_process_all.setEnabled(False)
        self.btn_process_all.clicked.connect(self.process_all)
        settings_layout.addWidget(self.btn_process_all)
        
        control_panel.addWidget(settings_group3, 1)
        control_panel.addWidget(settings_group2, 1)
        control_panel.addWidget(settings_group, 1)
        main_layout.addLayout(control_panel)

        # --- 進度條 ---
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(8)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setStyleSheet("QProgressBar { background: rgba(255, 255, 255, 0.2); border-radius: 4px; border: none; } QProgressBar::chunk { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4caf50, stop:1 #81c784); border-radius: 4px; }")
        self.progress_bar.hide()
        main_layout.addWidget(self.progress_bar)

        # --- 列表區 ---
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("background: transparent; border: none;")
        self.scroll_content = QWidget()
        self.scroll_content.setStyleSheet("background: transparent; color: black; font-weight: bold; ") 
        self.list_layout = QVBoxLayout(self.scroll_content)
        self.list_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.scroll_area.setWidget(self.scroll_content)
        main_layout.addWidget(self.scroll_area, 1)

    def load_images(self):
        files, _ = QFileDialog.getOpenFileNames(self, "開啟圖片", "", "Images (*.png *.jpg *.jpeg *.bmp)")
        if not files: return
        self.clear_list()
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        for f in files:
            img = cv2.imdecode(np.fromfile(f, dtype=np.uint8), cv2.IMREAD_COLOR)
            if img is not None:
                img = whiten_background(img)
                row = ImageRow(f, img, self)
                self.image_rows.append(row)
                self.list_layout.addWidget(row)
        QApplication.restoreOverrideCursor()
        self.btn_process_all.setEnabled(bool(self.image_rows))

    def clear_list(self):
        for i in reversed(range(self.list_layout.count())):
            widget = self.list_layout.itemAt(i).widget()
            if widget: widget.deleteLater()
        self.image_rows.clear()
        self.btn_process_all.setEnabled(False)
        self.btn_save_all.setEnabled(False)

    def process_all(self):
        self.btn_process_all.setEnabled(False)
        self.progress_bar.show()
        color_type = 'both' if self.radio_both.isChecked() else ('red' if self.radio_red.isChecked() else 'blue')
        fill_method = 'inpaint' if self.cb_inpaint.isChecked() else 'white'
        self.worker = ProcessWorker(self.image_rows, color_type, fill_method, self.cb_enhance.isChecked())
        self.worker.finished_row.connect(lambda idx, img: self.image_rows[idx].set_processed_image(img))
        self.worker.progress.connect(self.progress_bar.setValue)
        self.worker.all_done.connect(self.on_process_done)
        self.worker.start()

    def on_process_done(self):
        self.btn_save_all.setEnabled(True)
        self.btn_process_all.setEnabled(True)
        self.progress_bar.hide()
        QMessageBox.information(self, "完成", "清除完成！")

    def save_all(self):
        path = QFileDialog.getExistingDirectory(self, "選擇資料夾")
        if not path: return
        for row in self.image_rows:
            if row.processed_image is not None:
                name, ext = os.path.splitext(row.filename)
                cv2.imencode(ext or '.jpg', row.processed_image)[1].tofile(os.path.join(path, f"{name}_clean{ext or '.jpg'}"))
        QMessageBox.information(self, "完成", "已全部儲存。")

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.apply_theme()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
