"""
FlameKit 单元测试
测试各个模块的独立功能

运行方式：
    cd E:\CursorWorkSpace\Projects\CPIE\camera_demo
    python tests/test_flamekit_unit.py
"""
import sys
import os
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))


def test_imports():
    """测试模块导入"""
    print("\n" + "="*60)
    print("测试: 模块导入")
    print("="*60)
    
    try:
        from flamekit import FlameKit
        print("✓ from flamekit import FlameKit")
    except ImportError as e:
        print(f"✗ FlameKit 导入失败: {e}")
        return False
    
    try:
        from flamekit.config import ConfigManager, get_config
        print("✓ from flamekit.config import ConfigManager, get_config")
    except ImportError as e:
        print(f"✗ config 模块导入失败: {e}")
        return False
    
    try:
        from flamekit.camera import CameraCapture
        print("✓ from flamekit.camera import CameraCapture")
    except ImportError as e:
        print(f"✗ camera 模块导入失败: {e}")
        return False
    
    try:
        from flamekit.analyzer import FlameAnalyzer
        print("✓ from flamekit.analyzer import FlameAnalyzer")
    except ImportError as e:
        print(f"✗ analyzer 模块导入失败: {e}")
        return False
    
    print("\n✓ 所有模块导入成功")
    return True


def test_config_manager():
    """测试配置管理器"""
    print("\n" + "="*60)
    print("测试: 配置管理器")
    print("="*60)
    
    try:
        from flamekit.config import ConfigManager
        
        # 创建临时配置
        test_config_path = "./test_config.json"
        config = ConfigManager(config_file=test_config_path)
        print("✓ ConfigManager 实例化成功")
        
        # 测试获取配置
        exposure = config.get('camera.exposure_us', 4000)
        print(f"✓ 获取配置值: camera.exposure_us = {exposure}")
        
        # 测试设置配置
        config.set('test.value', 123, save=False)
        value = config.get('test.value')
        assert value == 123, f"配置设置失败: 期望 123, 实际 {value}"
        print(f"✓ 设置配置值: test.value = {value}")
        
        # 测试保存配置
        config.save_config()
        print(f"✓ 配置保存成功: {test_config_path}")
        
        # 清理
        if os.path.exists(test_config_path):
            os.remove(test_config_path)
            print(f"✓ 清理测试文件: {test_config_path}")
        
        print("\n✓ 配置管理器测试通过")
        return True
        
    except Exception as e:
        print(f"\n✗ 配置管理器测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_flamekit_instance():
    """测试 FlameKit 实例创建"""
    print("\n" + "="*60)
    print("测试: FlameKit 实例")
    print("="*60)
    
    try:
        from flamekit import FlameKit
        
        # 测试默认初始化
        kit = FlameKit()
        print("✓ FlameKit 默认实例创建成功")
        
        # 测试参数化初始化
        kit_custom = FlameKit(resolution_index=0, exposure_us=3000, force_mono=True)
        print("✓ FlameKit 参数化实例创建成功")
        
        # 检查属性
        assert hasattr(kit, 'config'), "缺少 config 属性"
        print("✓ kit.config 属性存在")
        
        assert hasattr(kit, 'camera'), "缺少 camera 属性"
        print("✓ kit.camera 属性存在")
        
        assert hasattr(kit, 'analyzer'), "缺少 analyzer 属性"
        print("✓ kit.analyzer 属性存在")
        
        # 检查方法
        methods = [
            'initialize', 'preview', 'capture_one_second', 
            'set_calibration', 'analyze', 'play_analyzed', 
            'save_max_result', 'release',
            'get_available_resolutions', 'print_available_resolutions'
        ]
        
        for method_name in methods:
            assert hasattr(kit, method_name), f"缺少方法: {method_name}"
            method = getattr(kit, method_name)
            assert callable(method), f"方法 {method_name} 不可调用"
            print(f"✓ kit.{method_name}() 方法存在且可调用")
        
        print("\n✓ FlameKit 实例测试通过")
        return True
        
    except Exception as e:
        print(f"\n✗ FlameKit 实例测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_analyzer_binarize():
    """测试分析器的二值化功能（使用测试图像）"""
    print("\n" + "="*60)
    print("测试: 图像分析器（二值化）")
    print("="*60)
    
    try:
        import numpy as np
        import cv2
        from flamekit.analyzer import FlameAnalyzer
        
        analyzer = FlameAnalyzer()
        print("✓ FlameAnalyzer 实例创建成功")
        
        # 创建测试图像（256x256，中心有一个亮斑）
        test_image = np.zeros((256, 256), dtype=np.uint8)
        cv2.circle(test_image, (128, 128), 50, 255, -1)
        print("✓ 创建测试图像: 256x256，中心亮斑")
        
        # 测试二值化
        binary = analyzer._binarize(test_image)
        print(f"✓ 二值化完成: shape={binary.shape}, dtype={binary.dtype}")
        
        # 检查二值化结果
        assert binary.shape == test_image.shape, "二值化后形状不匹配"
        assert binary.dtype == np.uint8, "二值化后数据类型不正确"
        assert np.max(binary) <= 255, "二值化后最大值超出范围"
        assert np.min(binary) >= 0, "二值化后最小值超出范围"
        print("✓ 二值化结果验证通过")
        
        print("\n✓ 图像分析器测试通过")
        return True
        
    except Exception as e:
        print(f"\n✗ 图像分析器测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def run_all_unit_tests():
    """运行所有单元测试"""
    print("\n" + "="*60)
    print("FlameKit 单元测试套件")
    print("="*60)
    
    tests = [
        ("模块导入", test_imports),
        ("配置管理器", test_config_manager),
        ("FlameKit实例", test_flamekit_instance),
        ("图像分析器", test_analyzer_binarize),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"\n✗ 测试 '{test_name}' 异常: {e}")
            results.append((test_name, False))
    
    # 汇总结果
    print("\n" + "="*60)
    print("测试结果汇总")
    print("="*60)
    
    passed = 0
    failed = 0
    for test_name, result in results:
        status = "✓ 通过" if result else "✗ 失败"
        print(f"{status}: {test_name}")
        if result:
            passed += 1
        else:
            failed += 1
    
    print("\n" + "="*60)
    print(f"总计: {passed} 通过, {failed} 失败")
    print("="*60)
    
    return failed == 0


if __name__ == "__main__":
    success = run_all_unit_tests()
    sys.exit(0 if success else 1)

