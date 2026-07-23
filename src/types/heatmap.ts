export type CrowdLevel = "low" | "moderate" | "crowded" | "overcrowded";

export interface Detection {
  x1: number;
  y1: number;
  x2: number;
  y2: number;
  confidence: number;
  track_id?: number | null;
}

export interface TrackMovement {
  track_id: number;
  start_x: number;
  start_y: number;
  end_x: number;
  end_y: number;
  speed: number;
  direction_deg: number;
}

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
  crowd_level: CrowdLevel;
  crowded_zones: CrowdedZone[];
  movement_index: number;
  movements: TrackMovement[];
}

export interface CameraStatus {
  camera_id: string;
  running: boolean;
  connected: boolean;
  fps: number;
  people_count: number;
  last_frame_at?: number | null;
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

export interface LiveFrame {
  camera_id: string;
  image: string;
  raw_image?: string;
  analytics: Analytics;
  status: CameraStatus;
}
