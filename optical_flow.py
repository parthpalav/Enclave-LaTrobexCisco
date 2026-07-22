import time
import abc
import numpy as np
import cv2
import torch
import torchvision.transforms.functional as F
from torchvision.models.optical_flow import raft_small, Raft_Small_Weights
from typing import Tuple, Dict, Any
from config import OpticalFlowConfig

class BaseOpticalFlow(abc.ABC):
    """
    Abstract base class for optical flow backends.
    """
    @abc.abstractmethod
    def compute(self, prev_frame: np.ndarray, curr_frame: np.ndarray) -> Tuple[np.ndarray, np.ndarray, float]:
        """
        Compute flow between prev_frame and curr_frame (BGR uint8).
        Returns:
            dense_flow: (H_down, W_down, 2) dense flow field (dx, dy)
            binned_flow: (grid_rows, grid_cols, 2) aggregated cell vectors
            compute_time_ms: latency in milliseconds
        """
        pass

    def bin_flow(self, dense_flow: np.ndarray, grid_rows: int, grid_cols: int) -> np.ndarray:
        """
        Bin dense flow (H, W, 2) into a (grid_rows, grid_cols, 2) vector field.
        """
        H, W, C = dense_flow.shape
        cell_h = H / grid_rows
        cell_w = W / grid_cols

        binned = np.zeros((grid_rows, grid_cols, 2), dtype=np.float32)
        for r in range(grid_rows):
            r_start = int(r * cell_h)
            r_end = int((r + 1) * cell_h)
            for c in range(grid_cols):
                c_start = int(c * cell_w)
                c_end = int((c + 1) * cell_w)

                cell_patch = dense_flow[r_start:r_end, c_start:c_end]
                if cell_patch.size > 0:
                    binned[r, c] = np.mean(cell_patch, axis=(0, 1))

        return binned


class RAFTOpticalFlow(BaseOpticalFlow):
    """
    RAFT-small PyTorch GPU Optical Flow implementation.
    """
    def __init__(self, config: OpticalFlowConfig, device: str = "cuda:0"):
        self.config = config
        self.device = device if torch.cuda.is_available() else "cpu"
        print(f"[OpticalFlow] Loading RAFT-small model on {self.device}...")
        self.weights = Raft_Small_Weights.DEFAULT
        self.model = raft_small(weights=self.weights, progress=False).to(self.device)
        self.model.eval()

    def compute(self, prev_frame: np.ndarray, curr_frame: np.ndarray) -> Tuple[np.ndarray, np.ndarray, float]:
        start_time = time.perf_counter()

        # Downsample frames
        w, h = self.config.downsample_width, self.config.downsample_height
        img1_resized = cv2.resize(prev_frame, (w, h))
        img2_resized = cv2.resize(curr_frame, (w, h))

        # Convert BGR to RGB and format as (C, H, W) normalized tensors
        img1_rgb = cv2.cvtColor(img1_resized, cv2.COLOR_BGR2RGB)
        img2_rgb = cv2.cvtColor(img2_resized, cv2.COLOR_BGR2RGB)

        t1 = torch.from_numpy(img1_rgb).permute(2, 0, 1).to(self.device).float()
        t2 = torch.from_numpy(img2_rgb).permute(2, 0, 1).to(self.device).float()

        # Preprocess using torchvision Raft weights transforms
        t1_prep, t2_prep = self.weights.transforms()(t1, t2)
        t1_batch = t1_prep.unsqueeze(0)
        t2_batch = t2_prep.unsqueeze(0)

        with torch.no_grad():
            list_of_flows = self.model(t1_batch, t2_batch)
            flow_predictions = list_of_flows[-1]  # Final refined flow tensor (1, 2, H, W)
            flow_np = flow_predictions[0].permute(1, 2, 0).cpu().numpy()  # (H, W, 2)

        # Bin flow into coarse grid
        binned = self.bin_flow(flow_np, self.config.grid_rows, self.config.grid_cols)

        compute_time_ms = (time.perf_counter() - start_time) * 1000.0
        return flow_np, binned, compute_time_ms


class FarnebackOpticalFlow(BaseOpticalFlow):
    """
    OpenCV Farneback Optical Flow (CPU/CUDA baseline fallback).
    """
    def __init__(self, config: OpticalFlowConfig, use_cuda: bool = True):
        self.config = config
        self.use_cuda = use_cuda and hasattr(cv2, 'cuda') and cv2.cuda.getCudaEnabledDeviceCount() > 0
        if self.use_cuda:
            print("[OpticalFlow] Initializing OpenCV CUDA Farneback...")
            self.cuda_farneback = cv2.cuda.FarnebackOpticalFlow.create(numLevels=3, pyrScale=0.5, fastPyrams=True, winSize=15, numIters=3, polyN=5, polySigma=1.2, flags=0)
        else:
            print("[OpticalFlow] Initializing OpenCV CPU Farneback fallback...")

    def compute(self, prev_frame: np.ndarray, curr_frame: np.ndarray) -> Tuple[np.ndarray, np.ndarray, float]:
        start_time = time.perf_counter()

        w, h = self.config.downsample_width, self.config.downsample_height
        prev_gray = cv2.cvtColor(cv2.resize(prev_frame, (w, h)), cv2.COLOR_BGR2GRAY)
        curr_gray = cv2.cvtColor(cv2.resize(curr_frame, (w, h)), cv2.COLOR_BGR2GRAY)

        if self.use_cuda:
            gpu_prev = cv2.cuda_GpuMat(prev_gray)
            gpu_curr = cv2.cuda_GpuMat(curr_gray)
            gpu_flow = self.cuda_farneback.calc(gpu_prev, gpu_curr, None)
            flow_np = gpu_flow.download()
        else:
            flow_np = cv2.calcOpticalFlowFarneback(
                prev_gray, curr_gray, None,
                pyr_scale=0.5, levels=3, winsize=15,
                iterations=3, poly_n=5, poly_sigma=1.2, flags=0
            )

        binned = self.bin_flow(flow_np, self.config.grid_rows, self.config.grid_cols)

        compute_time_ms = (time.perf_counter() - start_time) * 1000.0
        return flow_np, binned, compute_time_ms


def create_optical_flow_backend(config: OpticalFlowConfig, device: str = "cuda:0") -> BaseOpticalFlow:
    """
    Factory function to instantiate configured optical flow backend.
    """
    backend_name = config.backend.lower()
    if backend_name == "raft_small":
        try:
            return RAFTOpticalFlow(config, device=device)
        except Exception as e:
            print(f"[OpticalFlow] Warning: Failed to load RAFT-small ({e}). Falling back to Farneback.")
            return FarnebackOpticalFlow(config)
    elif backend_name == "farneback":
        return FarnebackOpticalFlow(config)
    else:
        raise ValueError(f"Unknown optical flow backend: {config.backend}")
