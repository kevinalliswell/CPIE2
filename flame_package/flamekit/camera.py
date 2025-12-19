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

from . import mvsdk
from .config import get_config


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
			DevList = mvsdk.CameraEnumerateDevice()
			if len(DevList) < 1:
				print("没有发现相机设备")
				return False

			DevInfo = DevList[0]
			print(f"找到相机: {DevInfo.acFriendlyName.decode('utf-8')}")

			self.hCamera = mvsdk.CameraInit(DevInfo, -1, -1)
			self.cap = mvsdk.CameraGetCapability(self.hCamera)
			monoSensor = (self.cap.sIspCapacity.bMonoSensor != 0)

			# 优先使用传入的参数，否则从配置文件读取
			force_mono = self.force_mono if self.force_mono is not None else self.config.get('camera.force_mono', True)
			# 如果用户传入了参数，保存到配置文件
			if self.force_mono is not None:
				self.config.set('camera.force_mono', self.force_mono, save=True)
			
			if force_mono or monoSensor:
				mvsdk.CameraSetIspOutFormat(self.hCamera, mvsdk.CAMERA_MEDIA_TYPE_MONO8)
				self.is_color = False
			else:
				mvsdk.CameraSetIspOutFormat(self.hCamera, mvsdk.CAMERA_MEDIA_TYPE_BGR8)
				self.is_color = True

			# 优先使用传入的参数，否则从配置文件读取
			res_index = self.resolution_index if self.resolution_index is not None else self.config.get('camera.resolution_index', 1)
			# 如果用户传入了参数，保存到配置文件
			if self.resolution_index is not None:
				self.config.set('camera.resolution_index', self.resolution_index, save=True)
			
			if res_index < self.cap.iImageSizeDesc:
				res = self.cap.pImageSizeDesc[res_index]
				mvsdk.CameraSetImageResolution(self.hCamera, res)
				print(f"使用分辨率: {res.iWidth}x{res.iHeight}")

			# 优先使用传入的参数，否则从配置文件读取
			exposure_us = self.exposure_us if self.exposure_us is not None else self.config.get('camera.exposure_us', 4000)
			# 如果用户传入了参数，保存到配置文件
			if self.exposure_us is not None:
				self.config.set('camera.exposure_us', self.exposure_us, save=True)
			
			mvsdk.CameraSetTriggerMode(self.hCamera, 0)
			mvsdk.CameraSetAeState(self.hCamera, 0)
			mvsdk.CameraSetExposureTime(self.hCamera, exposure_us)

			channels = 1 if not self.is_color else 3
			FrameBufferSize = self.cap.sResolutionRange.iWidthMax * self.cap.sResolutionRange.iHeightMax * channels
			self.frame_buffer = mvsdk.CameraAlignMalloc(FrameBufferSize, 16)

			mvsdk.CameraPlay(self.hCamera)

			self.is_initialized = True
			print("相机初始化成功")
			return True
		except mvsdk.CameraException as e:  # type: ignore
			print(f"相机初始化失败({e.error_code}): {e.message}")
			return False
		except Exception as e:
			print(f"相机初始化异常: {e}")
			return False

	def capture_sequence(self, save_dir: str, duration: float = 1.0) -> Tuple[List[str], int]:
		if not self.is_initialized:
			print("相机未初始化")
			return [], 0

		os.makedirs(save_dir, exist_ok=True)
		image_paths: List[str] = []
		frame_count = 0
		start_time = time.time()
		
		# 预先生成时间戳，避免每帧重复计算
		session_timestamp = time.strftime("%Y%m%d_%H%M%S", time.localtime())

		print(f"开始采集 {duration} 秒...")
		while time.time() - start_time < duration:
			try:
				pRawData, FrameHead = mvsdk.CameraGetImageBuffer(self.hCamera, 200)  # 降低超时到200ms
				mvsdk.CameraImageProcess(self.hCamera, pRawData, self.frame_buffer, FrameHead)
				mvsdk.CameraReleaseImageBuffer(self.hCamera, pRawData)

				if platform.system() == "Windows":
					mvsdk.CameraFlipFrameBuffer(self.frame_buffer, FrameHead, 1)

				frame_data = (mvsdk.c_ubyte * FrameHead.uBytes).from_address(self.frame_buffer)
				frame = np.frombuffer(frame_data, dtype=np.uint8)

				expected_size = FrameHead.iHeight * FrameHead.iWidth
				if FrameHead.uiMediaType == mvsdk.CAMERA_MEDIA_TYPE_MONO8:
					expected_size *= 1
				else:
					expected_size *= 3

				if len(frame) != expected_size:
					continue

				if FrameHead.uiMediaType == mvsdk.CAMERA_MEDIA_TYPE_MONO8:
					shape = (FrameHead.iHeight, FrameHead.iWidth)
				else:
					shape = (FrameHead.iHeight, FrameHead.iWidth, 3)

				frame = frame.reshape(shape).astype(np.uint8)

				if self.is_color and self.config.get('camera.force_mono', True):
					frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

				# 优化文件名生成，使用会话时间戳 + 帧序号
				filename = os.path.join(save_dir, f"frame_{session_timestamp}_{frame_count:04d}.jpg")
				
				# 降低JPEG质量到80，提升压缩速度（质量差异不明显，速度提升约2-3倍）
				cv2.imwrite(filename, frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
				image_paths.append(filename)
				frame_count += 1
			except mvsdk.CameraException as e:  # type: ignore
				if e.error_code != mvsdk.CAMERA_STATUS_TIME_OUT:
					print(f"采集失败: {e}")

		elapsed = time.time() - start_time
		fps = frame_count / elapsed if elapsed > 0 else 0
		print(f"采集完成: {frame_count} 帧, 耗时 {elapsed:.3f} 秒, 帧率 {fps:.2f} FPS")
		return image_paths, frame_count

	def capture_single_frame(self) -> Optional[np.ndarray]:
		if not self.is_initialized:
			return None
		try:
			pRawData, FrameHead = mvsdk.CameraGetImageBuffer(self.hCamera, 1000)
			mvsdk.CameraImageProcess(self.hCamera, pRawData, self.frame_buffer, FrameHead)
			mvsdk.CameraReleaseImageBuffer(self.hCamera, pRawData)

			if platform.system() == "Windows":
				mvsdk.CameraFlipFrameBuffer(self.frame_buffer, FrameHead, 1)

			frame_data = (mvsdk.c_ubyte * FrameHead.uBytes).from_address(self.frame_buffer)
			frame = np.frombuffer(frame_data, dtype=np.uint8)

			expected_size = FrameHead.iHeight * FrameHead.iWidth
			if FrameHead.uiMediaType == mvsdk.CAMERA_MEDIA_TYPE_MONO8:
				expected_size *= 1
			else:
				expected_size *= 3

			if len(frame) != expected_size:
				return None

			if FrameHead.uiMediaType == mvsdk.CAMERA_MEDIA_TYPE_MONO8:
				shape = (FrameHead.iHeight, FrameHead.iWidth)
			else:
				shape = (FrameHead.iHeight, FrameHead.iWidth, 3)

			frame = frame.reshape(shape).astype(np.uint8)
			if len(frame.shape) == 2:
				frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)
			if not frame.flags['C_CONTIGUOUS']:
				frame = np.ascontiguousarray(frame)
			return frame
		except mvsdk.CameraException as e:  # type: ignore
			if e.error_code != mvsdk.CAMERA_STATUS_TIME_OUT:
				print(f"采集单帧失败: {e}")
			return None
		except Exception as e:
			print(f"采集单帧异常: {e}")
			return None

	def release(self):
		if self.is_initialized and self.hCamera:
			try:
				mvsdk.CameraUnInit(self.hCamera)
				if self.frame_buffer:
					mvsdk.CameraAlignFree(self.frame_buffer)
				print("相机资源已释放")
			except Exception as e:
				print(f"释放相机资源失败: {e}")
			finally:
				self.is_initialized = False
				self.hCamera = None
				self.frame_buffer = None


