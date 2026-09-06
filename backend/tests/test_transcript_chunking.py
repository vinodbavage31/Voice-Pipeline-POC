import pytest
from sqlalchemy.orm import Session

from app.db.models import AudioDocument, Transcript, TranscriptChunk, TranscriptType
from app.services.transcript_chunking_service import ChunkingService


def test_chunk_ordering_and_overlap():
    text = " ".join(f"Sentence {index} has useful voice content." for index in range(1, 7))

    chunks = ChunkingService.build_chunks(
        text,
        target_tokens=12,
        max_tokens=18,
        overlap_tokens=3,
    )

    assert len(chunks) >= 2
    assert [chunk.chunk_index for chunk in chunks] == list(range(len(chunks)))
    assert "Sentence 1" in chunks[0].text
    for previous, current in zip(chunks, chunks[1:]):
        assert previous.text.split()[-3:] == current.text.split()[:3]
        assert current.token_count <= 18


def test_metadata_and_timestamps_are_preserved(db_session: Session):
    audio = AudioDocument(
        filename="meeting.wav",
        original_path="/data/uploads/meeting.wav",
        language="kn-IN",
        region="Karnataka",
        speaker_id="speaker-7",
    )
    db_session.add(audio)
    db_session.flush()
    transcript = Transcript(
        audio_document_id=audio.id,
        transcript_type=TranscriptType.redacted_english,
        text="One two three. Four five six.",
        language="en",
        model="saaras:v3",
        segments=[
            {"transcript": "One two three.", "start_time": 1.0, "end_time": 2.5},
            {"transcript": "Four five six.", "start_time": 3.0, "end_time": 4.5},
        ],
    )
    db_session.add(transcript)
    db_session.commit()

    chunks = ChunkingService.chunk_transcript(
        db_session,
        transcript,
        target_tokens=3,
        max_tokens=6,
        overlap_tokens=1,
    )

    assert len(chunks) == 2
    assert [(chunk.start_time, chunk.end_time) for chunk in chunks] == [
        (1.0, 2.5),
        (1.0, 4.5),
    ]
    for chunk in chunks:
        assert chunk.source_type == "voice"
        assert chunk.language == "en"
        assert chunk.region == "Karnataka"
        assert chunk.speaker_id == "speaker-7"
        assert chunk.audio_id == audio.id
        assert chunk.asr_model == "saaras:v3"

    parent = db_session.query(TranscriptChunk).filter_by(
        transcript_id=transcript.id,
        parent_chunk_id=None,
    ).one()
    assert parent.text == transcript.text
    assert [child.chunk_index for child in parent.children] == [0, 1]
    assert all(child.parent_chunk_id == parent.id for child in chunks)


def test_timestamps_are_interpolated_for_oversized_segment():
    text = " ".join(f"word{index}" for index in range(10)) + "."
    chunks = ChunkingService.build_chunks(
        text,
        segments=[
            {"transcript": text, "start_time": 10.0, "end_time": 20.0},
        ],
        target_tokens=4,
        max_tokens=4,
        overlap_tokens=0,
    )

    assert [chunk.token_count for chunk in chunks] == [4, 4, 2]
    assert chunks[0].start_time == 10.0
    assert chunks[-1].end_time == 20.0
    assert chunks[0].end_time <= chunks[1].start_time


def test_overlap_never_exceeds_maximum_and_keeps_timestamp_coverage():
    text = "First sentence has enough words here. Second sentence has many words here too."
    chunks = ChunkingService.build_chunks(
        text,
        segments=[
            {"transcript": "First sentence has enough words here.", "start_time": 0.0, "end_time": 6.0},
            {"transcript": "Second sentence has many words here too.", "start_time": 6.0, "end_time": 13.0},
        ],
        target_tokens=4,
        max_tokens=6,
        overlap_tokens=5,
    )

    assert all(chunk.token_count <= 6 for chunk in chunks)
    assert chunks[1].start_time == chunks[0].end_time


def test_oversized_sentence_timestamps_use_its_own_position():
    oversized = " ".join(f"word{index}" for index in range(8)) + "."
    text = f"Intro sentence. {oversized} Final sentence."
    chunks = ChunkingService.build_chunks(
        text,
        segments=[
            {"transcript": "Intro sentence.", "start_time": 0.0, "end_time": 2.0},
            {"transcript": oversized, "start_time": 2.0, "end_time": 10.0},
            {"transcript": "Final sentence.", "start_time": 10.0, "end_time": 12.0},
        ],
        target_tokens=4,
        max_tokens=4,
        overlap_tokens=0,
    )

    assert chunks[1].start_time == 2.0
    assert chunks[1].end_time < chunks[-1].start_time


def test_chunking_requires_redacted_english(db_session: Session):
    audio = AudioDocument(
        filename="meeting.wav",
        original_path="/data/uploads/meeting.wav",
    )
    db_session.add(audio)
    db_session.flush()
    transcript = Transcript(
        audio_document_id=audio.id,
        transcript_type=TranscriptType.original,
        text="Original transcript.",
    )
    db_session.add(transcript)
    db_session.commit()

    with pytest.raises(ValueError, match="redacted_english"):
        ChunkingService.chunk_transcript(db_session, transcript)


def test_chunking_replaces_existing_children(db_session: Session):
    audio = AudioDocument(
        filename="meeting.wav",
        original_path="/data/uploads/meeting.wav",
    )
    db_session.add(audio)
    db_session.flush()
    transcript = Transcript(
        audio_document_id=audio.id,
        transcript_type=TranscriptType.redacted_english,
        text="First sentence. Second sentence.",
    )
    db_session.add(transcript)
    db_session.commit()

    first = ChunkingService.chunk_transcript(
        db_session, transcript, target_tokens=2, max_tokens=4, overlap_tokens=0
    )
    second = ChunkingService.chunk_transcript(
        db_session, transcript, target_tokens=10, max_tokens=12, overlap_tokens=0
    )

    assert len(first) == 2
    assert len(second) == 1
    assert db_session.query(TranscriptChunk).filter_by(transcript_id=transcript.id).count() == 2
