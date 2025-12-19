"""
FlameKit 完整功能演示
展示所有操作流程和高级功能

运行方式：
    cd examples
    python full_demo.py
"""
from flamekit import FlameKit, __version__
import os


def main():
    """完整功能演示"""
    print("=" * 60)
    print(f"FlameKit v{__version__} - 完整功能演示")
    print("=" * 60)
    
    # 可选：使用自定义参数初始化
    # kit = FlameKit(resolution_index=1, exposure_us=4000, force_mono=True)
    kit = FlameKit()
    
    try:
        # 1. 显示版本和配置信息
        print("\n[信息] FlameKit 版本:", __version__)
        print("[信息] 配置文件路径:", kit.config.config_file)
        
        # 2. 初始化相机
        print("\n[步骤1] 初始化相机...")
        if not kit.initialize():
            print("❌ 相机初始化失败")
            return
        print("✅ 相机初始化成功")
        
        # 2.5. 显示支持的分辨率
        print("\n[步骤1.5] 查询相机支持的分辨率...")
        kit.print_available_resolutions()
        
        # 3. 预览（可自定义时长）
        print("\n[步骤2] 相机预览（5秒）...")
        print("提示: 按ESC键可提前退出预览")
        kit.preview(seconds=5.0, window_name="FlameKit Preview")
        
        # 4. 设置标定参数（如果需要）
        print("\n[步骤3] 设置标定参数...")
        current_calibration = kit.config.get('calibration.mm_per_pixel', 0.3152)
        print(f"当前标定参数: {current_calibration} mm/pixel")
        print("提示: 如需修改，使用 kit.set_calibration(0.3152)")
        
        # 5. 采集图像
        print("\n[步骤4] 高速采集1秒图像...")
        custom_temp_dir = "./demo_captures"
        images, count = kit.capture_one_second(temp_dir=custom_temp_dir)
        print(f"✅ 采集完成: {count} 帧")
        print(f"   保存目录: {custom_temp_dir}")
        
        if count == 0:
            print("❌ 未采集到图像")
            return
        
        # 6. 分析火焰（带详细输出）
        print("\n[步骤5] 分析火焰图像...")
        result, max_image = kit.analyze(save_annotated=True)
        
        print("\n分析结果:")
        print("-" * 40)
        if result.get('success'):
            print(f"✅ 检测到火焰")
            print(f"   最大长度: {result['max_length_mm']:.2f} mm")
            print(f"   最大宽度: {result['max_width_mm']:.2f} mm")
            print(f"   火焰面积: {result['area_mm2']:.2f} mm²")
            print(f"   轮廓数量: {result.get('contour_count', 0)}")
            print(f"   对应图片: {os.path.basename(max_image)}")
        else:
            print("⚠️  未检测到有效火焰")
            print("   提示: 可调整 config.json 中的分析参数")
        print("-" * 40)
        
        # 7. 播放结果（不同速度）
        print("\n[步骤6] 播放分析结果...")
        print("提示: 按ESC键可提前退出")
        
        print("  - 正常速度播放...")
        kit.play_analyzed(speed=1.0, window_name="Normal Speed")
        
        print("  - 慢速播放（0.5倍）...")
        kit.play_analyzed(speed=0.5, window_name="Slow Motion")
        
        # 8. 保存结果
        print("\n[步骤7] 保存结果...")
        custom_output_dir = "./demo_results"
        save_path = kit.save_max_result(output_dir=custom_output_dir)
        
        if save_path:
            print(f"✅ 结果已保存")
            print(f"   标注图: {save_path}")
            print(f"   原图: {max_image}")
        
        # 9. 显示配置信息
        print("\n[步骤8] 当前配置信息:")
        print("-" * 40)
        print(f"曝光时间: {kit.config.get('camera.exposure_us')} μs")
        print(f"分辨率索引: {kit.config.get('camera.resolution_index')}")
        print(f"标定参数: {kit.config.get('calibration.mm_per_pixel')} mm/pixel")
        print(f"二值化阈值: {kit.config.get('analysis.binary_threshold')}")
        print(f"最小火焰面积: {kit.config.get('analysis.min_flame_area')} px²")
        print("-" * 40)
        
        print("\n" + "=" * 60)
        print("✅ 完整功能演示完成！")
        print("=" * 60)
        print("\n提示:")
        print("  - 修改 config.json 可调整相机和分析参数")
        print("  - 运行 calibration_demo.py 可进行参数标定")
        print("  - 查看文档了解更多高级用法")
        
    except KeyboardInterrupt:
        print("\n\n⚠️  用户中断")
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print("\n释放相机资源...")
        kit.release()


if __name__ == "__main__":
    main()

