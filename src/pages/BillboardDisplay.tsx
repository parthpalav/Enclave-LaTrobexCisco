import React, { useEffect, useState } from 'react';
import { useSocket } from '../hooks/useSocket';
import { Monitor, AlertOctagon, Radio, ShieldAlert, Sparkles, ShoppingBag, Trees, TrainTrack, MapPin, Clock, Activity } from 'lucide-react';
import { reverseGeocode } from '../services/reverseGeocoding';

interface Ad {
  id: number;
  category: string;
  title: string;
  tagline: string;
  badge: string;
  theme: string;
  icon: React.ReactNode;
}

const FAKE_ADS: Ad[] = [
  {
    id: 1,
    category: 'TOURISM BOARD',
    title: 'Visit Incredible India',
    tagline: 'Experience Rich Culture, Timeless Heritage & Breathtaking Wonders',
    badge: 'OFFICIAL TRAVEL PARTNER',
    theme: 'from-amber-950 via-orange-950 to-slate-950 border-amber-500/40 text-amber-100',
    icon: <Sparkles className="w-16 h-16 text-amber-400 animate-pulse" />,
  },
  {
    id: 2,
    category: 'SPECIAL PROMOTION',
    title: 'Summer Mega Sale',
    tagline: 'Up to 50% Off Top International Brands at Central City Mall',
    badge: 'LIMITED TIME OFFER',
    theme: 'from-emerald-950 via-teal-950 to-slate-950 border-emerald-500/40 text-emerald-100',
    icon: <ShoppingBag className="w-16 h-16 text-emerald-400 animate-bounce" />,
  },
  {
    id: 3,
    category: 'CIVIC CAMPAIGN',
    title: 'Go Green City Initiative',
    tagline: 'Plant Trees, Reduce Single-Use Plastic & Keep Our City Clean',
    badge: 'CLEAN & GREEN METRO',
    theme: 'from-green-950 via-emerald-950 to-slate-950 border-green-500/40 text-green-100',
    icon: <Trees className="w-16 h-16 text-green-400" />,
  },
  {
    id: 4,
    category: 'PUBLIC TRANSIT',
    title: 'Metro Rapid Transit',
    tagline: 'Fast, Clean & Eco-Friendly High-Speed City Commute Every 3 Mins',
    badge: 'COMMUTE SMART',
    theme: 'from-indigo-950 via-blue-950 to-slate-950 border-indigo-500/40 text-indigo-100',
    icon: <TrainTrack className="w-16 h-16 text-cyan-400" />,
  },
];

