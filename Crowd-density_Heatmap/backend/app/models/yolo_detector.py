"""YOLO person detector with integrated ByteTrack tracking.

Primary model is YOLOv11 with an automatic fallback to YOLOv8. Each detector
instance owns its own model so per-camera tracker state stays isolated when
several cameras run concurrently.
"""

from __future__ import annotations

from app.core.logger import get_logger
from app.models import Detection

logger = get_logger(__name__)


def resolve_device(preference: str) -> str:
    """Resolve the compute device, honouring an 'auto' preference."""
    if preference and preference != "auto":
        return preference
    try:
        import torch

        if torch.cuda.is_available():
            return "cuda:0"
        # Apple Silicon MPS is a nice-to-have for local dev.
        if getattr(torch.backends, "mps", None) and torch.backends.mps.is_available():
            return "mps"
    except Exception:  # pragma: no cover - torch may be absent in some envs
        pass
    return "cpu"


class YoloDetector:
    """Wraps an Ultralytics YOLO model for person detection + tracking."""

    def __init__(
        self,
        model_path: str,
        fallback_path: str,
        device: str = "auto",
        confidence: float = 0.30,
        iou: float = 0.45,
        imgsz: int = 640,
        person_class_id: int = 0,
        tracker_config: str = "bytetrack.yaml",
        half: bool = False,
    ):
        self.device = resolve_device(device)
        self.confidence = confidence
        self.iou = iou
        self.imgsz = imgsz
        self.person_class_id = person_class_id
        self.tracker_config = tracker_config
        self.half = half and self.device.startswith("cuda")
        self.model_name = model_path
        self._model = self._load(model_path, fallback_path)

    def _load(self, model_path: str, fallback_path: str):
        from ultralytics import YOLO

        try:
            model = YOLO(model_path)
            self.model_name = model_path
            logger.info("Loaded YOLO model '%s' on %s", model_path, self.device)
        except Exception as exc:  # noqa: BLE001 - want a broad fallback
            logger.warning(
                "Failed to load primary model '%s' (%s); falling back to '%s'",
                model_path,
                exc,
                fallback_path,
            )
            model = YOLO(fallback_path)
            self.model_name = fallback_path
            logger.info("Loaded fallback YOLO model '%s'", fallback_path)
        model.to(self.device)
        return model

    def _to_detections(self, result) -> list[Detection]:
        detections: list[Detection] = []
        boxes = getattr(result, "boxes", None)
        if boxes is None or boxes.data is None or len(boxes) == 0:
            return detections

        xyxy = boxes.xyxy.cpu().numpy()
        confs = boxes.conf.cpu().numpy()
        classes = boxes.cls.cpu().numpy().astype(int)
        ids = (
            boxes.id.cpu().numpy().astype(int)
            if getattr(boxes, "id", None) is not None
            else [None] * len(xyxy)
        )

        for (x1, y1, x2, y2), conf, cls, tid in zip(xyxy, confs, classes, ids):
            if cls != self.person_class_id:
                continue
            detections.append(
                Detection(
                    x1=float(x1),
                    y1=float(y1),
                    x2=float(x2),
                    y2=float(y2),
                    confidence=float(conf),
                    track_id=(int(tid) if tid is not None else None),
                )
            )
        return detections

    def detect(self, frame) -> list[Detection]:
        """Detection only — no tracking (used in tests and one-off inference)."""
        results = self._model.predict(
            frame,
            conf=self.confidence,
            iou=self.iou,
            imgsz=self.imgsz,
            classes=[self.person_class_id],
            device=self.device,
            half=self.half,
            verbose=False,
        )
        return self._to_detections(results[0])

    def track(self, frame) -> list[Detection]:
        """Detect + track people with ByteTrack, persisting state per instance."""
        results = self._model.track(
            frame,
            conf=self.confidence,
            iou=self.iou,
            imgsz=self.imgsz,
            classes=[self.person_class_id],
            device=self.device,
            half=self.half,
            persist=True,
            tracker=self.tracker_config,
            verbose=False,
        )
        return self._to_detections(results[0])
