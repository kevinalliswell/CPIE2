from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout,
                               QLabel, QPushButton, QLineEdit, QTableWidget,
                               QTableWidgetItem, QMessageBox,
                               QGroupBox, QSplitter, QDialog,
                               QTextEdit, QStackedWidget, QRadioButton,
                               QDateEdit)
from PySide6.QtCore import Qt, QDate
from PySide6.QtGui import QShortcut, QKeySequence
from datetime import datetime, timedelta
import json
import yaml
import re
from utils.logger import LoggerManager
from utils.path_manager import PathManager
from views.ui_components.explosion_detail_card import ExplosionDetailCard
from views.ui_components.ignition_detail_card import IgnitionDetailCard
from views.dialogs.generate_report_dialog import GenerateReportDialog
from views.dialogs.export_dialog import ExportDialog
from views.dialogs.tangent_analysis_dialog import TangentAnalysisDialog
from controllers.explosion_controller import ExplosionController
from controllers.ignition_controller import IgnitionController
from utils.tools import Tools


class HistoryQueryPage(QWidget):
    """历史数据查询界面"""

    def __init__(self):
        super().__init__()

        self.logger = LoggerManager.get_logger(__name__)

        self.config = Tools.load_config(config_path=PathManager.get_config_path("experiment_config.yaml"))

        # # 初始化数据库 - 使用统一的data目录
        # os.makedirs("data", exist_ok=True)
        self.ignition_controller = IgnitionController(config=self.config)
        self.explosion_controller = ExplosionController(config=self.config)
        self.ignition_db = self.ignition_controller.db
        self.explosion_db = self.explosion_controller.db

        # 当前选中的实验
        self.current_experiment = None

        # 实验数据缓存
        self.experiments_data = []
        
        # 过滤条件
        self.selected_experiment_type = None  # None表示全部，'着火点'或'爆炸性'
        self.date_filter_start = None
        self.date_filter_end = None

        # 创建快捷键
        self.create_shortcuts()

        self.init_ui()
        
        # 初始化两个详情卡片为空状态
        self.explosion_detail_card.show_empty_state("请从左侧选择实验记录查看详情")
        self.ignition_detail_card.show_empty_state("请从左侧选择实验记录查看详情")
        
        # 连接两个详情卡片的信号
        self.explosion_detail_card.generate_report_requested.connect(self.on_generate_report)
        self.ignition_detail_card.generate_report_requested.connect(self.on_generate_report)
        self.ignition_detail_card.tangent_analysis_requested.connect(self.on_tangent_analysis)
        
        self.load_experiments()

    def create_shortcuts(self):
        """创建快捷键"""
        # Ctrl+Alt+P 修改密码
        change_pwd_sc = QShortcut(QKeySequence("Ctrl+Alt+P"), self)
        change_pwd_sc.activated.connect(self.change_password)

        # Ctrl+R 刷新数据
        refresh_sc = QShortcut(QKeySequence("Ctrl+R"), self)
        refresh_sc.activated.connect(self.load_experiments)

    def init_ui(self):
        layout = QVBoxLayout()

        # 搜索区域
        search_group = QGroupBox("搜索条件")
        search_layout = QHBoxLayout()

        search_layout.addWidget(QLabel("搜索:"))
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("输入关键字搜索...")
        self.search_edit.textChanged.connect(self.filter_experiments)
        search_layout.addWidget(self.search_edit)
        
        # 分类按钮
        # search_layout.addWidget(QLabel("分类:"))
        self.type_all_btn = QRadioButton("全部")
        self.type_all_btn.setChecked(True)
        self.type_all_btn.toggled.connect(lambda checked: self.on_type_filter_changed(None) if checked else None)
        search_layout.addWidget(self.type_all_btn)
        
        self.type_ignition_btn = QRadioButton("着火点实验")
        self.type_ignition_btn.toggled.connect(lambda checked: self.on_type_filter_changed('着火点') if checked else None)
        search_layout.addWidget(self.type_ignition_btn)
        
        self.type_explosion_btn = QRadioButton("爆炸性实验")
        self.type_explosion_btn.toggled.connect(lambda checked: self.on_type_filter_changed('爆炸性') if checked else None)
        search_layout.addWidget(self.type_explosion_btn)
        
        # 时间检索按钮
        # search_layout.addWidget(QLabel("时间:"))
        self.time_all_btn = QPushButton("全部")
        self.time_all_btn.setCheckable(True)
        self.time_all_btn.setChecked(True)
        self.time_all_btn.clicked.connect(self.on_time_filter_all)
        search_layout.addWidget(self.time_all_btn)
        
        self.time_week_btn = QPushButton("最近一周")
        self.time_week_btn.setCheckable(True)
        self.time_week_btn.clicked.connect(self.on_time_filter_week)
        search_layout.addWidget(self.time_week_btn)
        
        self.time_month_btn = QPushButton("最近一月")
        self.time_month_btn.setCheckable(True)
        self.time_month_btn.clicked.connect(self.on_time_filter_month)
        search_layout.addWidget(self.time_month_btn)
        
        self.time_custom_btn = QPushButton("自定义时间")
        self.time_custom_btn.setCheckable(True)
        self.time_custom_btn.clicked.connect(self.on_time_filter_custom)
        search_layout.addWidget(self.time_custom_btn)
        
        # 自定义日期选择器（初始隐藏）
        self.start_date_label = QLabel("开始:")
        self.start_date_label.setVisible(False)
        search_layout.addWidget(self.start_date_label)
        
        self.start_date_edit = QDateEdit()
        self.start_date_edit.setCalendarPopup(True)
        self.start_date_edit.setDate(QDate.currentDate().addDays(-7))
        self.start_date_edit.dateChanged.connect(self.on_custom_date_changed)
        self.start_date_edit.setVisible(False)
        search_layout.addWidget(self.start_date_edit)
        
        self.end_date_label = QLabel("结束:")
        self.end_date_label.setVisible(False)
        search_layout.addWidget(self.end_date_label)
        
        self.end_date_edit = QDateEdit()
        self.end_date_edit.setCalendarPopup(True)
        self.end_date_edit.setDate(QDate.currentDate())
        self.end_date_edit.dateChanged.connect(self.on_custom_date_changed)
        self.end_date_edit.setVisible(False)
        search_layout.addWidget(self.end_date_edit)
        
        # 时间按钮组（用于互斥）
        self.time_button_group = [self.time_all_btn, self.time_week_btn, 
                                  self.time_month_btn, self.time_custom_btn]

        self.refresh_btn = QPushButton("刷新")
        self.refresh_btn.clicked.connect(self.load_experiments)
        search_layout.addWidget(self.refresh_btn)

        self.delete_btn = QPushButton("删除记录")
        self.delete_btn.clicked.connect(self.delete_experiment)
        search_layout.addWidget(self.delete_btn)

        self.export_btn = QPushButton("导出数据")
        self.export_btn.clicked.connect(self.export_data)
        search_layout.addWidget(self.export_btn)

        search_group.setLayout(search_layout)
        layout.addWidget(search_group, 0)

        # 创建水平分割器来调整表格和详情区域的占比
        splitter = QSplitter(Qt.Horizontal)
        
        # 左侧：实验记录表格区域
        table_group = QGroupBox("实验记录")
        table_layout = QVBoxLayout()
        
        self.table = QTableWidget()
        self.table.setColumnCount(11)
        self.table.setHorizontalHeaderLabels([
            "实验类型", "实验会话ID", "实验编号", "实验名称", "样品名称", 
            "委托单位", "操作人员", "开始时间", "结束时间", "状态", "备注"
        ])
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        # 禁用单元格编辑
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        # 启用排序
        self.table.setSortingEnabled(True)
        self.table.itemSelectionChanged.connect(self.on_selection_changed)
        table_layout.addWidget(self.table)
        table_group.setLayout(table_layout)
        
        # 右侧：实验详情卡片区域
        detail_group = QGroupBox("实验详情")
        detail_layout = QVBoxLayout()
        detail_layout.setContentsMargins(0, 0, 0, 0)
        
        # 创建两个独立的详情卡片
        self.explosion_detail_card = ExplosionDetailCard()
        self.ignition_detail_card = IgnitionDetailCard()
        
        # 使用QStackedWidget管理两个卡片
        self.detail_stack = QStackedWidget()
        self.detail_stack.addWidget(self.explosion_detail_card)  # 索引0
        self.detail_stack.addWidget(self.ignition_detail_card)   # 索引1
        
        detail_layout.addWidget(self.detail_stack)
        detail_group.setLayout(detail_layout)
        
        # 将表格和详情卡片添加到分割器中
        splitter.addWidget(table_group)
        splitter.addWidget(detail_group)
        
        # 设置默认占比为3:2（表格占60%，详情占40%）
        splitter.setSizes([600, 400])
        
        # 将分割器添加到主布局中
        layout.addWidget(splitter, 1)

        self.setLayout(layout)

    def _load_config(self, config_path):
        """加载配置文件"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except Exception as e:
            self.logger.error(f"加载配置文件失败: {e}")
            return None

    def extract_experiment_id(self, experiment_name):
        """
        从 experiment_name 中提取实验编号
        
        Args:
            experiment_name: 实验名称字符串，可能格式：
                - "实验编号：EXP-20251205-094357 | 委托单位：..."
                - "IGN-20241201-001" (直接就是实验编号)
                - "EXP-20251205-094357" (直接就是实验编号)
            
        Returns:
            提取的实验编号，如 "EXP-20251205-094357" 或 "IGN-20241201-001"，如果提取失败返回 None
        """
        if not experiment_name:
            return None
        
        # 首先检查是否整个字符串就是实验编号格式（EXP- 或 IGN- 开头）
        direct_pattern = r'^([A-Z]{2,4}-\d{8}-\d{3,6})$'
        direct_match = re.match(direct_pattern, experiment_name.strip())
        if direct_match:
            return direct_match.group(1)
        
        # 尝试匹配实验编号格式：实验编号：EXP-YYYYMMDD-HHMMSS 或 实验编号：IGN-YYYYMMDD-NNN
        pattern1 = r'实验编号[：:]\s*([A-Z]{2,4}-\d{8}-\d{3,6})'
        match1 = re.search(pattern1, experiment_name)
        if match1:
            return match1.group(1)
        
        # 如果没有匹配到，尝试直接匹配 EXP- 或 IGN- 开头的格式
        pattern2 = r'([A-Z]{2,4}-\d{8}-\d{3,6})'
        match2 = re.search(pattern2, experiment_name)
        if match2:
            return match2.group(1)
        
        # 如果都没有匹配到，返回 None
        return None
    
    def load_experiments(self):
        """从数据库加载实验记录"""
        try:
            # 加载着火点实验
            ignition_sessions = self.ignition_db.get_all_experiment_sessions()
            for session in ignition_sessions:
                session['experiment_type'] = '着火点'
                # 如果 experiment_id 为空，尝试从 experiment_name 中提取
                if not session.get('experiment_id'):
                    experiment_name = session.get('experiment_name', '')
                    extracted_id = self.extract_experiment_id(experiment_name)
                    if extracted_id:
                        session['experiment_id'] = extracted_id
            
            # 加载爆炸性实验
            explosion_sessions = self.explosion_db.get_all_experiment_sessions()
            for session in explosion_sessions:
                session['experiment_type'] = '爆炸性'
                # 如果 experiment_id 为空，尝试从 experiment_name 中提取
                if not session.get('experiment_id'):
                    experiment_name = session.get('experiment_name', '')
                    extracted_id = self.extract_experiment_id(experiment_name)
                    if extracted_id:
                        session['experiment_id'] = extracted_id
            
            # 合并并按结束时间排序
            self.experiments_data = ignition_sessions + explosion_sessions
            self.experiments_data.sort(
                key=lambda x: x.get('end_time') or x.get('start_time') or '', 
                reverse=True
            )
            
            self.update_table(self.experiments_data)
            self.logger.info(f"加载了 {len(self.experiments_data)} 条实验记录")
            
        except Exception as e:
            self.logger.error(f"加载实验记录失败: {e}")
            QMessageBox.warning(self, "警告", f"加载实验记录失败：{str(e)}")

    def update_table(self, experiments):
        """更新表格显示"""
        # 暂时禁用排序以提高性能
        self.table.setSortingEnabled(False)
        self.table.setRowCount(0)
        
        for exp in experiments:
            row = self.table.rowCount()
            self.table.insertRow(row)
            
            # 列0: 实验类型
            self.table.setItem(row, 0, QTableWidgetItem(exp['experiment_type']))
            
            # 列1: 实验会话ID（数据库自增主键id）
            session_id = str(exp.get('id', ''))
            self.table.setItem(row, 1, QTableWidgetItem(session_id))
            
            # 列2: 实验编号（experiment_id，如果没有则显示为空）
            experiment_id = exp.get('experiment_id', '') or ''
            self.table.setItem(row, 2, QTableWidgetItem(experiment_id))
            
            # 列3: 实验名称
            exp_name = exp.get('experiment_name', '') or ''
            self.table.setItem(row, 3, QTableWidgetItem(exp_name))
            
            # 列4: 样品名称（需要处理两种格式）
            sample_name = ''
            if exp['experiment_type'] == '着火点':
                sample_names_json = exp.get('sample_names', '')
                if sample_names_json:
                    try:
                        names = json.loads(sample_names_json)
                        # 显示第一个样品名称，如果有多个则显示"样品1等N个"
                        valid_names = [n for n in names if n]
                        if valid_names:
                            if len(valid_names) == 1:
                                sample_name = valid_names[0]
                            else:
                                sample_name = f"{valid_names[0]}等{len(valid_names)}个"
                    except (json.JSONDecodeError, KeyError, IndexError):
                        sample_name = ''
            else:
                sample_name = exp.get('sample_name', '') or ''
            self.table.setItem(row, 4, QTableWidgetItem(sample_name))
            
            # 列5: 委托单位（两种实验类型都有此字段）
            client = exp.get('client', '') or ''
            self.table.setItem(row, 5, QTableWidgetItem(client))
            
            # 列6: 操作人员
            operator = exp.get('operator', '') or ''
            self.table.setItem(row, 6, QTableWidgetItem(operator))
            
            # 列7: 开始时间
            start_time = exp.get('start_time', '')
            if start_time:
                # 格式化时间显示
                try:
                    if '.' in start_time:
                        dt = datetime.strptime(start_time, '%Y-%m-%d %H:%M:%S.%f')
                    else:
                        dt = datetime.strptime(start_time, '%Y-%m-%d %H:%M:%S')
                    start_time = dt.strftime('%Y-%m-%d %H:%M:%S')
                except (ValueError, TypeError):
                    pass
            self.table.setItem(row, 7, QTableWidgetItem(start_time or ''))
            
            # 列8: 结束时间
            end_time = exp.get('end_time', '')
            if end_time:
                # 格式化时间显示
                try:
                    if '.' in end_time:
                        dt = datetime.strptime(end_time, '%Y-%m-%d %H:%M:%S.%f')
                    else:
                        dt = datetime.strptime(end_time, '%Y-%m-%d %H:%M:%S')
                    end_time = dt.strftime('%Y-%m-%d %H:%M:%S')
                except (ValueError, TypeError):
                    pass
            self.table.setItem(row, 8, QTableWidgetItem(end_time or ''))
            
            # 列9: 状态
            status = exp.get('status', '')
            status_dict = {
                'prepared': '已准备',
                'running': '运行中',
                'completed': '已完成',
                'cancelled': '已取消',
                'error': '错误'
            }
            status_text = status_dict.get(status, status)
            self.table.setItem(row, 9, QTableWidgetItem(status_text))
            
            # 列10: 备注（description字段）
            description = exp.get('description', '') or ''
            self.table.setItem(row, 10, QTableWidgetItem(description))
        
        # 重新启用排序
        self.table.setSortingEnabled(True)
        # 调整列宽
        self.table.resizeColumnsToContents()

    def filter_experiments(self):
        """过滤实验记录（支持关键字、类型和时间过滤）"""
        search_text = self.search_edit.text().lower()
        
        for row in range(self.table.rowCount()):
            # 获取实验数据
            if row >= len(self.experiments_data):
                self.table.hideRow(row)
                continue
                
            exp = self.experiments_data[row]
            
            # 类型过滤
            if self.selected_experiment_type is not None:
                if exp.get('experiment_type') != self.selected_experiment_type:
                    self.table.hideRow(row)
                    continue
            
            # 时间过滤
            if self.date_filter_start is not None or self.date_filter_end is not None:
                # 使用结束时间，如果没有则使用开始时间
                time_str = exp.get('end_time') or exp.get('start_time') or ''
                if time_str:
                    try:
                        if '.' in time_str:
                            exp_time = datetime.strptime(time_str, '%Y-%m-%d %H:%M:%S.%f')
                        else:
                            exp_time = datetime.strptime(time_str, '%Y-%m-%d %H:%M:%S')
                        
                        exp_date = exp_time.date()
                        
                        # 检查是否在时间范围内
                        if self.date_filter_start and exp_date < self.date_filter_start:
                            self.table.hideRow(row)
                            continue
                        if self.date_filter_end and exp_date > self.date_filter_end:
                            self.table.hideRow(row)
                            continue
                    except (ValueError, TypeError):
                        # 如果时间解析失败，显示该行
                        pass
                else:
                    # 如果没有时间信息，根据过滤条件决定是否显示
                    if self.date_filter_start or self.date_filter_end:
                        self.table.hideRow(row)
                        continue
            
            # 关键字搜索过滤
            if search_text:
                # 获取所有列的文本
                row_texts = [
                    self.table.item(row, col).text().lower() if self.table.item(row, col) else ''
                    for col in range(self.table.columnCount())
                ]
                
                # 如果任何一列包含搜索文本，显示该行
                if any(search_text in text for text in row_texts):
                    self.table.showRow(row)
                else:
                    self.table.hideRow(row)
            else:
                # 没有搜索文本，显示该行
                self.table.showRow(row)
    
    def on_type_filter_changed(self, exp_type):
        """分类过滤改变"""
        self.selected_experiment_type = exp_type
        self.filter_experiments()
    
    def on_time_filter_all(self):
        """显示全部时间"""
        # 确保当前按钮被选中
        self.time_all_btn.setChecked(True)
        # 取消其他按钮的选中状态
        for btn in self.time_button_group:
            if btn != self.time_all_btn:
                btn.setChecked(False)
        
        self.date_filter_start = None
        self.date_filter_end = None
        self.start_date_label.setVisible(False)
        self.start_date_edit.setVisible(False)
        self.end_date_label.setVisible(False)
        self.end_date_edit.setVisible(False)
        self.filter_experiments()
    
    def on_time_filter_week(self):
        """最近一周"""
        # 确保当前按钮被选中
        self.time_week_btn.setChecked(True)
        # 取消其他按钮的选中状态
        for btn in self.time_button_group:
            if btn != self.time_week_btn:
                btn.setChecked(False)
        
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=7)
        
        self.date_filter_start = start_date
        self.date_filter_end = end_date
        self.start_date_label.setVisible(False)
        self.start_date_edit.setVisible(False)
        self.end_date_label.setVisible(False)
        self.end_date_edit.setVisible(False)
        self.filter_experiments()
    
    def on_time_filter_month(self):
        """最近一月"""
        # 确保当前按钮被选中
        self.time_month_btn.setChecked(True)
        # 取消其他按钮的选中状态
        for btn in self.time_button_group:
            if btn != self.time_month_btn:
                btn.setChecked(False)
        
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=30)
        
        self.date_filter_start = start_date
        self.date_filter_end = end_date
        self.start_date_label.setVisible(False)
        self.start_date_edit.setVisible(False)
        self.end_date_label.setVisible(False)
        self.end_date_edit.setVisible(False)
        self.filter_experiments()
    
    def on_time_filter_custom(self):
        """自定义时间区间"""
        # 确保当前按钮被选中
        self.time_custom_btn.setChecked(True)
        # 取消其他按钮的选中状态
        for btn in self.time_button_group:
            if btn != self.time_custom_btn:
                btn.setChecked(False)
        
        # 显示日期选择器和标签
        self.start_date_label.setVisible(True)
        self.start_date_edit.setVisible(True)
        self.end_date_label.setVisible(True)
        self.end_date_edit.setVisible(True)
        
        # 设置默认日期（最近一周）
        end_date = QDate.currentDate()
        start_date = end_date.addDays(-7)
        self.start_date_edit.setDate(start_date)
        self.end_date_edit.setDate(end_date)
        
        # 应用过滤
        self.on_custom_date_changed()
    
    def on_custom_date_changed(self):
        """自定义日期改变"""
        if self.time_custom_btn.isChecked():
            start_qdate = self.start_date_edit.date()
            end_qdate = self.end_date_edit.date()
            
            # 转换为Python date对象
            self.date_filter_start = datetime(start_qdate.year(), start_qdate.month(), start_qdate.day()).date()
            self.date_filter_end = datetime(end_qdate.year(), end_qdate.month(), end_qdate.day()).date()
            
            self.filter_experiments()

    def on_selection_changed(self):
        """选中记录变化时更新当前实验"""
        selected = self.table.selectedItems()
        if selected:
            row = selected[0].row()
            if 0 <= row < len(self.experiments_data):
                self.current_experiment = self.experiments_data[row]
                self.logger.debug(f"选中实验: {self.current_experiment.get('experiment_name', 'Unknown')}")
                # 加载实验详情到右侧卡片
                self.load_experiment_detail()
        else:
            self.current_experiment = None
            self.explosion_detail_card.show_empty_state("请从左侧选择实验记录查看详情")
            self.ignition_detail_card.show_empty_state("请从左侧选择实验记录查看详情")
        
    def load_experiment_detail(self):
        """加载选中实验的详细信息到右侧卡片"""
        if not self.current_experiment:
            return
        
        exp_id = self.current_experiment.get('id')
        exp_type = self.current_experiment.get('experiment_type')
        
        # 准备实验数据
        exp_data = self.current_experiment.copy()
        
        try:
            # 根据实验类型加载详细数据
            if exp_type == '爆炸性':
                # 切换到爆炸性实验详情卡片
                self.detail_stack.setCurrentIndex(0)
                
                # 获取测试轮次和结果
                tests = self.explosion_db.get_session_test_rounds(exp_id)
                result = self.explosion_db.get_session_result(exp_id)
                
                # 转换为详情卡片需要的格式
                exp_data['tests'] = [
                    {
                        'test_sequence': t['round_number'],
                        'flame_length_mm': t['flame_length'],
                        'image_path': t.get('max_flame_image_path')
                    } for t in tests
                ]
                
                if result:
                    exp_data['max_flame_length'] = result.get('avg_flame_length')
                    exp_data['explosion_level'] = result.get('explosion_level')
                
                # 字段映射
                exp_data['experiment_code'] = exp_data.get('experiment_id', '')
                exp_data['inspector'] = exp_data.get('operator', '')
                exp_data['client_organization'] = exp_data.get('client', '')
                exp_data['repeat_times'] = result.get('total_rounds', 5) if result else 5
                
                # 调用爆炸性实验卡片的加载方法
                self.explosion_detail_card.load_experiment_detail(
                    exp_id, exp_data, 
                    explosion_db=self.explosion_db
                )
            
            elif exp_type == '着火点':
                # 切换到着火点实验详情卡片
                self.detail_stack.setCurrentIndex(1)
                
                # 获取着火点检测数据
                detections = self.ignition_db.get_ignition_detections(exp_id)
                
                # 解析样品名称
                sample_names_json = exp_data.get('sample_names', '[]')
                try:
                    sample_names = json.loads(sample_names_json)
                except (json.JSONDecodeError, TypeError):
                    sample_names = []
                
                # 构建样品数据
                samples = []
                sample_data = []
                for i, name in enumerate(sample_names, 1):
                    if name:  # 只添加非空样品名称
                        samples.append({
                            'name': name,
                            'position': i
                        })
                        
                        # 查找对应检测结果
                        detection = next((d for d in detections if d['channel'] == i), None)
                        if detection:
                            sample_data.append({
                                'sample_position': i,
                                'ignition_temperature': detection['ignition_temperature'],
                                'temperature_rise_rate': None,
                                'is_valid': True
                            })
                
                # 计算统计数据
                temps = [d['ignition_temperature'] for d in sample_data if d.get('ignition_temperature')]
                if temps:
                    exp_data['avg_ignition_temperature'] = sum(temps) / len(temps)
                    exp_data['highest_ignition_temp'] = max(temps)
                    exp_data['lowest_ignition_temp'] = min(temps)
                
                exp_data['samples'] = samples
                exp_data['sample_data'] = sample_data
                
                # 字段映射
                exp_data['experiment_code'] = exp_data.get('experiment_id', '')
                exp_data['inspector'] = exp_data.get('operator', '')
                exp_data['client_organization'] = exp_data.get('client', '')
                
                # 调用着火点实验卡片的加载方法
                self.ignition_detail_card.load_experiment_detail(
                    exp_id, exp_data,
                    ignition_db=self.ignition_db
                )
        except Exception as e:
            self.logger.error(f"加载实验详情失败: {e}")
            # 根据当前类型显示错误消息
            if exp_type == '爆炸性':
                self.explosion_detail_card.show_empty_state(f"加载实验详情失败：{str(e)}")
            else:
                self.ignition_detail_card.show_empty_state(f"加载实验详情失败：{str(e)}")
    
    def on_generate_report(self):
        """生成报告按钮点击处理"""
        if not self.current_experiment:
            QMessageBox.warning(self, "警告", "请先选择一个实验记录！")
            return
        
        exp_id = self.current_experiment.get('id')
        exp_type = self.current_experiment.get('experiment_type')
        
        # 准备实验数据（使用详情卡片中已加载的数据）
        exp_data = self.current_experiment.copy()
        
        # 根据实验类型准备数据
        if exp_type == '爆炸性':
            # 获取测试轮次和结果
            tests = self.explosion_db.get_session_test_rounds(exp_id)
            result = self.explosion_db.get_session_result(exp_id)
            
            # 转换为报告需要的格式
            exp_data['tests'] = [
                {
                    'test_sequence': t['round_number'],
                    'flame_length_mm': t['flame_length'],
                    'image_path': t.get('max_flame_image_path')
                } for t in tests
            ]
            
            if result:
                exp_data['max_flame_length'] = result.get('avg_flame_length')
                exp_data['explosion_level'] = result.get('explosion_level')
                exp_data['repeat_times'] = result.get('total_rounds', 5)
            
            # 字段映射
            exp_data['experiment_code'] = exp_data.get('experiment_id', '')
            exp_data['inspector'] = exp_data.get('operator', '')
            exp_data['client_organization'] = exp_data.get('client', '')
            
            # 如果没有结论，自动生成
            if not exp_data.get('conclusion'):
                try:
                    exp_data['conclusion'] = self.explosion_db.generate_conclusion(exp_id)
                except Exception:
                    pass  # 生成失败时使用默认值
            
            # 打开报告对话框
            dialog = GenerateReportDialog(
                exp_id, 'explosion', exp_data,
                explosion_db=self.explosion_db,
                ignition_db=None,
                parent=self
            )
            dialog.exec()
        
        elif exp_type == '着火点':
            # 获取着火点检测数据
            detections = self.ignition_db.get_ignition_detections(exp_id)
            
            # 解析样品名称
            sample_names_json = exp_data.get('sample_names', '[]')
            try:
                sample_names = json.loads(sample_names_json)
            except (json.JSONDecodeError, TypeError):
                sample_names = []
            
            # 构建样品数据
            samples = []
            sample_data = []
            for i, name in enumerate(sample_names, 1):
                if name:
                    samples.append({
                        'name': name,
                        'position': i
                    })
                    
                    # 查找对应检测结果
                    detection = next((d for d in detections if d['channel'] == i), None)
                    if detection:
                        sample_data.append({
                            'sample_position': i,
                            'ignition_temperature': detection['ignition_temperature'],
                            'temperature_rise_rate': None,
                            'is_valid': True
                        })
            
            # 计算统计数据
            temps = [d['ignition_temperature'] for d in sample_data if d.get('ignition_temperature')]
            if temps:
                exp_data['avg_ignition_temperature'] = sum(temps) / len(temps)
                exp_data['highest_ignition_temp'] = max(temps)
                exp_data['lowest_ignition_temp'] = min(temps)
            
            exp_data['samples'] = samples
            exp_data['sample_data'] = sample_data
            
            # 字段映射
            exp_data['experiment_code'] = exp_data.get('experiment_id', '')
            exp_data['inspector'] = exp_data.get('operator', '')
            exp_data['client_organization'] = exp_data.get('client', '')
            
            # 如果没有结论，自动生成
            if not exp_data.get('conclusion'):
                try:
                    exp_data['conclusion'] = self.ignition_db.generate_conclusion(exp_id)
                except Exception:
                    pass  # 生成失败时使用默认值
            
            # 打开报告对话框
            dialog = GenerateReportDialog(
                exp_id, 'ignition', exp_data,
                explosion_db=None,
                ignition_db=self.ignition_db,
                parent=self
            )
            dialog.exec()
    
    def on_tangent_analysis(self):
        """切线法分析按钮点击处理"""
        if not self.current_experiment:
            QMessageBox.warning(self, "警告", "请先选择一个实验记录！")
            return
        
        exp_type = self.current_experiment.get('experiment_type')
        
        # 只有着火点实验才能进行切线法分析
        if exp_type != '着火点':
            QMessageBox.warning(self, "警告", "只有着火点实验才能进行切线法分析！")
            return
        
        exp_id = self.current_experiment.get('id')
        
        try:
            # 创建并显示切线法分析对话框
            dialog = TangentAnalysisDialog(
                session_id=exp_id,
                db=self.ignition_db,
                config=self.config,
                parent=self
            )
            dialog.exec()
            
            # 分析完成后刷新详情（如果需要）
            self.load_experiment_detail()
            
        except Exception as e:
            self.logger.error(f"切线法分析失败: {e}")
            QMessageBox.critical(self, "错误", f"切线法分析失败: {str(e)}")

    def update_data_table(self, experiment, timestamps):
        """更新实验数据表格"""
        pass

    def delete_experiment(self):
        """删除实验记录"""
        # 密码确认
        from views.dialogs.password_confirm_dialog import PasswordConfirmDialog
        password_dialog = PasswordConfirmDialog(self)
        if password_dialog.exec() != QDialog.DialogCode.Accepted:
            return  # 用户取消或密码错误

        # 获取选中的记录
        items = self.table.selectedItems()
        if not items:
            QMessageBox.warning(self, "警告", "请先选择要删除的记录！")
            return

        # 确认删除
        row = items[0].row()
        if 0 <= row < len(self.experiments_data):
            experiment = self.experiments_data[row]
            exp_name = experiment.get('experiment_name', '')
            exp_type = experiment.get('experiment_type', '')
            session_id = experiment.get('id')
            experiment_id = experiment.get('experiment_id', '')

            # 查询将要删除的内容
            image_count = 0
            folder_info = ""
            
            try:
                if exp_type == '着火点':
                    # 查询着火点实验的图片数量
                    self.ignition_db.cursor.execute("""
                        SELECT COUNT(*) 
                        FROM ignition_detection 
                        WHERE session_id = ? AND tangent_analysis_image_path IS NOT NULL
                    """, (session_id,))
                    image_count = self.ignition_db.cursor.fetchone()[0] or 0
                    
                    # 检查实验文件夹
                    if experiment_id:
                        from utils.path_manager import PathManager
                        import os
                        experiment_folder = PathManager.get_data_path(f"analysis_images/{experiment_id}")
                        if os.path.exists(experiment_folder) and os.path.isdir(experiment_folder):
                            folder_info = f"\n• 实验文件夹: {experiment_id}/"
                else:
                    # 查询爆炸性实验的图片数量
                    self.explosion_db.cursor.execute("""
                        SELECT COUNT(*) 
                        FROM test_rounds 
                        WHERE session_id = ? AND max_flame_image_path IS NOT NULL
                    """, (session_id,))
                    image_count = self.explosion_db.cursor.fetchone()[0] or 0
            except Exception as e:
                self.logger.warning(f"查询删除信息失败: {e}")

            # 构建确认消息
            confirm_message = "确定要删除以下实验记录？\n\n"
            confirm_message += f"实验类型: {exp_type}\n"
            confirm_message += f"实验名称: {exp_name}\n"
            if experiment_id:
                confirm_message += f"实验编号: {experiment_id}\n"
            confirm_message += "\n将删除以下内容：\n"
            confirm_message += "• 数据库记录\n"
            if image_count > 0:
                confirm_message += f"• {image_count} 个关联图片文件\n"
            if folder_info:
                confirm_message += folder_info
            confirm_message += "\n此操作不可恢复！"

            reply = QMessageBox.question(
                self,
                "确认删除",
                confirm_message,
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No  # 默认选择"No"以提高安全性
            )

            if reply == QMessageBox.Yes:
                try:
                    # 根据实验类型调用对应的删除方法
                    if exp_type == '着火点':
                        success = self.ignition_db.delete_session(session_id)
                    else:
                        success = self.explosion_db.delete_session(session_id)
                    
                    if not success:
                        raise Exception("删除实验记录失败")

                    # 从数据列表中删除
                    self.experiments_data.pop(row)

                    # 更新表格显示
                    self.table.removeRow(row)
                    
                    # 如果删除的是当前选中的实验，清空详情卡片
                    if self.current_experiment and self.current_experiment.get('id') == session_id:
                        self.current_experiment = None
                        if exp_type == '着火点':
                            self.ignition_detail_card.show_empty_state("请从左侧选择实验记录查看详情")
                        else:
                            self.explosion_detail_card.show_empty_state("请从左侧选择实验记录查看详情")

                    QMessageBox.information(self, "提示", "删除成功！")
                    self.logger.info(f"删除实验记录: {exp_name} (类型: {exp_type}, ID: {session_id})")

                except Exception as e:
                    self.logger.error(f"删除记录失败: {e}")
                    QMessageBox.critical(self, "错误", f"删除记录失败：{str(e)}")

    def change_password(self):
        """修改管理员密码"""
        # TODO: 实现密码管理功能
        QMessageBox.information(self, "提示", "密码管理功能待实现")
        return
        
        # 以下代码待实现密码管理器后启用
        # # 验证旧密码
        # old_pwd, ok = QInputDialog.getText(
        #     self,
        #     "修改密码",
        #     "请输入旧密码:",
        #     QLineEdit.Password
        # )
        #
        # if not ok or not self.password_manager.verify_password(old_pwd):
        #     QMessageBox.warning(self, "警告", "密码错误！")
        #     return
        #
        # # 输入新密码
        # new_pwd, ok = QInputDialog.getText(
        #     self,
        #     "修改密码",
        #     "请输入新密码:",
        #     QLineEdit.Password
        # )
        #
        # if not ok:
        #     return
        #
        # # 确认新密码
        # confirm_pwd, ok = QInputDialog.getText(
        #     self,
        #     "修改密码",
        #     "请确认新密码:",
        #     QLineEdit.Password
        # )
        #
        # if not ok:
        #     return
        #
        # if new_pwd != confirm_pwd:
        #     QMessageBox.warning(self, "警告", "两次输入的密码不一致！")
        #     return
        #
        # # 修改密码
        # if self.password_manager.change_password(old_pwd, new_pwd):
        #     QMessageBox.information(self, "提示", "密码修改成功！")
        # else:
        #     QMessageBox.critical(self, "错误", "密码修改失败！")

    def export_data(self):
        """导出实验数据"""
        # 获取选中的实验ID列表
        selected_items = self.table.selectedItems()
        if not selected_items:
            # 如果没有选中，询问是否导出所有实验
            reply = QMessageBox.question(
                self,
                "导出数据",
                "未选择实验记录，是否导出所有实验数据？",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.No:
                return
            
            # 导出所有实验 - 检查是否有不同类型
            exp_types = set()
            for exp in self.experiments_data:
                exp_types.add('explosion' if exp.get('experiment_type') == '爆炸性' else 'ignition')
            
            if len(exp_types) > 1:
                QMessageBox.warning(
                    self,
                    "提示",
                    "检测到有不同类型的实验记录。\n请分别选择爆炸性实验或着火点实验进行导出。"
                )
                return
            
            experiment_ids = [exp.get('id') for exp in self.experiments_data]
            exp_type = exp_types.pop() if exp_types else 'explosion'
        else:
            # 导出选中的实验
            selected_rows = set()
            for item in selected_items:
                selected_rows.add(item.row())
            
            experiment_ids = []
            exp_types = set()
            for row in selected_rows:
                if 0 <= row < len(self.experiments_data):
                    exp = self.experiments_data[row]
                    experiment_ids.append(exp.get('id'))
                    exp_types.add('explosion' if exp.get('experiment_type') == '爆炸性' else 'ignition')
            
            # 如果选中了不同类型的实验，提示用户分别选择
            if len(exp_types) > 1:
                QMessageBox.warning(
                    self,
                    "提示",
                    "选中的实验记录包含不同类型（爆炸性和着火点）。\n请分别选择同一类型的实验进行导出。"
                )
                return
            
            exp_type = exp_types.pop() if exp_types else 'explosion'
        
        if not experiment_ids:
            QMessageBox.warning(self, "警告", "没有可导出的实验数据！")
            return
        
        # 打开导出对话框
        dialog = ExportDialog(experiment_ids, exp_type, self)
        dialog.export_confirmed.connect(self.handle_export_confirmed)
        dialog.exec()
    
    def handle_export_confirmed(self, config: dict):
        """处理导出确认"""
        try:
            file_path = config['file_path']
            format_type = config['format']
            experiment_ids = config['experiment_ids']
            exp_type = config['exp_type']
            include_basic = config.get('include_basic', True)
            include_results = config.get('include_results', True)
            include_rounds = config.get('include_rounds', False)  # 爆炸性实验轮次详情
            include_samples = config.get('include_samples', False)  # 着火点样品详情
            open_after_export = config.get('open_after_export', True)
            
            # 根据格式导出
            if format_type == 'excel':
                success = self._export_to_excel(
                    file_path, experiment_ids, exp_type, 
                    include_basic, include_results, include_rounds, include_samples
                )
            elif format_type == 'csv':
                success = self._export_to_csv(
                    file_path, experiment_ids, exp_type, 
                    include_basic, include_results, include_rounds, include_samples
                )
            else:
                QMessageBox.warning(self, "警告", f"不支持的导出格式: {format_type}")
                return
            
            if success:
                QMessageBox.information(
                    self,
                    "成功",
                    f"数据导出成功！\n文件: {file_path}\n共导出 {len(experiment_ids)} 条实验记录"
                )
                self.logger.info(f"导出实验数据: {len(experiment_ids)} 条记录 -> {file_path}")
                
                # 如果选择打开文件
                if open_after_export:
                    import os
                    import platform
                    if platform.system() == 'Windows':
                        os.startfile(file_path)
                    elif platform.system() == 'Darwin':  # macOS
                        os.system(f'open "{file_path}"')
                    else:  # Linux
                        os.system(f'xdg-open "{file_path}"')
            else:
                raise Exception("导出失败")
                
        except Exception as e:
            self.logger.error(f"导出数据失败: {e}")
            QMessageBox.critical(self, "错误", f"导出数据失败：{str(e)}")
    
    def _export_to_excel(self, file_path: str, experiment_ids: list, exp_type: str, 
                        include_basic: bool, include_results: bool,
                        include_rounds: bool = False, include_samples: bool = False) -> bool:
        """导出为Excel格式"""
        try:
            import openpyxl
            from openpyxl.styles import Font, Alignment, PatternFill
        except ImportError:
            QMessageBox.warning(
                self,
                "警告",
                "导出Excel需要openpyxl库，请先安装：\npip install openpyxl"
            )
            return False
        
        try:
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "实验数据"
            
            # 设置表头样式
            header_fill = PatternFill(start_color="00d9ff", end_color="00d9ff", fill_type="solid")
            header_font = Font(bold=True, color="000000")
            
            row = 1
            
            # 写入表头
            headers = ["实验会话ID", "实验编号", "实验名称", "实验类型", "委托单位", "样品名称", 
                      "操作人员", "开始时间", "结束时间", "状态", "备注"]
            
            if include_results:
                if exp_type == 'explosion':
                    headers.extend(["最大火焰长度(mm)", "平均火焰长度(mm)", "爆炸性等级", "测试轮次"])
                elif exp_type == 'ignition':
                    headers.extend(["平均着火温度(°C)", "最高温度(°C)", "最低温度(°C)", "样品数量"])
            
            for col, header in enumerate(headers, 1):
                cell = ws.cell(row, col, header)
                cell.fill = header_fill
                cell.font = header_font
                cell.alignment = Alignment(horizontal='center', vertical='center')
            
            row += 1
            
            # 写入数据
            for exp_id in experiment_ids:
                # 查找实验记录
                exp = next((e for e in self.experiments_data if e.get('id') == exp_id), None)
                if not exp:
                    continue
                
                exp_type_str = exp.get('experiment_type', '')
                is_explosion = exp_type_str == '爆炸性'
                
                # 基本信息
                data_row = [
                    exp.get('id', ''),
                    exp.get('experiment_id', '') or '',
                    exp.get('experiment_name', ''),
                    exp_type_str,
                    exp.get('client', ''),
                    self._get_sample_name(exp),
                    exp.get('operator', ''),
                    exp.get('start_time', '')[:19] if exp.get('start_time') else '',
                    exp.get('end_time', '')[:19] if exp.get('end_time') else '',
                    exp.get('status', ''),
                    exp.get('description', '') or '',
                ]
                
                # 测试结果
                if include_results:
                    if is_explosion:
                        # 获取爆炸性实验结果
                        result = self.explosion_db.get_session_result(exp_id)
                        tests = self.explosion_db.get_session_test_rounds(exp_id)
                        
                        max_flame = result.get('avg_flame_length', 0) if result else 0
                        avg_flame = result.get('avg_flame_length', 0) if result else 0
                        level = result.get('explosion_level', '') if result else ''
                        rounds = len(tests) if tests else 0
                        
                        data_row.extend([max_flame, avg_flame, level, rounds])
                    else:
                        # 获取着火点实验结果
                        detections = self.ignition_db.get_ignition_detections(exp_id)
                        temps = [d['ignition_temperature'] for d in detections if d.get('ignition_temperature')]
                        
                        avg_temp = sum(temps) / len(temps) if temps else None
                        highest_temp = max(temps) if temps else None
                        lowest_temp = min(temps) if temps else None
                        
                        # 解析样品数量
                        sample_names_json = exp.get('sample_names', '[]')
                        try:
                            sample_names = json.loads(sample_names_json)
                            sample_count = len([n for n in sample_names if n])
                        except (json.JSONDecodeError, TypeError):
                            sample_count = len(detections)
                        
                        data_row.extend([
                            f"{avg_temp:.1f}" if avg_temp else '',
                            f"{highest_temp:.1f}" if highest_temp else '',
                            f"{lowest_temp:.1f}" if lowest_temp else '',
                            sample_count
                        ])
                
                # 写入行
                for col, value in enumerate(data_row, 1):
                    ws.cell(row, col, value)
                
                row += 1
            
            # 调整列宽
            for col in range(1, len(headers) + 1):
                ws.column_dimensions[openpyxl.utils.get_column_letter(col)].width = 15
            
            # 如果需要导出详情数据
            if include_rounds and exp_type == 'explosion':
                self._add_explosion_rounds_sheet(wb, experiment_ids, header_fill, header_font)
            elif include_samples and exp_type == 'ignition':
                self._add_ignition_samples_sheet(wb, experiment_ids, header_fill, header_font)
            
            # 保存文件
            wb.save(file_path)
            return True
            
        except Exception as e:
            self.logger.error(f"导出Excel失败: {e}")
            return False
    
    def _add_explosion_rounds_sheet(self, wb, experiment_ids: list, header_fill, header_font):
        """添加爆炸性实验测试轮次详情工作表"""
        try:
            ws = wb.create_sheet(title="测试轮次详情")
            from openpyxl.styles import Alignment
            
            # 表头
            headers = ["实验ID", "实验名称", "轮次", "火焰长度(mm)", "图片路径", "测试时间"]
            for col, header in enumerate(headers, 1):
                cell = ws.cell(1, col, header)
                cell.fill = header_fill
                cell.font = header_font
                cell.alignment = Alignment(horizontal='center', vertical='center')
            
            # 数据
            row = 2
            for exp_id in experiment_ids:
                exp = next((e for e in self.experiments_data if e.get('id') == exp_id), None)
                if not exp or exp.get('experiment_type') != '爆炸性':
                    continue
                
                exp_name = exp.get('experiment_name', '')
                tests = self.explosion_db.get_session_test_rounds(exp_id)
                
                for test in tests:
                    ws.cell(row, 1, exp_id)
                    ws.cell(row, 2, exp_name)
                    ws.cell(row, 3, test.get('round_number', ''))
                    ws.cell(row, 4, test.get('flame_length', ''))
                    ws.cell(row, 5, test.get('max_flame_image_path', ''))
                    ws.cell(row, 6, test.get('timestamp', '')[:19] if test.get('timestamp') else '')
                    row += 1
            
            # 调整列宽
            ws.column_dimensions['A'].width = 10
            ws.column_dimensions['B'].width = 20
            ws.column_dimensions['C'].width = 10
            ws.column_dimensions['D'].width = 18
            ws.column_dimensions['E'].width = 40
            ws.column_dimensions['F'].width = 20
            
        except Exception as e:
            self.logger.error(f"添加测试轮次详情失败: {e}")
    
    def _add_ignition_samples_sheet(self, wb, experiment_ids: list, header_fill, header_font):
        """添加着火点实验样品详情工作表"""
        try:
            ws = wb.create_sheet(title="样品详情")
            from openpyxl.styles import Alignment
            
            # 表头
            headers = ["实验ID", "实验名称", "样品位置", "样品名称", "着火温度(°C)", "检测时间"]
            for col, header in enumerate(headers, 1):
                cell = ws.cell(1, col, header)
                cell.fill = header_fill
                cell.font = header_font
                cell.alignment = Alignment(horizontal='center', vertical='center')
            
            # 数据
            row = 2
            for exp_id in experiment_ids:
                exp = next((e for e in self.experiments_data if e.get('id') == exp_id), None)
                if not exp or exp.get('experiment_type') != '着火点':
                    continue
                
                exp_name = exp.get('experiment_name', '')
                detections = self.ignition_db.get_ignition_detections(exp_id)
                
                # 解析样品名称
                sample_names_json = exp.get('sample_names', '[]')
                try:
                    sample_names = json.loads(sample_names_json)
                except (json.JSONDecodeError, TypeError):
                    sample_names = []
                
                for detection in detections:
                    channel = detection.get('channel', 0)
                    sample_name = sample_names[channel - 1] if channel > 0 and channel <= len(sample_names) else f"样品{channel}"
                    
                    ws.cell(row, 1, exp_id)
                    ws.cell(row, 2, exp_name)
                    ws.cell(row, 3, channel)
                    ws.cell(row, 4, sample_name)
                    
                    temp = detection.get('ignition_temperature')
                    ws.cell(row, 5, f"{temp:.1f}" if temp is not None else '未着火')
                    
                    ws.cell(row, 6, detection.get('detection_time', '')[:19] if detection.get('detection_time') else '')
                    row += 1
            
            # 调整列宽
            ws.column_dimensions['A'].width = 10
            ws.column_dimensions['B'].width = 20
            ws.column_dimensions['C'].width = 12
            ws.column_dimensions['D'].width = 20
            ws.column_dimensions['E'].width = 18
            ws.column_dimensions['F'].width = 20
            
        except Exception as e:
            self.logger.error(f"添加样品详情失败: {e}")
    
    def _export_to_csv(self, file_path: str, experiment_ids: list, exp_type: str,
                      include_basic: bool, include_results: bool,
                      include_rounds: bool = False, include_samples: bool = False) -> bool:
        """导出为CSV格式（注：CSV格式不支持导出详情数据到多个工作表）"""
        import csv
        
        try:
            with open(file_path, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f)
                
                # 写入表头
                headers = ["实验会话ID", "实验编号", "实验名称", "实验类型", "委托单位", "样品名称",
                          "操作人员", "开始时间", "结束时间", "状态", "备注"]
                
                if include_results:
                    if exp_type == 'explosion':
                        headers.extend(["最大火焰长度(mm)", "平均火焰长度(mm)", "爆炸性等级", "测试轮次"])
                    elif exp_type == 'ignition':
                        headers.extend(["平均着火温度(°C)", "最高温度(°C)", "最低温度(°C)", "样品数量"])
                
                writer.writerow(headers)
                
                # 写入数据
                for exp_id in experiment_ids:
                    exp = next((e for e in self.experiments_data if e.get('id') == exp_id), None)
                    if not exp:
                        continue
                    
                    exp_type_str = exp.get('experiment_type', '')
                    is_explosion = exp_type_str == '爆炸性'
                    
                    # 基本信息
                    data_row = [
                        exp.get('id', ''),
                        exp.get('experiment_id', '') or '',
                        exp.get('experiment_name', ''),
                        exp_type_str,
                        exp.get('client', ''),
                        self._get_sample_name(exp),
                        exp.get('operator', ''),
                        exp.get('start_time', '')[:19] if exp.get('start_time') else '',
                        exp.get('end_time', '')[:19] if exp.get('end_time') else '',
                        exp.get('status', ''),
                        exp.get('description', '') or '',
                    ]
                    
                    # 测试结果
                    if include_results:
                        if is_explosion:
                            result = self.explosion_db.get_session_result(exp_id)
                            tests = self.explosion_db.get_session_test_rounds(exp_id)
                            
                            max_flame = result.get('avg_flame_length', 0) if result else 0
                            avg_flame = result.get('avg_flame_length', 0) if result else 0
                            level = result.get('explosion_level', '') if result else ''
                            rounds = len(tests) if tests else 0
                            
                            data_row.extend([max_flame, avg_flame, level, rounds])
                        else:
                            detections = self.ignition_db.get_ignition_detections(exp_id)
                            temps = [d['ignition_temperature'] for d in detections if d.get('ignition_temperature')]
                            
                            avg_temp = sum(temps) / len(temps) if temps else None
                            highest_temp = max(temps) if temps else None
                            lowest_temp = min(temps) if temps else None
                            
                            sample_names_json = exp.get('sample_names', '[]')
                            try:
                                sample_names = json.loads(sample_names_json)
                                sample_count = len([n for n in sample_names if n])
                            except (json.JSONDecodeError, TypeError):
                                sample_count = len(detections)
                            
                            data_row.extend([
                                f"{avg_temp:.1f}" if avg_temp else '',
                                f"{highest_temp:.1f}" if highest_temp else '',
                                f"{lowest_temp:.1f}" if lowest_temp else '',
                                sample_count
                            ])
                    
                    writer.writerow(data_row)
            
            return True
            
        except Exception as e:
            self.logger.error(f"导出CSV失败: {e}")
            return False
    
    def _get_sample_name(self, exp: dict) -> str:
        """获取样品名称"""
        exp_type = exp.get('experiment_type', '')
        if exp_type == '着火点':
            sample_names_json = exp.get('sample_names', '[]')
            try:
                sample_names = json.loads(sample_names_json)
                valid_names = [n for n in sample_names if n]
                if valid_names:
                    return valid_names[0] if len(valid_names) == 1 else f"{valid_names[0]}等{len(valid_names)}个"
            except (json.JSONDecodeError, TypeError):
                pass
        else:
            return exp.get('sample_name', '')
        return ''

    def _export_csv(self, data, filepath):
        """导出为CSV格式"""
        pass
            # TODO: 导入csv模块

    def _export_xlsx(self, data, filepath):
        """导出为Excel格式"""
        pass
        # TODO: 创建实验信息sheet

        # 创建实验数据sheet
        # TODO: 创建实验数据sheet

        # 创建Excel文件
        # TODO: 创建Excel文件


class ExperimentDetailDialog(QDialog):
    """实验详情对话框"""
    
    def __init__(self, experiment, ignition_db, explosion_db, parent=None):
        super().__init__(parent)
        self.experiment = experiment
        self.ignition_db = ignition_db
        self.explosion_db = explosion_db
        
        self.setWindowTitle(f"实验详情 - {experiment.get('experiment_name', 'Unknown')}")
        self.setMinimumSize(800, 600)
        self.init_ui()
    
    def init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout()
        
        # 基本信息区域
        basic_group = QGroupBox("基本信息")
        basic_layout = QVBoxLayout()
        
        basic_info = self._format_basic_info()
        basic_text = QTextEdit()
        basic_text.setPlainText(basic_info)
        basic_text.setReadOnly(True)
        basic_text.setMaximumHeight(200)
        basic_layout.addWidget(basic_text)
        basic_group.setLayout(basic_layout)
        layout.addWidget(basic_group)
        
        # 详细数据区域
        detail_group = QGroupBox("详细数据")
        detail_layout = QVBoxLayout()
        
        detail_info = self._format_detail_info()
        detail_text = QTextEdit()
        detail_text.setPlainText(detail_info)
        detail_text.setReadOnly(True)
        detail_layout.addWidget(detail_text)
        detail_group.setLayout(detail_layout)
        layout.addWidget(detail_group)
        
        # 关闭按钮
        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)
        
        self.setLayout(layout)
    
    def _format_basic_info(self):
        """格式化基本信息"""
        exp = self.experiment
        exp_type = exp.get('experiment_type', '')
        
        info = []
        info.append(f"实验类型: {exp_type}")
        info.append(f"会话ID: {exp.get('id', '')}")
        info.append(f"实验名称: {exp.get('experiment_name', '')}")
        info.append(f"开始时间: {exp.get('start_time', '')}")
        info.append(f"结束时间: {exp.get('end_time', '')}")
        info.append(f"操作人员: {exp.get('operator', '')}")
        info.append(f"状态: {exp.get('status', '')}")
        
        # 委托单位（两种实验类型都有）
        info.append(f"委托单位: {exp.get('client', '')}")
        
        if exp_type == '着火点':
            sample_names_json = exp.get('sample_names', '')
            if sample_names_json:
                try:
                    names = json.loads(sample_names_json)
                    info.append(f"样品数量: {len(names)}")
                except (json.JSONDecodeError, KeyError):
                    pass
        else:
            info.append(f"样品名称: {exp.get('sample_name', '')}")
        
        info.append(f"描述: {exp.get('description', '')}")
        
        return '\n'.join(info)
    
    def _format_detail_info(self):
        """格式化详细信息"""
        exp = self.experiment
        exp_type = exp.get('experiment_type', '')
        session_id = exp.get('id')
        
        if exp_type == '着火点':
            return self._format_ignition_detail(session_id)
        else:
            return self._format_explosion_detail(session_id)
    
    def _format_ignition_detail(self, session_id):
        """格式化着火点实验详细信息"""
        info = []
        
        # 样品名称列表
        sample_names_json = self.experiment.get('sample_names', '')
        if sample_names_json:
            try:
                names = json.loads(sample_names_json)
                info.append("样品列表:")
                for i, name in enumerate(names, 1):
                    info.append(f"  样品{i}: {name}")
                info.append("")
            except (json.JSONDecodeError, KeyError):
                pass
        
        # 着火点检测结果
        detections = self.ignition_db.get_ignition_detections(session_id)
        if detections:
            info.append("着火点检测结果:")
            for detection in detections:
                channel = detection.get('channel', 0)
                temp = detection.get('ignition_temperature', 0)
                timestamp = detection.get('timestamp', '')
                info.append(f"  通道{channel}: {temp}°C (时间: {timestamp})")
        else:
            info.append("着火点检测结果: 无检测记录")
        
        return '\n'.join(info)
    
    def _format_explosion_detail(self, session_id):
        """格式化爆炸性实验详细信息"""
        info = []
        
        # 测试轮次数据
        rounds = self.explosion_db.get_session_test_rounds(session_id)
        if rounds:
            info.append(f"测试轮次数据 (共{len(rounds)}轮):")
            for round_data in rounds:
                round_num = round_data.get('round_number', 0)
                flame_len = round_data.get('flame_length', 0)
                img_path = round_data.get('max_flame_image_path', '')
                info.append(f"  第{round_num}轮: 火焰长度={flame_len}mm")
                if img_path:
                    info.append(f"      图片: {img_path}")
            info.append("")
        
        # 实验结果
        result = self.explosion_db.get_session_result(session_id)
        if result:
            info.append("实验结果:")
            info.append(f"  总轮次: {result.get('total_rounds', 0)}")
            info.append(f"  平均火焰长度: {result.get('avg_flame_length', 0)}mm")
            info.append(f"  爆炸性等级: {result.get('explosion_level', '')}")
            info.append(f"  记录时间: {result.get('timestamp', '')}")
        else:
            info.append("实验结果: 无结果记录")
        
        return '\n'.join(info)

 