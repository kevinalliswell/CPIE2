"""
触摸屏副屏显示窗口
专为1024×600分辨率触摸屏设计的实时监控界面
"""

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QSplitter, QFrame
)
from pathlib import Path

from PySide6.QtCore import Qt, Signal, QTimer
from datetime import datetime

from utils.path_manager import PathManager
from views.ui_components.monitor_panels import (
    ExplosionMonitorPanel,
    IgnitionMonitorPanel
)
# from views.resources.styles import StyleManager


class SecondaryDisplayWindow(QMainWindow):
    """
    触摸屏副屏显示窗口

    特点：
    - 固定1024×600分辨率
    - 触摸友好的大按钮
    - 实时监控数据显示
    - 支持两种监控模式切换
    """

    # 信号
    window_closed = Signal()  # 窗口关闭信号

    @staticmethod
    def _resolve_style_path() -> Path:
        """解析副屏样式文件路径。"""
        return Path(PathManager.get_styles_path("secondary_display_light.qss"))

    def __init__(self, explosion_controller=None, ignition_controller=None, parent=None):
        super().__init__(parent)

        self.secondary_style_path = self._resolve_style_path()

        # 保存控制器引用
        self.explosion_controller = explosion_controller
        self.ignition_controller = ignition_controller

        # 缩放比例（根据屏幕分辨率自动计算）
        self.scale_factor = 1.0

        # 窗口配置
        self.setWindowTitle("CPIE 触摸屏监控")
        # 不固定分辨率，让窗口适应显示器
        self.setMinimumSize(800, 480)  # 设置最小尺寸，防止过小

        # 无边框全屏窗口
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)

        # 初始化UI
        self._init_ui()

        # 应用样式
        self._apply_styles()

        # 设置定时器更新时间
        self.clock_timer = QTimer(self)
        self.clock_timer.timeout.connect(self._update_time)
        self.clock_timer.start(1000)

        # 尝试将窗口移动到第二显示器
        self._move_to_secondary_screen()

        # 启动控制器的数据监控（用于实时数据推送）
        self._start_controllers_monitoring()

    def _init_ui(self):
        """初始化UI"""
        # 中心widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 主布局
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # 创建顶部标题栏
        title_bar = self._create_title_bar()
        main_layout.addWidget(title_bar)
        
        # 创建合并的内容区域（左右分栏）
        content_widget = self._create_merged_content()
        main_layout.addWidget(content_widget)
    
    def _create_title_bar(self) -> QWidget:
        """创建顶部标题栏"""
        title_bar = QWidget()
        title_bar.setObjectName("secondaryNavBar")
        title_bar.setFixedHeight(60)
        
        layout = QHBoxLayout(title_bar)
        layout.setContentsMargins(15, 0, 15, 0)
        layout.setSpacing(10)
        
        # Logo和标题
        logo_label = QLabel("🔥 CPIE 实时监控")
        logo_label.setObjectName("secondaryLogoLabel")
        layout.addWidget(logo_label)
        
        layout.addStretch()
        
        # 时间标签
        self.time_label = QLabel()
        self.time_label.setObjectName("secondaryTimeLabel")
        layout.addWidget(self.time_label)
        self._update_time()
        
        return title_bar
    
    def _create_merged_content(self) -> QWidget:
        """创建合并的内容区域（左右分栏显示两个面板）"""
        # 使用QSplitter实现左右分栏
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setObjectName("secondaryContentSplitter")
        splitter.setChildrenCollapsible(False)  # 防止面板被完全折叠
        
        # 左侧：爆炸性实验监控
        try:
            explosion_widget = QWidget()
            explosion_layout = QVBoxLayout(explosion_widget)
            explosion_layout.setContentsMargins(10, 10, 10, 10)
            explosion_layout.setSpacing(10)
            
            # 添加标题
            explosion_title = QLabel("💥 爆炸性实验监控")
            explosion_title.setObjectName("section_title")
            explosion_title.setStyleSheet("font-weight: bold; color: #2c3e50; font-size: 24px; padding: 10px;")
            explosion_layout.addWidget(explosion_title)
            
            # 添加分隔线
            separator1 = QFrame()
            separator1.setFrameShape(QFrame.Shape.HLine)
            separator1.setFrameShadow(QFrame.Shadow.Sunken)
            separator1.setStyleSheet("color: #bdc3c7;")
            explosion_layout.addWidget(separator1)
            
            self.explosion_panel = ExplosionMonitorPanel()
            if self.explosion_controller:
                self.explosion_panel.connect_controller_signals(self.explosion_controller)
            explosion_layout.addWidget(self.explosion_panel)
            explosion_layout.addStretch()
            
            splitter.addWidget(explosion_widget)
        except Exception as e:
            print(f"加载爆炸性实验监控面板失败: {e}")
            error_widget = self._create_error_panel("爆炸性实验监控", str(e))
            splitter.addWidget(error_widget)
        
        # 右侧：着火点实验监控
        try:
            ignition_widget = QWidget()
            ignition_layout = QVBoxLayout(ignition_widget)
            ignition_layout.setContentsMargins(10, 10, 10, 10)
            ignition_layout.setSpacing(10)
            
            # 添加标题
            ignition_title = QLabel("🔥 着火点实验监控")
            ignition_title.setObjectName("section_title")
            ignition_title.setStyleSheet("font-weight: bold; color: #2c3e50; font-size: 24px; padding: 10px;")
            ignition_layout.addWidget(ignition_title)
            
            # 添加分隔线
            separator2 = QFrame()
            separator2.setFrameShape(QFrame.Shape.HLine)
            separator2.setFrameShadow(QFrame.Shadow.Sunken)
            separator2.setStyleSheet("color: #bdc3c7;")
            ignition_layout.addWidget(separator2)
            
            self.ignition_panel = IgnitionMonitorPanel()
            if self.ignition_controller:
                self.ignition_panel.connect_controller_signals(self.ignition_controller)
            ignition_layout.addWidget(self.ignition_panel)
            ignition_layout.addStretch()
            
            splitter.addWidget(ignition_widget)
        except Exception as e:
            print(f"加载着火点实验监控面板失败: {e}")
            error_widget = self._create_error_panel("着火点实验监控", str(e))
            splitter.addWidget(error_widget)
        
        # 设置左右面板的初始比例（50:50）
        splitter.setSizes([500, 500])
        
        return splitter
    
    def _create_error_panel(self, panel_name: str, error_msg: str) -> QWidget:
        """创建错误面板"""
        error_widget = QWidget()
        layout = QVBoxLayout(error_widget)
        
        error_label = QLabel(f"❌ {panel_name}加载失败")
        error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        error_label.setStyleSheet("font-size: 24px; color: #dc3545;")
        
        detail_label = QLabel(f"错误信息: {error_msg}")
        detail_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        detail_label.setWordWrap(True)
        detail_label.setStyleSheet("font-size: 14px; color: #666;")
        
        layout.addStretch()
        layout.addWidget(error_label)
        layout.addWidget(detail_label)
        layout.addStretch()
        
        return error_widget
    
    def _apply_styles(self):
        """应用副屏专用亮色样式"""
        try:
            if self.secondary_style_path.exists():
                with open(self.secondary_style_path, 'r', encoding='utf-8') as f:
                    style = f.read()
                    self.setStyleSheet(style)
                    print("✅ 副屏亮色样式已应用")
            else:
                print(f"⚠ 样式文件未找到: {self.secondary_style_path}")
                # 应用基础样式作为后备
                self._apply_fallback_style()
        except Exception as e:
            print(f"⚠ 应用副屏样式失败: {e}")
            # 应用基础样式作为后备
            self._apply_fallback_style()
    
    def _apply_fallback_style(self):
        """应用后备样式（如果主样式文件加载失败）"""
        fallback_style = """
        QWidget {
            font-family: 'Microsoft YaHei', 'SimHei', sans-serif;
            font-size: 16px;
            color: #2c3e50;
            background-color: #f5f7fa;
        }
        
        #secondaryNavBar {
            background: #ffffff;
            border-bottom: 3px solid #3498db;
        }
        
        #secondaryContentSplitter {
            background-color: #f5f7fa;
        }
        
        #secondaryContentSplitter::handle {
            background-color: #bdc3c7;
            width: 3px;
        }
        
        #secondaryContentSplitter::handle:hover {
            background-color: #3498db;
        }
        
        #largeMetricCard {
            background-color: #ffffff;
            border: 3px solid #e1e8ed;
            border-radius: 10px;
            padding: 15px;
        }
        """
        self.setStyleSheet(fallback_style)
        print("ℹ 已应用后备样式")
    
    def _apply_scaled_styles(self):
        """应用缩放后的样式"""
        if self.scale_factor == 1.0:
            return
        
        try:
            # 内容区域使用适中的缩放比例（1.1倍）
            content_scale = self.scale_factor * 1.1
            
            # 动态生成缩放样式
            scaled_style = f"""
                /* 导航栏缩放（保持原比例）*/
                #secondaryNavBar {{
                    min-height: {int(60 * self.scale_factor)}px;
                    max-height: {int(60 * self.scale_factor)}px;
                }}
                
                #secondaryLogoLabel {{
                    font-size: {int(20 * self.scale_factor)}px;
                }}
                
                #secondaryContentSplitter::handle {{
                    width: {int(3 * self.scale_factor)}px;
                }}
                
                #secondaryTimeLabel {{
                    font-size: {int(14 * self.scale_factor)}px;
                }}
                
                #secondaryControlButton {{
                    font-size: {int(18 * self.scale_factor)}px;
                    min-width: {int(60 * self.scale_factor)}px;
                    min-height: {int(45 * self.scale_factor)}px;
                }}
                
                #secondaryCloseButton {{
                    font-size: {int(18 * self.scale_factor)}px;
                    min-width: {int(80 * self.scale_factor)}px;
                    min-height: {int(45 * self.scale_factor)}px;
                }}
                
                /* 大尺寸卡片缩放（使用更大比例）*/
                #largeMetricCard {{
                    border-radius: {int(10 * content_scale)}px;
                    padding: {int(15 * content_scale)}px;
                }}
                
                QLabel#largeMetricIcon {{
                    font-size: {int(32 * content_scale)}px !important;
                }}
                
                QLabel#largeMetricTitle {{
                    font-size: {int(20 * content_scale)}px !important;
                }}
                
                QLabel#largeMetricValue {{
                    font-size: {int(64 * content_scale)}px !important;
                }}
                
                QLabel#largeMetricUnit {{
                    font-size: {int(32 * content_scale)}px !important;
                }}
                
                QLabel#largeMetricHint {{
                    font-size: {int(14 * content_scale)}px !important;
                }}
                
                /* 日志和其他组件缩放 */
                #compactLogWidget {{
                    border-radius: {int(10 * content_scale)}px;
                    padding: {int(10 * content_scale)}px;
                }}
                
                #compactLogTitle, #miniFlameTitle, #miniChartTitle {{
                    font-size: {int(18 * content_scale)}px !important;
                    padding-bottom: {int(5 * content_scale)}px;
                }}
                
                #compactLogItem {{
                    font-size: {int(14 * content_scale)}px !important;
                    padding: {int(5 * content_scale)}px;
                }}
                
                #miniFlameLength, #miniChartCurrentTemp {{
                    font-size: {int(14 * content_scale)}px !important;
                }}
                
                /* 火焰查看器和温度图表缩放 */
                #miniFlameViewer, #miniTempChart {{
                    border-radius: {int(10 * content_scale)}px;
                    padding: {int(10 * content_scale)}px;
                }}
                
                #miniFlameImage {{
                    min-width: {int(380 * content_scale)}px;
                    min-height: {int(220 * content_scale)}px;
                    border-radius: {int(4 * content_scale)}px;
                    border-width: {int(2 * content_scale)}px;
                }}
                
                /* PlotWidget 需要用 QWidget 选择器 */
                #miniTempChart QWidget {{
                    min-width: {int(380 * content_scale)}px;
                    min-height: {int(220 * content_scale)}px;
                }}
                
                /* 紧急停止按钮缩放 */
                #emergencyStopButton {{
                    font-size: {int(22 * content_scale)}px;
                    min-width: {int(180 * content_scale)}px;
                    min-height: {int(70 * content_scale)}px;
                    border-radius: {int(10 * content_scale)}px;
                }}
                
                /* 样品温度项缩放（更大字体）*/
                #sampleTempItem {{
                    border-radius: {int(8 * content_scale)}px;
                    padding: {int(8 * content_scale)}px;
                }}
                
                #sampleTempItem QLabel {{
                    font-size: {int(16 * content_scale)}px;
                }}
                
                /* 样品温度数值特别大 - 使用属性选择器 */
                QLabel[class="temp_value"] {{
                    font-size: {int(40 * content_scale)}px !important;
                }}
                
                /* 进度条缩放 */
                QProgressBar {{
                    height: {int(40 * content_scale)}px;
                    font-size: {int(18 * content_scale)}px;
                    border-radius: {int(6 * content_scale)}px;
                    border-width: {int(2 * content_scale)}px;
                }}
                
                QProgressBar::chunk {{
                    border-radius: {int(4 * content_scale)}px;
                }}
                
                /* 实验状态卡片 */
                #explosionStatusWidget, #ignitionStatusWidget {{
                    border-radius: {int(10 * content_scale)}px;
                    padding: {int(12 * content_scale)}px;
                    border-width: {int(2 * content_scale)}px;
                }}
                
                #explosionStatusWidget QLabel, #ignitionStatusWidget QLabel {{
                    font-size: {int(18 * content_scale)}px;
                }}
                
                /* 状态标签特别大 */
                QLabel#status_label {{
                    font-size: {int(28 * content_scale)}px !important;
                }}
                
                QLabel#cycle_label {{
                    font-size: {int(18 * content_scale)}px !important;
                }}
                
                QLabel#sample_label {{
                    font-size: {int(16 * content_scale)}px !important;
                }}
                
                /* 章节标题 */
                QLabel#section_title {{
                    font-size: {int(24 * content_scale)}px !important;
                }}
                
                QLabel#section_subtitle {{
                    font-size: {int(20 * content_scale)}px !important;
                }}
                
                /* 设备状态卡片缩放 */
                #deviceStatusCard {{
                    border-radius: {int(10 * content_scale)}px;
                    padding: {int(12 * content_scale)}px;
                    border-width: {int(2 * content_scale)}px;
                }}
                
                #deviceStatusCard QLabel {{
                    font-size: {int(16 * content_scale)}px;
                }}
                
                /* 设备名称 */
                QLabel#device_name_label {{
                    font-size: {int(20 * content_scale)}px !important;
                }}
                
                /* 设备数值 */
                QLabel#device_value_label {{
                    font-size: {int(32 * content_scale)}px !important;
                }}
                
                /* 设备状态指示器 */
                QLabel#device_status_indicator {{
                    font-size: {int(22 * content_scale)}px !important;
                }}
                
                /* 设备统计框 */
                #deviceStatsFrame {{
                    border-radius: {int(10 * content_scale)}px;
                    padding: {int(15 * content_scale)}px;
                    border-width: {int(2 * content_scale)}px;
                }}
                
                #deviceStatsFrame QLabel {{
                    font-size: {int(15 * content_scale)}px;
                }}
                
                /* 炉温卡片特殊处理 */
                QWidget[objectName="furnace_temp_card"] #largeMetricValue {{
                    font-size: {int(72 * content_scale)}px;
                }}
                
                /* 滚动条缩放 */
                QScrollBar:vertical {{
                    width: {int(12 * content_scale)}px;
                    border-radius: {int(6 * content_scale)}px;
                }}
                
                QScrollBar::handle:vertical {{
                    border-radius: {int(6 * content_scale)}px;
                    min-height: {int(30 * content_scale)}px;
                }}
                
                QScrollBar:horizontal {{
                    height: {int(12 * content_scale)}px;
                    border-radius: {int(6 * content_scale)}px;
                }}
                
                QScrollBar::handle:horizontal {{
                    border-radius: {int(6 * content_scale)}px;
                    min-width: {int(30 * content_scale)}px;
                }}
            """
            
            # 追加缩放样式
            current_style = self.styleSheet()
            self.setStyleSheet(current_style + scaled_style)
            
            print(f"✅ 已应用缩放样式 - 导航栏: {self.scale_factor:.2f}x, 内容: {content_scale:.2f}x")
        
        except Exception as e:
            print(f"⚠ 应用缩放样式失败: {e}")
    
    def _move_to_secondary_screen(self):
        """尝试将窗口移动到第二显示器并全屏显示"""
        try:
            from PySide6.QtWidgets import QApplication
            screens = QApplication.screens()
            
            target_screen = None
            
            if len(screens) > 1:
                # 使用第二个显示器
                target_screen = screens[1]
            else:
                # 使用主显示器
                target_screen = screens[0]
                print("ℹ 未检测到第二显示器，将在主显示器全屏显示")
            
            if target_screen:
                geometry = target_screen.geometry()
                screen_width = geometry.width()
                screen_height = geometry.height()
                
                # 计算缩放比例（基于1024×600的设计分辨率）
                base_width = 1024
                base_height = 600
                
                # 使用较小的缩放比例，以保证内容不会太挤
                width_scale = screen_width / base_width
                height_scale = screen_height / base_height
                self.scale_factor = min(width_scale, height_scale)
                
                # 限制缩放范围（0.7到2.5之间，避免字体过大）
                self.scale_factor = max(0.7, min(2.5, self.scale_factor))
                
                print("✅ 触摸屏窗口配置:")
                print(f"   屏幕分辨率: {screen_width}×{screen_height}")
                print(f"   设计分辨率: {base_width}×{base_height}")
                print(f"   自动缩放比例: {self.scale_factor:.2f}x")
                
                # 移动到目标显示器
                self.move(geometry.x(), geometry.y())
                self.setScreen(target_screen)
                
                # 应用缩放样式
                self._apply_scaled_styles()
                
                # 全屏显示
                self.showFullScreen()
                
                if len(screens) > 1:
                    print("   已在第二显示器全屏显示")
                else:
                    print("   已在主显示器全屏显示")
        except Exception as e:
            print(f"⚠ 配置显示器失败: {e}")
            import traceback
            traceback.print_exc()
    
    def _update_time(self):
        """更新时间显示"""
        current_time = datetime.now().strftime("%H:%M:%S")
        self.time_label.setText(f"⏰ {current_time}")
    
    
    def _toggle_fullscreen(self):
        """切换全屏显示"""
        if self.isFullScreen():
            self.showNormal()
            print("[触摸屏] 退出全屏模式")
        else:
            self.showFullScreen()
            print("[触摸屏] 进入全屏模式")
    
    def keyPressEvent(self, event):
        """键盘事件处理"""
        # F11 或 ESC 切换全屏
        if event.key() == Qt.Key.Key_F11:
            self._toggle_fullscreen()
            event.accept()
        elif event.key() == Qt.Key.Key_Escape and self.isFullScreen():
            self.showNormal()
            event.accept()
        else:
            super().keyPressEvent(event)
    
    def _start_controllers_monitoring(self):
        """启动控制器的数据监控"""
        try:
            if self.explosion_controller and hasattr(self.explosion_controller, 'start_data_monitoring'):
                self.explosion_controller.start_data_monitoring()
                print("[触摸屏] 爆炸性控制器数据监控已启动")
            
            if self.ignition_controller and hasattr(self.ignition_controller, 'start_data_monitoring'):
                self.ignition_controller.start_data_monitoring()
                print("[触摸屏] 着火点控制器数据监控已启动")
        except Exception as e:
            print(f"⚠ 启动数据监控失败: {e}")
    
    def _stop_controllers_monitoring(self):
        """停止控制器的数据监控"""
        try:
            if self.explosion_controller and hasattr(self.explosion_controller, 'stop_data_monitoring'):
                self.explosion_controller.stop_data_monitoring()
                print("[触摸屏] 爆炸性控制器数据监控已停止")
            
            if self.ignition_controller and hasattr(self.ignition_controller, 'stop_data_monitoring'):
                self.ignition_controller.stop_data_monitoring()
                print("[触摸屏] 着火点控制器数据监控已停止")
        except Exception as e:
            print(f"⚠ 停止数据监控失败: {e}")
    
    def closeEvent(self, event):
        """关闭事件"""
        print("[触摸屏] 窗口关闭")
        
        # 停止定时器
        self.clock_timer.stop()
        
        # 停止控制器数据监控
        self._stop_controllers_monitoring()
        
        # 断开控制器信号
        try:
            if hasattr(self, 'explosion_panel') and self.explosion_panel and self.explosion_controller:
                self.explosion_panel.disconnect_controller_signals(self.explosion_controller)
            if hasattr(self, 'ignition_panel') and self.ignition_panel and self.ignition_controller:
                self.ignition_panel.disconnect_controller_signals(self.ignition_controller)
        except Exception as e:
            print(f"⚠ 断开信号失败: {e}")
        
        # 发出关闭信号
        self.window_closed.emit()
        
        event.accept()


if __name__ == "__main__":
    """测试触摸屏窗口"""
    import sys
    from PySide6.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    
    window = SecondaryDisplayWindow()
    window.show()
    
    sys.exit(app.exec())

