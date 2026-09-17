import { useCallback, useEffect, useRef, useState } from "react";

import type { Turn } from "../api/types";

/** Split text into sentences. Browsers cut off long utterances, so each sentence is spoken separately. */
export function splitSentences(text: string): string[] {
  return text
    .replace(/\s+/g, " ")
    .split(/(?<=[.!?])\s+/)
    .map((s) => s.trim())
    .filter(Boolean);
}

/** Tests and screenshots can skip audio with ?skipAudio=1 or localStorage "pte:skip-audio" = "1". */
export function shouldSkipAudio(): boolean {
  try {
    if (new URLSearchParams(window.location.search).get("skipAudio") === "1") return true;
    return window.localStorage.getItem("pte:skip-audio") === "1";
  } catch {
    return false;
  }
}

interface Line {
  text: string;
  voiceIndex: number;
}

function englishVoices(): SpeechSynthesisVoice[] {
  const voices = window.speechSynthesis.getVoices();
  const english = voices.filter((v) => v.lang.toLowerCase().startsWith("en"));
  const preferred = ["en-au", "en-nz", "en-gb", "en-us"];
  return english.sort(
    (a, b) => preferred.indexOf(a.lang.toLowerCase()) - preferred.indexOf(b.lang.toLowerCase()),
  );
}

export interface Speech {
  supported: boolean;
  speaking: boolean;
  play: (script: string | Turn[], onEnd?: () => void) => void;
  stop: () => void;
}

export function useSpeech(): Speech {
  const supported = typeof window !== "undefined" && "speechSynthesis" in window;
  const [speaking, setSpeaking] = useState(false);
  const runId = useRef(0);
  const skipTimer = useRef<number>();

  const stop = useCallback(() => {
    runId.current += 1;
    window.clearTimeout(skipTimer.current);
    if (supported) window.speechSynthesis.cancel();
    setSpeaking(false);
  }, [supported]);

  const play = useCallback(
    (script: string | Turn[], onEnd?: () => void) => {
      stop();
      const run = runId.current;
      const finish = () => {
        if (run !== runId.current) return;
        setSpeaking(false);
        onEnd?.();
      };
      setSpeaking(true);

      if (shouldSkipAudio() || !supported) {
        skipTimer.current = window.setTimeout(finish, shouldSkipAudio() ? 300 : 0);
        return;
      }

      const speakers: string[] = [];
      const lines: Line[] =
        typeof script === "string"
          ? splitSentences(script).map((text) => ({ text, voiceIndex: 0 }))
          : script.flatMap((turn) => {
              if (!speakers.includes(turn.speaker)) speakers.push(turn.speaker);
              const voiceIndex = speakers.indexOf(turn.speaker);
              return splitSentences(turn.text).map((text) => ({ text, voiceIndex }));
            });

      const voices = englishVoices();
      let index = 0;
      const speakNext = () => {
        if (run !== runId.current) return;
        if (index >= lines.length) {
          finish();
          return;
        }
        const line = lines[index++];
        const utterance = new SpeechSynthesisUtterance(line.text);
        if (voices.length) utterance.voice = voices[line.voiceIndex % voices.length];
        utterance.lang = utterance.voice?.lang ?? "en-AU";
        utterance.rate = 0.95;
        // Different speakers in a discussion also get a slightly different pitch.
        utterance.pitch = 1 + ((line.voiceIndex % 3) - 1) * 0.15;
        utterance.onend = speakNext;
        utterance.onerror = speakNext;
        window.speechSynthesis.speak(utterance);
      };
      speakNext();
    },
    [stop, supported],
  );

  useEffect(() => stop, [stop]);

  return { supported, speaking, play, stop };
}
