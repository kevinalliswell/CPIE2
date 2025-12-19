"""
FlameKit 参数标定工具
用于计算像素到毫米的转换参数

使用方法：
1. 在相机视野中放置已知长度的参考物（如标尺）
2. 运行此脚本
3. 在预览窗口中点击参考物的起点和终点
4. 输入参考物的实际长度（毫米）
5. 标定参数会自动保存

运行方式：
    cd examples
    python calibration_demo.py
"""
import cv2
import numpy as np
from flamekit import FlameKit, __version__


class CalibrationTool:
    """标定工具类"""
    
    def __init__(self, resolution_index=None):
        # 可选：指定分辨率进行标定
        if resolution_index is not None:
            self.kit = FlameKit(resolution_index=resolution_index)
        else:
            self.kit = FlameKit()
        self.points = []
        self.current_image = None
        self.window_name = "Calibration - Click two points"
        self.actual_length_mm = None
        
    def mouse_callback(self, event, x, y, flags, param):
        """鼠标回调函数"""
        if event == cv2.EVENT_LBUTTONDOWN:
            if len(self.points) < 2:
                self.points.append((x, y))
                print(f"点 {len(self.points)}: ({x}, {y})")
                
                # 在图像上标记点
                cv2.circle(self.current_image, (x, y), 5, (0, 255, 0), -1)
                if len(self.points) == 2:
                    # 绘制连线
                    cv2.line(self.current_image, self.points[0], self.points[1], (0, 255, 0), 2)
                    pixel_distance = np.sqrt(
                        (self.points[1][0] - self.points[0][0]) ** 2 +
                        (self.points[1][1] - self.points[0][1]) ** 2
                    )
                    print(f"像素距离: {pixel_distance:.2f} px")
                cv2.imshow(self.window_name, self.current_image)
    
    def run(self):
        """运行标定工具"""
        print("=" * 60)
        print(f"FlameKit v{__version__} - 参数标定工具")
        print("=" * 60)
        
        try:
            # 1. 初始化相机
            print("\n[1/5] 初始化相机...")
            if not self.kit.initialize():
                print("❌ 相机初始化失败")
                return
            print("✅ 相机初始化成功")
            
            # 1.5. 显示分辨率信息
            print("\n[1.5/5] 相机分辨率信息:")
            self.kit.print_available_resolutions()
            print(f"当前使用分辨率索引: {self.kit.config.get('camera.resolution_index')}")
            
            # 2. 捕获一帧图像用于标定
            print("\n[2/5] 捕获标定图像...")
            print("提示: 请确保参考物在相机视野中")
            frame = self.kit.camera.capture_single_frame()
            if frame is None:
                print("❌ 无法捕获图像")
                return
            
            self.current_image = frame.copy()
            
            # 3. 设置鼠标回调
            cv2.namedWindow(self.window_name, cv2.WINDOW_NORMAL)
            cv2.setMouseCallback(self.window_name, self.mouse_callback)
            
            print("\n[3/5] 标定操作:")
            print("-" * 40)
            print("1. 在窗口中点击参考物的起点")
            print("2. 点击参考物的终点")
            print("3. 按任意键继续")
            print("-" * 40)
            
            # 显示图像并等待用户点击
            cv2.imshow(self.window_name, self.current_image)
            cv2.waitKey(0)
            
            if len(self.points) < 2:
                print("❌ 未选择足够的点，标定取消")
                return
            
            # 4. 输入实际长度
            print("\n[4/5] 输入参考物实际长度:")
            print("-" * 40)
            try:
                self.actual_length_mm = float(input("请输入参考物的实际长度（毫米）: "))
            except ValueError:
                print("❌ 输入无效，标定取消")
                return
            
            if self.actual_length_mm <= 0:
                print("❌ 长度必须大于0，标定取消")
                return
            
            # 计算标定参数
            pixel_distance = np.sqrt(
                (self.points[1][0] - self.points[0][0]) ** 2 +
                (self.points[1][1] - self.points[0][1]) ** 2
            )
            
            if pixel_distance == 0:
                print("❌ 两点距离为0，标定取消")
                return
            
            mm_per_pixel = self.actual_length_mm / pixel_distance
            
            # 保存标定参数
            self.kit.set_calibration(mm_per_pixel)
            
            # 显示结果
            print("\n" + "=" * 60)
            print("✅ 标定完成！")
            print("=" * 60)
            print(f"像素距离: {pixel_distance:.2f} px")
            print(f"实际长度: {self.actual_length_mm:.4f} mm")
            print(f"标定参数: {mm_per_pixel:.6f} mm/pixel")
            print(f"配置文件: {self.kit.config.config_file}")
            print("=" * 60)
            
            # 显示标定结果图像
            result_image = self.current_image.copy()
            cv2.line(result_image, self.points[0], self.points[1], (0, 255, 0), 2)
            cv2.circle(result_image, self.points[0], 5, (0, 255, 0), -1)
            cv2.circle(result_image, self.points[1], 5, (0, 255, 0), -1)
            
            mid_x = (self.points[0][0] + self.points[1][0]) // 2
            mid_y = (self.points[0][1] + self.points[1][1]) // 2
            text = f"{self.actual_length_mm:.2f}mm ({pixel_distance:.1f}px)"
            cv2.putText(result_image, text, (mid_x - 100, mid_y - 10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            
            cv2.imshow("Calibration Result", result_image)
            print("\n按任意键关闭窗口...")
            cv2.waitKey(0)
            cv2.destroyAllWindows()
            
        except KeyboardInterrupt:
            print("\n\n⚠️  用户中断")
        except Exception as e:
            print(f"\n❌ 错误: {e}")
            import traceback
            traceback.print_exc()
        finally:
            print("\n释放相机资源...")
            self.kit.release()


def main():
    """主函数"""
    import sys
    
    # 支持命令行参数指定分辨率
    resolution_index = None
    if len(sys.argv) > 1:
        try:
            resolution_index = int(sys.argv[1])
            print(f"使用命令行指定的分辨率索引: {resolution_index}")
        except ValueError:
            print(f"警告: 无效的分辨率索引 '{sys.argv[1]}'，使用默认值")
    
    tool = CalibrationTool(resolution_index=resolution_index)
    tool.run()


if __name__ == "__main__":
    main()

