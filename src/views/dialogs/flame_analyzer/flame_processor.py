#!/usr/bin/env python
# -*- encoding: utf-8 -*-
"""
火焰图像处理业务逻辑模块
Flame Image Processing Module
"""
import os
import logging
from pathlib import Path
from typing import List, Tuple, Dict, Optional
import cv2
import numpy as np
from dataclasses import dataclass

from .config_manager import FlameAnalyzerConfig


@dataclass
class FlameAnalysisResult:
    """火焰分析结果数据类"""
    filename: str
    flame_size_mm: int
    flame_region: Tuple[int, int, int, int]  # (x, y, w, h)
    success: bool = True
    error_message: str = ""


@dataclass
class FlameStatistics:
    """火焰统计数据类"""
    max_flame_size: int
    min_flame_size: int
    average_flame_size: float
    max_flame_index: int
    max_flame_file: str
    total_images: int
    failed_images: int


class FlameImageProcessor:
    """火焰图像处理器 - 独立的业务逻辑类"""
    
    def __init__(self, config: FlameAnalyzerConfig):
        """
        初始化处理器
        
        Args:
            config: 配置对象
        """
        self.config = config
        self.logger = self._setup_logger()
    
    def _setup_logger(self) -> logging.Logger:
        """设置日志"""
        logger = logging.getLogger('FlameImageProcessor')
        
        if self.config.logging_enabled:
            logger.setLevel(getattr(logging, self.config.log_level))
            
            # 确保日志目录存在
            log_file = self.config.log_file
            log_file.parent.mkdir(parents=True, exist_ok=True)
            
            # 文件处理器
            fh = logging.FileHandler(log_file, encoding='utf-8')
            fh.setLevel(logging.DEBUG)
            
            # 控制台处理器
            ch = logging.StreamHandler()
            ch.setLevel(logging.INFO)
            
            # 格式化
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            fh.setFormatter(formatter)
            ch.setFormatter(formatter)
            
            logger.addHandler(fh)
            logger.addHandler(ch)
        
        return logger
    
    def get_image_files(self, folder_path: str) -> List[str]:
        """
        获取文件夹中所有支持的图像文件
        
        Args:
            folder_path: 文件夹路径
            
        Returns:
            图像文件名列表
        """
        if not os.path.exists(folder_path):
            self.logger.error(f"文件夹不存在: {folder_path}")
            return []
        
        image_files = [
            f for f in os.listdir(folder_path)
            if f.lower().endswith(self.config.image_formats)
        ]
        
        self.logger.info(f"在 {folder_path} 中找到 {len(image_files)} 个图像文件")
        return sorted(image_files)
    
    def preprocess_image(self, img: np.ndarray) -> np.ndarray:
        """
        预处理图像以便于分析
        
        Args:
            img: OpenCV图像
            
        Returns:
            二值化图像
        """
        # 转换为灰度图像
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # 应用阈值获取火焰区域
        _, binary = cv2.threshold(
            gray, 
            self.config.flame_threshold, 
            255, 
            cv2.THRESH_BINARY
        )
        
        return binary
    
    def find_flame_region(self, binary_img: np.ndarray) -> Tuple[int, Tuple[int, int, int, int]]:
        """
        查找火焰区域
        
        Args:
            binary_img: 二值化图像
            
        Returns:
            (火焰尺寸(mm), 火焰区域(x,y,w,h))
        """
        # 查找轮廓
        contours, _ = cv2.findContours(
            binary_img, 
            cv2.RETR_EXTERNAL, 
            cv2.CHAIN_APPROX_SIMPLE
        )
        
        if len(contours) == 0:
            return 0, (0, 0, 0, 0)
        
        # 找到最大轮廓
        max_contour = max(contours, key=cv2.contourArea)
        x, y, w, h = cv2.boundingRect(max_contour)
        
        # 计算实际火焰长度(毫米)
        flame_size_mm = int(w * self.config.mm_per_pixel)
        
        self.logger.debug(f"检测到火焰: 宽度={w}px, 实际尺寸={flame_size_mm}mm")
        
        return flame_size_mm, (x, y, w, h)
    
    def detect_flame(self, img: np.ndarray) -> Tuple[int, Tuple[int, int, int, int]]:
        """
        检测火焰并返回火焰尺寸和区域
        
        Args:
            img: OpenCV图像
            
        Returns:
            (火焰尺寸(mm), 火焰区域(x,y,w,h))
        """
        binary_img = self.preprocess_image(img)
        flame_size, flame_region = self.find_flame_region(binary_img)
        return flame_size, flame_region
    
    def annotate_image(self, img: np.ndarray, flame_region: Tuple[int, int, int, int], 
                      flame_size: int) -> np.ndarray:
        """
        在图像上标注火焰区域
        
        Args:
            img: 原始图像
            flame_region: 火焰区域 (x, y, w, h)
            flame_size: 火焰尺寸(mm)
            
        Returns:
            标注后的图像
        """
        x, y, w, h = flame_region
        annotated = img.copy()
        
        # 绘制边界框
        cv2.rectangle(
            annotated, 
            (x, y), 
            (x + w, y + h), 
            self.config.bbox_color, 
            self.config.bbox_thickness
        )
        
        # 添加文字标签
        label = f"Fire Width: {flame_size}mm"
        cv2.putText(
            annotated, 
            label, 
            (x, y - 10), 
            self.config.cv_font, 
            self.config.font_scale, 
            self.config.text_color, 
            self.config.text_thickness
        )
        
        return annotated
    
    def process_single_image(self, image_path: str) -> FlameAnalysisResult:
        """
        处理单张图像
        
        Args:
            image_path: 图像路径
            
        Returns:
            分析结果
        """
        filename = os.path.basename(image_path)
        
        try:
            # 读取图像
            img = cv2.imread(image_path)
            if img is None:
                raise ValueError(f"无法读取图像: {image_path}")
            
            # 检测火焰
            flame_size, flame_region = self.detect_flame(img)
            
            return FlameAnalysisResult(
                filename=filename,
                flame_size_mm=flame_size,
                flame_region=flame_region,
                success=True
            )
        
        except Exception as e:
            self.logger.error(f"处理图像 {filename} 失败: {e}")
            return FlameAnalysisResult(
                filename=filename,
                flame_size_mm=0,
                flame_region=(0, 0, 0, 0),
                success=False,
                error_message=str(e)
            )
    
    def process_and_save_image(self, input_path: str, output_path: str) -> FlameAnalysisResult:
        """
        处理图像并保存标注后的结果
        
        Args:
            input_path: 输入图像路径
            output_path: 输出图像路径
            
        Returns:
            分析结果
        """
        result = self.process_single_image(input_path)
        
        if result.success:
            try:
                # 读取原图
                img = cv2.imread(input_path)
                
                # 标注图像
                annotated = self.annotate_image(img, result.flame_region, result.flame_size_mm)
                
                # 保存
                cv2.imwrite(output_path, annotated)
                self.logger.info(f"已保存标注图像: {output_path}")
                
            except Exception as e:
                self.logger.error(f"保存标注图像失败: {e}")
                result.success = False
                result.error_message = f"保存失败: {e}"
        
        return result
    
    def calculate_statistics(self, results: List[FlameAnalysisResult]) -> Optional[FlameStatistics]:
        """
        计算统计数据
        
        Args:
            results: 分析结果列表
            
        Returns:
            统计数据
        """
        # 过滤出成功的结果
        successful_results = [r for r in results if r.success]
        
        if not successful_results:
            self.logger.warning("没有成功的分析结果")
            return None
        
        # 提取火焰尺寸
        flame_sizes = [r.flame_size_mm for r in successful_results]
        
        max_size = max(flame_sizes)
        min_size = min(flame_sizes)
        avg_size = round(sum(flame_sizes) / len(flame_sizes), 1)
        
        max_index = flame_sizes.index(max_size)
        max_file = successful_results[max_index].filename
        
        failed_count = len([r for r in results if not r.success])
        
        stats = FlameStatistics(
            max_flame_size=max_size,
            min_flame_size=min_size,
            average_flame_size=avg_size,
            max_flame_index=max_index,
            max_flame_file=max_file,
            total_images=len(results),
            failed_images=failed_count
        )
        
        self.logger.info(f"统计完成: 最大={max_size}mm, 最小={min_size}mm, 平均={avg_size}mm")
        
        return stats
    
    def batch_process_images(self, input_folder: str, output_folder: str) -> List[FlameAnalysisResult]:
        """
        批量处理图像(流式处理,节省内存)
        
        Args:
            input_folder: 输入文件夹
            output_folder: 输出文件夹
            
        Returns:
            分析结果列表
        """
        # 确保输出文件夹存在
        os.makedirs(output_folder, exist_ok=True)
        
        # 获取所有图像文件
        image_files = self.get_image_files(input_folder)
        
        if not image_files:
            self.logger.warning(f"在 {input_folder} 中没有找到图像文件")
            return []
        
        results = []
        
        for filename in image_files:
            input_path = os.path.join(input_folder, filename)
            output_path = os.path.join(output_folder, filename)
            
            # 处理并保存
            result = self.process_and_save_image(input_path, output_path)
            results.append(result)
        
        self.logger.info(f"批量处理完成: 总计={len(results)}, 成功={sum(r.success for r in results)}")
        
        return results


if __name__ == "__main__":
    # 测试处理器
    config = FlameAnalyzerConfig()
    processor = FlameImageProcessor(config)
    
    print(f"处理器已初始化,配置阈值={config.flame_threshold}, 比例={config.mm_per_pixel} mm/pixel")
