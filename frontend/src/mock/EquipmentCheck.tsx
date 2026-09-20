import { useEffect, useState } from "react";

import { useRecorder } from "../hooks/useRecorder";
import { useSpeech } from "../hooks/useSpeech";
import styles from "./Mock.module.css";

/**
 * The headset check students do before the real test: play a sentence to check the speakers, then
 * record a few words and listen back to check the microphone.
 */
export function EquipmentCheck({ onReady }: { onReady: (ready: boolean) => void }) {
  const speech = useSpeech();
  const recorder = useRecorder();
  const [spoke, setSpoke] = useState(false);
  const [recorded, setRecorded] = useState(false);

  const ready = spoke && recorded;
  useEffect(() => onReady(ready), [ready, onReady]);
  useEffect(() => () => void recorder.stop(), []);

  return (
    <div>
      <h2>Check your equipment</h2>
      <p className={styles.saveNote}>
        The mock test plays audio once only and records your speaking answers, so check both now. Headphones with a
        microphone work best.
      </p>

      <div className={styles.checkRow}>
        <button
          type="button"
          className={styles.secondary}
          onClick={() =>
            speech.play("This is the audio check for your mock test. If you can hear this sentence clearly, your speakers are working.", () =>
              setSpoke(true),
            )
          }
        >
          {speech.speaking ? "Playing…" : "1. Test the audio"}
        </button>
        {spoke && <span className={styles.ok}>Audio played</span>}
        {!speech.supported && <span className={styles.bad}>This browser can't play the test audio.</span>}
      </div>

      <div className={styles.checkRow}>
        {!recorder.recording ? (
          <button
            type="button"
            className={styles.secondary}
            onClick={() => {
              setRecorded(false);
              void recorder.start();
            }}
          >
            2. Test the microphone
          </button>
        ) : (
          <button
            type="button"
            className={styles.secondary}
            onClick={() => {
              recorder.stop();
              setRecorded(true);
            }}
          >
            Stop recording
          </button>
        )}
        {recorder.recording && <span>Say a few words, then press stop.</span>}
        {recorded && recorder.audioUrl && (
          <audio controls src={recorder.audioUrl}>
            <track kind="captions" />
          </audio>
        )}
        {recorded && !recorder.audioUrl && <span className={styles.bad}>No recording was captured.</span>}
      </div>

      {recorder.error && <p className={styles.bad}>{recorder.error}</p>}
      {recorded && recorder.transcript && <p className={styles.saveNote}>What we heard: {recorder.transcript}</p>}
      {recorded && !recorder.recognitionSupported && (
        <p className={styles.saveNote}>
          This browser can't turn speech into text, so you'll rate your own speaking answers. Chrome and Edge can do it
          automatically.
        </p>
      )}
    </div>
  );
}
