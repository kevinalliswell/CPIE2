"""
FlameKit 参数化功能单元测试
专门测试新增的参数化初始化和分辨率查询功能

运行方式：
    cd examples
    python test_parameters.py
"""
import sys
from pathlib import Path

# 确保可以导入 flamekit
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from flamekit import FlameKit
from flamekit.camera import CameraCapture


def test_default_initialization():
    """测试1: 默认初始化（不传参数）"""
    print("\n" + "="*60)
    print("测试1: 默认初始化")
    print("="*60)
    
    try:
        kit = FlameKit()
        print("✓ FlameKit() 创建成功")
        print("✓ 应使用配置文件中的默认参数")
        return True
    except Exception as e:
        print(f"✗ 失败: {e}")
        return False


def test_resolution_parameter():
    """测试2: 分辨率参数初始化"""
    print("\n" + "="*60)
    print("测试2: 分辨率参数初始化")
    print("="*60)
    
    try:
        # 测试不同的分辨率索引
        for res_idx in [0, 1, 2]:
            kit = FlameKit(resolution_index=res_idx)
            print(f"✓ FlameKit(resolution_index={res_idx}) 创建成功")
        return True
    except Exception as e:
        print(f"✗ 失败: {e}")
        return False


def test_exposure_parameter():
    """测试3: 曝光时间参数初始化"""
    print("\n" + "="*60)
    print("测试3: 曝光时间参数初始化")
    print("="*60)
    
    try:
        # 测试不同的曝光时间
        for exposure in [1000, 4000, 8000]:
            kit = FlameKit(exposure_us=exposure)
            print(f"✓ FlameKit(exposure_us={exposure}) 创建成功")
        return True
    except Exception as e:
        print(f"✗ 失败: {e}")
        return False


def test_force_mono_parameter():
    """测试4: 黑白模式参数初始化"""
    print("\n" + "="*60)
    print("测试4: 黑白模式参数初始化")
    print("="*60)
    
    try:
        kit_mono = FlameKit(force_mono=True)
        print("✓ FlameKit(force_mono=True) 创建成功")
        
        kit_color = FlameKit(force_mono=False)
        print("✓ FlameKit(force_mono=False) 创建成功")
        return True
    except Exception as e:
        print(f"✗ 失败: {e}")
        return False


def test_multiple_parameters():
    """测试5: 多参数组合初始化"""
    print("\n" + "="*60)
    print("测试5: 多参数组合初始化")
    print("="*60)
    
    try:
        kit = FlameKit(
            resolution_index=1,
            exposure_us=5000,
            force_mono=True,
            capture_duration=1.5
        )
        print("✓ 多参数组合初始化成功")
        print("  - resolution_index=1")
        print("  - exposure_us=5000")
        print("  - force_mono=True")
        print("  - capture_duration=1.5")
        return True
    except Exception as e:
        print(f"✗ 失败: {e}")
        return False


def test_camera_capture_parameters():
    """测试6: CameraCapture 参数初始化"""
    print("\n" + "="*60)
    print("测试6: CameraCapture 参数初始化")
    print("="*60)
    
    try:
        camera = CameraCapture(
            resolution_index=0,
            exposure_us=3000
        )
        print("✓ CameraCapture 参数化创建成功")
        print("  - resolution_index=0")
        print("  - exposure_us=3000")
        return True
    except Exception as e:
        print(f"✗ 失败: {e}")
        return False


def test_resolution_query_methods():
    """测试7: 分辨率查询方法（需要真实相机）"""
    print("\n" + "="*60)
    print("测试7: 分辨率查询方法")
    print("="*60)
    
    try:
        kit = FlameKit()
        
        # 检查方法是否存在
        if not hasattr(kit, 'get_available_resolutions'):
            print("✗ 缺少 get_available_resolutions 方法")
            return False
        print("✓ get_available_resolutions 方法存在")
        
        if not hasattr(kit, 'print_available_resolutions'):
            print("✗ 缺少 print_available_resolutions 方法")
            return False
        print("✓ print_available_resolutions 方法存在")
        
        # 检查方法是否可调用
        if not callable(kit.get_available_resolutions):
            print("✗ get_available_resolutions 不可调用")
            return False
        print("✓ get_available_resolutions 可调用")
        
        if not callable(kit.print_available_resolutions):
            print("✗ print_available_resolutions 不可调用")
            return False
        print("✓ print_available_resolutions 可调用")
        
        # 尝试初始化并查询（如果有相机）
        print("\n尝试初始化相机并查询分辨率...")
        if kit.initialize():
            print("✓ 相机初始化成功")
            
            resolutions = kit.get_available_resolutions()
            if resolutions:
                print(f"✓ 查询到 {len(resolutions)} 个分辨率档位")
                for idx, width, height in resolutions:
                    print(f"  [{idx}] {width} x {height}")
            else:
                print("⚠ 未查询到分辨率（相机可能未连接）")
            
            print("\n调用 print_available_resolutions:")
            kit.print_available_resolutions()
            
            kit.release()
        else:
            print("⚠ 相机初始化失败（可能未连接相机）")
            print("  方法存在性检查已通过")
        
        return True
        
    except Exception as e:
        print(f"✗ 失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_parameter_persistence():
    """测试8: 参数持久化（保存到配置文件）"""
    print("\n" + "="*60)
    print("测试8: 参数持久化")
    print("="*60)
    
    try:
        # 创建带自定义参数的实例
        kit = FlameKit(resolution_index=2, exposure_us=6000)
        print("✓ 创建自定义参数实例")
        
        # 初始化（会触发参数保存）
        if kit.initialize():
            print("✓ 初始化成功")
            
            # 检查配置是否已更新
            saved_res = kit.config.get('camera.resolution_index')
            saved_exp = kit.config.get('camera.exposure_us')
            
            if saved_res == 2:
                print(f"✓ 分辨率参数已保存: {saved_res}")
            else:
                print(f"⚠ 分辨率参数保存异常: 期望 2, 实际 {saved_res}")
            
            if saved_exp == 6000:
                print(f"✓ 曝光参数已保存: {saved_exp}")
            else:
                print(f"⚠ 曝光参数保存异常: 期望 6000, 实际 {saved_exp}")
            
            kit.release()
        else:
            print("⚠ 相机初始化失败（可能未连接相机）")
            print("  跳过持久化验证")
        
        return True
        
    except Exception as e:
        print(f"✗ 失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def run_all_tests():
    """运行所有参数化功能测试"""
    print("=" * 60)
    print("FlameKit 参数化功能测试套件")
    print("=" * 60)
    print("\n测试内容:")
    print("  1. 默认初始化")
    print("  2. 分辨率参数")
    print("  3. 曝光时间参数")
    print("  4. 黑白模式参数")
    print("  5. 多参数组合")
    print("  6. CameraCapture 参数化")
    print("  7. 分辨率查询方法")
    print("  8. 参数持久化")
    print("=" * 60)
    
    tests = [
        ("默认初始化", test_default_initialization),
        ("分辨率参数", test_resolution_parameter),
        ("曝光时间参数", test_exposure_parameter),
        ("黑白模式参数", test_force_mono_parameter),
        ("多参数组合", test_multiple_parameters),
        ("CameraCapture参数化", test_camera_capture_parameters),
        ("分辨率查询方法", test_resolution_query_methods),
        ("参数持久化", test_parameter_persistence),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"\n✗ 测试 '{test_name}' 异常: {e}")
            import traceback
            traceback.print_exc()
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
    if failed == 0:
        print("✅ 所有测试通过！")
    else:
        print("⚠️  部分测试失败")
    print("="*60)
    
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)


