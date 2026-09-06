import { FormEvent, useEffect, useMemo, useState } from 'react'
import './styles.css'

type View = 'upload' | 'processing' | 'result' | 'search'
type Stage = 'Audio preprocessing' | 'ASR' | 'Translation' | 'PII redaction' | 'Chunking' | 'Embedding' | 'Indexing'
type Audio = { id: number; filename: string; duration?: number; language?: string; region?: string; speaker_id?: string; processing_status: string; processing_stage?: string; processing_error?: string }
type Transcript = { id: number; transcript_type: string; text: string; language?: string; provider?: string; model?: string; confidence?: number }
type Chunk = { id: number; text: string; chunk_index: number; token_count: number; start_time?: number; end_time?: number }
type PipelineResult = { audio: Audio; transcripts: Transcript[]; chunks: Chunk[] }
type SearchItem = { chunk_id: number; content: string; score: number; rank: number; metadata: Record<string, unknown> }
type SearchResponse = { vector_results: SearchItem[]; keyword_results: SearchItem[]; rrf_results: SearchItem[]; reranked_results: SearchItem[] }

const stages: Stage[] = ['Audio preprocessing', 'ASR', 'Translation', 'PII redaction', 'Chunking', 'Embedding', 'Indexing']

function App() {
  const [view, setView] = useState<View>('upload')
  const [file, setFile] = useState<File | null>(null)
  const [region, setRegion] = useState('')
  const [speakerId, setSpeakerId] = useState('')
  const [audio, setAudio] = useState<Audio | null>(null)
  const [result, setResult] = useState<PipelineResult | null>(null)
  const [activeStage, setActiveStage] = useState(-1)
  const [error, setError] = useState('')
  const [query, setQuery] = useState('')
  const [searchRegion, setSearchRegion] = useState('')
  const [topK, setTopK] = useState(5)
  const [search, setSearch] = useState<SearchResponse | null>(null)
  const [searching, setSearching] = useState(false)

  useEffect(() => {
    if (view !== 'processing') return
    setActiveStage(0)
    const timer = window.setInterval(() => setActiveStage((stage) => Math.min(stage + 1, stages.length - 1)), 900)
    return () => window.clearInterval(timer)
  }, [view])

  const transcriptMap = useMemo(() => Object.fromEntries((result?.transcripts ?? []).map((item) => [item.transcript_type, item])), [result])

  async function upload(event: FormEvent) {
    event.preventDefault()
    if (!file) { setError('Choose an audio file first.'); return }
    setError('')
    setView('processing')
    const data = new FormData()
    data.append('file', file)
    if (region) data.append('region', region)
    if (speakerId) data.append('speaker_id', speakerId)
    try {
      const response = await fetch('/api/v1/audio/upload', { method: 'POST', body: data })
      if (!response.ok) throw new Error((await response.json()).detail ?? 'Upload failed')
      const uploaded: Audio = await response.json()
      setAudio(uploaded)
      setActiveStage(stages.length - 1)
      const resultResponse = await fetch(`/api/v1/audio/${uploaded.id}/result`)
      if (!resultResponse.ok) throw new Error('Could not load processing results')
      setResult(await resultResponse.json())
      if (uploaded.processing_status === 'failed') setError(uploaded.processing_error ?? 'Processing failed')
      setView('result')
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Something went wrong')
      setView('upload')
    }
  }

  async function runSearch(event: FormEvent) {
    event.preventDefault()
    if (!query.trim()) return
    setSearching(true)
    setError('')
    try {
      const response = await fetch('/api/v1/search', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ query, region: searchRegion || null, top_k: topK }) })
      if (!response.ok) throw new Error((await response.json()).detail ?? 'Search failed')
      setSearch(await response.json())
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Search failed')
    } finally { setSearching(false) }
  }

  return <main className="shell">
    <header className="topbar">
      <button className="brand" onClick={() => setView('upload')}><span className="brand-mark">V</span><span>Voice / RAG</span></button>
      <nav className="nav" aria-label="Primary navigation">
        <button className={view === 'upload' ? 'active' : ''} onClick={() => setView('upload')}>Upload audio</button>
        <button className={view === 'processing' ? 'active' : ''} disabled={!audio && view !== 'processing'} onClick={() => setView('processing')}>Processing</button>
        <button className={view === 'result' ? 'active' : ''} disabled={!result} onClick={() => setView('result')}>Transcript result</button>
        <button className={view === 'search' ? 'active' : ''} onClick={() => setView('search')}>Search</button>
      </nav>
      <span className="system-status"><i /> Prototype online</span>
    </header>
    <section className="content">
      <div className="eyebrow">VOICE PROCESSING WORKSPACE</div>
      {error && <div className="alert">{error}</div>}
      {view === 'upload' && <UploadPage file={file} setFile={setFile} region={region} setRegion={setRegion} speakerId={speakerId} setSpeakerId={setSpeakerId} onSubmit={upload} />}
      {view === 'processing' && <ProcessingPage audio={audio} activeStage={activeStage} />}
      {view === 'result' && <ResultPage result={result} transcriptMap={transcriptMap} />}
      {view === 'search' && <SearchPage query={query} setQuery={setQuery} region={searchRegion} setRegion={setSearchRegion} topK={topK} setTopK={setTopK} onSubmit={runSearch} search={search} searching={searching} />}
    </section>
  </main>
}

