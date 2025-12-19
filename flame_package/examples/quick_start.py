"""
FlameKit 快速开始示例
最简单的使用方式，适合快速验证

运行方式：
    cd examples
    python quick_start.py
"""
from flamekit import FlameKit, __version__


def main():
    """快速开始示例"""
    print("=" * 60)
    print(f"FlameKit v{__version__} - 快速开始")
    print("=" * 60)
    
    # 创建 FlameKit 实例
    # 可选：传入自定义参数，例如 kit = FlameKit(resolution_index=0, exposure_us=5000)
    kit = FlameKit()
    
    try:
        # 1. 初始化相机
        print("\n[1/7] 初始化相机...")
        if not kit.initialize():
            print("❌ 相机初始化失败，请检查连接和驱动")
            return
        print("✅ 相机初始化成功")
        
        # 1.5. 查看支持的分辨率（可选）
        print("\n[1.5/7] 查看相机支持的分辨率...")
        kit.print_available_resolutions()
        
        # 2. 预览（可选，3秒）
        print("\n[2/7] 相机预览（3秒，按ESC提前退出）...")
        kit.preview(seconds=3.0)
        
        # 3. 采集1秒图像
        print("\n[3/7] 高速采集1秒图像...")
        images, count = kit.capture_one_second()
        print(f"✅ 采集完成: {count} 帧")
        
        if count == 0:
            print("❌ 未采集到图像")
            return
        
        # 4. 分析火焰
        print("\n[4/7] 分析火焰...")
        result, max_image = kit.analyze()
        
        if result.get('success'):
            print(f"✅ 分析成功")
            print(f"   最大火焰长度: {result['max_length_mm']:.2f} mm")
            print(f"   最大火焰宽度: {result['max_width_mm']:.2f} mm")
            print(f"   火焰面积: {result['area_mm2']:.2f} mm²")
            print(f"   对应图片: {max_image}")
        else:
            print("⚠️  未检测到有效火焰")
        
        # 5. 播放结果（可选）
        print("\n[5/7] 播放分析结果（按ESC提前退出）...")
        kit.play_analyzed(speed=1.0)
        
        # 6. 保存结果
        print("\n[6/7] 保存结果...")
        save_path = kit.save_max_result()
        if save_path:
            print(f"✅ 结果已保存: {save_path}")
        
        print("\n" + "=" * 60)
        print("✅ 快速开始示例完成！")
        print("=" * 60)
        
    except KeyboardInterrupt:
        print("\n\n⚠️  用户中断")
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # 释放资源
        print("\n释放相机资源...")
        kit.release()


if __name__ == "__main__":
    main()

