import re
from dataclasses import dataclass
from typing import Any, Iterable, Optional

from sqlalchemy.orm import Session

from app.db.models import Transcript, TranscriptChunk, TranscriptType


@dataclass
class ChunkDraft:
    text: str
    chunk_index: int
    token_count: int
    start_time: Optional[float] = None
    end_time: Optional[float] = None


class ChunkingService:
    """Build and persist ordered chunks for redacted English transcripts."""

    DEFAULT_TARGET_TOKENS = 350
    DEFAULT_MAX_TOKENS = 500
    DEFAULT_OVERLAP_TOKENS = 40

    _sentence_pattern = re.compile(r".+?(?:[.!?](?=\s|$)|$)", re.DOTALL)

    @classmethod
    def build_chunks(
        cls,
        text: str,
        segments: Optional[Iterable[Any]] = None,
        target_tokens: int = DEFAULT_TARGET_TOKENS,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        overlap_tokens: int = DEFAULT_OVERLAP_TOKENS,
    ) -> list[ChunkDraft]:
        if target_tokens <= 0 or max_tokens < target_tokens:
            raise ValueError("max_tokens must be greater than or equal to target_tokens")
        if overlap_tokens < 0 or overlap_tokens >= max_tokens:
            raise ValueError("overlap_tokens must be smaller than max_tokens")

        normalized_text = " ".join(text.split())
        if not normalized_text:
            return []

        timestamp_ranges = cls._timestamp_ranges(segments)
        sentences = cls._sentences(normalized_text)
        units: list[tuple[list[str], int, int]] = []
        token_cursor = 0
        for sentence in sentences:
            sentence_tokens = sentence.split()
            start = token_cursor
            end = start + len(sentence_tokens)
            units.append((sentence_tokens, start, end))
            token_cursor = end

        drafts: list[ChunkDraft] = []
        current_tokens: list[tuple[str, int]] = []

        def emit() -> None:
            nonlocal current_tokens
            if not current_tokens:
                return
            start = current_tokens[0][1]
            end = current_tokens[-1][1] + 1
            start_time, end_time = cls._time_for_tokens(timestamp_ranges, start, end)
            drafts.append(
                ChunkDraft(
                    text=" ".join(token for token, _ in current_tokens),
                    chunk_index=len(drafts),
                    token_count=len(current_tokens),
                    start_time=start_time,
                    end_time=end_time,
                )
            )
            current_tokens = []

        for sentence_tokens, sentence_start, sentence_end in units:
            if len(sentence_tokens) > max_tokens:
                emit()
                step = max_tokens - overlap_tokens
                for offset in range(0, len(sentence_tokens), step):
                    part = sentence_tokens[offset : offset + max_tokens]
                    part_start, part_end = cls._time_for_tokens(
                        timestamp_ranges,
                        sentence_start + offset,
                        sentence_start + offset + len(part),
                    )
                    drafts.append(
                        ChunkDraft(
                            text=" ".join(part),
                            chunk_index=len(drafts),
                            token_count=len(part),
                            start_time=part_start,
                            end_time=part_end,
                        )
                    )
                    if offset + len(part) == len(sentence_tokens):
                        break
                continue

            if current_tokens and len(current_tokens) + len(sentence_tokens) > target_tokens:
                previous_tokens = current_tokens
                emit()
                overlap_count = min(
                    overlap_tokens,
                    max_tokens - len(sentence_tokens),
                    len(previous_tokens),
                )
                current_tokens = previous_tokens[-overlap_count:] if overlap_count else []

            current_tokens.extend(
                (token, sentence_start + offset)
                for offset, token in enumerate(sentence_tokens)
            )

        emit()
        return drafts

    @classmethod
    def chunk_transcript(
        cls,
        db: Session,
        transcript: Transcript,
        target_tokens: int = DEFAULT_TARGET_TOKENS,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        overlap_tokens: int = DEFAULT_OVERLAP_TOKENS,
    ) -> list[TranscriptChunk]:
        if transcript.transcript_type != TranscriptType.redacted_english:
            raise ValueError("Only redacted_english transcripts can be chunked")
        if transcript.audio_document is None:
            raise ValueError("Transcript must belong to an audio document")

        drafts = cls.build_chunks(
            transcript.text,
            segments=transcript.segments,
            target_tokens=target_tokens,
            max_tokens=max_tokens,
            overlap_tokens=overlap_tokens,
        )
        existing_chunks = db.query(TranscriptChunk).filter(
            TranscriptChunk.transcript_id == transcript.id
        ).all()
        for existing_chunk in existing_chunks:
            if existing_chunk.parent_chunk_id is not None:
                db.delete(existing_chunk)
        db.flush()
        for existing_chunk in existing_chunks:
            if existing_chunk.parent_chunk_id is None:
                db.delete(existing_chunk)
        db.flush()

        parent = TranscriptChunk(
            transcript_id=transcript.id,
            text=" ".join(transcript.text.split()),
            chunk_index=-1,
            token_count=len(" ".join(transcript.text.split()).split()),
            source_type="voice",
            language=transcript.language,
            region=transcript.audio_document.region,
            speaker_id=transcript.audio_document.speaker_id,
            audio_id=transcript.audio_document.id,
            start_time=drafts[0].start_time if drafts else None,
            end_time=drafts[-1].end_time if drafts else None,
            asr_model=transcript.model,
        )
        db.add(parent)
        db.flush()

        children = [
            TranscriptChunk(
                transcript_id=transcript.id,
                parent_chunk_id=parent.id,
                text=draft.text,
                chunk_index=draft.chunk_index,
                token_count=draft.token_count,
                source_type="voice",
                language=transcript.language,
                region=transcript.audio_document.region,
                speaker_id=transcript.audio_document.speaker_id,
                audio_id=transcript.audio_document.id,
                start_time=draft.start_time,
                end_time=draft.end_time,
                asr_model=transcript.model,
            )
            for draft in drafts
        ]
        db.add_all(children)
        db.commit()
        for child in children:
            db.refresh(child)
        return children

    @classmethod
    def _sentences(cls, text: str) -> list[str]:
        sentences = [match.group(0).strip() for match in cls._sentence_pattern.finditer(text)]
        return [sentence for sentence in sentences if sentence]

    @staticmethod
    def _timestamp_ranges(segments: Optional[Iterable[Any]]) -> list[tuple[int, int, Optional[float], Optional[float]]]:
        ranges = []
        cursor = 0
        for segment in segments or []:
            segment_text = segment.get("transcript", "") if isinstance(segment, dict) else getattr(segment, "transcript", "")
            tokens = segment_text.split()
            if not tokens:
                continue
            start_time = segment.get("start_time") if isinstance(segment, dict) else getattr(segment, "start_time", None)
            end_time = segment.get("end_time") if isinstance(segment, dict) else getattr(segment, "end_time", None)
            ranges.append((cursor, cursor + len(tokens), start_time, end_time))
            cursor += len(tokens)
        return ranges

    @staticmethod
    def _time_for_tokens(
        ranges: list[tuple[int, int, Optional[float], Optional[float]]],
        start: int,
        end: int,
    ) -> tuple[Optional[float], Optional[float]]:
        matching = [item for item in ranges if item[1] > start and item[0] < end]
        if not matching:
            return None, None
        if len(matching) == 1:
            range_start, range_end, start_time, end_time = matching[0]
            if start_time is None or end_time is None or range_end == range_start:
                return start_time, end_time
            duration = end_time - start_time
            relative_start = (max(start, range_start) - range_start) / (range_end - range_start)
            relative_end = (min(end, range_end) - range_start) / (range_end - range_start)
            return start_time + duration * relative_start, start_time + duration * relative_end
        return matching[0][2], matching[-1][3]