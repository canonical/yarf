# 0002 - Search inside windows when OCR misses text

- Status: Proposed
- Date: 2026-11-16

## Context

RapidOCR 3.9 changed its default models to PP-OCRv6 small. Since then,
`Match Text` misses text that is plainly on screen
([#310](https://github.com/canonical/yarf/issues/310)).

The text detection model is at fault, not recognition. Whether it finds text
depends on the whole image and its exact size, not on the size of the text. In
the reported screenshots it finds the missing text once the image is cropped to
the window that holds it.

YARF uses only the models shipped in the RapidOCR wheel. It must not depend on
downloading other models in CI or inside the snap.

## Decision

When a text search finds no match, YARF repeats the same search inside each
window-like region of the screenshot. A cheap image-processing step proposes the
regions, with no extra model. Where nested windows find the same text, YARF
keeps the closest match.

The fallback sits outside the OCR engines. It only changes which part of the
screenshot an engine reads, so it works the same for RapidOCR, Tesseract, and
any engine added later.

The fallback is on by default. Tests can turn it off per call or for a whole
suite. A search that already matches takes the same path as before. Reading all
text on screen has no miss to react to, so it searches windows only when a test
opts in.

## Alternatives considered

- **Switch to the PP-OCRv4 or PP-OCRv5 detector.** It finds the missed text, but
  it is not in the wheel. Shipping it ourselves adds a model to maintain, and
  the PP-OCRv4 detector lost isolated symbols such as `×` and `π`.
- **Fix it inside the RapidOCR reader.** Other engines would not get the
  fallback, and it would depend on one engine's internals.
- **Always search inside windows.** This costs extra on every call and changes
  results for searches that work today.
- **Opt in only.** The tests affected by #310 would keep failing until their
  authors found the option.
- **Upscale, tile, or detect at several scales.** These were slower and found
  less than window crops in our comparison.
- **Another OCR engine.** Tesseract is weaker on user interface text. OnnxTR
  found less and downloads its models. ocrs reports no confidence and reads
  only ASCII.

## Consequences

- A search that misses now costs more. This affects waits in `Match Text` and
  checks that text is absent.
- A check that text is absent can now fail where OCR used to miss text that was
  on screen.
- The fallback only adds results. If no window is found, results match the
  behavior before this decision.
- Every OCR engine must support searching within a region of the image, which
  is how the fallback reaches it.
- The window proposal is a heuristic, tuned on a few screenshots. Adjust it
  against real failures rather than replacing it with a model download.
- The keyword suite keeps the #310 screenshots. Re-check them whenever an OCR
  engine or its bundled models change.
