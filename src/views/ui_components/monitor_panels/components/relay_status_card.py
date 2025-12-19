"""
继电器状态卡片
显示4路继电器状态（导通/关闭）
"""

from PySide6.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QLabel, QGridLayout
from PySide6.QtCore import Qt


class RelayStatusCard(QFrame):
    """
    继电器状态卡片
    显示4路继电器状态
    """
    
    # 继电器名称映射（中文）
    RELAY_NAMES = {
        '1': '喷吹阀',
        '2': '吹扫阀',
        '3': '除尘器',
        '4': '预留'
    }
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.setObjectName("relayStatusCard")
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setStyleSheet(
            "QFrame#relayStatusCard { "
            "background-color: #ffffff; "
            "border: 3px solid #e1e8ed; "
            "border-radius: 10px; "
            "padding: 15px; "
            "}"
        )
        
        # 主布局
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        
        # 标题行
        title_layout = QHBoxLayout()
        title_layout.setSpacing(8)
        
        icon_label = QLabel("⚡")
        icon_label.setStyleSheet("font-size: 32px;")
        
        title_label = QLabel("继电器状态")
        title_label.setStyleSheet("font-weight: bold; color: #666; font-size: 22px;")
        
        title_layout.addWidget(icon_label)
        title_layout.addWidget(title_label)
        title_layout.addStretch()
        
        layout.addLayout(title_layout)
        
        # 继电器状态网格（2x2布局）
        relay_grid = QGridLayout()
        relay_grid.setSpacing(10)
        
        self.relay_labels = {}
        
        # 创建4路继电器状态显示
        relay_ids = ['1', '2', '3', '4']
        for idx, relay_id in enumerate(relay_ids):
            row = idx // 2
            col = idx % 2
            
            # 继电器名称
            name_label = QLabel(self.RELAY_NAMES.get(relay_id, f'CH{relay_id}'))
            name_label.setStyleSheet("font-size: 18px; color: #34495e; font-weight: bold;")
            relay_grid.addWidget(name_label, row * 2, col)
            
            # 继电器状态
            status_label = QLabel("关闭")
            status_label.setObjectName(f"relay_status_{relay_id}")
            status_label.setStyleSheet(
                "padding: 2px 6px; background-color: #95a5a6; color: white; "
                "border-radius: 6px; font-weight: bold; font-size: 16px; "
                "min-height: 10px; max-height: 40px;"
            )
            status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            relay_grid.addWidget(status_label, row * 2 + 1, col)
            
            self.relay_labels[relay_id] = status_label
        
        layout.addLayout(relay_grid)
        layout.addStretch()
    
    def update_relay_states(self, relay_states: dict):
        """
        更新继电器状态
        Args:
            relay_states: 字典格式 {relay_id: state}，如 {'1': True, '2': False}
        """
        for relay_id, label in self.relay_labels.items():
            state = relay_states.get(relay_id, False)
            
            if state:
                label.setText("导通")
                label.setStyleSheet(
                    "padding: 2px 6px; background-color: #4caf50; color: white; "
                    "border-radius: 6px; font-weight: bold; font-size: 16px; "
                    "min-height: 40px; max-height: 40px;"
                )
            else:
                label.setText("关闭")
                label.setStyleSheet(
                    "padding: 2px 6px; background-color: #95a5a6; color: white; "
                    "border-radius: 6px; font-weight: bold; font-size: 16px; "
                    "min-height: 10px; max-height: 40px;"
                )
    
    def reset(self):
        """重置所有继电器状态为关闭"""
        for label in self.relay_labels.values():
            label.setText("关闭")
            label.setStyleSheet(
                "padding: 8px 12px; background-color: #95a5a6; color: white; "
                "border-radius: 6px; font-weight: bold; font-size: 20px; "
                "min-height: 40px; max-height: 40px;"
            )