export const BillboardDisplay: React.FC = () => {
  const { isConnected, isEmergency, emergencyPayload } = useSocket();
  const [adIndex, setAdIndex] = useState<number>(0);
  const [locationName, setLocationName] = useState<string | null>(null);
  const [isResolvingLocation, setIsResolvingLocation] = useState<boolean>(false);
  const [lastUpdatedTime, setLastUpdatedTime] = useState<string>(new Date().toLocaleTimeString());

  // Cycle through fake ads every 5 seconds when NO emergency is active
  useEffect(() => {
    if (isEmergency) return;

    const interval = setInterval(() => {
      setAdIndex((prev) => (prev + 1) % FAKE_ADS.length);
    }, 5000);

    return () => clearInterval(interval);
  }, [isEmergency]);

  // Update last updated timestamp whenever socket status or emergency alert changes
  useEffect(() => {
    setLastUpdatedTime(new Date().toLocaleTimeString());
  }, [isEmergency, emergencyPayload]);

  // Reverse geocoding lookup when an emergency SOS payload arrives with GPS coordinates
  useEffect(() => {
    if (!isEmergency || !emergencyPayload) {
      setLocationName(null);
      return;
    }

    const lat = emergencyPayload.latitude;
    const lon = emergencyPayload.longitude;

    if (typeof lat === 'number' && typeof lon === 'number') {
      setIsResolvingLocation(true);
      reverseGeocode(lat, lon)
        .then((placeName) => {
          setLocationName(placeName);
        })
        .catch(() => {
          setLocationName(`${lat.toFixed(4)}, ${lon.toFixed(4)}`);
        })
        .finally(() => {
          setIsResolvingLocation(false);
        });
    } else {
      setLocationName('Location unavailable');
    }
  }, [isEmergency, emergencyPayload]);

  const currentAd = FAKE_ADS[adIndex];
  const formattedTime = emergencyPayload?.timestamp
    ? new Date(emergencyPayload.timestamp).toLocaleTimeString()
    : new Date().toLocaleTimeString();

  const isEarthquake = emergencyPayload?.disasterType === 'EARTHQUAKE' || emergencyPayload?.title?.toLowerCase().includes('earthquake');
  const bannerHeader = isEarthquake ? '🚨 EARTHQUAKE WARNING 🚨' : '🚨 PUBLIC SAFETY ALERT 🚨';
  const emergencyHeading = isEarthquake ? 'Earthquake detected. Evacuate to open ground immediately.' : 'OVERCROWDING DETECTED / EVACUATE IMMEDIATELY';

  return (
    <div className="h-screen w-screen bg-slate-950 text-slate-100 flex flex-col justify-between p-6 overflow-hidden select-none font-sans relative">
      {/* Background LED Mesh Pattern */}
      <div 
        className="absolute inset-0 opacity-20 pointer-events-none bg-[radial-gradient(#38bdf8_1px,transparent_1px)] [background-size:16px_16px]" 
        aria-hidden="true"
      />

      {/* Top LED Billboard Header */}
      <header className="relative z-10 flex items-center justify-between bg-slate-900/90 border border-slate-800 px-6 py-4 rounded-2xl shadow-xl backdrop-blur-md">
        <div className="flex items-center space-x-3">
          <div className="p-2 bg-slate-800 rounded-xl text-cyan-400 border border-slate-700">
            <Monitor className="w-6 h-6 animate-pulse" />
          </div>
          <div>
            <h1 className="text-xl font-extrabold tracking-wider text-white uppercase font-mono">
              CITY DIGITAL LED DISPLAY • SECTOR 4
            </h1>
            <p className="text-xs font-mono text-slate-400">
              ROADSIDE PUBLIC INFORMATION BROADCAST NETWORK
            </p>
          </div>
        </div>

        {/* Connection Badge */}
        <div className={`flex items-center space-x-2 px-4 py-2 rounded-full border text-xs font-bold font-mono ${
          isConnected
            ? 'bg-emerald-950/80 border-emerald-500/40 text-emerald-400'
            : 'bg-rose-950/80 border-rose-500/40 text-rose-400'
        }`}>
          <span className={`w-2.5 h-2.5 rounded-full ${isConnected ? 'bg-emerald-500 animate-ping' : 'bg-rose-500'}`} />
          <span>{isConnected ? 'LIVE FEED ACTIVE' : 'NETWORK OFFLINE'}</span>
        </div>
      </header>

      {/* Main Center Content: Switch between Advertisements Cycle & Emergency Alert Takeover */}
      {isEmergency ? (
        /* Emergency Takeover State with Geographic Location */
        <main className="relative z-10 flex-1 my-6 bg-gradient-to-br from-red-950 via-rose-950 to-slate-950 border-8 border-red-600 rounded-3xl p-8 flex flex-col items-center justify-center text-center shadow-2xl animate-pulse space-y-5">
          <div className="flex items-center space-x-3 bg-red-900/90 border border-red-500/60 px-6 py-3 rounded-2xl shadow-2xl">
            <ShieldAlert className="w-9 h-9 text-red-100 animate-bounce shrink-0" />
            <h2 className="text-2xl font-black tracking-widest text-white uppercase">
              {bannerHeader}
            </h2>
          </div>

          <div className="space-y-3 max-w-3xl">
            <div className="w-20 h-20 mx-auto rounded-full bg-red-900/80 border-2 border-red-400 flex items-center justify-center shadow-2xl">
              {isEarthquake ? (
                <Activity className="w-12 h-12 text-amber-200 animate-ping" />
              ) : (
                <AlertOctagon className="w-12 h-12 text-red-100 animate-ping" />
              )}
            </div>

            <h3 className="text-3xl font-black text-amber-200 tracking-tight uppercase leading-tight">
              {emergencyHeading}
            </h3>

            {/* Geographic Location Display Section */}
            <div className="bg-red-900/70 border border-red-500/60 p-4 rounded-2xl max-w-xl mx-auto space-y-1 shadow-inner">
              <p className="text-xs font-bold text-red-200 uppercase tracking-widest flex items-center justify-center gap-1.5">
                <MapPin className="w-4 h-4 text-red-300 animate-bounce" />
                <span>Emergency reported near</span>
              </p>

              <h4 className="text-2xl font-black text-amber-200 tracking-wide uppercase">
                {isResolvingLocation ? (
                  <span className="animate-pulse">Resolving location coordinates...</span>
                ) : (
                  locationName || 'Location unavailable'
                )}
              </h4>
            </div>

            <p className="text-lg font-bold text-red-100 max-w-xl mx-auto leading-relaxed">
              AVOID ENTERING THE AFFECTED AREA. EMERGENCY SERVICES ARE RESPONDING.
            </p>
          </div>

          <div className="bg-red-900/80 border border-red-500 px-6 py-2 rounded-2xl text-xs font-mono text-white font-bold tracking-widest">
            TIME OF BROADCAST: {formattedTime}
          </div>
        </main>
      ) : (
        /* Normal State: Cycling Advertisements */
        <main className={`relative z-10 flex-1 my-6 bg-gradient-to-br ${currentAd.theme} border-2 rounded-3xl p-10 flex flex-col items-center justify-center text-center shadow-2xl transition-all duration-700 space-y-6`}>
          <div className="px-4 py-1.5 bg-slate-900/80 border border-slate-700/60 rounded-full text-xs font-mono tracking-widest uppercase font-bold text-slate-300">
            {currentAd.category}
          </div>

          <div className="w-28 h-28 rounded-3xl bg-slate-900/60 border border-slate-700/60 flex items-center justify-center shadow-inner">
            {currentAd.icon}
          </div>

          <div className="space-y-3 max-w-2xl">
            <h2 className="text-5xl font-black tracking-tight text-white drop-shadow-md">
              {currentAd.title}
            </h2>
            <p className="text-xl font-semibold text-slate-200 leading-snug">
              {currentAd.tagline}
            </p>
          </div>

          <div className="px-5 py-2 bg-slate-950/70 border border-slate-800 rounded-xl text-xs font-mono text-slate-400 font-bold tracking-wider">
            {currentAd.badge}
          </div>
        </main>
      )}

      {/* Bottom Ticker Bar with Live Timestamp Label */}
      <footer className="relative z-10 bg-slate-900/90 border border-slate-800 px-6 py-3 rounded-2xl flex items-center justify-between text-xs font-mono text-slate-400 backdrop-blur-md">
        <div className="flex items-center space-x-2">
          <Radio className="w-4 h-4 text-cyan-400 animate-pulse" />
          <span>BROADCAST CHANNEL: PUBLIC-EMERGENCY-DISPLAY-01</span>
        </div>
        <div className="flex items-center space-x-2 text-slate-300 font-bold">
          <Clock className="w-3.5 h-3.5 text-cyan-400" />
          <span>Last Updated: {lastUpdatedTime}</span>
        </div>
      </footer>
    </div>
  );
};
