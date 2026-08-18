"""Development runtime for Muse 2 acquisition and valid window reporting."""

import argparse
import time
from typing import Callable, Optional, Sequence

from backend.app.eeg.buffer import EEGInferenceBuffer, WINDOW_SIZE
from backend.app.eeg.contracts import (
    EEGChunk,
    MUSE_EEG_CHANNEL_ORDER,
    SAMPLING_RATE_HZ,
)
from backend.app.eeg.diagnostics import MusePhase1Diagnostics
from backend.app.eeg.window_validator import EEGWindowValidator
from backend.app.model.contracts import (
    CognitivePrediction,
    MODEL_OUTPUT_CLASSES,
)
from backend.app.model.exceptions import (
    InvalidModelInput,
    InvalidModelOutput,
    ModelExecutionError,
    ModelProviderLoadError,
)
from backend.app.model.inference_service import ModelInferenceService
from backend.app.model.provider import create_runtime_model_provider
from backend.app.muse.muse_collector import MuseCollector


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Collect Muse 2 EEG and report valid one-second windows.",
    )
    parser.add_argument(
        "--mac-address",
        help="Optional Muse 2 Bluetooth MAC address.",
    )
    parser.add_argument(
        "--serial-number",
        help="Optional Muse 2 device name/serial number.",
    )
    parser.add_argument(
        "--poll-interval",
        type=float,
        default=0.1,
        help="Seconds between BrainFlow buffer reads (default: 0.1).",
    )
    return parser


def predict_and_log_model_result(
    inference_service: ModelInferenceService,
    window: EEGChunk,
    write_line: Callable[[str], None] = print,
) -> Optional[CognitivePrediction]:
    """Isolate a single model failure so acquisition can continue."""

    try:
        prediction = inference_service.predict(window)
    except InvalidModelInput as error:
        write_line("MODEL INPUT INVALID")
        write_line(str(error))
        return None
    except InvalidModelOutput as error:
        write_line("MODEL OUTPUT INVALID")
        write_line(str(error))
        return None
    except ModelExecutionError as error:
        write_line("MODEL EXECUTION ERROR")
        write_line(str(error))
        return None

    write_line("MODEL PREDICTION")
    write_line("state: {0}".format(prediction.state))
    write_line("confidence: {0:.3f}".format(prediction.confidence))
    write_line("probabilities:")
    for state in MODEL_OUTPUT_CLASSES:
        write_line(
            "{0}: {1:.3f}".format(
                state,
                prediction.probabilities[state],
            )
        )
    return prediction


def run(
    mac_address: Optional[str] = None,
    serial_number: Optional[str] = None,
    poll_interval: float = 0.1,
) -> None:
    if poll_interval <= 0:
        raise ValueError("poll_interval must be positive")

    collector = MuseCollector(
        mac_address=mac_address,
        serial_number=serial_number,
    )
    buffer = EEGInferenceBuffer()
    validator = EEGWindowValidator()
    model_provider = create_runtime_model_provider()
    inference_service = ModelInferenceService(
        provider=model_provider,
        window_validator=validator,
    )
    diagnostics: Optional[MusePhase1Diagnostics] = None

    try:
        collector.connect()
        diagnostics = MusePhase1Diagnostics()
        print("Muse connected")
        print("Sampling rate:")
        print("{0} Hz".format(SAMPLING_RATE_HZ))
        print("Channel order:")
        for channel in MUSE_EEG_CHANNEL_ORDER:
            print(channel)
        print("Model provider:")
        print(model_provider.display_name)

        while True:
            chunk = collector.read_chunk()
            if chunk is None:
                time.sleep(poll_interval)
                continue

            print("Chunk received:")
            print("{0} samples".format(chunk.sample_count))
            diagnostics.observe_chunk(chunk)
            candidates = buffer.append(chunk)

            if not candidates:
                print("Buffer:")
                print(
                    "{0} / {1}".format(
                        buffer.buffered_sample_count,
                        WINDOW_SIZE,
                    )
                )

            for candidate in candidates:
                print("Buffer:")
                print("{0} / {0}".format(WINDOW_SIZE))
                validation = validator.validate(candidate)
                candidate_diagnostic = diagnostics.observe_candidate(
                    candidate,
                    validation,
                )
                if not validation.valid:
                    print("WINDOW SKIPPED")
                    print("validation:")
                    print("FAIL")
                    print(validation.reason)
                    print("maximum timestamp gap:")
                    maximum_gap = (
                        candidate_diagnostic.maximum_timestamp_gap_seconds
                    )
                    if maximum_gap is None:
                        print("n/a")
                    else:
                        print(
                            "{0:.6f} seconds ({1:.3f} ms)".format(
                                maximum_gap,
                                maximum_gap * 1_000.0,
                            )
                        )
                    continue

                print("WINDOW READY")
                print("shape:")
                print(candidate.samples.shape)
                print("validation:")
                print("PASS")
                print("duration:")
                print("{0:.6f} seconds".format(validation.duration_seconds))
                predict_and_log_model_result(inference_service, candidate)

            if candidates and buffer.buffered_sample_count:
                print("Buffer:")
                print(
                    "{0} / {1}".format(
                        buffer.buffered_sample_count,
                        WINDOW_SIZE,
                    )
                )

            time.sleep(poll_interval)
    except KeyboardInterrupt:
        print("Stopping Muse stream")
    finally:
        try:
            collector.close()
        finally:
            if diagnostics is not None:
                print(diagnostics.format_summary())


def main(argv: Optional[Sequence[str]] = None) -> None:
    args = build_argument_parser().parse_args(argv)
    try:
        run(
            mac_address=args.mac_address,
            serial_number=args.serial_number,
            poll_interval=args.poll_interval,
        )
    except ModelProviderLoadError as error:
        raise SystemExit(str(error)) from error


if __name__ == "__main__":
    main()
