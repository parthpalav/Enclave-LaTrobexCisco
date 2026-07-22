export interface NominatimResponse {
  display_name?: string;
  address?: {
    suburb?: string;
    neighbourhood?: string;
    quarter?: string;
    residential?: string;
    road?: string;
    city_district?: string;
    city?: string;
    town?: string;
    village?: string;
    state?: string;
    [key: string]: string | undefined;
  };
}

/**
 * Performs reverse geocoding using OpenStreetMap Nominatim API
 * to convert GPS coordinates into a human-readable location name.
 * 
 * @param lat - Latitude coordinate
 * @param lon - Longitude coordinate
 * @returns Human-readable place name or raw coordinate string on failure
 */
export async function reverseGeocode(lat: number, lon: number): Promise<string> {
  const url = `https://nominatim.openstreetmap.org/reverse?format=jsonv2&lat=${lat}&lon=${lon}`;

  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 5000); // 5s timeout

    const response = await fetch(url, {
      headers: {
        'Accept': 'application/json',
        'User-Agent': 'CrowdShield-Emergency-Control-Center/1.0',
      },
      signal: controller.signal,
    });

    clearTimeout(timeoutId);

    if (response.ok) {
      const data = (await response.json()) as NominatimResponse;
      const addr = data.address;

      if (addr) {
        // Prioritize local landmark/road/suburb names for public billboard clarity
        const primary =
          addr.suburb ||
          addr.neighbourhood ||
          addr.quarter ||
          addr.residential ||
          addr.road ||
          addr.city_district;

        const secondary = addr.city || addr.town || addr.village || addr.state;

        if (primary && secondary) {
          return `${primary}, ${secondary}`.toUpperCase();
        }

        if (primary) {
          return primary.toUpperCase();
        }

        if (secondary) {
          return secondary.toUpperCase();
        }
      }

      if (data.display_name) {
        const parts = data.display_name.split(',');
        const shortName = parts.slice(0, 2).join(',').trim();
        return shortName.toUpperCase();
      }
    }
  } catch (err) {
    // Fail gracefully on timeout or network error
    console.warn('Reverse geocoding network lookup failed:', err);
  }

  // Fallback to raw coordinates format if reverse geocoding is unavailable
  return `${lat.toFixed(4)}, ${lon.toFixed(4)}`;
}
