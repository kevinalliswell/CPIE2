# src/ui/main_window.py
import os

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QFrame,
    QHBoxLayout, QStackedWidget, QMessageBox
)
from PySide6.QtCore import QTimer
from PySide6.QtGui import QAction, QIcon, QKeySequence

from src.utils.logger import LoggerManager
from src.utils.path_manager import PathManager
from src.utils.tools import Tools
from src.views.pages.about_page import AboutPage
from src.views.pages.config_page import ConfigPage
from src.views.pages.explosion_page import ExplosionExperimentPage
from src.views.pages.help_page import HelpPage
from src.views.pages.history_query_page import HistoryQueryPage
from src.views.pages.home_page import HomePage
from src.views.pages.ignition_page import IgnitionExperimentPage
from src.views.ui_components.sidebar import Sidebar
from src.views.ui_components.status_bar import StatusBar
from src.views.ui_components.title_bar import TitleBar

# from models.user_manager import UserManager  # 已禁用用户管理功能


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.logger = LoggerManager.get_logger(__name__)
        self.device_manager = None
        self.data_handler = None
        self.integrated_control_page = None

        # 触摸屏窗口引用
        self.secondary_display_window = None
        
        # 已禁用用户管理功能
        # # 用户管理
        # self.user_manager = UserManager()
        # self.current_user = self.user_manager.get_current_user()
        # if self.current_user:
        #     self.logger.info(f"当前登录用户: {self.current_user.username} ({self.current_user.role})")

        # 软件信息
        self.software_info = Tools.load_software_info()
        self.setWindowTitle(f"{self.software_info['description']} V{self.software_info['version']}")
        self.setMinimumSize(1200, 800)
        
        # 窗体状态管理
        self.is_window_maximized = False
        
        # 设置窗口图标
        self._set_window_icon()

        # 初始化后端
        self.init_backend()

        # 应用暗色主题
        Tools.apply_stylesheet("dark")

        
        self.logger.debug("主窗口初始化完成===")

        # 加载配置
        self.config_path = PathManager.get_config_path('experiment_config.yaml')
        self.config = Tools.load_config(config_path=self.config_path)
        self.ui_config = self.config['ui']

        # 检查数据和配置文件是否存在
        self._check_data_and_config_files()
        
        # 初始化 UI
        self._init_ui()

        # 设置全屏快捷键
        self._create_fullscreen_action()

        # TODO：后续添加自动打开触摸屏窗口功能
        QTimer.singleShot(1000, self._open_secondary_display)

    def _open_secondary_display(self):
        """打开触摸屏副屏窗口"""
        # 如果窗口已经存在且可见，则激活它
        if self.secondary_display_window is not None:
            if self.secondary_display_window.isVisible():
                self.secondary_display_window.activateWindow()
                self.secondary_display_window.raise_()
                print("[主窗口] 触摸屏窗口已激活")
                return
        
        try:
            # 导入触摸屏窗口类
            from .secondary_display_window import SecondaryDisplayWindow
            
            # 获取控制器引用（从页面中获取）
            explosion_controller = self._get_explosion_controller()
            ignition_controller = self._get_ignition_controller()
            
            if not explosion_controller or not ignition_controller:
                print("[主窗口] ⚠ 控制器未初始化，稍后重试...")
                QTimer.singleShot(2000, self._open_secondary_display)
                return
            
            # 创建触摸屏窗口
            self.secondary_display_window = SecondaryDisplayWindow(
                explosion_controller=explosion_controller,
                ignition_controller=ignition_controller,
                ui_config=self.ui_config,
                parent=None  # 独立窗口
            )
            
            # 连接窗口关闭信号
            self.secondary_display_window.window_closed.connect(
                self._on_secondary_display_closed
            )
            
            # 显示窗口
            self.secondary_display_window.show()
            
            print("[主窗口] 触摸屏窗口已打开")
        
        except Exception as e:
            print(f"[主窗口] 打开触摸屏窗口失败: {e}")
            import traceback
            traceback.print_exc()
    
    def _get_explosion_controller(self):
        """从爆炸性实验页面获取控制器"""
        try:
            # 页面索引：0=Home, 1=Explosion, 2=Ignition...
            explosion_page = self.stacked_widget.widget(1)
            if hasattr(explosion_page, 'controller'):
                return explosion_page.controller
        except Exception as e:
            print(f"[主窗口] 获取爆炸性控制器失败: {e}")
        return None
    
    def _get_ignition_controller(self):
        """从着火点实验页面获取控制器"""
        try:
            # 页面索引：0=Home, 1=Explosion, 2=Ignition...
            ignition_page = self.stacked_widget.widget(2)
            if hasattr(ignition_page, 'controller'):
                return ignition_page.controller
        except Exception as e:
            print(f"[主窗口] 获取着火点控制器失败: {e}")
        return None
    
    def _on_secondary_display_closed(self):
        """触摸屏窗口关闭处理"""
        print("[主窗口] 触摸屏窗口已关闭")
        self.secondary_display_window = None

    
    def _set_window_icon(self):
        """设置窗口图标"""
        try:
            icon_paths = [
                PathManager.get_resources_path(os.path.join("icons", "cpie_logo_icon.ico")),
                PathManager.get_resources_path(os.path.join("icons", "cpie_logo_icon.icns")),
            ]

            for icon_path in icon_paths:
                if os.path.exists(icon_path):
                    icon = QIcon(icon_path)
                    if not icon.isNull():
                        self.setWindowIcon(icon)
                        self.logger.info(f"窗口图标设置成功: {icon_path}")
                        return

            self.logger.warning("未找到可用的窗口图标文件")
        except Exception as e:
            self.logger.error(f"设置窗口图标失败: {e}")

    # ==============================
    # UI 初始化
    # ==============================
    def _init_ui(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)
        main_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.setSpacing(3)

        # 标题栏
        self.title_bar = TitleBar(self.software_info)
        title_frame = QFrame()
        title_layout = QVBoxLayout(title_frame)
        title_layout.setContentsMargins(0, 0, 0, 0)
        title_layout.addWidget(self.title_bar)
        main_layout.addWidget(title_frame)

        # 内容区（侧边栏 + 页面区）
        content_layout = QHBoxLayout()
        content_layout.setContentsMargins(8, 8, 8, 8)
        content_layout.setSpacing(10)

        # 左侧 Sidebar
        self.sidebar = Sidebar()
        self.sidebar.setObjectName("Sidebar")  # 设置对象名称以应用样式
        self.sidebar.page_selected.connect(self._on_sidebar_clicked)
        content_layout.addWidget(self.sidebar)

        # 页面区
        self.stacked_widget = QStackedWidget()
        content_layout.addWidget(self.stacked_widget, 1)

        content_widget = QWidget()
        content_widget.setLayout(content_layout)
        main_layout.addWidget(content_widget)

        # 底部状态栏
        self.status_bar = StatusBar(self)
        self.setStatusBar(self.status_bar)


        # 创建并添加所有页面
        self._create_pages()

    # ==============================
    # 检查数据和配置文件是否存在
    # ==============================
    def _check_data_and_config_files(self):
        """检查数据和配置文件（已简化，由各模块自己管理）"""
        # 配置文件由 __init__ 中的 _load_config 处理
        # 数据库文件由各自的Database类在初始化时创建
        pass

    # ==============================
    # 后端初始化
    # ==============================
    def init_backend(self):
        """初始化后端（Controllers）"""
        PathManager.initialize_directories()
        self.logger.info("项目目录结构初始化完成")


    # ==============================
    # 页面管理
    # ==============================
    def _create_pages(self):

        # 着火点实验标签页
        ignition_config = self.config['ignition_experiment']
        
        # 爆炸性实验标签页
        explosion_config = self.config['explosion_experiment']

        pages = [
            HomePage(),
            ExplosionExperimentPage(config=explosion_config, ui_config=self.ui_config),
            IgnitionExperimentPage(config=ignition_config, ui_config=self.ui_config),
            HistoryQueryPage(),
            ConfigPage(config=self.config, ui_config=self.ui_config, config_path=self.config_path),
            HelpPage(),
            AboutPage(),
        ]

        for page in pages:
            self.stacked_widget.addWidget(page)

    

    # ==============================
    # 通信状态
    # ==============================
    def _check_communication_status(self):
        """定时检查设备连接状态"""
        pass
        # try:
        #     # 使用 get_connection_status() 验证实际设备连接状态
        #     # 该方法会检查：线程状态 + 串口可用性 + 数据有效性
        #     is_connected, device_names, error_msg = self.device_manager.get_connection_status()
            
        #     if is_connected:
        #         # 有设备正常连接
        #         self.title_bar.update_communication_status(True, device_names)
        #         self.status_bar.set_message(f"已连接设备: {device_names}")
        #     else:
        #         # 无设备连接或设备异常
        #         self.title_bar.update_communication_status(False, "", error_msg)
        #         if error_msg:
        #             self.status_bar.set_message(f"设备状态: {error_msg}")
        #         else:
        #             self.status_bar.set_message("没有设备连接")
        # except Exception as e:
        #     self.logger.error(f"通信状态检查出错: {e}")
        #     self.title_bar.update_communication_status(False, "", str(e))
        #     self.status_bar.set_message(f"通信错误: {str(e)[:50]}")

    # ==============================
    # 工具
    # ==============================
    def _on_sidebar_clicked(self, index):
        self.stacked_widget.setCurrentIndex(index)

    def _create_fullscreen_action(self):
        action = QAction("全屏模式", self)
        action.setShortcut(QKeySequence("F11"))
        action.triggered.connect(self._toggle_fullscreen)
        self.addAction(action)
        self.is_fullscreen = False

    def _toggle_fullscreen(self):
        if self.is_fullscreen:
            self.showNormal()
        else:
            self.showFullScreen()
        self.is_fullscreen = not self.is_fullscreen


    def changeEvent(self, event):
        """窗体状态变化事件处理"""
        super().changeEvent(event)
        
        if event.type() == event.Type.WindowStateChange:
            # 检测窗体最大化状态变化
            current_maximized = self.isMaximized()
            
            if current_maximized != self.is_window_maximized:
                self.is_window_maximized = current_maximized
                self._notify_window_state_changed(current_maximized)

    def _notify_window_state_changed(self, is_maximized):
        """通知窗口状态变化（可用于通知相关组件）"""
        # 如果需要通知其他组件窗口状态变化，可以在这里添加逻辑
        pass

    def closeEvent(self, event):
        # 增加关闭提示
        reply = QMessageBox.question(
            self,
            "退出确认",
            "确定要退出系统吗？\n\n退出后将结束实验、保存实验数据并关闭所有设备。",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply == QMessageBox.No:
            event.ignore()
            return

        if not self._on_stop_all_experiments():
            QMessageBox.critical(
                self, "退出未完成",
                "设备停止或实验保存未确认，窗口将保持打开。请检查设备与日志后重试退出。",
            )
            event.ignore()
            return
        if self.secondary_display_window is not None:
            self.secondary_display_window.close()
            self.secondary_display_window = None
        self.logger.info("应用程序关闭完成")
        super().closeEvent(event)

    def _on_stop_all_experiments(self):
        """Prepare every device before closing any page's database or resources."""
        pages = [self.stacked_widget.widget(i) for i in range(self.stacked_widget.count())]
        prepared = True
        for page in pages:
            try:
                if hasattr(page, 'prepare_shutdown') and page.prepare_shutdown() is False:
                    prepared = False
            except Exception as error:
                self.logger.error("停止设备或保存会话失败: %s", error)
                prepared = False
        if not prepared:
            return False
        cleaned = True
        for page in pages:
            try:
                if hasattr(page, 'cleanup') and page.cleanup() is False:
                    cleaned = False
            except Exception as error:
                self.logger.error("页面资源清理失败: %s", error)
                cleaned = False
        return cleaned
