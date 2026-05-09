import sys
import os
import cv2
import numpy as np
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QLabel, QFileDialog, 
                             QRadioButton, QButtonGroup, QCheckBox, 
                             QGroupBox, QMessageBox, QScrollArea, QFrame, QSizePolicy)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QImage, QPixmap, QPainter

from image_processor import process_image, enhance_text, whiten_background

class ResponsiveImageLabel(QLabel):
    """可以根據視窗大小自動縮放圖片的標籤"""
    def __init__(self, text=""):
        super().__init__(text)
        self.original_pixmap = None
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet("background-color: #e0e0e0; border: 1px solid #aaa; border-radius: 4px;")
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
        self.update() # 觸發重新繪製
        
    def paintEvent(self, event):
        super().paintEvent(event)
        if self.original_pixmap and not self.original_pixmap.isNull():
            painter = QPainter(self)
            painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
            
            # 計算等比例縮放的大小和置中位置
            scaled = self.original_pixmap.scaled(
                self.size(), 
                Qt.AspectRatioMode.KeepAspectRatio, 
                Qt.TransformationMode.SmoothTransformation
            )
            
            x = (self.width() - scaled.width()) // 2
            y = (self.height() - scaled.height()) // 2
            
            painter.drawPixmap(x, y, scaled)

