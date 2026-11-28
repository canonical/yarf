# 0002 - Search inside windows when OCR misses text

- Status: Accepted
- Date: 2026-11-25

## Context

RapidOCR 3.9 changed its default models to PP-OCRv6 small. Since then,
`Match Text` misses text that is plainly on screen
([#310](https://github.com/canonical/yarf/issues/310)).

The text detection model is at fault, not recognition. Whether it finds text
depends on the whole image, not the size of the text. Cropping the reported
screenshots to the window that holds the text makes the model find it.

YARF must not depend on downloading models beyond those in the RapidOCR
wheel, in CI or in the snap.

## Decision

When a text search finds no match, YARF repeats the same search inside each
window-like region of the screenshot. A cheap image-processing step proposes
the regions. In `Match Text`, the window search stops at the keyword's
timeout.

The fallback sits outside the OCR engines, so it works the same for RapidOCR,
Tesseract, and any engine added later.

A Robot Framework variable, `${OCR_WINDOW_FALLBACK}`, is the only switch.
The fallback is on by default, and a run, suite, or test can turn it off.
There is no keyword argument, so removing the fallback later does not
break any suite. `Read Text` does not use the fallback.

The fallback is temporary. Remove it once the RapidOCR version bundled in the
wheel finds the #310 regression text without it. The keyword suite keeps a
skipped check for that text. Unskip it after a RapidOCR update to run it.

## Alternatives considered

- **Switch to the PP-OCRv4 or PP-OCRv5 detector.** It finds the missed text,
  but it is not in the wheel. Shipping it adds a model to maintain, and
  PP-OCRv4 lost isolated symbols such as `×` and `π`.
- **Always search inside windows on text searches.** This costs extra on
  every call and changes results for searches that work today.
- **Opt in only.** The tests affected by #310 would keep failing until their
  authors found the option.
- **A keyword argument for each call.** It gives finer control, but removing
  it with the fallback would break the suites that pass it.
- **Another engine or detector.** Tesseract, OnnxTR, and multi-scale
  detection found less on interface text or needed a model download.

## Consequences

- A text search that misses now costs more. `Match Text` checks the screen
  less often while it waits, and checks that text is absent take longer.
- A check that text is absent can now fail where OCR used to miss text that
  was on screen.
- The fallback only adds results, never removes them.
- The fallback requires every OCR engine to search within a region of the
  image.
- The keyword suite keeps the #310 screenshots. Re-check them whenever an OCR
  engine or its bundled models change.
