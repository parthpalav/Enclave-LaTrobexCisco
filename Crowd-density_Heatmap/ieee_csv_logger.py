#!/usr/bin/env python3
"""IEEE CSV Data Logger for Crowd Density & People Detection.

This script logs people detection analytics from the CrowdVision engine at regular
intervals (default: every 2 minutes / 120 seconds) along with dynamic geographical location data.

CSV Format:
    Serial Number, Date, Time, Timestamp, People Count, Camera ID, Location, Latitude, Longitude

Features:
    - Auto-increments serial numbers.
    - Generates date (YYYY-MM-DD) and time (HH:MM:SS).
    - Logs people count fetched from live CrowdVision backend API.
    - Dynamically queries real-time high-accuracy device GPS location (synced via web browser / client).
    - Appends data to a CSV file every 2 minutes.
    - Prints CSV data to stdout for piping to serial ports or external IEEE interfaces.
    - Optional direct Serial Port support (via pySerial) to transmit data to IEEE hardware ports.

Usage:
    # Run continuous logger with dynamic location detection (every 2 minutes)
    python3 ieee_csv_logger.py

    # Specify custom location coordinates and location name
    python3 ieee_csv_logger.py --location "Main Gate Campus" --lat 18.5204 --lon 73.8567

    # Specify custom interval (120 seconds) and custom output file
    python3 ieee_csv_logger.py --interval 120 --output ieee_geo_data.csv

    # Run once immediately (useful for cron jobs or testing)
    python3 ieee_csv_logger.py --run-once

    # Send CSV output to a hardware serial port (IEEE hardware interface)
    python3 ieee_csv_logger.py --serial-port /dev/ttyUSB0 --baudrate 9600
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import time
from datetime import datetime
import urllib.error
import urllib.request

DEFAULT_API_URL = os.getenv("CROWDVISION_API_URL", "http://localhost:8000/api/v1")
DEFAULT_OUTPUT_FILE = os.getenv("IEEE_OUTPUT_FILE", "ieee_people_count.csv")
DEFAULT_INTERVAL_SECONDS = int(os.getenv("IEEE_LOG_INTERVAL", "120"))  # 2 minutes

DEFAULT_LOCATION_NAME = os.getenv("GEO_LOCATION", "Dynamic Location")
DEFAULT_LATITUDE = float(os.getenv("GEO_LATITUDE", "0.0"))
DEFAULT_LONGITUDE = float(os.getenv("GEO_LONGITUDE", "0.0"))

CSV_HEADERS = [
    "Serial_Number",
    "Date",
    "Time",
    "Timestamp",
    "People_Count",
    "Camera_ID",
    "Location",
    "Latitude",
    "Longitude",
]


def fetch_dynamic_backend_location(api_url: str) -> dict:
    """Fetch current dynamic GPS location from backend location API."""
    url = f"{api_url.rstrip('/')}/location/current"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "IEEE-CSV-Logger/1.0"})
        with urllib.request.urlopen(req, timeout=3) as resp:
            if resp.status == 200:
                data = json.loads(resp.read().decode("utf-8"))
                if data.get("latitude") and data.get("longitude") and data.get("latitude") != 0.0:
                    return {
                        "location": data.get("location", "Dynamic GPS"),
                        "latitude": round(float(data.get("latitude")), 6),
                        "longitude": round(float(data.get("longitude")), 6),
                    }
    except Exception:
        pass
    return {}


def auto_detect_ip_geolocation() -> dict:
    """Fetch geographical location based on public IP services if dynamic GPS is unavailable."""
    services = [
        ("https://ipapi.co/json/", lambda d: (f"{d.get('city')}, {d.get('country_name')}", float(d.get("latitude")), float(d.get("longitude")))),
        ("http://ip-api.com/json/", lambda d: (f"{d.get('city')}, {d.get('country')}", float(d.get("lat")), float(d.get("lon")))),
    ]
    for url, parser in services:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "IEEE-CSV-Logger/1.0"})
            with urllib.request.urlopen(req, timeout=3) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode("utf-8"))
                    loc_name, lat, lon = parser(data)
                    if loc_name and lat and lon:
                        return {
                            "location": loc_name,
                            "latitude": round(lat, 6),
                            "longitude": round(lon, 6),
                        }
        except Exception:
            continue

    return {
        "location": DEFAULT_LOCATION_NAME,
        "latitude": DEFAULT_LATITUDE,
        "longitude": DEFAULT_LONGITUDE,
    }


def resolve_current_location(
    api_url: str,
    cli_loc: str | None,
    cli_lat: float | None,
    cli_lon: float | None,
    cam_meta: dict,
) -> tuple[str, float, float]:
    """Resolve location using priority: CLI Args > Dynamic Backend GPS > Camera Meta > Env Vars > IP Geo."""
    # 1. CLI Explicit Arguments
    if cli_loc and cli_lat is not None and cli_lon is not None:
        return cli_loc, cli_lat, cli_lon

    # 2. Dynamic Backend GPS (Synced from browser/client)
    dyn = fetch_dynamic_backend_location(api_url)
    if dyn.get("latitude") and dyn.get("longitude") and dyn.get("latitude") != 0.0:
        loc_name = cli_loc or dyn.get("location", "Dynamic Location")
        lat = cli_lat if cli_lat is not None else dyn["latitude"]
        lon = cli_lon if cli_lon is not None else dyn["longitude"]
        return loc_name, lat, lon

    # 3. Camera Metadata
    cam_loc = cam_meta.get("location")
    cam_lat = cam_meta.get("latitude")
    cam_lon = cam_meta.get("longitude")
    if cam_loc and cam_lat is not None and cam_lon is not None:
        return cli_loc or cam_loc, cli_lat if cli_lat is not None else cam_lat, cli_lon if cli_lon is not None else cam_lon

    # 4. Environment Variables
    env_loc = os.getenv("GEO_LOCATION")
    env_lat = float(os.getenv("GEO_LATITUDE")) if os.getenv("GEO_LATITUDE") else None
    env_lon = float(os.getenv("GEO_LONGITUDE")) if os.getenv("GEO_LONGITUDE") else None
    if env_loc and env_lat is not None and env_lon is not None:
        return cli_loc or env_loc, cli_lat if cli_lat is not None else env_lat, cli_lon if cli_lon is not None else env_lon

    # 5. IP Geolocation Fallback
    ip_geo = auto_detect_ip_geolocation()
    loc_name = cli_loc or env_loc or cam_loc or ip_geo.get("location", DEFAULT_LOCATION_NAME)
    lat = cli_lat if cli_lat is not None else (env_lat if env_lat is not None else ip_geo.get("latitude", DEFAULT_LATITUDE))
    lon = cli_lon if cli_lon is not None else (env_lon if env_lon is not None else ip_geo.get("longitude", DEFAULT_LONGITUDE))

    return loc_name, lat, lon


def get_active_camera_id(api_url: str) -> tuple[str, dict]:
    """Fetch active camera_id and optional location metadata from backend API."""
    url = f"{api_url.rstrip('/')}/camera/list"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "IEEE-CSV-Logger/1.0"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            if resp.status == 200:
                data = json.loads(resp.read().decode("utf-8"))
                if isinstance(data, list) and len(data) > 0:
                    cam = data[0]
                    cam_id = str(cam.get("camera_id", "CAM"))
                    meta = {
                        "location": cam.get("location"),
                        "latitude": cam.get("latitude"),
                        "longitude": cam.get("longitude"),
                    }
                    return cam_id, meta
    except Exception as err:
        print(f"[Warning] Could not auto-detect camera from {url}: {err}", file=sys.stderr)
    return "CAM", {}


def fetch_people_count(api_url: str, camera_id: str) -> tuple[int, dict]:
    """Fetch current people count and full analytics dict from backend API."""
    url = f"{api_url.rstrip('/')}/analytics/current?camera_id={camera_id}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "IEEE-CSV-Logger/1.0"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            if resp.status == 200:
                data = json.loads(resp.read().decode("utf-8"))
                count = int(data.get("people_count", 0))
                return count, data
    except urllib.error.HTTPError as err:
        if err.code == 404:
            print(f"[Notice] Camera '{camera_id}' analytics not found. Defaulting count to 0.", file=sys.stderr)
        else:
            print(f"[Warning] HTTP Error {err.code} fetching analytics: {err.reason}", file=sys.stderr)
    except Exception as err:
        print(f"[Warning] Could not fetch analytics from API ({err}). Defaulting count to 0.", file=sys.stderr)

    return 0, {}


def get_next_serial_number(filepath: str) -> int:
    """Calculate next auto-increment serial number based on existing CSV file rows."""
    if not os.path.exists(filepath):
        return 1
    
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            header = next(reader, None)
            if not header:
                return 1
            rows = [r for r in reader if r]
            if not rows:
                return 1
            last_row = rows[-1]
            if last_row and last_row[0].isdigit():
                return int(last_row[0]) + 1
    except Exception as err:
        print(f"[Warning] Error reading existing CSV serial number: {err}", file=sys.stderr)
    return 1


def initialize_csv(filepath: str) -> None:
    """Initialize or upgrade CSV file with standard headers if missing or outdated."""
    file_exists = os.path.exists(filepath) and os.path.getsize(filepath) > 0
    if not file_exists:
        dirname = os.path.dirname(filepath)
        if dirname:
            os.makedirs(dirname, exist_ok=True)

        with open(filepath, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(CSV_HEADERS)
        print(f"[Info] Initialized new CSV file: '{filepath}'", file=sys.stderr)
    else:
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                reader = csv.reader(f)
                header = next(reader, None)
            if not header or ("Latitude" not in header or "Location" not in header):
                with open(filepath, "r", encoding="utf-8") as f:
                    lines = f.readlines()
                lines[0] = ",".join(CSV_HEADERS) + "\n"
                with open(filepath, "w", encoding="utf-8") as f:
                    f.writelines(lines)
                print(f"[Info] Updated CSV header in '{filepath}' to include location fields.", file=sys.stderr)
        except Exception as err:
            print(f"[Warning] Error verifying CSV header in '{filepath}': {err}", file=sys.stderr)


def log_entry(
    serial_no: int,
    people_count: int,
    camera_id: str,
    location: str,
    latitude: float,
    longitude: float,
    output_file: str,
    serial_connection=None,
) -> tuple[int, str]:
    """Write a single entry to CSV file, stdout, and optional serial port."""
    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    time_str = now.strftime("%H:%M:%S")
    timestamp_str = now.strftime("%Y-%m-%d %H:%M:%S")

    row = [
        serial_no,
        date_str,
        time_str,
        timestamp_str,
        people_count,
        camera_id,
        location,
        latitude,
        longitude,
    ]
    csv_line = f"{serial_no},{date_str},{time_str},{timestamp_str},{people_count},{camera_id},{location},{latitude},{longitude}"

    # 1. Append to CSV File
    with open(output_file, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(row)
        f.flush()

    # 2. Print CSV row to stdout
    print(csv_line, flush=True)

    # 3. Optional: Write to Hardware Serial Port
    if serial_connection is not None:
        try:
            serial_connection.write((csv_line + "\r\n").encode("utf-8"))
            serial_connection.flush()
        except Exception as err:
            print(f"[Error] Failed to send data to serial port: {err}", file=sys.stderr)

    return serial_no + 1, csv_line


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Log people detection count to CSV format every 2 minutes with dynamic geographical location for IEEE port integration."
    )
    parser.add_argument(
        "-o", "--output",
        default=DEFAULT_OUTPUT_FILE,
        help=f"Path to CSV output file (default: {DEFAULT_OUTPUT_FILE})"
    )
    parser.add_argument(
        "-i", "--interval",
        type=int,
        default=DEFAULT_INTERVAL_SECONDS,
        help=f"Logging interval in seconds (default: {DEFAULT_INTERVAL_SECONDS} seconds / 2 mins)"
    )
    parser.add_argument(
        "--api-url",
        default=DEFAULT_API_URL,
        help=f"CrowdVision backend API URL (default: {DEFAULT_API_URL})"
    )
    parser.add_argument(
        "--camera-id",
        default=None,
        help="Camera ID to fetch detection count for (default: auto-detect active camera)"
    )
    parser.add_argument(
        "-l", "--location",
        default=None,
        help="Geographical location name (e.g. 'Campus Gate'). Defaults to dynamic location."
    )
    parser.add_argument(
        "--lat", "--latitude",
        dest="latitude",
        type=float,
        default=None,
        help="Latitude coordinate (e.g. 18.5204)."
    )
    parser.add_argument(
        "--lon", "--longitude",
        dest="longitude",
        type=float,
        default=None,
        help="Longitude coordinate (e.g. 73.8567)."
    )
    parser.add_argument(
        "-p", "--serial-port",
        default=None,
        help="Optional hardware serial port (e.g. /dev/ttyUSB0 or COM3) for IEEE hardware port interface"
    )
    parser.add_argument(
        "-b", "--baudrate",
        type=int,
        default=9600,
        help="Serial port baud rate (default: 9600)"
    )
    parser.add_argument(
        "--run-once",
        action="store_true",
        help="Log a single reading immediately and exit"
    )
    parser.add_argument(
        "--no-immediate",
        action="store_true",
        help="Wait interval seconds before logging the first entry (default logs immediately on start)"
    )

    args = parser.parse_args()

    # Initialize Serial Port connection if specified
    ser = None
    if args.serial_port:
        try:
            import serial  # pyserial
            ser = serial.Serial(args.serial_port, args.baudrate, timeout=2)
            print(f"[Info] Connected to Serial Port '{args.serial_port}' at {args.baudrate} baud.", file=sys.stderr)
        except ImportError:
            print("[Error] 'pyserial' package is not installed. Run 'pip install pyserial' to use --serial-port.", file=sys.stderr)
            sys.exit(1)
        except Exception as err:
            print(f"[Error] Failed to open serial port '{args.serial_port}': {err}", file=sys.stderr)
            sys.exit(1)

    # Determine Camera ID & location metadata
    camera_id = args.camera_id
    cam_meta = {}
    if not camera_id:
        camera_id, cam_meta = get_active_camera_id(args.api_url)

    # Resolve initial location
    location_name, latitude, longitude = resolve_current_location(
        args.api_url, args.location, args.latitude, args.longitude, cam_meta
    )

    # Prepare CSV file
    initialize_csv(args.output)
    serial_no = get_next_serial_number(args.output)

    print(f"=== IEEE People Count CSV Logger Started ===", file=sys.stderr)
    print(f" Output File : {os.path.abspath(args.output)}", file=sys.stderr)
    print(f" Camera ID   : {camera_id}", file=sys.stderr)
    print(f" Initial Loc : {location_name} (Lat: {latitude}, Lon: {longitude})", file=sys.stderr)
    print(f" Interval    : {args.interval} seconds ({args.interval / 60:.1f} mins)", file=sys.stderr)
    print(f" Starting S.No: {serial_no}", file=sys.stderr)
    print(f" Format      : Serial_Number, Date, Time, Timestamp, People_Count, Camera_ID, Location, Latitude, Longitude", file=sys.stderr)
    print(f"--------------------------------------------------", file=sys.stderr)

    if args.run_once:
        count, _ = fetch_people_count(args.api_url, camera_id)
        location_name, latitude, longitude = resolve_current_location(
            args.api_url, args.location, args.latitude, args.longitude, cam_meta
        )
        log_entry(serial_no, count, camera_id, location_name, latitude, longitude, args.output, ser)
        print(f"[Info] Completed run-once task.", file=sys.stderr)
        return

    # Continuous Loop
    first_run = True
    try:
        while True:
            if not first_run or args.no_immediate:
                time.sleep(args.interval)
            first_run = False

            count, _ = fetch_people_count(args.api_url, camera_id)
            location_name, latitude, longitude = resolve_current_location(
                args.api_url, args.location, args.latitude, args.longitude, cam_meta
            )
            serial_no, _ = log_entry(
                serial_no, count, camera_id, location_name, latitude, longitude, args.output, ser
            )

    except KeyboardInterrupt:
        print("\n[Info] Logger stopped by user (Ctrl+C). Exiting cleanly.", file=sys.stderr)
    finally:
        if ser and ser.is_open:
            ser.close()


if __name__ == "__main__":
    main()