class ImageRow(QFrame):
    """代表列表中單個圖片處理列的 UI 元件"""
    def __init__(self, file_path, original_image, parent_window):
        super().__init__()
        self.file_path = file_path
        self.filename = os.path.basename(file_path)
        self.original_image = original_image
        self.processed_image = None
        self.parent_window = parent_window

        self.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Raised)
        self.setLineWidth(1)
        self.setStyleSheet("ImageRow { background-color: #f9f9f9; margin-bottom: 5px; border-radius: 5px; }")
        # 設定列的最小高度，這樣縮放時版面不會太擠
        self.setMinimumHeight(200)

        layout = QHBoxLayout(self)

        # 檔案名稱
        name_label = QLabel(self.filename)
        name_label.setFixedWidth(150)
        name_label.setWordWrap(True)
        layout.addWidget(name_label)

        # 原圖預覽 (響應式)
        self.orig_preview = ResponsiveImageLabel("原圖")
        layout.addWidget(self.orig_preview, 1)

        # 處理後預覽 (響應式)
        self.proc_preview = ResponsiveImageLabel("處理後預覽")
        layout.addWidget(self.proc_preview, 1)

        # 單獨儲存按鈕
        self.btn_save = QPushButton("儲存此圖片")
        self.btn_save.setFixedWidth(100)
        self.btn_save.setEnabled(False)
        self.btn_save.clicked.connect(self.save_individual)
        layout.addWidget(self.btn_save)

        # 顯示原圖預覽縮圖
        self.orig_preview.set_image(self.original_image)

    def set_processed_image(self, img):
        self.processed_image = img
        self.proc_preview.set_image(self.processed_image)
        self.btn_save.setEnabled(True)

    def save_individual(self):
        if self.processed_image is not None:
            # 預設儲存檔名：原檔名加上 _processed
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


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("考卷手寫筆記去除工具 - 批量處理版")
        self.resize(1100, 800)
        
        self.image_rows = []

        self.setup_ui()

    def setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # --- 上方控制面板 ---
        top_panel = QWidget()
        top_layout = QHBoxLayout(top_panel)
        top_layout.setContentsMargins(0, 0, 0, 0)

        # 檔案操作群組
        file_group = QGroupBox("檔案操作")
        file_layout = QVBoxLayout()
        
        btn_layout = QHBoxLayout()
        self.btn_load = QPushButton("載入圖片 (支援多選)")
        self.btn_load.clicked.connect(self.load_images)
        self.btn_save_all = QPushButton("全部儲存 (左上角)")
        self.btn_save_all.clicked.connect(self.save_all)
        self.btn_save_all.setEnabled(False)
        self.btn_save_all.setStyleSheet("background-color: #2196F3; color: white; font-weight: bold;")
        
        btn_layout.addWidget(self.btn_save_all)
        btn_layout.addWidget(self.btn_load)
        
        file_layout.addLayout(btn_layout)
        file_group.setLayout(file_layout)
        top_layout.addWidget(file_group)

        # 處理設定群組
        param_group = QGroupBox("處理設定")
        param_layout = QVBoxLayout()

        # 顏色與容差配置 (水平排列以節省空間)
        settings_layout1 = QHBoxLayout()
        settings_layout1.addWidget(QLabel("要去除的顏色:"))
        self.radio_red = QRadioButton("紅色")
        self.radio_blue = QRadioButton("藍色")
        self.radio_both = QRadioButton("紅+藍皆去除")
        self.radio_both.setChecked(True) # 預設改為雙色去除，更方便
        self.color_group = QButtonGroup()
        self.color_group.addButton(self.radio_red)
        self.color_group.addButton(self.radio_blue)
        self.color_group.addButton(self.radio_both)
        settings_layout1.addWidget(self.radio_red)
        settings_layout1.addWidget(self.radio_blue)
        settings_layout1.addWidget(self.radio_both)
        settings_layout1.addStretch()
        param_layout.addLayout(settings_layout1)

        # 進階設定配置
        settings_layout2 = QHBoxLayout()
        self.cb_inpaint = QCheckBox("使用智慧修補 (更徹底去除痕跡)")
        self.cb_inpaint.setChecked(True) # 預設開啟智慧修補
        self.cb_enhance = QCheckBox("增強黑白對比")
        settings_layout2.addWidget(self.cb_inpaint)
        settings_layout2.addWidget(self.cb_enhance)
        settings_layout2.addStretch()
        
        self.btn_process_all = QPushButton("全部轉換")
        self.btn_process_all.setMinimumHeight(40)
        self.btn_process_all.setMinimumWidth(120)
        self.btn_process_all.clicked.connect(self.process_all)
        self.btn_process_all.setEnabled(False)
        self.btn_process_all.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")
        settings_layout2.addWidget(self.btn_process_all)

        param_layout.addLayout(settings_layout2)
        param_group.setLayout(param_layout)
        top_layout.addWidget(param_group, 1)

        main_layout.addWidget(top_panel)

        # --- 下方圖片排排站展示區 ---
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        
        self.scroll_content = QWidget()
        self.list_layout = QVBoxLayout(self.scroll_content)
        self.list_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        self.scroll_area.setWidget(self.scroll_content)
        main_layout.addWidget(self.scroll_area, 1)

    def load_images(self):
        file_names, _ = QFileDialog.getOpenFileNames(self, "開啟圖片 (可多選)", "", "Images (*.png *.jpg *.jpeg *.bmp)")
        if not file_names:
            return

        # 清除舊的列表
        self.clear_list()

        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        
        for file_name in file_names:
            # 讓 UI 更新，避免大量載入時「沒有回應」
            QApplication.processEvents()
            
            # 讀取圖片並處理背景
            img = cv2.imdecode(np.fromfile(file_name, dtype=np.uint8), cv2.IMREAD_COLOR)
            if img is not None:
                # 載入圖片時自動套用背景去灰白化
                img = whiten_background(img)
                
                # 建立新的 UI 行
                row_widget = ImageRow(file_name, img, self)
                self.image_rows.append(row_widget)
                self.list_layout.addWidget(row_widget)
                
        QApplication.restoreOverrideCursor()
        
        if self.image_rows:
            self.btn_process_all.setEnabled(True)
            self.btn_save_all.setEnabled(False)
        else:
            QMessageBox.warning(self, "錯誤", "無法載入任何圖片。")

    def clear_list(self):
        for i in reversed(range(self.list_layout.count())): 
            widget = self.list_layout.itemAt(i).widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()
        self.image_rows.clear()
        self.btn_process_all.setEnabled(False)
        self.btn_save_all.setEnabled(False)

    def process_all(self):
        if not self.image_rows:
            return

        self.btn_process_all.setEnabled(False)
        self.btn_load.setEnabled(False)
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)

        try:
            if self.radio_both.isChecked():
                color_type = 'both'
            elif self.radio_red.isChecked():
                color_type = 'red'
            else:
                color_type = 'blue'
                
            # 使用者要求取消滑桿，直接帶入 0
            tolerance = 0
            fill_method = 'inpaint' if self.cb_inpaint.isChecked() else 'white'
            enhance = self.cb_enhance.isChecked()

            for row in self.image_rows:
                # 讓 UI 有機會更新 (例如進度提示)
                QApplication.processEvents() 
                
                # 執行影像處理
                processed = process_image(row.original_image, color_type, tolerance, fill_method)
                if enhance:
                    processed = enhance_text(processed)
                    
                row.set_processed_image(processed)

            self.btn_save_all.setEnabled(True)
            QMessageBox.information(self, "完成", "所有圖片轉換完成！\n您可以在右側單獨儲存，或點擊左上角全部儲存。")

        except Exception as e:
            QMessageBox.critical(self, "處理錯誤", f"發生錯誤: {str(e)}")
        finally:
            self.btn_process_all.setEnabled(True)
            self.btn_load.setEnabled(True)
            QApplication.restoreOverrideCursor()

    def save_all(self):
        if not self.image_rows:
            return

        dir_path = QFileDialog.getExistingDirectory(self, "選擇儲存資料夾 (全部儲存)")
        if not dir_path:
            return

        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        success_count = 0
        
        for row in self.image_rows:
            if row.processed_image is not None:
                name, ext = os.path.splitext(row.filename)
                # 確保副檔名格式正確
                if not ext:
                    ext = ".jpg"
                
                save_path = os.path.join(dir_path, f"{name}_processed{ext}")
                
                is_success, im_buf_arr = cv2.imencode(ext, row.processed_image)
                if is_success:
                    im_buf_arr.tofile(save_path)
                    success_count += 1
                    
        QApplication.restoreOverrideCursor()
        QMessageBox.information(self, "儲存完成", f"成功儲存 {success_count} 張圖片到:\n{dir_path}")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
