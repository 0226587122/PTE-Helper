import { useCallback, useEffect, useRef, useState } from "react";

/* The Web Speech API isn't in the standard TypeScript DOM types yet. */
interface RecognitionResult {
  isFinal: boolean;
  0: { transcript: string };
}
interface RecognitionEvent {
  resultIndex: number;
  results: ArrayLike<RecognitionResult>;
}
interface Recognition {
  lang: string;
  continuous: boolean;
  interimResults: boolean;
  onresult: ((event: RecognitionEvent) => void) | null;
  onend: (() => void) | null;
  onerror: ((event: { error: string }) => void) | null;
  start: () => void;
  stop: () => void;
}
type RecognitionConstructor = new () => Recognition;

function recognitionConstructor(): RecognitionConstructor | null {
  const w = window as unknown as { SpeechRecognition?: RecognitionConstructor; webkitSpeechRecognition?: RecognitionConstructor };
  return w.SpeechRecognition ?? w.webkitSpeechRecognition ?? null;
}

export interface Recorder {
  recordingSupported: boolean;
  recognitionSupported: boolean;
  recording: boolean;
  transcript: string;
  audioUrl: string | null;
  error: string | null;
  start: () => Promise<void>;
  stop: () => string;
}

/**
 * Records the student's answer in the browser and transcribes it with the Web Speech API where available.
 * The recording stays on the device (a local blob URL for playback). Only the transcript is ever sent to the server.
 */
export function useRecorder(): Recorder {
  const recordingSupported =
    typeof navigator !== "undefined" && !!navigator.mediaDevices?.getUserMedia && typeof MediaRecorder !== "undefined";
  const recognitionSupported = typeof window !== "undefined" && recognitionConstructor() !== null;

  const [recording, setRecording] = useState(false);
  const [transcript, setTranscript] = useState("");
  const [audioUrl, setAudioUrl] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const finalText = useRef("");
  const interimText = useRef("");
  const active = useRef(false);
  const recorder = useRef<MediaRecorder | null>(null);
  const stream = useRef<MediaStream | null>(null);
  const recognition = useRef<Recognition | null>(null);

  const start = useCallback(async () => {
    if (active.current) return;
    setError(null);
    finalText.current = "";
    interimText.current = "";
    setTranscript("");
    setAudioUrl((url) => {
      if (url) URL.revokeObjectURL(url);
      return null;
    });
    active.current = true;
    setRecording(true);

    if (recordingSupported) {
      try {
        const media = await navigator.mediaDevices.getUserMedia({ audio: true });
        if (!active.current) {
          media.getTracks().forEach((t) => t.stop());
          return;
        }
        stream.current = media;
        const chunks: Blob[] = [];
        const mediaRecorder = new MediaRecorder(media);
        mediaRecorder.ondataavailable = (event) => event.data.size && chunks.push(event.data);
        mediaRecorder.onstop = () => {
          if (chunks.length) setAudioUrl(URL.createObjectURL(new Blob(chunks, { type: mediaRecorder.mimeType })));
          media.getTracks().forEach((t) => t.stop());
        };
        mediaRecorder.start();
        recorder.current = mediaRecorder;
      } catch {
        setError("We couldn't use your microphone. Check your browser's permission settings, then rate yourself below.");
      }
    }

    const Constructor = recognitionConstructor();
    if (Constructor) {
      const rec = new Constructor();
      rec.lang = "en-AU";
      rec.continuous = true;
      rec.interimResults = true;
      rec.onresult = (event) => {
        let interim = "";
        for (let i = event.resultIndex; i < event.results.length; i++) {
          const result = event.results[i];
          if (result.isFinal) finalText.current += `${result[0].transcript} `;
          else interim += result[0].transcript;
        }
        interimText.current = interim;
        setTranscript(`${finalText.current}${interim}`.trim());
      };
      rec.onerror = (event) => {
        if (event.error === "not-allowed") {
          setError("Speech recognition was blocked. You can still rate your own answer below.");
        }
      };
      // Chrome stops listening after a pause; restart while we're still recording.
      rec.onend = () => {
        if (active.current) {
          try {
            rec.start();
          } catch {
            /* already started */
          }
        }
      };
      try {
        rec.start();
        recognition.current = rec;
      } catch {
        /* recognition could not start; self rating remains available */
      }
    }
  }, [recordingSupported]);

  const stop = useCallback(() => {
    if (!active.current) return `${finalText.current}${interimText.current}`.trim();
    active.current = false;
    setRecording(false);
    recognition.current?.stop();
    recognition.current = null;
    if (recorder.current && recorder.current.state !== "inactive") recorder.current.stop();
    else stream.current?.getTracks().forEach((t) => t.stop());
    recorder.current = null;
    const text = `${finalText.current}${interimText.current}`.trim();
    setTranscript(text);
    return text;
  }, []);

  useEffect(
    () => () => {
      active.current = false;
      recognition.current?.stop();
      if (recorder.current && recorder.current.state !== "inactive") recorder.current.stop();
      stream.current?.getTracks().forEach((t) => t.stop());
    },
    [],
  );

  return { recordingSupported, recognitionSupported, recording, transcript, audioUrl, error, start, stop };
}
