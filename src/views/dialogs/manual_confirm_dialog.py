"""
人工确认对话框
用于循环实验间的人工装填煤粉确认，集成火焰分析和图像播放功能
"""

import json
import shutil
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QSlider, QProgressDialog, QMessageBox, QApplication
)
from PySide6.QtCore import Qt, QTimer, Signal, QThread
from PySide6.QtGui import QPixmap

# 导入火焰分析器
from flamekit import FlameAnalyzer  # type: ignore


class ImageLoaderThread(QThread):
    """图片预加载线程"""
    
    # 信号：加载进度 (当前索引, 总数)
    progress_updated = Signal(int, int)
    # 信号：加载完成 (图片字典)
    loading_completed = Signal(object)  # 使用 object 而不是 dict
    # 信号：加载失败
    loading_failed = Signal(str)
    
    def __init__(self, image_paths: List[str], parent=None):
        super().__init__(parent)
        self.image_paths = image_paths
        self._is_running = True
    
    def run(self):
        """在独立线程中预加载所有图片"""
        pixmap_cache: Dict[int, QPixmap] = {}
        
        try:
            for i, path in enumerate(self.image_paths):
                if not self._is_running:
                    return
                
                pixmap = QPixmap(path)
                if not pixmap.isNull():
                    pixmap_cache[i] = pixmap
                
                self.progress_updated.emit(i + 1, len(self.image_paths))
            
            self.loading_completed.emit(pixmap_cache)
            
        except Exception as e:
            self.loading_failed.emit(str(e))
    
    def stop(self):
        """停止加载"""
        self._is_running = False


