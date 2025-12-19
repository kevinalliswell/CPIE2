import os
import time
from typing import List, Tuple, Optional, Dict

import cv2

# 使用根目录下封装的内部模块
from .camera import CameraCapture
from .analyzer import FlameAnalyzer
from .config import get_config


class FlameKit:
	"""
	最小可用封装：
	- 预览
	- 高速采集（1s）到临时目录
	- 参数标定（设置 mm_per_pixel）
	- 火焰长度分析（批量，返回最大值及图片路径）
	- 分析后图像的 1s 播放（可设置速度倍率）
	- 保存最大火焰图与路径
	"""

	def __init__(self, 
	             resolution_index: Optional[int] = None,
	             exposure_us: Optional[int] = None,
	             force_mono: Optional[bool] = None,
	             capture_duration: Optional[float] = None):
		self.config = get_config()
		self.camera = CameraCapture(
			resolution_index=resolution_index,
			exposure_us=exposure_us,
			force_mono=force_mono,
			capture_duration=capture_duration
		)
		self.analyzer = FlameAnalyzer()
		self._last_image_paths: List[str] = []
		self._last_analysis: Optional[Dict] = None
		self._last_max_image_path: str = ""
		self._initialized: bool = False

	def initialize(self) -> bool:
		if self._initialized:
			return True
		ok = self.camera.initialize()
		self._initialized = bool(ok)
		
		# 检查标定参数是否匹配当前分辨率
		if ok:
			self._check_calibration_resolution()
		
		return self._initialized
	
	def _check_calibration_resolution(self) -> None:
		"""检查标定参数是否匹配当前分辨率"""
		try:
			resolutions = self.get_available_resolutions()
			if not resolutions:
				return
			
			res_index = self.config.get('camera.resolution_index', 1)
			if res_index >= len(resolutions):
				return
			
			_, width, height = resolutions[res_index]
			current_resolution = f"{width}x{height}"
			calibration_resolution = self.config.get('calibration.calibration_resolution')
			
			# 检查是否有该分辨率的历史标定参数
			history_key = f"calibration_history.resolutions.{current_resolution}"
			history_calibration = self.config.get(history_key)
			
			if history_calibration is not None:
				# 自动加载该分辨率的标定参数
				current_mm_per_pixel = self.config.get('calibration.mm_per_pixel')
				if abs(current_mm_per_pixel - history_calibration) > 0.0001:
					print(f"✓ 自动加载分辨率 {current_resolution} 的标定参数: {history_calibration:.6f} mm/pixel")
					self.config.set('calibration.mm_per_pixel', history_calibration, save=True)
					self.analyzer.set_calibration(history_calibration)
			elif calibration_resolution and calibration_resolution != current_resolution:
				# 警告：分辨率已改变但没有对应的标定参数
				print(f"⚠️  警告：分辨率已从 {calibration_resolution} 改为 {current_resolution}")
				print(f"    当前标定参数可能不准确，建议重新标定！")
				print(f"    当前 mm_per_pixel: {self.config.get('calibration.mm_per_pixel'):.6f}")
			else:
				# 首次使用该分辨率
				print(f"ℹ️  当前分辨率: {current_resolution}")
				print(f"    mm_per_pixel: {self.config.get('calibration.mm_per_pixel'):.6f}")
				
		except Exception as e:
			print(f"检查标定分辨率时出错: {e}")
	
	def get_available_resolutions(self) -> List[Tuple[int, int, int]]:
		"""
		获取相机支持的所有分辨率
		返回: [(索引, 宽度, 高度), ...]
		"""
		if not self._initialized:
			print("请先调用 initialize() 初始化相机")
			return []
		return self.camera.get_available_resolutions()
	
	def print_available_resolutions(self) -> None:
		"""打印相机支持的所有分辨率"""
		if not self._initialized:
			self.initialize()
		self.camera.print_available_resolutions()

	def preview(self, seconds: float = 3.0, window_name: str = "Preview") -> None:
		"""
		相机画面预览（简单窗口，ESC提前退出）
		"""
		if not self.initialize():
			print("相机未就绪，无法预览")
			return

		start_t = time.time()
		cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
		try:
			while time.time() - start_t < seconds:
				frame = self.camera.capture_single_frame()
				if frame is None:
					continue
				cv2.imshow(window_name, frame)
				if cv2.waitKey(1) & 0xFF == 27:  # ESC
					break
		finally:
			cv2.destroyWindow(window_name)

	def capture_one_second(self, temp_dir: Optional[str] = None) -> Tuple[List[str], int]:
		"""
		高速采集 1s（目录可配置），返回(图片路径列表, 帧数)
		"""
		if not self.initialize():
			print("相机未就绪，无法采集")
			return [], 0

		temp_dir = temp_dir or self.config.get('paths.temp_dir', './temp_captures')
		os.makedirs(temp_dir, exist_ok=True)

		# 清空目录
		for f in os.listdir(temp_dir):
			fp = os.path.join(temp_dir, f)
			try:
				if os.path.isfile(fp):
					os.unlink(fp)
			except Exception as _:
				pass

		imgs, n = self.camera.capture_sequence(temp_dir, duration=1.0)
		self._last_image_paths = imgs
		return imgs, n

	def set_calibration(self, mm_per_pixel: float, save_for_current_resolution: bool = True) -> None:
		"""
		设置标定参数（最小接口）
		
		Args:
			mm_per_pixel: 每像素对应的毫米数
			save_for_current_resolution: 是否保存当前分辨率的标定参数
		"""
		self.analyzer.set_calibration(mm_per_pixel)
		self.config.set('calibration.mm_per_pixel', mm_per_pixel, save=True)
		
		# 保存当前分辨率信息
		if save_for_current_resolution and self._initialized:
			resolutions = self.get_available_resolutions()
			if resolutions:
				res_index = self.config.get('camera.resolution_index', 1)
				if res_index < len(resolutions):
					_, width, height = resolutions[res_index]
					resolution_key = f"{width}x{height}"
					
					# 保存当前分辨率
					self.config.set('calibration.calibration_resolution', resolution_key, save=False)
					
					# 保存到历史记录
					history_key = f"calibration_history.resolutions.{resolution_key}"
					self.config.set(history_key, mm_per_pixel, save=False)
					
					# 一次性保存
					self.config.save_config()
					print(f"✓ 标定参数已保存（分辨率：{resolution_key}）")

	def analyze(self, image_paths: Optional[List[str]] = None, save_annotated: bool = True) -> Tuple[Dict, str]:
		"""
		批量分析，返回(最大结果字典, 对应图像路径)
		"""
		paths = image_paths if image_paths is not None else self._last_image_paths
		if not paths:
			print("没有可分析的图像")
			return {'success': False, 'max_length_mm': 0.0, 'max_width_mm': 0.0, 'area_mm2': 0.0}, ""

		max_result, max_img = self.analyzer.batch_analyze(paths, save_annotated=save_annotated)
		self._last_analysis = max_result
		self._last_max_image_path = max_img
		return max_result, max_img

	def play_analyzed(self, image_paths: Optional[List[str]] = None, speed: float = 1.0,
	                  window_name: str = "Playback", target_fps: int = 240, duration_s: float = 1.0) -> None:
		"""
		分析后的图像播放（约1s），可设置速度倍率
		- 目标 240fps，按 speed 调整播放间隔
		"""
		paths = image_paths if image_paths is not None else self._last_image_paths
		if not paths:
			print("没有可播放的图像")
			return

		cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
		interval_ms = max(1, int(1000 / (target_fps * max(0.1, speed))))
		start_t = time.time()
		try:
			for p in paths:
				img = cv2.imread(p)
				if img is None:
					continue
				cv2.imshow(window_name, img)
				if cv2.waitKey(interval_ms) & 0xFF == 27:  # ESC
					break
				if time.time() - start_t >= duration_s:
					break
		finally:
			cv2.destroyWindow(window_name)

	def save_max_result(self, output_dir: Optional[str] = None) -> Optional[str]:
		"""
		保存最大火焰长度的标注图（若已标注），返回保存路径；并打印原图路径
		"""
		if not self._last_analysis or not self._last_analysis.get('success'):
			print("暂无可保存的分析结果")
			return None

		output_dir = output_dir or self.config.get('paths.output_dir', './results')
		os.makedirs(output_dir, exist_ok=True)

		annotated = self._last_analysis.get('annotated_image')
		save_path = None
		if annotated is not None:
			save_path = os.path.join(output_dir, "max_flame_annotated.jpg")
			cv2.imwrite(save_path, annotated)

		print(f"最大火焰对应原图路径: {self._last_max_image_path}")
		if save_path:
			print(f"标注图已保存: {save_path}")
		return save_path

	def release(self) -> None:
		self.camera.release()


