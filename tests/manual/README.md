# 手工诊断脚本

这些脚本需要人员操作 Qt 窗口、已有实验数据，或会向数据库写入样例数据，不属于自动验收。默认 `python -m pytest` 只运行真正的自动测试，不收集此目录。

先安装 `requirements-dev.txt` 与本地 Modbus 包。在**独立实验数据副本**对应的源码目录运行，例如：

```bash
python tests/manual/test_new_experiment_dialogs.py
python tests/manual/test_tangent_analysis_dialog.py --help
python tests/manual/test_tangent_analysis_from_db.py --help
python tests/manual/test_tangent_direct.py --help
python tests/manual/test_ignition_temperature_plot.py
python tests/manual/test_tangent_method_visualization.py
```

切线、温度曲线脚本读取源码项目 `data/ignition_experiment.db`；请先把所需实验库复制到独立源码副本，保留原文件。`migrate_database.py`、`test_database_system.py`、`test_insert_data.py` 会迁移/新增数据，只可针对可丢弃的数据库副本运行，不能作为自动化通过证据。
