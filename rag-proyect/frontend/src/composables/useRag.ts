import { ref } from 'vue'

export interface Metadata {
  title?: string
  url?: string
  pais?: string
  categoria?: string
  [key: string]: string | number | boolean | null | undefined
}

export interface Source {
  score: number
  text: string
  metadata: Metadata
  chunk_id: string | null
  doc_id: string | null
}

export interface RagResponse {
  query: string
  answer: string
  detected_country: string | null
  filters_applied: Record<string, string>
  sources: Source[]
}

interface MetaEvent {
  type: 'meta'
  detected_country: string | null
  filters_applied: Record<string, string>
  sources: Source[]
}

interface TokenEvent {
  type: 'token'
  content: string
}

interface DoneEvent {
  type: 'done'
}

type SseEvent = MetaEvent | TokenEvent | DoneEvent

export interface StreamCallbacks {
  onMeta?: (data: MetaEvent) => void
  onToken?: (token: string) => void
  onDone?: () => void
}

export function useRag () {
  const loading = ref<boolean>(false)
  const error   = ref<string | null>(null)

  async function ask (
    query: string,
    topK = 5,
    filters: Record<string, string> | null = null,
  ): Promise<RagResponse | null> {
    loading.value = true
    error.value   = null
    try {
      const res = await fetch('/ask', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query, top_k: topK, filters }),
      })
      if (!res.ok) {
        const detail = await res.json().catch(() => ({})) as { detail?: string }
        throw new Error(detail.detail ?? `HTTP ${res.status}`)
      }
      return (await res.json()) as RagResponse
    } catch (e) {
      error.value = (e as Error).message
      return null
    } finally {
      loading.value = false
    }
  }

  async function askStream (
    query: string,
    topK = 5,
    callbacks: StreamCallbacks = {},
  ): Promise<void> {
    const { onMeta, onToken, onDone } = callbacks
    loading.value = true
    error.value   = null
    try {
      const res = await fetch('/ask/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query, top_k: topK }),
      })
      if (!res.ok) throw new Error(`HTTP ${res.status}`)

      const reader  = res.body!.getReader()
      const decoder = new TextDecoder()
      let   buffer  = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const parts = buffer.split('\n\n')
        buffer = parts.pop() ?? ''

        for (const part of parts) {
          if (!part.startsWith('data: ')) continue
          const data = JSON.parse(part.slice(6)) as SseEvent
          if      (data.type === 'meta'  && onMeta)  onMeta(data)
          else if (data.type === 'token' && onToken) onToken(data.content)
          else if (data.type === 'done'  && onDone)  onDone()
        }
      }
    } catch (e) {
      error.value = (e as Error).message
    } finally {
      loading.value = false
    }
  }

  return { loading, error, ask, askStream }
}
