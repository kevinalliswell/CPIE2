#!/usr/bin/env python
# -*- encoding: utf-8 -*-
"""
优化版火焰分析仪UI模块
Optimized Flame Analyzer Widget
"""
import json
import os
import csv
import shutil
from time import time
from pathlib import Path
from typing import List, Dict, Optional

from PySide6 import QtWidgets
from PySide6.QtCore import Qt, Signal, QStandardPaths
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QMessageBox, QProgressDialog, QApplication, QDialog, QFileDialog

from .config_manager import FlameAnalyzerConfig
from .flame_processor import FlameImageProcessor, FlameAnalysisResult, FlameStatistics


class FlameAnalyzerWidget(QDialog):
    """
    优化版火焰分析仪主窗口
    
    改进点:
    1. 使用配置类管理参数
    2. 分离业务逻辑和UI逻辑
    3. 流式处理节省内存
    4. 增强异常处理
    5. 优化进度更新频率
    """
    
    # 定义信号
    window_closed = Signal(dict)
    
    def __init__(self, input_folder: str, config: Optional[FlameAnalyzerConfig] = None,
                 processor: Optional[FlameImageProcessor] = None):
        """
        初始化窗口
        
        Args:
            input_folder: 输入图像文件夹
            config: 配置对象,可选
            processor: 处理器对象,可选(用于测试)
        """
        super().__init__()
        
        # 配置和处理器
        self.config = config or FlameAnalyzerConfig()
        self.processor = processor or FlameImageProcessor(self.config)
        
        # 数据
        self.input_folder = input_folder
        self.output_folder = None
        self.analysis_results: List[FlameAnalysisResult] = []
        self.statistics: Optional[FlameStatistics] = None
        self.exp_results: Dict = {}
        
        # 时间记录
        self.start_time = 0
        
        # 播放控制
        self.is_playing = False
        self.play_speed = 1.0  # 默认1倍速
        self.play_timer = None
        
        # 分析完成标志
        self.analysis_completed = False
        
        # 初始化UI
        self._init_ui()
        
        # 自动启动分析（延迟100ms，确保窗口完全显示后再启动）
        from PySide6.QtCore import QTimer
        QTimer.singleShot(100, self._auto_start_analysis)
    
    def _init_ui(self):
        """初始化用户界面"""
        self.setWindowTitle(self.config.window_title)
        self.setWindowFlags(Qt.Dialog | Qt.WindowCloseButtonHint)
        self.setWindowModality(Qt.ApplicationModal)
        self.resize(1000, 700)
        
        # 主布局（QDialog直接使用setLayout）
        main_layout = QtWidgets.QVBoxLayout(self)
        
        # 顶部信息区
        info_group = self._create_info_group()
        main_layout.addWidget(info_group)
        
        # 中间内容区
        content_layout = QtWidgets.QHBoxLayout()
        
        # 左侧列表
        list_group = self._create_list_group()
        content_layout.addWidget(list_group, 1)
        
        # 右侧图像显示
        image_group = self._create_image_group()
        content_layout.addWidget(image_group, 2)
        
        main_layout.addLayout(content_layout)
        
        # 底部按钮区
        button_layout = self._create_button_layout()
        main_layout.addLayout(button_layout)
        
        # 连接信号
        self._connect_signals()
    
    def _create_info_group(self) -> QtWidgets.QGroupBox:
        """创建信息显示组"""
        group = QtWidgets.QGroupBox("分析信息")
        layout = QtWidgets.QVBoxLayout()
        
        # 统计标签
        self.max_label = QtWidgets.QLabel("最大值: -- mm")
        self.min_label = QtWidgets.QLabel("最小值: -- mm")
        self.avg_label = QtWidgets.QLabel("平均值: -- mm")
        
        # 路径标签
        self.lb_img_path = QtWidgets.QLabel("图片保存路径: 未开始分析")
        self.lb_img_path.setWordWrap(True)
        
        layout.addWidget(self.max_label)
        layout.addWidget(self.min_label)
        layout.addWidget(self.avg_label)
        layout.addWidget(self.lb_img_path)
        
        group.setLayout(layout)
        return group
    
    def _create_list_group(self) -> QtWidgets.QGroupBox:
        """创建列表显示组"""
        group = QtWidgets.QGroupBox("分析结果列表")
        layout = QtWidgets.QVBoxLayout()
        
        # 列表控件
        self.list_widget = QtWidgets.QListWidget()
        layout.addWidget(self.list_widget)
        
        # 导航按钮
        nav_layout = QtWidgets.QHBoxLayout()
        self.prev_button = QtWidgets.QPushButton("上一张")
        self.next_button = QtWidgets.QPushButton("下一张")
        nav_layout.addWidget(self.prev_button)
        nav_layout.addWidget(self.next_button)
        layout.addLayout(nav_layout)
        
        # ========== 播放控制 ==========
        play_control_layout = QtWidgets.QVBoxLayout()
        
        # 播放/暂停按钮
        play_button_layout = QtWidgets.QHBoxLayout()
        self.play_pause_button = QtWidgets.QPushButton("▶ 播放")
        self.play_pause_button.setMinimumHeight(35)
        self.play_pause_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3d8b40;
            }
        """)
        play_button_layout.addWidget(self.play_pause_button)
        play_control_layout.addLayout(play_button_layout)
        
        # 速度控制
        speed_layout = QtWidgets.QHBoxLayout()
        speed_label = QtWidgets.QLabel("播放速度:")
        self.speed_slider = QtWidgets.QSlider(Qt.Horizontal)
        self.speed_slider.setMinimum(1)   # 0.5倍速 (对应索引1)
        self.speed_slider.setMaximum(6)   # 16倍速 (对应索引6)
        self.speed_slider.setValue(2)     # 默认1.0倍速 (对应索引2)
        self.speed_slider.setTickPosition(QtWidgets.QSlider.TicksBelow)
        self.speed_slider.setTickInterval(1)
        
        self.speed_value_label = QtWidgets.QLabel("1.0x")
        self.speed_value_label.setMinimumWidth(50)
        self.speed_value_label.setAlignment(Qt.AlignCenter)
        self.speed_value_label.setStyleSheet("font-weight: bold;")
        
        speed_layout.addWidget(speed_label)
        speed_layout.addWidget(self.speed_slider)
        speed_layout.addWidget(self.speed_value_label)
        play_control_layout.addLayout(speed_layout)
        
        layout.addLayout(play_control_layout)
        # ========== 播放控制结束 ==========
        
        group.setLayout(layout)
        return group
    
    def _create_image_group(self) -> QtWidgets.QGroupBox:
        """创建图像显示组"""
        group = QtWidgets.QGroupBox("图像预览")
        layout = QtWidgets.QVBoxLayout()
        
        # 图像显示标签
        self.lb_img_viewer = QtWidgets.QLabel()
        self.lb_img_viewer.setAlignment(Qt.AlignCenter)
        self.lb_img_viewer.setMinimumSize(600, 400)
        self.lb_img_viewer.setStyleSheet("border: 1px solid gray;")
        self.lb_img_viewer.setScaledContents(False)
        
        layout.addWidget(self.lb_img_viewer)
        
        # 添加另存为按钮
        button_layout = QtWidgets.QHBoxLayout()
        self.save_image_btn = QtWidgets.QPushButton("另存为当前图片")
        self.save_image_btn.setMinimumHeight(35)
        self.save_image_btn.setEnabled(False)  # 初始禁用，有图片显示时启用
        self.save_image_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
            QPushButton:pressed {
                background-color: #0D47A1;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
        """)
        button_layout.addStretch()
        button_layout.addWidget(self.save_image_btn)
        button_layout.addStretch()
        layout.addLayout(button_layout)
        
        group.setLayout(layout)
        return group
    
    def _create_button_layout(self) -> QtWidgets.QHBoxLayout:
        """创建按钮布局"""
        layout = QtWidgets.QHBoxLayout()
        
        # 移除"开始分析"按钮，改为自动分析
        self.btn_quit = QtWidgets.QPushButton("关闭")
        self.btn_quit.setMinimumHeight(40)
        self.btn_quit.setEnabled(False)  # 初始禁用，分析完成后启用
        
        layout.addStretch()  # 添加弹簧使按钮居中
        layout.addWidget(self.btn_quit)
        layout.addStretch()
        
        return layout
    
    def _connect_signals(self):
        """连接信号和槽"""
        self.list_widget.itemSelectionChanged.connect(self.on_item_selection_changed)
        self.prev_button.clicked.connect(self.on_prev_button_clicked)
        self.next_button.clicked.connect(self.on_next_button_clicked)
        # 移除"开始分析"按钮信号连接（已改为自动分析）
        self.btn_quit.clicked.connect(self.on_quit_clicked)
        
        # 播放控制信号
        self.play_pause_button.clicked.connect(self.on_play_pause_clicked)
        self.speed_slider.valueChanged.connect(self.on_speed_changed)
        
        # 另存为按钮信号
        self.save_image_btn.clicked.connect(self.on_save_image_clicked)
    
    def _auto_start_analysis(self):
        """自动启动分析（在窗口显示后调用）"""
        if not self.input_folder or not os.path.exists(self.input_folder):
            QMessageBox.warning(self, "警告", "输入文件夹不存在!")
            self.close()
            return
        
        # 检查是否有图像文件
        image_files = self.processor.get_image_files(self.input_folder)
        if not image_files:
            QMessageBox.warning(self, '警告', '文件夹中没有图片!')
            self.close()
            return
        
        # 开始分析
        self.start_time = time()
        success = self._run_analysis(image_files)
        
        if success:
            # 计算耗时
            elapsed_time = time() - self.start_time
            print(f'图像分析完成,耗时: {elapsed_time:.2f}秒')
            
            # 更新UI
            self._update_ui_with_results()
            
            # 标记分析完成
            self.analysis_completed = True
            
            # 启用关闭按钮
            self.btn_quit.setEnabled(True)
            
            # 显示完成消息（在分析完成后立即显示，而不是在关闭时）
            QMessageBox.information(self, "完成", f"分析完成!\n耗时: {elapsed_time:.2f}秒\n数据已保存")
        else:
            # 分析失败，允许关闭
            self.btn_quit.setEnabled(True)
    
    def _run_analysis(self, image_files: List[str]) -> bool:
        """
        运行图像分析
        
        Args:
            image_files: 图像文件列表
            
        Returns:
            是否成功
        """
        total_images = len(image_files)
        
        # 创建进度对话框
        progress_dialog = QProgressDialog("图片分析中...", "取消", 0, 100, self)
        progress_dialog.setWindowTitle("分析进度")
        progress_dialog.setWindowModality(Qt.WindowModal)
        progress_dialog.setMinimumDuration(0)
        
        try:
            # 生成输出文件夹
            self.output_folder = self._generate_temp_folder()
            self.lb_img_path.setText(f'图片保存路径: {self.output_folder}')
            
            # 批量处理
            self.analysis_results = []
            update_interval = max(1, self.config.progress_update_interval)
            
            for i, filename in enumerate(image_files):
                if progress_dialog.wasCanceled():
                    QMessageBox.information(self, "提示", "分析已取消")
                    return False
                
                input_path = os.path.join(self.input_folder, filename)
                output_path = os.path.join(self.output_folder, filename)
                
                # 处理单张图像
                result = self.processor.process_and_save_image(input_path, output_path)
                self.analysis_results.append(result)
                
                # 更新进度(减少频率)
                if i % update_interval == 0 or i == total_images - 1:
                    progress = int((i + 1) / total_images * 100)
                    progress_dialog.setValue(progress)
                    QApplication.processEvents()
            
            progress_dialog.setValue(100)
            
            # 计算统计数据
            self.statistics = self.processor.calculate_statistics(self.analysis_results)
            
            if self.statistics is None:
                QMessageBox.warning(self, "警告", "没有成功分析的图像!")
                return False
            
            # 报告失败的图像
            if self.statistics.failed_images > 0:
                failed_files = [r.filename for r in self.analysis_results if not r.success]
                max_display = self.config.max_display_failed_files
                failed_msg = "\n".join(failed_files[:max_display])
                if len(failed_files) > max_display:
                    failed_msg += f"\n... 还有 {len(failed_files) - max_display} 个"
                
                QMessageBox.warning(
                    self, 
                    "部分失败", 
                    f"有 {self.statistics.failed_images} 个文件处理失败:\n{failed_msg}"
                )
            
            return True
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"分析过程出错: {str(e)}")
            return False
        finally:
            progress_dialog.close()
    
    def _update_ui_with_results(self):
        """使用分析结果更新UI"""
        if not self.statistics:
            return
        
        # 更新统计标签
        self.max_label.setText(f"最大值: {self.statistics.max_flame_size} mm")
        self.min_label.setText(f"最小值: {self.statistics.min_flame_size} mm")
        self.avg_label.setText(f"平均值: {self.statistics.average_flame_size} mm")
        
        # 填充列表
        self.list_widget.clear()
        for result in self.analysis_results:
            if result.success:
                self.list_widget.addItem(f"{result.filename}: {result.flame_size_mm} mm")
            else:
                self.list_widget.addItem(f"{result.filename}: 分析失败")
        
        # 定位到最大值
        maximum_row = next((index for index, result in enumerate(self.analysis_results)
                            if result.success and result.filename == self.statistics.max_flame_file), -1)
        self.list_widget.setCurrentRow(maximum_row)
        
        # 保存结果到字典
        max_flame_path = os.path.join(self.output_folder, self.statistics.max_flame_file)
        self.exp_results = {
            'max_flame_size': self.statistics.max_flame_size,
            'min_flame_size': self.statistics.min_flame_size,
            'average_flame_size': self.statistics.average_flame_size,
            'max_flame_image_path': max_flame_path,
            'total_images': self.statistics.total_images,
            'failed_images': self.statistics.failed_images
        }
        
        # 保存历史数据(如果配置文件存在)
        if self.config.exp_data_json_path.exists():
            self._save_explosion_data(self.statistics.max_flame_size)
        
        # 复制最大火焰图片到指定文件夹
        self._copy_max_flame_image(max_flame_path)
    
    def _save_explosion_data(self, flame_size: int):
        """
        保存爆炸性数据到CSV

        Args:
            flame_size: 火焰尺寸
        """
        try:
            json_path = self.config.exp_data_json_path
            with open(json_path, 'r', encoding='utf-8') as json_file:
                json_data = json.load(json_file)

            dict_data = {
                '检测日期': json_data.get('exp_date_time', ''),
                '检测机构': json_data.get('exp_org', ''),
                '委托单位': json_data.get('exp_requester', ''),
                '实验人员': json_data.get('exp_staff', ''),
                '实验编号': json_data.get('exp_id', ''),
                '样品编号': json_data.get('exp_counter', ''),
                '样品名称': json_data.get('sample_name', ''),
                '爆炸性/mm': flame_size,
                '备注信息': '',
            }

            self._save_to_csv(dict_data)

        except (OSError, json.JSONDecodeError) as e:
            print(f"保存爆炸性数据失败: {e}")
        except Exception as e:
            print(f"保存爆炸性数据失败: {e}")
    
    def _save_to_csv(self, dict_data: Dict):
        """保存数据到CSV文件"""
        csv_path = self.config.history_csv_path
        
        try:
            # 确保目录存在
            csv_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 写入CSV
            with open(csv_path, 'a', newline='', encoding='utf-8') as file:
                writer = csv.DictWriter(file, fieldnames=dict_data.keys())
                if file.tell() == 0:
                    writer.writeheader()
                writer.writerow(dict_data)
            
            print(f"数据已保存到: {csv_path}")
            
        except PermissionError:
            QMessageBox.critical(
                self, '错误', 
                '文件无法保存,可能正在被其他程序使用。\n请确保文件没有被打开后再试。'
            )
        except Exception as e:
            QMessageBox.critical(self, '错误', f'保存数据出错: {str(e)}')
    
    def _generate_temp_folder(self) -> str:
        """生成临时文件夹（用于保存分析后的标注图像）"""
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 使用配置的火焰结果文件夹作为基础路径
        base_folder = self.config.flame_output_folder
        temp_folder = base_folder / f"analysis_{timestamp}"
        temp_folder.mkdir(parents=True, exist_ok=True)
        
        return str(temp_folder)
    
    def on_item_selection_changed(self):
        """列表选择改变事件"""
        current_item = self.list_widget.currentItem()
        if not current_item or not self.output_folder:
            self.save_image_btn.setEnabled(False)
            return
        
        try:
            # 提取文件名
            text = current_item.text()
            filename = text.split(":")[0].strip()
            
            # 加载并显示图像
            image_path = os.path.join(self.output_folder, filename)
            if os.path.exists(image_path):
                pixmap = QPixmap(image_path)
                self.lb_img_viewer.setPixmap(
                    pixmap.scaled(
                        self.lb_img_viewer.width(), 
                        self.lb_img_viewer.height(), 
                        Qt.KeepAspectRatio
                    )
                )
                # 启用另存为按钮
                self.save_image_btn.setEnabled(True)
            else:
                self.save_image_btn.setEnabled(False)
        except Exception as e:
            print(f"显示图像失败: {e}")
            self.save_image_btn.setEnabled(False)
    
    def on_prev_button_clicked(self):
        """上一张按钮"""
        current_row = self.list_widget.currentRow()
        if current_row > 0:
            self.list_widget.setCurrentRow(current_row - 1)
    
    def on_next_button_clicked(self):
        """下一张按钮"""
        current_row = self.list_widget.currentRow()
        if current_row < self.list_widget.count() - 1:
            self.list_widget.setCurrentRow(current_row + 1)
    
    def on_quit_clicked(self):
        """退出按钮"""
        # 自动分析模式下，只要按钮启用就可以关闭
        self.close()
    
    def reject(self):
        """Route Escape and dialog rejection through result delivery and cleanup."""
        self.close()

    def closeEvent(self, event):
        """窗口关闭事件"""
        # 停止播放
        if self.is_playing:
            self._stop_playing()
        
        if not self.analysis_completed:
            # 未完成分析（可能分析失败或用户提前关闭），发出警告
            reply = QMessageBox.warning(
                self, 
                '警告', 
                '分析尚未完成,确定要关闭吗?\n关闭后数据将不会保存。',
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if reply == QMessageBox.No:
                event.ignore()
                return
            else:
                # 未分析完成就关闭，发送空结果
                self.window_closed.emit({})
                event.accept()
                return
        
        # 发送结果信号（在关闭前发送，避免重复弹出）
        self.window_closed.emit(self.exp_results)
        
        # 清理临时文件夹
        # self._cleanup_temp_folders()
        
        # 移除消息框，避免在关闭过程中弹出导致窗口重复打开
        # 数据保存提示已在分析完成时显示
        event.accept()
    
    def _cleanup_temp_folders(self):
        """安全清理临时文件夹"""
        for folder in [self.input_folder, self.output_folder]:
            if folder and os.path.exists(folder):
                try:
                    # 确保是临时目录,防止误删
                    if '/tmp/' in folder or 'temp' in folder.lower():
                        shutil.rmtree(folder)
                        print(f"已删除临时文件夹: {folder}")
                except Exception as e:
                    print(f"删除文件夹失败 {folder}: {e}")
    
    def on_play_pause_clicked(self):
        """播放/暂停按钮点击事件"""
        from PySide6.QtCore import QTimer
        
        if self.list_widget.count() == 0:
            QMessageBox.warning(self, "提示", "请先进行图片分析")
            return
        
        self.is_playing = not self.is_playing
        
        if self.is_playing:
            # 开始播放
            self.play_pause_button.setText("⏸ 暂停")
            self.play_pause_button.setStyleSheet("""
                QPushButton {
                    background-color: #ff9800;
                    color: white;
                    border-radius: 5px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #e68900;
                }
                QPushButton:pressed {
                    background-color: #cc7a00;
                }
            """)
            
            # 创建定时器
            if self.play_timer is None:
                self.play_timer = QTimer(self)
                self.play_timer.timeout.connect(self._play_next_frame)
            
            # 根据速度设置间隔 (基准间隔1000ms)
            interval = int(1000 / self.play_speed)
            self.play_timer.start(interval)
            
        else:
            # 暂停播放
            self.play_pause_button.setText("▶ 播放")
            self.play_pause_button.setStyleSheet("""
                QPushButton {
                    background-color: #4CAF50;
                    color: white;
                    border-radius: 5px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #45a049;
                }
                QPushButton:pressed {
                    background-color: #3d8b40;
                }
            """)
            
            if self.play_timer:
                self.play_timer.stop()
    
    def on_speed_changed(self, value):
        """速度滑块变化事件"""
        # 速度映射: 1->0.5x, 2->1x, 3->2x, 4->4x, 5->8x, 6->16x
        speed_map = {
            1: 0.5,
            2: 1.0,
            3: 2.0,
            4: 4.0,
            5: 8.0,
            6: 16.0
        }
        
        self.play_speed = speed_map.get(value, 1.0)
        self.speed_value_label.setText(f"{self.play_speed:.1f}x")
        
        # 如果正在播放，更新定时器间隔
        if self.is_playing and self.play_timer:
            interval = int(1000 / self.play_speed)
            self.play_timer.setInterval(interval)
    
    def _play_next_frame(self):
        """播放下一帧"""
        current_row = self.list_widget.currentRow()
        total_count = self.list_widget.count()
        
        if total_count == 0:
            self._stop_playing()
            return
        
        # 移动到下一张，循环播放
        next_row = (current_row + 1) % total_count
        self.list_widget.setCurrentRow(next_row)
    
    def _stop_playing(self):
        """停止播放"""
        self.is_playing = False
        self.play_pause_button.setText("▶ 播放")
        self.play_pause_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3d8b40;
            }
        """)
        
        if self.play_timer:
            self.play_timer.stop()
    
    def _copy_max_flame_image(self, source_path: str):
        """
        复制最大火焰图片到指定文件夹
        
        Args:
            source_path: 源图片路径
        """
        try:
            from datetime import datetime
            
            # 获取目标文件夹
            target_folder = self.config.max_flame_save_folder
            
            # 确保目标文件夹存在
            target_folder.mkdir(parents=True, exist_ok=True)
            
            # 生成目标文件名 (带时间戳)
            source_file = Path(source_path)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            new_filename = f"{source_file.stem}_{timestamp}_max{source_file.suffix}"
            target_path = target_folder / new_filename
            
            # 复制文件
            shutil.copy2(source_path, target_path)
            
            # 记录日志
            print(f"✅ 最大火焰图片已复制:")
            print(f"   源文件: {source_path}")
            print(f"   目标文件: {target_path}")
            print(f"   火焰尺寸: {self.statistics.max_flame_size} mm")
            
            # 更新结果字典
            self.exp_results['max_flame_saved_path'] = str(target_path)
            self.exp_results['max_flame_saved_time'] = timestamp
            
            return target_path
            
        except PermissionError:
            error_msg = f"无权限写入目标文件夹: {target_folder}"
            print(f"❌ {error_msg}")
            QMessageBox.critical(self, "权限错误", error_msg)
            return None
            
        except Exception as e:
            error_msg = f"复制最大火焰图片失败: {str(e)}"
            print(f"❌ {error_msg}")
            # 不弹出警告框,避免打断用户操作
            print(f"   如需保存最大火焰图片,请检查配置文件中的路径设置")
            return None
    
    def on_save_image_clicked(self):
        """另存为按钮点击事件"""
        current_item = self.list_widget.currentItem()
        if not current_item or not self.output_folder:
            QMessageBox.warning(self, "警告", "请先选择要保存的图片！")
            return
        
        try:
            # 提取文件名和火焰尺寸
            text = current_item.text()
            parts = text.split(":")
            if len(parts) < 2:
                QMessageBox.warning(self, "警告", "无法解析图片信息！")
                return
            
            filename = parts[0].strip()
            flame_info = parts[1].strip()  # 例如 "285.5 mm" 或 "分析失败"
            
            # 获取源图片路径
            source_path = os.path.join(self.output_folder, filename)
            if not os.path.exists(source_path):
                QMessageBox.warning(self, "警告", "图片文件不存在！")
                return
            
            # 获取桌面路径
            desktop_path = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DesktopLocation)
            
            # 生成默认文件名
            default_filename = self._generate_save_filename(filename, flame_info)
            
            # 获取原始图片扩展名
            _, ext = os.path.splitext(source_path)
            if not ext:
                ext = '.jpg'
            
            # 完整的默认保存路径
            default_save_path = os.path.join(desktop_path, default_filename + ext)
            
            # 弹出保存对话框
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "另存为",
                default_save_path,
                f"图片文件 (*{ext});;所有文件 (*.*)"
            )
            
            # 如果用户取消了保存
            if not file_path:
                return
            
            # 复制文件
            shutil.copy(source_path, file_path)
            QMessageBox.information(self, "成功", f"图片已保存至:\n{file_path}")
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"保存图片失败:\n{str(e)}")
    
    def _generate_save_filename(self, original_filename: str, flame_info: str) -> str:
        """
        生成保存文件名
        
        Args:
            original_filename: 原始文件名
            flame_info: 火焰信息字符串，例如 "285.5 mm"
            
        Returns:
            生成的文件名（不含扩展名）
        """
        # 清理原始文件名（去除扩展名）
        base_name = os.path.splitext(original_filename)[0]
        base_name = self._sanitize_filename(base_name)
        
        # 提取火焰尺寸
        parts = []
        parts.append(f"flame_analysis_{base_name}")
        
        # 如果有火焰尺寸信息，添加到文件名
        if "mm" in flame_info and "失败" not in flame_info:
            try:
                flame_size = flame_info.replace("mm", "").strip()
                parts.append(f"{flame_size}mm")
            except:
                pass
        
        return "_".join(parts)
    
    def _sanitize_filename(self, filename: str) -> str:
        """清理文件名中的非法字符"""
        # Windows文件名非法字符: < > : " / \ | ? *
        illegal_chars = '<>:"/\\|?*'
        for char in illegal_chars:
            filename = filename.replace(char, '_')
        return filename.strip()


if __name__ == "__main__":
    import sys
    
    app = QApplication(sys.argv)
    
    # 创建测试输入文件夹
    # test_folder = "/tmp/test_flame_images"
    # os.makedirs(test_folder, exist_ok=True)

    test_folder = "images_test"
    
    window = FlameAnalyzerWidget(test_folder)
    window.show()
    
    sys.exit(app.exec())
