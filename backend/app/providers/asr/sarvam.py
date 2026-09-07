import json
import logging
import os
import tempfile

import httpx

from app.providers.asr.base import ASRProvider
from app.schemas.asr import ASRResponse, ASRSegment
from app.services.ffmpeg_service import FFmpegService

logger = logging.getLogger(__name__)

try:
    from sarvamai import SarvamAI
except ImportError:
    SarvamAI = None


class SarvamASR(ASRProvider):
    """
    ASR implementation for Sarvam AI.
    """

    def __init__(self, model: str, language: str, api_key: str):
        super().__init__(model, language)
        if not api_key:
            raise ValueError("SARVAM_API_KEY must be provided")
        if SarvamAI is None:
            raise ImportError(
                "sarvamai package is required. Install it using 'pip install sarvamai'"
            )

        self.api_key = api_key
        self.client = SarvamAI(api_subscription_key=self.api_key)

    @staticmethod
    def _coerce_response(response):
        if isinstance(response, dict):
            return response
        if hasattr(response, "model_dump"):
            return response.model_dump()
        return response.__dict__ if hasattr(response, "__dict__") else {}

    @staticmethod
    def _extract_text(payload):
        if isinstance(payload, dict):
            return payload.get("transcript") or payload.get("text") or ""
        return getattr(payload, "transcript", getattr(payload, "text", ""))

    @staticmethod
    def _extract_segments(payload):
        if not payload:
            return []

        timestamps = payload.get("timestamps") if isinstance(payload, dict) else getattr(payload, "timestamps", None)
        entries = None

        if isinstance(timestamps, dict):
            entries = timestamps.get("segments") or timestamps.get("items") or timestamps.get("results")
        elif isinstance(timestamps, list):
            entries = timestamps

        if entries is None:
            raw_segments = payload.get("segments") if isinstance(payload, dict) else getattr(payload, "segments", None)
            if isinstance(raw_segments, list):
                entries = raw_segments

        segments = []
        if isinstance(entries, list):
            for item in entries:
                if not isinstance(item, dict):
                    continue
                transcript = item.get("text") or item.get("transcript") or item.get("sentence") or ""
                start = item.get("start") if item.get("start") is not None else item.get("start_time")
                end = item.get("end") if item.get("end") is not None else item.get("end_time")
                if transcript:
                    segments.append(
                        ASRSegment(
                            transcript=transcript,
                            start_time=float(start) if start is not None else None,
                            end_time=float(end) if end is not None else None,
                        )
                    )
        return segments

    def _normalize_response(self, response, *, request_id=None) -> ASRResponse:
        payload = self._coerce_response(response)
        transcript = self._extract_text(payload)
        segments = self._extract_segments(payload)

        if isinstance(payload, dict):
            request_id = payload.get("request_id") or request_id
            language = payload.get("language_code") or payload.get("language") or self.language
            confidence = payload.get("language_probability") or payload.get("confidence")
        else:
            request_id = getattr(payload, "request_id", request_id)
            language = getattr(payload, "language_code", getattr(payload, "language", self.language))
            confidence = getattr(payload, "language_probability", getattr(payload, "confidence", None))

        return ASRResponse(
            transcript=transcript or "",
            language=language or self.language,
            provider="sarvam",
            model=self.model,
            confidence=float(confidence) if confidence is not None else None,
            segments=segments,
            request_id=request_id,
        )

    def _transcribe_direct(self, file_path: str) -> ASRResponse:
        with open(file_path, "rb") as f:
            response = self.client.speech_to_text.transcribe(
                file=f,
                model=self.model,
                language_code=self.language,
            )
        return self._normalize_response(response)

    def _transcribe_batch(self, file_path: str) -> ASRResponse:
        batch_job = self.client.speech_to_text_job.create_job(
            model=self.model,
            mode="transcribe",
            with_timestamps=True,
            language_code=self.language,
        )
        batch_job.upload_files([file_path])
        batch_job.start()
        final_status = batch_job.wait_until_complete(timeout=1800)

        if getattr(final_status, "job_state", "").lower() != "completed":
            raise RuntimeError(f"Sarvam batch ASR job did not complete: {final_status}")

        file_results = batch_job.get_file_results()
        successful = file_results.get("successful") or []
        if not successful:
            raise RuntimeError(f"Sarvam batch ASR returned no successful outputs: {file_results}")

        output_file = successful[0].get("output_file")
        if not output_file:
            raise RuntimeError(f"Sarvam batch ASR output file missing from results: {successful}")

        logger.info("Fetching raw Sarvam batch output URL without re-encoding the Azure SAS query string.")
        download_links = self.client.speech_to_text_job.get_download_links(
            job_id=batch_job.job_id,
            files=[output_file],
        )
        file_url = download_links.download_urls[output_file].file_url
        if not file_url:
            raise RuntimeError(f"Sarvam batch output URL missing for file {output_file}")

        with tempfile.TemporaryDirectory(prefix="sarvam_batch_") as output_dir:
            try:
                response = httpx.get(file_url, follow_redirects=True, timeout=60.0)
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                logger.exception(
                    "Sarvam batch output download failed for %s with HTTP %s; using raw SAS URL from get_download_links().",
                    output_file,
                    exc.response.status_code if exc.response else "unknown",
                )
                raise RuntimeError(f"Download failed for {output_file}: {exc.response.status_code if exc.response else 'unknown'}") from exc
            except Exception as exc:
                logger.exception("Unexpected error while downloading Sarvam batch output for %s", output_file)
                raise RuntimeError(f"Download failed for {output_file}: {exc}") from exc

            output_path = os.path.join(output_dir, os.path.basename(output_file))
            with open(output_path, "wb") as fh:
                fh.write(response.content)

            with open(output_path, "r", encoding="utf-8") as fh:
                payload = json.load(fh)

        return self._normalize_response(payload, request_id=batch_job.job_id)

    def transcribe(self, file_path: str) -> ASRResponse:
        try:
            duration = FFmpegService.extract_metadata(file_path).get("duration", 0.0)
            if duration > 30:
                return self._transcribe_batch(file_path)
            return self._transcribe_direct(file_path)
        except Exception as e:
            raise Exception(f"Sarvam AI API failed: {str(e)}")
