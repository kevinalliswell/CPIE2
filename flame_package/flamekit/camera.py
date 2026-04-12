"""
最小可用相机采集封装
"""
import time
import os
import sys
from pathlib import Path
import numpy as np
import cv2
import platform
from typing import List, Tuple, Optional

from .config import get_config

mvsdk = None
_CAMERA_EXCEPTION = None


def _load_mvsdk():
	global mvsdk
	global _CAMERA_EXCEPTION
	if mvsdk is None:
		from . import mvsdk as _mvsdk
		mvsdk = _mvsdk
		_CAMERA_EXCEPTION = getattr(_mvsdk, "CameraException", Exception)
	return mvsdk


class CameraCapture:
	"""相机采集类（简化版，直接复用原逻辑）"""

	def __init__(self,
	             resolution_index: Optional[int] = None,
	             exposure_us: Optional[int] = None,
	             force_mono: Optional[bool] = None,
	             capture_duration: Optional[float] = None):
		self.config = get_config()
		self.hCamera = None
		self.cap = None
		self.is_color = False
		self.frame_buffer = None
		self.is_initialized = False

		# 存储用户传入的参数
		self.resolution_index = resolution_index
		self.exposure_us = exposure_us
		self.force_mono = force_mono
		self.capture_duration = capture_duration

	def get_available_resolutions(self) -> List[Tuple[int, int, int]]:
		"""
		获取相机支持的所有分辨率
		返回: [(索引, 宽度, 高度), ...]
		"""
		if not self.is_initialized or self.cap is None:
			print("相机未初始化，请先调用 initialize()")
			return []

		resolutions = []
		for i in range(self.cap.iImageSizeDesc):
			res = self.cap.pImageSizeDesc[i]
			resolutions.append((i, res.iWidth, res.iHeight))
		return resolutions

	def print_available_resolutions(self) -> None:
		"""打印相机支持的所有分辨率"""
		resolutions = self.get_available_resolutions()
		if not resolutions:
			return

		print("\n相机支持的分辨率档位：")
		print("-" * 50)
		for idx, width, height in resolutions:
			print(f"索引 {idx}: {width} x {height} 像素")
		print("-" * 50)

	def initialize(self) -> bool:
		try:
			mvsdk_module = _load_mvsdk()
			DevList = mvsdk_module.CameraEnumerateDevice()
			if len(DevList) < 1:
				print("没有发现相机设备")
				return False

			DevInfo = DevList[0]
			print(f"找到相机: {DevInfo.acFriendlyName.decode('utf-8')}")

			self.hCamera = mvsdk_module.CameraInit(DevInfo, -1, -1)
			self.cap = mvsdk_module.CameraGetCapability(self.hCamera)
			monoSensor = (self.cap.sIspCapacity.bMonoSensor != 0)

			# 优先使用传入的参数，否则从配置文件读取
			force_mono = self.force_mono if self.force_mono is not None else self.config.get('camera.force_mono', True)
			# 如果用户传入了参数，保存到配置文件
			if self.force_mono is not None:
				self.config.set('camera.force_mono', self.force_mono, save=True)

			if force_mono or monoSensor:
				mvsdk_module.CameraSetIspOutFormat(self.hCamera, mvsdk_module.CAMERA_MEDIA_TYPE_MONO8)
				self.is_color = False
			else:
				mvsdk_module.CameraSetIspOutFormat(self.hCamera, mvsdk_module.CAMERA_MEDIA_TYPE_BGR8)
				self.is_color = True

			# 优先使用传入的参数，否则从配置文件读取
			res_index = self.resolution_index if self.resolution_index is not None else self.config.get('camera.resolution_index', 1)
			# 如果用户传入了参数，保存到配置文件
			if self.resolution_index is not None:
				self.config.set('camera.resolution_index', self.resolution_index, save=True)

			if res_index < self.cap.iImageSizeDesc:
				res = self.cap.pImageSizeDesc[res_index]
				mvsdk_module.CameraSetImageResolution(self.hCamera, res)
				print(f"使用分辨率: {res.iWidth}x{res.iHeight}")

			# 优先使用传入的参数，否则从配置文件读取
			exposure_us = self.exposure_us if self.exposure_us is not None else self.config.get('camera.exposure_us', 4000)
			# 如果用户传入了参数，保存到配置文件
			if self.exposure_us is not None:
				self.config.set('camera.exposure_us', self.exposure_us, save=True)

			mvsdk_module.CameraSetTriggerMode(self.hCamera, 0)
			mvsdk_module.CameraSetAeState(self.hCamera, 0)
			mvsdk_module.CameraSetExposureTime(self.hCamera, exposure_us)

			channels = 1 if not self.is_color else 3
			frame_buffer_size = self.cap.sResolutionRange.iWidthMax * self.cap.sResolutionRange.iHeightMax * channels
			self.frame_buffer = mvsdk_module.CameraAlignMalloc(frame_buffer_size, 16)

			mvsdk_module.CameraPlay(self.hCamera)

			self.is_initialized = True
			print("相机初始化成功")
			return True
		except _CAMERA_EXCEPTION as e:  # type: ignore
			print(f"相机初始化失败({getattr(e, 'error_code', 'unknown')}): {getattr(e, 'message', e)}")
			return False
		except Exception as e:
			print(f"相机初始化异常: {e}")
			return False

	def capture_sequence(self, save_dir: str, duration: float = 1.0) -> Tuple[List[str], int]:
		if not self.is_initialized:
			print("相机未初始化")
			return [], 0

		mvsdk_module = _load_mvsdk()
		os.makedirs(save_dir, exist_ok=True)
		
		frames_in_memory: List[np.ndarray] = []
		frame_count = 0
		start_time = time.time()

		print(f"开始高速采集 {duration} 秒 (内存缓冲模式)...")
		
		# 第一阶段：极速采集到内存
		while time.time() - start_time < duration:
			try:
				# 200ms 超时限制，对于高速采集足够
				pRawData, FrameHead = mvsdk_module.CameraGetImageBuffer(self.hCamera, 200)
				mvsdk_module.CameraImageProcess(self.hCamera, pRawData, self.frame_buffer, FrameHead)
				mvsdk_module.CameraReleaseImageBuffer(self.hCamera, pRawData)

				if platform.system() == "Windows":
					mvsdk_module.CameraFlipFrameBuffer(self.frame_buffer, FrameHead, 1)

				# 复制数据到 numpy 数组（必须 copy 否则会被后续帧覆盖）
				frame_data = (mvsdk_module.c_ubyte * FrameHead.uBytes).from_address(self.frame_buffer)
				frame = np.frombuffer(frame_data, dtype=np.uint8).copy()

				# 记录形状信息，稍后统一处理
				is_mono = (FrameHead.uiMediaType == mvsdk_module.CAMERA_MEDIA_TYPE_MONO8)
				shape = (FrameHead.iHeight, FrameHead.iWidth) if is_mono else (FrameHead.iHeight, FrameHead.iWidth, 3)
				
				frames_in_memory.append((frame.reshape(shape), is_mono))
				frame_count += 1
				
			except _CAMERA_EXCEPTION as e:
				if getattr(e, 'error_code', None) != mvsdk_module.CAMERA_STATUS_TIME_OUT:
					print(f"采集异常: {e}")

		elapsed = time.time() - start_time
		actual_fps = frame_count / elapsed if elapsed > 0 else 0
		print(f"采集完成: {frame_count} 帧, 耗时 {elapsed:.3f} 秒, 实际采集帧率 {actual_fps:.2f} FPS")

		# 第二阶段：批量保存到磁盘
		print(f"正在将 {frame_count} 帧保存到磁盘...")
		image_paths: List[str] = []
		session_timestamp = time.strftime("%Y%m%d_%H%M%S", time.localtime())
		
		save_start = time.time()
		force_mono_cfg = self.config.get('camera.force_mono', True)
		
		for i, (frame, is_mono) in enumerate(frames_in_memory):
			# 根据配置处理颜色空间
			if not is_mono and force_mono_cfg:
				frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
			
			filename = os.path.join(save_dir, f"frame_{session_timestamp}_{i:04d}.jpg")
			# 使用较快的压缩参数
			cv2.imwrite(filename, frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
			image_paths.append(filename)
			
			if (i + 1) % 50 == 0:
				print(f"已保存 {i + 1}/{frame_count} 帧...")

		save_elapsed = time.time() - save_start
		print(f"保存完成，耗时 {save_elapsed:.2f} 秒")
		
		return image_paths, frame_count

	def capture_single_frame(self) -> Optional[np.ndarray]:
		if not self.is_initialized:
			return None

		mvsdk_module = _load_mvsdk()
		try:
			pRawData, FrameHead = mvsdk_module.CameraGetImageBuffer(self.hCamera, 1000)
			mvsdk_module.CameraImageProcess(self.hCamera, pRawData, self.frame_buffer, FrameHead)
			mvsdk_module.CameraReleaseImageBuffer(self.hCamera, pRawData)

			if platform.system() == "Windows":
				mvsdk_module.CameraFlipFrameBuffer(self.frame_buffer, FrameHead, 1)

			frame_data = (mvsdk_module.c_ubyte * FrameHead.uBytes).from_address(self.frame_buffer)
			frame = np.frombuffer(frame_data, dtype=np.uint8)

			expected_size = FrameHead.iHeight * FrameHead.iWidth
			if FrameHead.uiMediaType == mvsdk_module.CAMERA_MEDIA_TYPE_MONO8:
				expected_size *= 1
			else:
				expected_size *= 3

			if len(frame) != expected_size:
				return None

			if FrameHead.uiMediaType == mvsdk_module.CAMERA_MEDIA_TYPE_MONO8:
				shape = (FrameHead.iHeight, FrameHead.iWidth)
			else:
				shape = (FrameHead.iHeight, FrameHead.iWidth, 3)

			frame = frame.reshape(shape).astype(np.uint8)
			if len(frame.shape) == 2:
				frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)
			if not frame.flags['C_CONTIGUOUS']:
				frame = np.ascontiguousarray(frame)
			return frame
		except _CAMERA_EXCEPTION as e:  # type: ignore
			if getattr(e, 'error_code', None) != mvsdk_module.CAMERA_STATUS_TIME_OUT:
				print(f"采集单帧失败: {e}")
			return None
		except Exception as e:
			print(f"采集单帧异常: {e}")
			return None

	def release(self):
		if self.is_initialized and self.hCamera:
			try:
				mvsdk_module = _load_mvsdk()
				mvsdk_module.CameraUnInit(self.hCamera)
				if self.frame_buffer:
					mvsdk_module.CameraAlignFree(self.frame_buffer)
				print("相机资源已释放")
			except Exception as e:
				print(f"释放相机资源失败: {e}")
			finally:
				self.is_initialized = False
				self.hCamera = None
				self.frame_buffer = None
				self.cap = None
				self.is_color = False