function UploadPage(props: { file: File | null; setFile: (file: File | null) => void; region: string; setRegion: (value: string) => void; speakerId: string; setSpeakerId: (value: string) => void; onSubmit: (event: FormEvent) => void }) {
  return <div className="page-grid"><div className="intro"><p className="kicker">01 / INGEST</p><h1>Turn spoken<br /><em>knowledge</em> into signal.</h1><p className="lede">Upload a conversation and the workspace will transcribe, translate, protect, and index it for grounded search.</p><div className="metric-row"><div><strong>7</strong><span>pipeline stages</span></div><div><strong>16k</strong><span>Hz normalized audio</span></div></div></div><form className="upload-panel" onSubmit={props.onSubmit}><div className="panel-heading"><span>Audio source</span><small>Required</small></div><label className="dropzone"><input type="file" accept="audio/*,.m4a,.webm" onChange={(event) => props.setFile(event.target.files?.[0] ?? null)} /><span className="upload-icon">↑</span><strong>{props.file ? props.file.name : 'Choose an audio file'}</strong><small>{props.file ? `${(props.file.size / 1024 / 1024).toFixed(2)} MB ready` : 'WAV, MP3, M4A, FLAC, OGG or WEBM'}</small></label><div className="fields"><label>Region<select value={props.region} onChange={(event) => props.setRegion(event.target.value)}><option value="">Select a region</option><option>Karnataka</option><option>Tamil Nadu</option><option>Kerala</option><option>Andhra Pradesh</option><option>Other</option></select></label><label>Speaker ID<input value={props.speakerId} onChange={(event) => props.setSpeakerId(event.target.value)} placeholder="e.g. speaker-07" /></label></div><button className="primary" type="submit">Process audio <span>→</span></button><p className="privacy">Original audio stays in your workspace. PII redaction runs on transcript text only.</p></form></div>
}

function ProcessingPage({ audio, activeStage }: { audio: Audio | null; activeStage: number }) {
  return <div className="processing-page"><div className="section-title"><p className="kicker">02 / PROCESSING</p><h1>Building your<br /><em>searchable record.</em></h1><p className="lede">Each stage runs in sequence. Your source remains untouched while a protected search layer is prepared.</p></div><div className="stage-list">{stages.map((stage, index) => <div className={`stage ${index < activeStage ? 'done' : index === activeStage ? 'current' : ''}`} key={stage}><span className="stage-number">{index < activeStage ? '✓' : `0${index + 1}`}</span><div><strong>{stage}</strong><small>{index < activeStage ? 'Complete' : index === activeStage ? 'In progress' : 'Waiting'}</small></div><span className="stage-dot" /></div>)}</div>{audio && <div className="processing-file"><span>Processing</span><strong>{audio.filename}</strong><small>{audio.region || 'Region not specified'} {audio.speaker_id ? `· ${audio.speaker_id}` : ''}</small></div>}</div>
}

