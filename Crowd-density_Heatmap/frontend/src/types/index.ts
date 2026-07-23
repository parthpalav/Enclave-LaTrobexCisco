export interface CrowdedZone {
  x: number;
  y: number;
  radius: number;
  intensity: number;
}

export interface Analytics {
  camera_id: string;
  timestamp: number;
  people_count: number;
  density_score: number;
  average_density: number;
  max_density: number;
  crowd_level: "low" | "moderate" | "crowded" | "overcrowded";
  crowded_zones: CrowdedZone[];
  movement_index: number;
  fps?: number;
}

export interface CameraStatus {
  camera_id: string;
  running: boolean;
  connected: boolean;
  fps: number;
  people_count: number;
  last_frame_at: number | null;
}

export interface LiveFrame {
  type: "frame";
  status: CameraStatus;
  analytics: Analytics;
  image?: string;
  raw_image?: string;
}

export interface AddCameraPayload {
  camera_id: string;
  name: string;
  source: string;
  location?: string;
  latitude?: number;
  longitude?: number;
  enabled?: boolean;
  crowd_moderate_threshold?: number;
  crowd_crowded_threshold?: number;
  crowd_overcrowded_threshold?: number;
}
