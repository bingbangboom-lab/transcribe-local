import marimo

app = marimo.App(width="medium")


@app.cell
def _():
    import tempfile
    from pathlib import Path

    import marimo as mo
    import transcribe_cpp

    from transcribe import DEFAULT_OUTPUT_DIR, KNOWN_MODELS, resolve_model, transcribe_file
    return (
        DEFAULT_OUTPUT_DIR,
        KNOWN_MODELS,
        Path,
        mo,
        resolve_model,
        tempfile,
        transcribe_cpp,
        transcribe_file,
    )


@app.cell
def _(mo):
    mo.md(
        """
        # transcribe-local

        Upload an audio file and transcribe it locally. The transcript is also
        saved as a `.txt` file in the `output/` folder.
        """
    )


@app.cell
def _(KNOWN_MODELS, mo):
    audio_file = mo.ui.file(kind="area", label="Audio file")
    model_choice = mo.ui.dropdown(options=list(KNOWN_MODELS), value="parakeet", label="Model")
    language = mo.ui.text(label="Language (e.g. en-US or auto; leave empty for default)")
    with_timestamps = mo.ui.switch(value=True, label="Timestamps")
    run_button = mo.ui.run_button(label="Transcribe")

    mo.vstack([audio_file, model_choice, language, with_timestamps, run_button])
    return audio_file, language, model_choice, run_button, with_timestamps


@app.cell
def _(
    DEFAULT_OUTPUT_DIR,
    Path,
    audio_file,
    language,
    mo,
    model_choice,
    resolve_model,
    run_button,
    tempfile,
    transcribe_cpp,
    transcribe_file,
    with_timestamps,
):
    mo.stop(not run_button.value, mo.md("Upload a file and press **Transcribe**."))
    mo.stop(not audio_file.value, mo.md("Please upload an audio file first."))

    model_path = resolve_model(model_choice.value)
    mo.stop(not model_path.is_file(), mo.md(f"Model not found: `{model_path}`. See the README for download instructions."))

    uploaded = audio_file.value[0]
    DEFAULT_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as tmp_dir:
        audio_path = Path(tmp_dir) / uploaded.name
        audio_path.write_bytes(uploaded.contents)

        with transcribe_cpp.Model(str(model_path)) as model:
            output_path = transcribe_file(
                audio_path,
                model,
                DEFAULT_OUTPUT_DIR,
                with_timestamps=with_timestamps.value,
                language=language.value or None,
            )

    mo.vstack([
        mo.md(f"Saved to `{output_path}`"),
        mo.plain_text(output_path.read_text(encoding="utf-8")),
    ])


if __name__ == "__main__":
    app.run()
