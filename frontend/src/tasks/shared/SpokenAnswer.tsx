import type { SelfRating } from "../../api/types";
import type { TaskProps } from "../types";
import styles from "../Tasks.module.css";

const LABELS: Record<keyof Omit<SelfRating, "correct">, string> = {
  content: "Content",
  fluency: "Fluency",
  pronunciation: "Pronunciation",
};

function RatingRow({
  label,
  value,
  onChange,
  disabled,
}: {
  label: string;
  value: number | undefined;
  onChange: (n: number) => void;
  disabled: boolean;
}) {
  return (
    <div className={styles.ratingRow} role="group" aria-label={label}>
      <span>{label}</span>
      {[1, 2, 3, 4, 5].map((n) => (
        <button
          key={n}
          type="button"
          className={value === n ? styles.ratingButtonOn : styles.ratingButton}
          onClick={() => onChange(n)}
          disabled={disabled}
          aria-pressed={value === n}
        >
          {n}
        </button>
      ))}
    </div>
  );
}

/**
 * Recording status, the live transcript and the self rating fallback used by every speaking task.
 * Recordings stay in the browser; only the transcript and ratings are submitted.
 */
export function SpokenAnswer({ stage, recorder, response, onChange, review, question, type }: TaskProps) {
  const rating = response.self_rating ?? {};
  const transcript = review ? question.response?.transcript ?? "" : recorder?.transcript ?? response.transcript ?? "";
  const isShortAnswer = type.code === "ASQ";
  const needsContentRating = !transcript.trim();
  const setRating = (key: keyof SelfRating, value: number | boolean) =>
    onChange({ ...response, self_rating: { ...rating, [key]: value } });

  let status: string;
  if (review) status = "Your answer";
  else if (stage === "answer") status = "Recording… speak now";
  else if (stage === "prep") status = "Recording starts when the preparation time ends";
  else if (stage === "done") status = "Recording complete";
  else status = "Waiting for the audio to finish";

  return (
    <div className={styles.panel}>
      <div className={styles.recordBox}>
        <div className={styles.recordStatus} aria-live="polite">
          <span className={stage === "answer" && !review ? styles.dotLive : styles.dot} aria-hidden />
          {status}
        </div>

        {recorder && !recorder.recognitionSupported && !review && (
          <div className={styles.notice}>
            Your browser can't turn speech into text (Chrome and Edge can). You can still record and listen back,
            then rate your own answer below.
          </div>
        )}
        {recorder?.error && !review && <div className={styles.notice}>{recorder.error}</div>}

        {(stage === "answer" || stage === "done" || review) && (
          <div>
            <div className={styles.audioHint}>What we heard</div>
            <div className={styles.transcript}>{transcript || "No speech picked up yet."}</div>
          </div>
        )}

        {recorder?.audioUrl && !review && (
          <audio controls src={recorder.audioUrl}>
            <track kind="captions" />
          </audio>
        )}

        {(stage === "done" || review) && (
          <div className={styles.rating}>
            {isShortAnswer ? (
              needsContentRating && (
                <div className={styles.ratingRow}>
                  <span>Did you say the right answer?</span>
                  <button
                    type="button"
                    className={rating.correct === true ? styles.ratingButtonOn : styles.ratingButton}
                    style={{ width: "auto", padding: "0 0.8rem", borderRadius: 999 }}
                    onClick={() => setRating("correct", true)}
                    disabled={review}
                  >
                    Yes
                  </button>
                  <button
                    type="button"
                    className={rating.correct === false ? styles.ratingButtonOn : styles.ratingButton}
                    style={{ width: "auto", padding: "0 0.8rem", borderRadius: 999 }}
                    onClick={() => setRating("correct", false)}
                    disabled={review}
                  >
                    No
                  </button>
                </div>
              )
            ) : (
              <>
                <div className={styles.audioHint}>
                  {needsContentRating
                    ? "We didn't get a transcript, so rate your own answer from 1 (weak) to 5 (excellent)."
                    : "Optional: listen back and rate your delivery from 1 (weak) to 5 (excellent)."}
                </div>
                {needsContentRating && (
                  <RatingRow label={LABELS.content} value={rating.content} onChange={(n) => setRating("content", n)} disabled={review} />
                )}
                <RatingRow label={LABELS.fluency} value={rating.fluency} onChange={(n) => setRating("fluency", n)} disabled={review} />
                <RatingRow
                  label={LABELS.pronunciation}
                  value={rating.pronunciation}
                  onChange={(n) => setRating("pronunciation", n)}
                  disabled={review}
                />
              </>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
