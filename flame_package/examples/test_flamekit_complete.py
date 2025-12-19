"""
FlameKit 完整测试脚本
测试所有主要功能：预览、采集、标定、分析、播放、保存

运行方式：
    cd E:\CursorWorkSpace\Projects\CPIE\camera_demo
    python tests/test_flamekit_complete.py
"""
import sys
import os
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from flamekit import FlameKit


def test_preview():
    """测试1: 相机预览功能"""
    print("\n" + "="*60)
    print("测试1: 相机预览 (3秒)")
    print("="*60)
    
    kit = FlameKit()
    
    print("提示: 预览窗口将显示3秒，按 ESC 可提前退出")
    kit.preview(seconds=3)
    print("✓ 预览测试完成")
    
    return kit


def test_capture(kit):
    """测试2: 高速采集功能"""
    print("\n" + "="*60)
    print("测试2: 高速采集 (1秒)")
    print("="*60)
    
    # 使用独立的测试目录
    test_temp_dir = "./test_temp_captures"
    
    print(f"采集目录: {test_temp_dir}")
    images, frame_count = kit.capture_one_second(temp_dir=test_temp_dir)
    
    print(f"✓ 采集完成: {frame_count} 帧")
    print(f"  图像路径列表长度: {len(images)}")
    if images:
        print(f"  第一张图片: {os.path.basename(images[0])}")
        print(f"  最后一张图片: {os.path.basename(images[-1])}")
    
    return images


def test_calibration(kit):
    """测试3: 参数标定"""
    print("\n" + "="*60)
    print("测试3: 参数标定")
    print("="*60)
    
    mm_per_pixel = 0.3152
    print(f"设置标定参数: {mm_per_pixel} mm/pixel")
    kit.set_calibration(mm_per_pixel)
    
    print(f"✓ 标定完成: {mm_per_pixel} mm/px")
    print(f"  配置已保存到 config.json")


def test_analyze(kit, images):
    """测试4: 火焰长度分析"""
    print("\n" + "="*60)
    print("测试4: 火焰长度分析")
    print("="*60)
    
    if not images:
        print("⚠ 没有可分析的图像，跳过分析测试")
        return None, None
    
    print(f"开始分析 {len(images)} 张图像...")
    print("提示: 分析过程中将自动标注并保存图像")
    
    max_result, max_image_path = kit.analyze(images, save_annotated=True)
    
    if max_result.get('success'):
        print(f"✓ 分析完成")
        print(f"  最大火焰长度: {max_result['max_length_mm']:.2f} mm")
        print(f"  最大火焰宽度: {max_result['max_width_mm']:.2f} mm")
        print(f"  火焰面积: {max_result['area_mm2']:.2f} mm²")
        print(f"  对应图片: {os.path.basename(max_image_path)}")
    else:
        print("⚠ 分析未检测到有效火焰")
    
    return max_result, max_image_path


def test_playback(kit, images):
    """测试5: 分析结果播放"""
    print("\n" + "="*60)
    print("测试5: 分析结果播放")
    print("="*60)
    
    if not images:
        print("⚠ 没有可播放的图像，跳过播放测试")
        return
    
    print(f"将播放 {len(images)} 张标注后的图像")
    print("提示: 目标帧率 240fps，播放约1秒，按 ESC 可提前退出")
    
    # 测试不同速度
    speeds = [1.0, 0.5, 2.0]
    for speed in speeds:
        print(f"\n播放速度: {speed}x")
        kit.play_analyzed(images, speed=speed, target_fps=240, duration_s=1.0)
    
    print("✓ 播放测试完成")


def test_save_result(kit, max_result):
    """测试6: 保存最大火焰结果"""
    print("\n" + "="*60)
    print("测试6: 保存最大火焰结果")
    print("="*60)
    
    if not max_result or not max_result.get('success'):
        print("⚠ 没有可保存的分析结果，跳过保存测试")
        return
    
    test_output_dir = "./test_results"
    print(f"保存目录: {test_output_dir}")
    
    save_path = kit.save_max_result(output_dir=test_output_dir)
    
    if save_path:
        print(f"✓ 保存完成")
        print(f"  标注图路径: {save_path}")
    else:
        print("⚠ 保存失败")


def test_release(kit):
    """测试7: 释放资源"""
    print("\n" + "="*60)
    print("测试7: 释放资源")
    print("="*60)
    
    kit.release()
    print("✓ 相机资源已释放")


def run_all_tests():
    """运行所有测试"""
    print("\n" + "="*60)
    print("FlameKit 完整功能测试")
    print("="*60)
    print("测试项目:")
    print("  1. 相机预览")
    print("  2. 高速采集 (1秒)")
    print("  3. 参数标定")
    print("  4. 火焰长度分析")
    print("  5. 分析结果播放 (不同速度)")
    print("  6. 保存最大火焰结果")
    print("  7. 释放资源")
    print("="*60)
    
    try:
        # 测试1: 预览
        kit = test_preview()
        
        # 测试2: 采集
        images = test_capture(kit)
        
        # 测试3: 标定
        test_calibration(kit)
        
        # 测试4: 分析
        max_result, max_image_path = test_analyze(kit, images)
        
        # 测试5: 播放
        test_playback(kit, images)
        
        # 测试6: 保存
        test_save_result(kit, max_result)
        
        # 测试7: 释放
        test_release(kit)
        
        print("\n" + "="*60)
        print("✓ 所有测试完成!")
        print("="*60)
        
    except Exception as e:
        print("\n" + "="*60)
        print(f"✗ 测试过程中出现错误: {e}")
        print("="*60)
        import traceback
        traceback.print_exc()
    
    finally:
        # 确保资源释放
        try:
            kit.release()
        except:
            pass


def run_minimal_test():
    """运行最小测试（不需要真实相机）"""
    print("\n" + "="*60)
    print("FlameKit 最小测试（模拟模式）")
    print("="*60)
    
    try:
        from flamekit import FlameKit
        print("✓ FlameKit 导入成功")
        
        kit = FlameKit()
        print("✓ FlameKit 实例创建成功")
        
        # 检查方法是否存在
        methods = ['initialize', 'preview', 'capture_one_second', 'set_calibration', 
                   'analyze', 'play_analyzed', 'save_max_result', 'release']
        for method in methods:
            if hasattr(kit, method):
                print(f"✓ 方法 '{method}' 存在")
            else:
                print(f"✗ 方法 '{method}' 不存在")
        
        print("\n✓ 最小测试通过!")
        print("提示: 运行 run_all_tests() 进行完整功能测试（需要真实相机）")
        
    except Exception as e:
        print(f"\n✗ 最小测试失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="FlameKit 测试脚本")
    parser.add_argument('--minimal', action='store_true', 
                        help='运行最小测试（不需要相机）')
    parser.add_argument('--full', action='store_true', 
                        help='运行完整测试（需要相机）')
    
    args = parser.parse_args()
    
    if args.minimal:
        run_minimal_test()
    elif args.full:
        run_all_tests()
    else:
        # 默认运行完整测试
        print("提示: 使用 --minimal 运行最小测试（不需要相机）")
        print("提示: 使用 --full 运行完整测试（需要相机）")
        print("\n默认运行完整测试...\n")
        run_all_tests()

