"""
Marimo notebook with the LLM benchmark report.

Export to static HTML:
marimo export html --no-include-code report.py -o report.html -- \
    --results RESULTS_DIR

Open interactively:
marimo edit report.py -- --results RESULTS_DIR

RESULTS_DIR is loaded with make_report.load_results().
"""

import marimo

__generated_with = "0.25.1"
app = marimo.App(width="full", app_title="LLM benchmark")


@app.cell
def _():
    import sys
    from pathlib import Path

    import altair as alt
    import marimo as mo

    sys.path.insert(0, str(mo.notebook_dir()))
    import make_report

    results_dir = Path(mo.cli_args().get("results", "results"))
    summary, per_test = make_report.load_results(results_dir)
    data = alt.Data(values=summary)
    height = max(120, 22 * len(summary))
    return alt, data, height, make_report, mo, per_test, results_dir, summary


@app.cell
def _(alt, height):
    def bar(data, field: str, title: str, sort: str = "-x") -> alt.Chart:
        return (
            alt.Chart(data, title=title)
            .transform_filter(f"isValid(datum['{field}'])")
            .mark_bar()
            .encode(
                x=alt.X(f"{field}:Q", title=field),
                y=alt.Y("Model:N", sort=sort, title=None),
                color="Provider:N",
                tooltip=["Model:N", f"{field}:Q"],
            )
            .properties(width=420, height=height)
        )

    return (bar,)


@app.cell
def _(mo, per_test, results_dir, summary):
    mo.md(
        f"""
        # LLM GUI navigation benchmark

        {len(summary)} models, {len(per_test)} tests, from `{results_dir}`.
        Each model drives an Ubuntu 24.04 desktop live session over VNC, see
        the notes at the end.
        """
    )
    return


@app.cell
def _(mo, summary):
    mo.vstack(
        [mo.md("## Summary per model"), mo.ui.table(summary, selection=None)]
    )
    return


@app.cell
def _(alt, bar, height, mo, summary):
    _efficiency = [
        {
            "Model": s["Model"],
            "Provider": s["Provider"],
            "Tests passed": s["Passed"],
            "Total USD": s["Cost (USD)"],
            "USD per passed test": s["USD / passed test"],
            "Passed tests per $1": s["Passed tests per $1"],
        }
        for s in summary
        if s["Cost (USD)"]
    ]
    _efficiency.sort(key=lambda e: -e["Passed tests per $1"])
    _data = alt.Data(values=_efficiency)
    _points = alt.Chart(
        _data, title="Cost vs. success (top-left is best)"
    ).encode(
        x=alt.X("Total USD:Q"),
        y=alt.Y("Tests passed:Q"),
        color="Provider:N",
        tooltip=["Model:N", "Tests passed:Q", "Total USD:Q"],
    )
    mo.vstack(
        [
            mo.md("## Cost efficiency"),
            mo.ui.table(_efficiency, selection=None),
            alt.hconcat(
                bar(
                    _data,
                    "Passed tests per $1",
                    "Passed tests per $1 (higher is better)",
                ),
                bar(
                    _data,
                    "USD per passed test",
                    "Cost per passed test in USD (lower is better)",
                    sort="x",
                ),
            ),
            (
                _points.mark_circle(size=80)
                + _points.mark_text(align="left", dx=6).encode(text="Model:N")
            ).properties(width=900, height=max(400, height)),
        ]
    )
    return


@app.cell
def _(alt, bar, data, height, mo):
    _tokens = (
        alt.Chart(data, title="Tokens per model")
        .transform_fold(
            ["Prompt tokens", "Completion tokens"], as_=["Kind", "Tokens"]
        )
        .mark_bar()
        .encode(
            x=alt.X("Tokens:Q", stack="zero"),
            y=alt.Y("Model:N", sort="-x", title=None),
            color=alt.Color("Kind:N", scale=alt.Scale(scheme="set2")),
            tooltip=["Model:N", "Kind:N", "Tokens:Q"],
        )
        .properties(width=420, height=height)
    )
    mo.vstack(
        [
            mo.md("## Charts"),
            alt.vconcat(
                alt.hconcat(
                    bar(data, "Passed", "Tests passed"),
                    bar(data, "Cost (USD)", "Total cost (USD)"),
                ),
                alt.hconcat(
                    _tokens,
                    bar(data, "Inference time (s)", "Total inference time"),
                ).resolve_scale(color="independent"),
                bar(
                    data,
                    "Avg latency / request (s)",
                    "Average latency per request",
                ),
            ).resolve_scale(color="independent"),
        ]
    )
    return


@app.cell
def _(mo, per_test, summary):
    _tests = list(dict.fromkeys(t["Test"] for t in per_test))
    _status = {(t["Model"], t["Test"]): t["Status"] for t in per_test}
    _matrix = [
        {
            "Model": s["Model"],
            **{t: _status.get((s["Model"], t), "") for t in _tests},
            "Passed": s["Passed"],
        }
        for s in summary
    ]
    mo.vstack([mo.md("## Pass matrix"), mo.ui.table(_matrix, selection=None)])
    return


@app.cell
def _(mo, per_test):
    mo.vstack([mo.md("## Per test"), mo.ui.table(per_test, selection=None)])
    return


@app.cell
def _(make_report, mo):
    mo.md(
        "## Notes\n\n"
        + "\n".join(f"- **{k}**: {v}" for k, v in make_report.NOTES)
    )
    return


if __name__ == "__main__":
    app.run()
