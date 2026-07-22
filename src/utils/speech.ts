const DEFAULT_EMERGENCY_MESSAGE =
  'Attention. Threat detected. Evacuation protocol activated. Please remain calm and proceed to the nearest safe exit.';

// Store active utterance in a global reference to prevent Chrome garbage collection bug
let activeUtterance: SpeechSynthesisUtterance | null = null;

/**
 * Synthesizes a 2-tone public address warning chime (Beep... Beep...)
 * using the browser Web Audio API.
 */
export function playWarningChime(): Promise<void> {
  return new Promise((resolve) => {
    try {
      const AudioCtx =
        window.AudioContext ||
        (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;

      if (!AudioCtx) {
        console.log('[Speech Diagnostic] Web Audio API AudioContext not available');
        return resolve();
      }

      const ctx = new AudioCtx();

      if (ctx.state === 'suspended') {
        ctx.resume().catch(() => {});
      }

      // Tone 1 (523.25 Hz - C5)
      const osc1 = ctx.createOscillator();
      const gain1 = ctx.createGain();
      osc1.type = 'sine';
      osc1.frequency.setValueAtTime(523.25, ctx.currentTime);
      gain1.gain.setValueAtTime(0.25, ctx.currentTime);
      osc1.connect(gain1);
      gain1.connect(ctx.destination);

      osc1.start(ctx.currentTime);
      osc1.stop(ctx.currentTime + 0.15);

      // Tone 2 (659.25 Hz - E5)
      const osc2 = ctx.createOscillator();
      const gain2 = ctx.createGain();
      osc2.type = 'sine';
      osc2.frequency.setValueAtTime(659.25, ctx.currentTime + 0.18);
      gain2.gain.setValueAtTime(0.3, ctx.currentTime + 0.18);
      osc2.connect(gain2);
      gain2.connect(ctx.destination);

      osc2.start(ctx.currentTime + 0.18);
      osc2.stop(ctx.currentTime + 0.45);

      setTimeout(() => {
        ctx.close().catch(() => {});
        resolve();
      }, 500);
    } catch (err) {
      console.warn('[Speech Diagnostic] Web Audio chime error:', err);
      resolve();
    }
  });
}

/**
 * Helper to select best available English voice from SpeechSynthesis.
 */
function getEnglishVoice(synth: SpeechSynthesis): SpeechSynthesisVoice | null {
  const voices = synth.getVoices();
  console.log(`[Speech Diagnostic] Available voices count: ${voices.length}`);
  if (!voices || voices.length === 0) return null;

  const englishVoice =
    voices.find((v) => v.lang.startsWith('en-US') || v.lang.startsWith('en-GB')) ||
    voices.find((v) => v.lang.startsWith('en'));

  if (englishVoice) {
    console.log(`[Speech Diagnostic] Selected voice: ${englishVoice.name} (${englishVoice.lang})`);
  }
  return englishVoice || null;
}

/**
 * Performs actual speech dispatch with full event listeners & error logging.
 */
function executeSpeech(textToSpeak: string): void {
  const synth = window.speechSynthesis;

  // 1. Cancel previous speech and unpause queue if stuck
  synth.cancel();
  if (synth.paused) {
    synth.resume();
  }

  // 2. Create utterance instance and retain reference to prevent GC
  const utterance = new SpeechSynthesisUtterance(textToSpeak);
  activeUtterance = utterance;

  utterance.rate = 0.9;
  utterance.pitch = 1.0;
  utterance.volume = 1.0;

  // Voice Selection
  const voice = getEnglishVoice(synth);
  if (voice) {
    utterance.voice = voice;
  } else {
    console.log('[Speech Diagnostic] Voices list empty or loading asynchronously, using browser default voice.');
  }

  // Event Listeners for Diagnostics
  utterance.onstart = () => {
    console.log('[Speech Diagnostic] 🔊 SpeechSynthesisUtterance STARTED speaking!');
  };

  utterance.onend = () => {
    console.log('[Speech Diagnostic] ✅ SpeechSynthesisUtterance ENDED cleanly.');
    activeUtterance = null;
  };

  utterance.onerror = (event) => {
    console.error('[Speech Diagnostic] ❌ SpeechSynthesisUtterance ERROR:', event.error, event);
    activeUtterance = null;
  };

  console.log('[Speech Diagnostic] Calling window.speechSynthesis.speak()...');
  synth.speak(utterance);
  console.log('[Speech Diagnostic] window.speechSynthesis.speak() invoked. Speaking status:', synth.speaking, 'Pending:', synth.pending);

  // Resume queue if browser suspended speech dispatch
  if (synth.paused) {
    synth.resume();
  }
}

/**
 * Triggers the browser's native Web Speech API (window.speechSynthesis)
 * to announce the emergency warning.
 *
 * @param message - Optional custom message to announce
 */
export function speakEmergency(message?: string): void {
  console.log('[Speech Diagnostic] speakEmergency() called.');

  const hasSpeechSynth = typeof window !== 'undefined' && 'speechSynthesis' in window;
  console.log(`[Speech Diagnostic] window.speechSynthesis exists: ${hasSpeechSynth}`);

  if (!hasSpeechSynth) {
    console.warn('Web Speech API (speechSynthesis) is not supported by this browser.');
    return;
  }

  const textToSpeak = message || DEFAULT_EMERGENCY_MESSAGE;

  // Play attention chime first, then execute speech
  playWarningChime().then(() => {
    const synth = window.speechSynthesis;

    // Check if voices are loaded or waiting on 'voiceschanged'
    const voices = synth.getVoices();
    if (voices.length === 0 && 'onvoiceschanged' in synth) {
      console.log('[Speech Diagnostic] Voices array is empty. Registering onvoiceschanged listener...');
      synth.onvoiceschanged = () => {
        console.log('[Speech Diagnostic] onvoiceschanged fired.');
        synth.onvoiceschanged = null;
        executeSpeech(textToSpeak);
      };
      // Fallback timeout in case onvoiceschanged does not fire
      setTimeout(() => {
        if (activeUtterance === null) {
          executeSpeech(textToSpeak);
        }
      }, 300);
    } else {
      executeSpeech(textToSpeak);
    }
  });
}

/**
 * Immediately cancels any active speech synthesis playback.
 */
export function stopEmergencySpeech(): void {
  console.log('[Speech Diagnostic] stopEmergencySpeech() called.');
  if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
    try {
      window.speechSynthesis.cancel();
      activeUtterance = null;
      console.log('[Speech Diagnostic] window.speechSynthesis.cancel() executed.');
    } catch (err) {
      console.warn('Failed to stop speech synthesis:', err);
    }
  }
}
