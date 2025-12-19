"""
FlameKit 参数化功能演示
展示如何在初始化时传入自定义参数，以及如何查询相机支持的分辨率

运行方式：
    cd examples
    python parameters_demo.py
"""
from flamekit import FlameKit, __version__


def demo_resolution_query():
    """演示1: 查询相机支持的分辨率"""
    print("=" * 60)
    print("演示1: 查询相机支持的分辨率")
    print("=" * 60)
    
    # 使用默认配置初始化
    kit = FlameKit()
    
    try:
        # 初始化相机
        print("\n初始化相机...")
        if not kit.initialize():
            print("❌ 相机初始化失败")
            return None
        print("✅ 相机初始化成功")
        
        # 查询并显示所有支持的分辨率
        print("\n查询支持的分辨率档位:")
        kit.print_available_resolutions()
        
        # 获取分辨率列表（编程方式）
        resolutions = kit.get_available_resolutions()
        if resolutions:
            print(f"\n编程方式获取: 共 {len(resolutions)} 个分辨率档位")
            for idx, width, height in resolutions:
                print(f"  索引 {idx}: {width}x{height} ({width*height/1000000:.2f} MP)")
        
        return kit
        
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()
        return None


def demo_default_init():
    """演示2: 默认初始化（从配置文件读取）"""
    print("\n" + "=" * 60)
    print("演示2: 默认初始化（使用配置文件）")
    print("=" * 60)
    
    # 不传参数，使用配置文件的默认值
    kit = FlameKit()
    
    try:
        if not kit.initialize():
            print("❌ 初始化失败")
            return
        
        print("✅ 使用配置文件默认参数初始化成功")
        print(f"  分辨率索引: {kit.config.get('camera.resolution_index')}")
        print(f"  曝光时间: {kit.config.get('camera.exposure_us')} μs")
        print(f"  黑白模式: {kit.config.get('camera.force_mono')}")
        print(f"  配置文件: {kit.config.config_file}")
        
    finally:
        kit.release()


def demo_custom_resolution():
    """演示3: 自定义分辨率初始化"""
    print("\n" + "=" * 60)
    print("演示3: 自定义分辨率初始化")
    print("=" * 60)
    
    # 指定分辨率索引（例如：0=最高分辨率，1=中等，2=最低）
    resolution_index = 0
    print(f"\n使用自定义分辨率索引: {resolution_index}")
    
    kit = FlameKit(resolution_index=resolution_index)
    
    try:
        if not kit.initialize():
            print("❌ 初始化失败")
            return
        
        print("✅ 自定义分辨率初始化成功")
        print(f"  当前分辨率索引: {kit.config.get('camera.resolution_index')}")
        print("  提示: 参数已自动保存到配置文件")
        
        # 显示实际使用的分辨率
        kit.print_available_resolutions()
        
    finally:
        kit.release()


def demo_custom_exposure():
    """演示4: 自定义曝光时间初始化"""
    print("\n" + "=" * 60)
    print("演示4: 自定义曝光时间初始化")
    print("=" * 60)
    
    # 指定曝光时间（微秒）
    exposure_us = 5000
    print(f"\n使用自定义曝光时间: {exposure_us} μs")
    
    kit = FlameKit(exposure_us=exposure_us)
    
    try:
        if not kit.initialize():
            print("❌ 初始化失败")
            return
        
        print("✅ 自定义曝光时间初始化成功")
        print(f"  当前曝光时间: {kit.config.get('camera.exposure_us')} μs")
        print("  提示: 参数已自动保存到配置文件")
        
        # 预览效果
        print("\n预览相机画面（3秒）...")
        kit.preview(seconds=3.0)
        
    finally:
        kit.release()


