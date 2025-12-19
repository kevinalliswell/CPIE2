"""
最小可用火焰图像分析封装
"""
import cv2
import numpy as np
from typing import Tuple, Optional, Dict, List
from .config import get_config


class FlameAnalyzer:
	"""火焰分析器（简化版）"""

	def __init__(self):
		self.config = get_config()
		self.mm_per_pixel = self.config.get('calibration.mm_per_pixel', 0.3152)

	def set_calibration(self, mm_per_pixel: float):
		self.mm_per_pixel = mm_per_pixel
		self.config.set('calibration.mm_per_pixel', mm_per_pixel, save=True)

	def analyze_flame(self, image_path: str, save_annotated: bool = False) -> Dict:
		result = {
			'max_length_mm': 0.0,
			'max_width_mm': 0.0,
			'area_mm2': 0.0,
			'binary_image': None,
			'annotated_image': None,
			'success': False,
			'contour_count': 0,
			'image_path': image_path
		}
		try:
			image = cv2.imread(image_path)
			if image is None:
				return result

			if len(image.shape) == 3:
				gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
			else:
				gray = image.copy()

			binary = self._binarize(gray)
			result['binary_image'] = binary

			contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
			result['contour_count'] = len(contours)
			if len(contours) == 0:
				result['annotated_image'] = image
				return result

			max_contour = max(contours, key=cv2.contourArea)
			area_px = cv2.contourArea(max_contour)
			min_area = self.config.get('analysis.min_flame_area', 1000)
			if area_px < min_area:
				result['annotated_image'] = image
				return result

			rect = cv2.minAreaRect(max_contour)
			box = cv2.boxPoints(rect).astype(np.int32)

			width_px, height_px = rect[1]
			length_px = max(width_px, height_px)
			width_px_actual = min(width_px, height_px)

			result['max_length_mm'] = float(length_px) * self.mm_per_pixel
			result['max_width_mm'] = float(width_px_actual) * self.mm_per_pixel
			result['area_mm2'] = float(area_px) * (self.mm_per_pixel ** 2)
			result['success'] = True

			annotated = image.copy()
			if len(annotated.shape) == 2:
				annotated = cv2.cvtColor(annotated, cv2.COLOR_GRAY2BGR)
			cv2.drawContours(annotated, [max_contour], 0, (0, 255, 255), 2)
			cv2.drawContours(annotated, [box], 0, (0, 255, 0), 2)

			center_x, center_y = int(rect[0][0]), int(rect[0][1])
			text = f"Length: {result['max_length_mm']:.1f}mm"
			cv2.putText(annotated, text, (center_x - 80, center_y - 20),
			            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
			text2 = f"Width: {result['max_width_mm']:.1f}mm"
			cv2.putText(annotated, text2, (center_x - 80, center_y + 10),
			            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)

			result['annotated_image'] = annotated
			if save_annotated and annotated is not None:
				cv2.imwrite(image_path, annotated)
		except Exception as _:
			pass
		return result

	def batch_analyze(self, image_paths: List[str], save_annotated: bool = True) -> Tuple[Dict, str]:
		max_result = None
		max_length = 0.0
		max_image_path = ""
		for path in image_paths:
			res = self.analyze_flame(path, save_annotated=save_annotated)
			if res.get('success') and res.get('max_length_mm', 0.0) > max_length:
				max_length = float(res['max_length_mm'])
				max_result = res
				max_image_path = path
		if max_result is None:
			max_result = {'max_length_mm': 0.0, 'max_width_mm': 0.0, 'area_mm2': 0.0, 'success': False}
		return max_result, max_image_path

	def _binarize(self, gray_image: np.ndarray) -> np.ndarray:
		blurred = cv2.GaussianBlur(gray_image, (5, 5), 0)
		use_otsu = self.config.get('analysis.use_otsu', True)
		threshold = self.config.get('analysis.binary_threshold', 0)
		if use_otsu:
			_, binary = cv2.threshold(blurred, threshold, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
		else:
			_, binary = cv2.threshold(blurred, threshold, 255, cv2.THRESH_BINARY)
		kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
		binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel, iterations=1)
		binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel, iterations=1)
		return binary

	def manual_calibrate(self, image: np.ndarray, point1: Tuple[int, int],
	                     point2: Tuple[int, int], actual_distance_mm: float) -> float:
		pixel_distance = np.sqrt((point2[0] - point1[0]) ** 2 + (point2[1] - point1[1]) ** 2)
		if pixel_distance == 0:
			return self.mm_per_pixel
		mm_per_pixel = float(actual_distance_mm) / float(pixel_distance)
		self.set_calibration(mm_per_pixel)
		return mm_per_pixel


