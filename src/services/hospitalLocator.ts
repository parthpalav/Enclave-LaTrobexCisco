import { calculateDistance } from '../utils/distance';

export interface LocationCoordinates {
  latitude: number;
  longitude: number;
}

export interface HospitalInfo {
  name: string;
  latitude: number;
  longitude: number;
  distanceMeters: number;
}

interface OverpassElement {
  type: string;
  id: number;
  lat?: number;
  lon?: number;
  center?: {
    lat: number;
    lon: number;
  };
  tags?: {
    name?: string;
    'name:en'?: string;
    amenity?: string;
    [key: string]: string | undefined;
  };
}

interface OverpassResponse {
  elements: OverpassElement[];
}

/**
 * Requests the user's current GPS coordinates via browser Geolocation API.
 */
export function getUserLocation(): Promise<LocationCoordinates> {
  return new Promise((resolve, reject) => {
    if (typeof window === 'undefined' || !navigator.geolocation) {
      return reject(new Error('Geolocation is not supported by your browser.'));
    }

    navigator.geolocation.getCurrentPosition(
      (position) => {
        resolve({
          latitude: position.coords.latitude,
          longitude: position.coords.longitude,
        });
      },
      (error) => {
        switch (error.code) {
          case error.PERMISSION_DENIED:
            reject(new Error('Location permission is required to navigate to the nearest hospital.'));
            break;
          case error.POSITION_UNAVAILABLE:
            reject(new Error('Unable to determine your current location.'));
            break;
          case error.TIMEOUT:
            reject(new Error('Unable to determine your current location. (Timeout)'));
            break;
          default:
            reject(new Error('Unable to determine your current location.'));
            break;
        }
      },
      {
        enableHighAccuracy: true,
        timeout: 10000,
        maximumAge: 0,
      }
    );
  });
}

/**
 * Queries OpenStreetMap Overpass API for nearby hospitals within 5000m
 * and computes the closest hospital using the Haversine formula.
 */
export async function fetchNearestHospital(
  coords: LocationCoordinates
): Promise<HospitalInfo | null> {
  const { latitude, longitude } = coords;
  const radiusMeters = 5000;

  const overpassQuery = `[out:json];(node["amenity"="hospital"](around:${radiusMeters},${latitude},${longitude});way["amenity"="hospital"](around:${radiusMeters},${latitude},${longitude});relation["amenity"="hospital"](around:${radiusMeters},${latitude},${longitude}););out center;`;

  const endpoints = [
    'https://overpass-api.de/api/interpreter',
    'https://overpass.kumi.systems/api/interpreter',
  ];

  let responseData: OverpassResponse | null = null;
  let lastError: Error | null = null;

  for (const endpoint of endpoints) {
    try {
      const response = await fetch(endpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: `data=${encodeURIComponent(overpassQuery)}`,
      });

      if (response.ok) {
        responseData = (await response.json()) as OverpassResponse;
        break;
      }
    } catch (err) {
      lastError = err instanceof Error ? err : new Error('Network failure');
    }
  }

  if (!responseData || !Array.isArray(responseData.elements)) {
    if (lastError) {
      throw new Error('Unable to contact the hospital lookup service. Please check your internet connection.');
    }
    return null;
  }

  const hospitals: HospitalInfo[] = [];

  for (const element of responseData.elements) {
    const lat = element.lat ?? element.center?.lat;
    const lon = element.lon ?? element.center?.lon;

    if (lat !== undefined && lon !== undefined) {
      const name =
        element.tags?.name ||
        element.tags?.['name:en'] ||
        'Emergency Hospital';

      const dist = calculateDistance(latitude, longitude, lat, lon);

      hospitals.push({
        name,
        latitude: lat,
        longitude: lon,
        distanceMeters: dist,
      });
    }
  }

  if (hospitals.length === 0) {
    return null;
  }

  // Sort by distance ascending to find the absolute closest hospital
  hospitals.sort((a, b) => a.distanceMeters - b.distanceMeters);

  return hospitals[0];
}