def demo_multiple_parameters():
    """演示5: 同时指定多个参数"""
    print("\n" + "=" * 60)
    print("演示5: 同时指定多个参数")
    print("=" * 60)
    
    # 同时指定多个参数
    params = {
        'resolution_index': 1,
        'exposure_us': 3000,
        'force_mono': True,
        'capture_duration': 1.0
    }
    
    print("\n自定义参数:")
    for key, value in params.items():
        print(f"  {key}: {value}")
    
    kit = FlameKit(**params)
    
    try:
        if not kit.initialize():
            print("❌ 初始化失败")
            return
        
        print("\n✅ 多参数初始化成功")
        print("当前配置:")
        print(f"  分辨率索引: {kit.config.get('camera.resolution_index')}")
        print(f"  曝光时间: {kit.config.get('camera.exposure_us')} μs")
        print(f"  黑白模式: {kit.config.get('camera.force_mono')}")
        print(f"  采集时长: {kit.config.get('camera.capture_duration')} s")
        print("\n提示: 所有参数已自动保存到配置文件")
        
        # 测试采集
        print("\n测试采集功能...")
        images, count = kit.capture_one_second()
        print(f"✅ 采集完成: {count} 帧")
        
    finally:
        kit.release()


def demo_camera_capture_direct():
    """演示6: 直接使用 CameraCapture（高级用法）"""
    print("\n" + "=" * 60)
    print("演示6: 直接使用 CameraCapture（高级用法）")
    print("=" * 60)
    
    from flamekit.camera import CameraCapture
    
    # 直接创建 CameraCapture 实例，传入自定义参数
    camera = CameraCapture(
        resolution_index=2,
        exposure_us=2000,
        force_mono=True
    )
    
    try:
        print("\n使用自定义参数直接初始化 CameraCapture...")
        if not camera.initialize():
            print("❌ 初始化失败")
            return
        
        print("✅ CameraCapture 初始化成功")
        
        # 查询分辨率
        resolutions = camera.get_available_resolutions()
        if resolutions:
            print(f"\n相机支持 {len(resolutions)} 个分辨率档位:")
            for idx, width, height in resolutions:
                indicator = " ← 当前使用" if idx == 2 else ""
                print(f"  [{idx}] {width} x {height}{indicator}")
        
        # 捕获单帧测试
        print("\n测试单帧捕获...")
        frame = camera.capture_single_frame()
        if frame is not None:
            print(f"✅ 单帧捕获成功: shape={frame.shape}, dtype={frame.dtype}")
        
    finally:
        camera.release()


def main():
    """主函数"""
    print("=" * 60)
    print(f"FlameKit v{__version__} - 参数化功能演示")
    print("=" * 60)
    print("\n本演示将展示以下功能:")
    print("  1. 查询相机支持的分辨率")
    print("  2. 默认初始化（使用配置文件）")
    print("  3. 自定义分辨率初始化")
    print("  4. 自定义曝光时间初始化")
    print("  5. 同时指定多个参数")
    print("  6. 直接使用 CameraCapture（高级用法）")
    print("=" * 60)
    
    try:
        # 演示1: 查询分辨率（并保持kit实例用于后续演示）
        kit = demo_resolution_query()
        if kit:
            kit.release()
        
        # 演示2: 默认初始化
        input("\n按 Enter 继续演示2...")
        demo_default_init()
        
        # 演示3: 自定义分辨率
        input("\n按 Enter 继续演示3...")
        demo_custom_resolution()
        
        # 演示4: 自定义曝光时间
        input("\n按 Enter 继续演示4...")
        demo_custom_exposure()
        
        # 演示5: 多参数初始化
        input("\n按 Enter 继续演示5...")
        demo_multiple_parameters()
        
        # 演示6: 直接使用 CameraCapture
        input("\n按 Enter 继续演示6...")
        demo_camera_capture_direct()
        
        print("\n" + "=" * 60)
        print("✅ 所有演示完成！")
        print("=" * 60)
        print("\n提示:")
        print("  - 传入的参数会自动保存到配置文件")
        print("  - 不传参数时使用配置文件的默认值")
        print("  - 可以只传入部分参数，其余使用默认值")
        print("  - 参数优先级: 传入参数 > 配置文件")
        
    except KeyboardInterrupt:
        print("\n\n⚠️  用户中断")
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()