function ResultPage({ result, transcriptMap }: { result: PipelineResult | null; transcriptMap: Record<string, Transcript> }) {
  if (!result) return <EmptyState title="No transcript yet" />
  return <div className="result-page"><div className="section-title result-heading"><div><p className="kicker">03 / TRANSCRIPT RESULT</p><h1>{result.audio.filename}</h1><p className="lede">Protected transcript record with source timings and indexed chunks.</p></div><span className="complete-pill"><i /> Processed</span></div><div className="metadata-strip"><Meta label="Region" value={result.audio.region || 'Not specified'} /><Meta label="Speaker" value={result.audio.speaker_id || 'Not specified'} /><Meta label="Duration" value={result.audio.duration ? `${result.audio.duration.toFixed(1)} sec` : 'Unavailable'} /><Meta label="Language" value={result.audio.language || transcriptMap.original?.language || 'kn-IN'} /></div><div className="transcript-grid"><TranscriptCard title="Original Kannada" transcript={transcriptMap.original} tone="source" /><TranscriptCard title="English translation" transcript={transcriptMap.translated_english} tone="translation" /><TranscriptCard title="PII-redacted English" transcript={transcriptMap.redacted_english} tone="protected" /></div><div className="chunks-section"><div className="section-label"><span>Indexed chunks</span><small>{result.chunks.length} child chunks</small></div>{result.chunks.map((chunk) => <div className="chunk-row" key={chunk.id}><span className="chunk-index">{String(chunk.chunk_index + 1).padStart(2, '0')}</span><p>{chunk.text}</p><span className="timestamp">{formatTime(chunk.start_time)} — {formatTime(chunk.end_time)}</span></div>)}</div></div>
}

function TranscriptCard({ title, transcript, tone }: { title: string; transcript?: Transcript; tone: string }) { return <article className={`transcript-card ${tone}`}><div className="card-label"><span>{title}</span><small>{transcript?.provider || 'Pending'}</small></div><p>{transcript?.text || 'No transcript available.'}</p><div className="card-foot">{transcript?.model || '—'} {transcript?.confidence ? `· ${(transcript.confidence * 100).toFixed(0)}% confidence` : ''}</div></article> }
function Meta({ label, value }: { label: string; value: string }) { return <div><small>{label}</small><strong>{value}</strong></div> }
function formatTime(value?: number) { return value == null || !Number.isFinite(value) ? '--:--' : `${Math.floor(value / 60).toString().padStart(2, '0')}:${Math.floor(value % 60).toString().padStart(2, '0')}` }

function SearchPage(props: { query: string; setQuery: (value: string) => void; region: string; setRegion: (value: string) => void; topK: number; setTopK: (value: number) => void; onSubmit: (event: FormEvent) => void; search: SearchResponse | null; searching: boolean }) {
  const groups: Array<[string, SearchItem[]]> = props.search ? [['Final reranked', props.search.reranked_results], ['RRF candidates', props.search.rrf_results], ['Vector results', props.search.vector_results], ['Keyword results', props.search.keyword_results]] : []
  return <div className="search-page"><div className="section-title"><p className="kicker">04 / SEARCH</p><h1>Ask the record.</h1><p className="lede">Compare semantic, keyword, fused, and reranked evidence without losing the trail.</p></div><form className="search-bar" onSubmit={props.onSubmit}><input value={props.query} onChange={(event) => props.setQuery(event.target.value)} placeholder="Ask a question about your recordings..." /><select value={props.region} onChange={(event) => props.setRegion(event.target.value)}><option value="">All regions</option><option>Karnataka</option><option>Tamil Nadu</option><option>Kerala</option><option>Andhra Pradesh</option></select><label className="top-k">Top <input type="number" min="1" max="20" value={props.topK} onChange={(event) => props.setTopK(Number(event.target.value))} /></label><button className="primary" type="submit">{props.searching ? 'Searching...' : 'Search'} <span>→</span></button></form>{groups.length ? <div className="search-groups">{groups.map(([title, items]) => <section className="search-group" key={title}><div className="section-label"><span>{title}</span><small>{items.length} results</small></div>{items.map((item) => <article className="search-result" key={`${title}-${item.chunk_id}`}><div className="result-rank">#{item.rank}</div><div className="result-body"><p>{item.content}</p><div className="result-meta"><span>{String(item.metadata.source_type || 'voice')}</span><span>{String(item.metadata.region || 'All regions')}</span><span>{formatTime(Number(item.metadata.start_time))} — {formatTime(Number(item.metadata.end_time))}</span><span>Audio #{String(item.metadata.audio_id || '—')}</span></div></div><strong className="score">{item.score.toFixed(4)}<small>score</small></strong></article>)}</section>)}</div> : <EmptyState title="Search across your indexed voice records" />}</div>
}

function EmptyState({ title }: { title: string }) { return <div className="empty-state"><span>⌕</span><h2>{title}</h2></div> }

export default App