class ManualConfirmDialog(QDialog):
    """
    人工确认对话框
    
    Features:
    - 显示当前循环编号
    - 集成火焰图像分析功能
    - 播放分析后的火焰图像(可调速)
    - 显示火焰分析结果
    - 确认/取消按钮（需先完成分析）
    """
    
    confirmed = Signal(dict)  # 确认信号，传递分析结果
    cancelled = Signal()      # 取消信号
    
    def __init__(self, cycle_number: int, image_paths: List[str], parent=None):
        """
        Args:
            cycle_number: 当前循环编号
            image_paths: 原始图像路径列表
            parent: 父窗口
        """
        super().__init__(parent)
        
        self.cycle_number = cycle_number
        self.image_paths = image_paths  # 原始图像路径
        self.analyzed_images: List[str] = []  # 分析后的图像路径
        self.current_image_index = 0
        self.is_playing = False
        self.is_analyzed = False  # 是否已完成分析
        
        # 火焰分析结果
        self.analysis_result: Optional[Dict] = None
        self.max_flame_image_path: str = ""
        self.persistent_max_flame_path: str = ""  # 持久化路径
        
        # 图片缓存
        self.pixmap_cache: Dict[int, QPixmap] = {}
        self.loader_thread = None
        
        # 文件夹路径
        self.system_data_path = ""
        self.temp_captures_dir = ""
        self.temp_analyzed_dir = ""
        self.result_images_dir = ""
        
        # 火焰分析器
        self.flame_analyzer = None
        try:
            self.flame_analyzer = FlameAnalyzer()
        except Exception as e:
            print(f"[警告] FlameAnalyzer 初始化失败: {e}")
        
        # 从配置文件加载播放参数和路径配置
        self.load_playback_config()
        self.load_path_config()
        
        self.setup_ui()
        self.setup_timer()
    
    def load_playback_config(self):
        """从配置文件加载播放参数"""
        try:
            # 使用PathManager获取配置路径（打包后安全）
            try:
                from utils.path_manager import PathManager
                config_path = Path(PathManager.get_config_path("settings.json"))
            except ImportError:
                config_path = Path(__file__).parent.parent.parent.parent / "config" / "settings.json"
            
            if config_path.exists():
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    playback_config = config.get('camera', {}).get('playback', {})
                    
                    # 读取默认FPS，计算帧间隔(ms)
                    default_fps = playback_config.get('default_fps', 30)
                    self.playback_speed = int(1000 / default_fps)  # 转换为毫秒
                    
                    # 读取速度选项
                    self.speed_options = playback_config.get('speed_options', [0.25, 0.5, 1.0, 2.0, 4.0])
            else:
                # 默认值
                self.playback_speed = 33  # 30fps
                self.speed_options = [0.25, 0.5, 1.0, 2.0, 4.0]
        except Exception as e:
            print(f"加载配置文件失败: {e}")
            self.playback_speed = 33
            self.speed_options = [0.25, 0.5, 1.0, 2.0, 4.0]
    
    def load_path_config(self):
        """从配置文件加载路径配置"""
        try:
            # 使用PathManager获取配置路径（打包后安全）
            try:
                from utils.path_manager import PathManager
                config_path = Path(PathManager.get_config_path("settings.json"))
            except ImportError:
                config_path = Path(__file__).parent.parent.parent.parent / "config" / "settings.json"
            
            if config_path.exists():
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    
                    # 读取系统数据路径
                    self.system_data_path = config.get('system', {}).get('data_path', 'D:\\CoalDust\\Data')
                    
                    # 构建各个子文件夹路径
                    self.temp_captures_dir = str(Path(self.system_data_path) / "temp_captures")
                    self.temp_analyzed_dir = str(Path(self.system_data_path) / "temp_captures_analyzed")
                    self.result_images_dir = str(Path(self.system_data_path) / "result_images")
                    
                    # 确保文件夹存在
                    Path(self.temp_captures_dir).mkdir(parents=True, exist_ok=True)
                    Path(self.temp_analyzed_dir).mkdir(parents=True, exist_ok=True)
                    Path(self.result_images_dir).mkdir(parents=True, exist_ok=True)
                    
                    print(f"[路径配置] 原始图片: {self.temp_captures_dir}")
                    print(f"[路径配置] 分析图片: {self.temp_analyzed_dir}")
                    print(f"[路径配置] 持久化: {self.result_images_dir}")
            else:
                # 使用默认路径
                self.system_data_path = "D:\\CoalDust\\Data"
                self.temp_captures_dir = "D:\\CoalDust\\Data\\temp_captures"
                self.temp_analyzed_dir = "D:\\CoalDust\\Data\\temp_captures_analyzed"
                self.result_images_dir = "D:\\CoalDust\\Data\\result_images"
                
        except Exception as e:
            print(f"加载路径配置失败: {e}")
            # 使用默认路径
            self.system_data_path = "D:\\CoalDust\\Data"
            self.temp_captures_dir = "D:\\CoalDust\\Data\\temp_captures"
            self.temp_analyzed_dir = "D:\\CoalDust\\Data\\temp_captures_analyzed"
            self.result_images_dir = "D:\\CoalDust\\Data\\result_images"
    
    def on_analyze_clicked(self):
        """开始火焰分析"""
        # 详细检查图片路径
        print(f"[调试] 传入的图片路径数量: {len(self.image_paths)}")
        print(f"[调试] temp_captures 目录: {self.temp_captures_dir}")
        
        if not self.image_paths:
            # 尝试从 temp_captures 目录读取图片
            temp_dir = Path(self.temp_captures_dir)
            if temp_dir.exists():
                found_images = []
                for ext in ['.jpg', '.jpeg', '.png', '.bmp']:
                    found_images.extend(list(temp_dir.glob(f'*{ext}')))
                    found_images.extend(list(temp_dir.glob(f'*{ext.upper()}')))
                
                if found_images:
                    self.image_paths = [str(p) for p in found_images]
                    print(f"[自动发现] 在 temp_captures 中找到 {len(self.image_paths)} 张图片")
                else:
                    QMessageBox.warning(
                        self, 
                        "警告", 
                        f"没有可分析的图像！\n\n"
                        f"请确保原始图片存在于:\n{self.temp_captures_dir}\n\n"
                        f"支持格式: .jpg, .jpeg, .png, .bmp"
                    )
                    return
            else:
                QMessageBox.warning(
                    self, 
                    "警告", 
                    f"临时文件夹不存在:\n{self.temp_captures_dir}\n\n"
                    f"请先进行图像采集！"
                )
                return
        
        if self.flame_analyzer is None:
            QMessageBox.warning(self, "警告", "火焰分析器未初始化！")
            return
        
        if self.is_analyzed:
            QMessageBox.information(self, "提示", "已完成分析，无需重复分析！")
            return
        
        # 禁用分析按钮
        self.analyze_btn.setEnabled(False)
        
        # 创建进度对话框
        progress_dialog = QProgressDialog("正在分析火焰图像...", "取消", 0, 100, self)
        progress_dialog.setWindowTitle("火焰分析进度")
        progress_dialog.setWindowModality(Qt.WindowModal)
        progress_dialog.setMinimumDuration(0)
        progress_dialog.setValue(0)
        
        try:
            # 清空分析文件夹
            if Path(self.temp_analyzed_dir).exists():
                for file in Path(self.temp_analyzed_dir).glob('*'):
                    if file.is_file():
                        file.unlink()
            
            # 设置进度为不确定模式
            progress_dialog.setRange(0, 0)
            progress_dialog.setLabelText(f"正在分析 {len(self.image_paths)} 张图像...")
            QApplication.processEvents()
            
            # 复制原始图片到分析文件夹
            analyzed_image_paths = []
            for img_path in self.image_paths:
                src_path = Path(img_path)
                # print(f"[复制图片] {src_path} -> 存在: {src_path.exists()}")
                if src_path.exists():
                    dst_path = Path(self.temp_analyzed_dir) / src_path.name
                    shutil.copy2(src_path, dst_path)
                    analyzed_image_paths.append(str(dst_path))
                else:
                    print(f"[警告] 图片不存在: {src_path}")
            
            if not analyzed_image_paths:
                raise Exception(f"没有找到有效的图像文件！\n检查路径:\n{self.temp_captures_dir}")
            
            # 使用 FlameAnalyzer 批量分析（会直接在复制的图片上标注）
            result_data, max_img_path = self.flame_analyzer.batch_analyze(
                analyzed_image_paths,
                save_annotated=True
            )
            
            # 分析完成，恢复进度条
            progress_dialog.setRange(0, 100)
            progress_dialog.setValue(100)
            
            # 保存分析结果
            self.analysis_result = result_data
            self.max_flame_image_path = max_img_path  # 这是 temp_analyzed_dir 中的路径
            self.is_analyzed = True
            
            # 更新结果显示
            max_length = result_data.get('max_length_mm', 0.0)
            max_width = result_data.get('max_width_mm', 0.0)
            area = result_data.get('area_mm2', 0.0)
            
            self.max_label.setText(f"最大火焰长度: {max_length:.2f} mm")
            self.width_label.setText(f"最大火焰宽度: {max_width:.2f} mm")
            self.area_label.setText(f"火焰面积: {area:.2f} mm²")
            
            # 分析后的图像路径
            self.analyzed_images = analyzed_image_paths
            
            # 复制最大火焰图片到持久化文件夹
            if max_img_path and Path(max_img_path).exists():
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                persistent_filename = f"cycle_{self.cycle_number}_{timestamp}_max_flame.jpg"
                self.persistent_max_flame_path = str(Path(self.result_images_dir) / persistent_filename)
                shutil.copy2(max_img_path, self.persistent_max_flame_path)
                print(f"[持久化] 最大火焰图片已保存: {self.persistent_max_flame_path}")
            
            # 启动图片加载
            self.start_loading_analyzed_images()
            
            # 启用播放控制和确认按钮
            self.play_btn.setEnabled(True)
            self.confirm_btn.setEnabled(True)
            
            QMessageBox.information(
                self, 
                "分析完成", 
                f"火焰分析完成！\n\n"
                f"最大火焰长度: {max_length:.2f} mm\n"
                f"最大火焰宽度: {max_width:.2f} mm\n"
                f"火焰面积: {area:.2f} mm²\n\n"
                f"最大火焰图片已保存到: {Path(self.persistent_max_flame_path).name}"
            )
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"火焰分析失败: {str(e)}\n\n请检查图片路径是否正确。")
            self.analyze_btn.setEnabled(True)
            import traceback
            traceback.print_exc()
        finally:
            progress_dialog.close()
    
    def start_loading_analyzed_images(self):
        """启动分析后图片的预加载"""
        if not self.analyzed_images:
            return
        
        self.loader_thread = ImageLoaderThread(self.analyzed_images, self)
        self.loader_thread.progress_updated.connect(self.on_loading_progress)
        self.loader_thread.loading_completed.connect(self.on_loading_completed)
        self.loader_thread.loading_failed.connect(self.on_loading_failed)
        self.loader_thread.start()
        
        # 显示加载提示
        self.image_label.setText("正在加载分析后的图片...")
    
    def on_loading_progress(self, current: int, total: int):
        """加载进度更新"""
        self.image_label.setText(f"加载图片中... {current}/{total}")
    
    def on_loading_completed(self, pixmap_cache: Dict[int, QPixmap]):
        """加载完成"""
        self.pixmap_cache = pixmap_cache
        
        if self.pixmap_cache:
            self.load_image(0)
            self.image_label.setText("图片加载完成，可以播放查看")
        else:
            self.image_label.setText("暂无可用图片")
    
    def on_loading_failed(self, error_msg: str):
        """加载失败"""
        self.image_label.setText(f"图片加载失败: {error_msg}")
    
    def setup_ui(self):
        """初始化UI"""
        self.setWindowTitle("人工确认 - 火焰分析")
        self.setModal(True)
        self.setMinimumSize(900, 800)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)
        
        # 标题
        title_label = QLabel(f"第 {self.cycle_number} 次实验完成")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("""
            QLabel {
                font-size: 24px;
                font-weight: bold;
                color: #fff;
                padding: 10px;
            }
        """)
        layout.addWidget(title_label)
        
        # 提示信息
        info_label = QLabel("请先点击【开始分析】进行火焰图像分析后进行下一次实验...")
        info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        info_label.setStyleSheet("""
            QLabel {
                font-size: 16px;
                color: #ffa500;
                padding: 2px;
                background-color: rgba(255, 165, 0, 0.1);
                border: none;
                background:transparent;
            }
        """)
        layout.addWidget(info_label)
        
        # 图像显示区域（移到最上方）
        image_container = QVBoxLayout()
        image_container.setSpacing(10)
        
        # 图像标签
        self.image_label = QLabel("暂无图像")
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setMinimumSize(640, 480)
        self.image_label.setStyleSheet("""
            QLabel {
                background-color: #000;
                border: 2px solid rgba(255, 255, 255, 0.3);
                border-radius: 5px;
            }
        """)
        image_container.addWidget(self.image_label)
        
        # 图像信息
        self.image_info_label = QLabel("图像 0 / 0")
        self.image_info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_info_label.setStyleSheet("font-size: 13px; color: #aaa; background:transparent;")
        image_container.addWidget(self.image_info_label)
        
        layout.addLayout(image_container)
        
        # 分析结果显示区域
        result_container = QHBoxLayout()
        result_container.setSpacing(15)
        
        self.max_label = QLabel("最大火焰长度: -- mm")
        self.max_label.setStyleSheet("font-size: 15px; color: #00ff00; font-weight: bold;")
        result_container.addWidget(self.max_label)
        
        self.width_label = QLabel("最大火焰宽度: -- mm")
        self.width_label.setStyleSheet("font-size: 15px; color: #00aaff; font-weight: bold;")
        result_container.addWidget(self.width_label)
        
        self.area_label = QLabel("火焰面积: -- mm²")
        self.area_label.setStyleSheet("font-size: 15px; color: #ffaa00; font-weight: bold;")
        result_container.addWidget(self.area_label)
        
        layout.addLayout(result_container)
        
        # 添加弹性空间，将按钮推到下方
        layout.addStretch()
        
        # 第一行按钮：分析、播放控制、确认/取消
        first_row_layout = QHBoxLayout()
        first_row_layout.setSpacing(15)
        
        # 分析按钮
        self.analyze_btn = QPushButton("🔥 开始分析")
        self.analyze_btn.setFixedSize(180, 50)
        self.analyze_btn.clicked.connect(self.on_analyze_clicked)
        self.analyze_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 1, y2: 0,
                    stop: 0 #ff6600,
                    stop: 1 #ff9900
                );
                border: none;
                color: #fff;
                border-radius: 8px;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 1, y2: 0,
                    stop: 0 #ff7700,
                    stop: 1 #ffaa00
                );
            }
            QPushButton:disabled {
                background-color: rgba(100, 100, 100, 0.3);
                color: #666;
            }
        """)
        first_row_layout.addWidget(self.analyze_btn)
        
        first_row_layout.addStretch()
        
        # 上一张按钮
        self.prev_btn = QPushButton("◀ 上一张")
        self.prev_btn.setFixedWidth(100)
        self.prev_btn.setEnabled(False)  # 初始禁用
        self.prev_btn.clicked.connect(self.on_prev_image)
        self.apply_button_style(self.prev_btn, "#555")
        first_row_layout.addWidget(self.prev_btn)
        
        # 播放/暂停按钮
        self.play_btn = QPushButton("▶ 播放")
        self.play_btn.setFixedWidth(100)
        self.play_btn.setEnabled(False)  # 初始禁用
        self.play_btn.clicked.connect(self.on_play_pause)
        self.apply_button_style(self.play_btn, "#00aa00")
        first_row_layout.addWidget(self.play_btn)
        
        # 下一张按钮
        self.next_btn = QPushButton("下一张 ▶")
        self.next_btn.setFixedWidth(100)
        self.next_btn.setEnabled(False)  # 初始禁用
        self.next_btn.clicked.connect(self.on_next_image)
        self.apply_button_style(self.next_btn, "#555")
        first_row_layout.addWidget(self.next_btn)
        
        first_row_layout.addStretch()
        
        # 取消按钮
        cancel_btn = QPushButton("取消")
        cancel_btn.setFixedSize(140, 45)
        cancel_btn.clicked.connect(self.on_cancel)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(100, 100, 100, 0.3);
                border: 1px solid rgba(255, 255, 255, 0.3);
                color: #fff;
                border-radius: 5px;
                font-size: 15px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: rgba(150, 150, 150, 0.4);
            }
        """)
        first_row_layout.addWidget(cancel_btn)
        
        # 确认按钮
        self.confirm_btn = QPushButton("✓ 确认继续")
        self.confirm_btn.setFixedSize(140, 45)
        self.confirm_btn.setEnabled(False)  # 初始禁用，分析完成后才能点击
        self.confirm_btn.clicked.connect(self.on_confirm)
        self.confirm_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 1, y2: 0,
                    stop: 0 #00ff00,
                    stop: 1 #00cc00
                );
                border: none;
                color: #000;
                border-radius: 5px;
                font-size: 15px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 1, y2: 0,
                    stop: 0 #00ff33,
                    stop: 1 #00dd00
                );
            }
            QPushButton:disabled {
                background-color: rgba(100, 100, 100, 0.3);
                color: #666;
            }
        """)
        first_row_layout.addWidget(self.confirm_btn)
        
        layout.addLayout(first_row_layout)
        
        # 第二行按钮：播放速度控制
        second_row_layout = QHBoxLayout()
        second_row_layout.setSpacing(10)
        
        second_row_layout.addStretch()
        
        speed_label = QLabel("播放速度:")
        speed_label.setStyleSheet("font-size: 13px; color: #ccc;")
        second_row_layout.addWidget(speed_label)
        
        self.speed_slider = QSlider(Qt.Orientation.Horizontal)
        self.speed_slider.setMinimum(0)
        self.speed_slider.setMaximum(len(self.speed_options) - 1)
        # 找到1.0x对应的索引作为默认值
        default_index = self.speed_options.index(1.0) if 1.0 in self.speed_options else len(self.speed_options) // 2
        self.speed_slider.setValue(default_index)
        self.speed_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.speed_slider.setTickInterval(1)
        self.speed_slider.valueChanged.connect(self.on_speed_changed)
        self.speed_slider.setFixedWidth(300)  # 固定宽度
        second_row_layout.addWidget(self.speed_slider)
        
        self.speed_value_label = QLabel(f"{self.speed_options[default_index]}x")
        self.speed_value_label.setStyleSheet("font-size: 13px; color: #ccc; min-width: 60px;")
        second_row_layout.addWidget(self.speed_value_label)
        
        second_row_layout.addStretch()
        layout.addLayout(second_row_layout)
        
        # 应用全局样式
        self.setStyleSheet("""
            QDialog {
                background-color: #1a1a2e;
                color: #ffffff;
            }
        """)
    
    def apply_button_style(self, button: QPushButton, color: str):
        """应用按钮样式"""
        button.setStyleSheet(f"""
            QPushButton {{
                background-color: {color};
                border: none;
                color: #fff;
                padding: 8px;
                border-radius: 5px;
                font-size: 13px;
            }}
            QPushButton:hover {{
                opacity: 0.8;
            }}
            QPushButton:disabled {{
                background-color: rgba(100, 100, 100, 0.3);
                color: #666;
            }}
        """)
    
    def setup_timer(self):
        """设置播放定时器"""
        self.play_timer = QTimer(self)
        self.play_timer.timeout.connect(self.on_timer_tick)
    
    def load_image(self, index: int):
        """从缓存加载图像（性能优化）"""
        # 使用分析后的图像列表
        images = self.analyzed_images if self.is_analyzed else self.image_paths
        
        if not images or index < 0 or index >= len(images):
            return
        
        try:
            # 从缓存中获取图片
            pixmap = self.pixmap_cache.get(index)
            
            if pixmap is None or pixmap.isNull():
                self.image_label.setText("图像不可用")
                return
            
            # 缩放图像以适应标签大小
            scaled_pixmap = pixmap.scaled(
                self.image_label.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            
            self.image_label.setPixmap(scaled_pixmap)
            self.current_image_index = index
            
            # 更新信息
            self.image_info_label.setText(
                f"图像 {index + 1} / {len(images)}"
            )
            
            # 更新按钮状态
            self.prev_btn.setEnabled(index > 0)
            self.next_btn.setEnabled(index < len(images) - 1)
            
        except Exception as e:
            self.image_label.setText(f"加载错误: {str(e)}")
    
    def on_prev_image(self):
        """上一张"""
        if self.current_image_index > 0:
            self.load_image(self.current_image_index - 1)
    
    def on_next_image(self):
        """下一张"""
        images = self.analyzed_images if self.is_analyzed else self.image_paths
        if self.current_image_index < len(images) - 1:
            self.load_image(self.current_image_index + 1)
    
    def on_play_pause(self):
        """播放/暂停"""
        images = self.analyzed_images if self.is_analyzed else self.image_paths
        if not images:
            return
        
        self.is_playing = not self.is_playing
        
        if self.is_playing:
            self.play_btn.setText("⏸ 暂停")
            self.apply_button_style(self.play_btn, "#ff8800")
            self.play_timer.start(self.playback_speed)
        else:
            self.play_btn.setText("▶ 播放")
            self.apply_button_style(self.play_btn, "#00aa00")
            self.play_timer.stop()
    
    def on_timer_tick(self):
        """定时器触发"""
        images = self.analyzed_images if self.is_analyzed else self.image_paths
        
        # 加载下一张图像
        next_index = self.current_image_index + 1
        
        if next_index >= len(images):
            # 循环播放
            next_index = 0
        
        self.load_image(next_index)
    
    def on_speed_changed(self, value: int):
        """速度滑块变化"""
        # 根据速度选项计算实际播放间隔
        speed_multiplier = self.speed_options[value]
        # 从配置文件读取的基础速度除以倍率
        base_speed = int(1000 / 30)  # 默认30fps的基础间隔
        actual_speed = int(base_speed / speed_multiplier)
        
        self.playback_speed = actual_speed
        self.speed_value_label.setText(f"{speed_multiplier}x")
        
        # 如果正在播放，更新定时器间隔
        if self.is_playing:
            self.play_timer.setInterval(self.playback_speed)
    
    def on_confirm(self):
        """确认按钮"""
        if not self.is_analyzed:
            QMessageBox.warning(self, "警告", "请先完成火焰分析！")
            return
        
        # 停止播放
        if self.is_playing:
            self.play_timer.stop()
        
        # 构造返回结果（使用持久化路径）
        result = {
            'cycle': self.cycle_number,
            'max_length_mm': self.analysis_result.get('max_length_mm', 0.0),
            'max_width_mm': self.analysis_result.get('max_width_mm', 0.0),
            'area_mm2': self.analysis_result.get('area_mm2', 0.0),
            'image_path': self.persistent_max_flame_path,  # 返回持久化路径
            'temp_analyzed_path': self.max_flame_image_path,  # 临时分析路径
            'analyzed': True
        }
        
        self.confirmed.emit(result)
        self.accept()
    
    def on_cancel(self):
        """取消按钮"""
        # 停止播放
        if self.is_playing:
            self.play_timer.stop()
        
        self.cancelled.emit()
        self.reject()
    
    def closeEvent(self, event):
        """关闭事件"""
        # 停止播放
        if self.is_playing:
            self.play_timer.stop()
        
        # 停止并清理加载线程
        if self.loader_thread and self.loader_thread.isRunning():
            self.loader_thread.stop()
            self.loader_thread.wait()  # 等待线程结束
        
        # 清理缓存
        self.pixmap_cache.clear()
        
        super().closeEvent(event)

