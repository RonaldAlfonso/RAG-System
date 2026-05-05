<template>
  <q-page class="chat-wrap">

    <div ref="chatEl" class="messages-area">

      <!-- Estado vacío -->
      <div v-if="messages.length === 0" class="text-center text-grey-5 q-mt-xl">
        <q-icon name="travel_explore" size="72px" />
        <div class="text-h6 q-mt-md">¿En qué destino piensas?</div>
        <div class="text-caption">Pregunta sobre turismo en Latinoamérica</div>
      </div>

      <!-- Mensajes -->
      <div v-for="(msg, i) in messages" :key="i" class="q-mb-xl">

        <!-- Pregunta usuario -->
        <div class="row justify-end q-mb-sm">
          <q-chat-message
            :text="[msg.query]"
            sent
            bg-color="teal-8"
            text-color="white"
          />
        </div>

        <!-- Respuesta LLM -->
        <div class="row justify-start items-end q-gutter-sm">
          <q-avatar size="32px" color="grey-3">
            <q-icon name="smart_toy" color="teal-8" />
          </q-avatar>

          <div style="max-width: 75%">
            <q-card flat bordered>
              <q-card-section class="q-pa-md">
                <div class="text-body2" style="white-space: pre-wrap">
                  {{ msg.answer }}<span v-if="msg.streaming" class="cursor-blink">▋</span>
                </div>
              </q-card-section>
              <q-card-actions v-if="msg.detected_country" class="q-pa-sm q-pt-none">
                <q-chip
                  dense
                  color="teal-1"
                  text-color="teal-9"
                  icon="flag"
                  :label="`Filtrado por: ${msg.detected_country}`"
                  class="text-caption"
                />
              </q-card-actions>
            </q-card>

            <!-- Fuentes -->
            <q-expansion-item
              v-if="msg.sources.length"
              dense
              icon="menu_book"
              :label="`${msg.sources.length} fuentes consultadas`"
              class="q-mt-xs text-caption text-grey-7"
              header-class="text-caption"
            >
              <q-card
                v-for="(s, j) in msg.sources"
                :key="j"
                flat
                bordered
                class="q-mt-xs"
              >
                <q-card-section class="q-pa-sm">
                  <div class="row items-center q-gutter-xs q-mb-xs">
                    <q-badge :label="`score ${s.score.toFixed(3)}`" color="blue-grey-4" />
                    <a
                      v-if="s.metadata.url"
                      :href="s.metadata.url"
                      target="_blank"
                      class="text-teal-8 text-caption"
                    >{{ s.metadata.title || s.metadata.url }}</a>
                    <span v-else class="text-caption text-grey-7">
                      {{ s.metadata.title || '—' }}
                    </span>
                  </div>
                  <div class="text-caption text-grey-7 ellipsis-3-lines">{{ s.text }}</div>
                </q-card-section>
              </q-card>
            </q-expansion-item>
          </div>
        </div>

      </div>
    </div>

    <!-- Input -->
    <div class="q-pa-md bg-white shadow-up-2">
      <q-input
        v-model="input"
        outlined
        rounded
        placeholder="Ej: ¿Qué ver en Machu Picchu?"
        :disable="loading"
        @keyup.enter="sendQuery"
      >
        <template #append>
          <q-btn
            round flat
            icon="send"
            color="teal-8"
            :loading="loading"
            :disable="!input.trim()"
            @click="sendQuery"
          />
        </template>
      </q-input>
    </div>

  </q-page>
</template>

<script lang="ts">
import { defineComponent, ref, nextTick } from 'vue'
import { useRag } from 'src/composables/useRag'
import type { Source } from 'src/composables/useRag'

interface Message {
  query: string
  answer: string
  detected_country: string | null
  sources: Source[]
  streaming: boolean
}

export default defineComponent({
  name: 'IndexPage',

  setup () {
    const { loading, askStream } = useRag()

    const messages = ref<Message[]>([])
    const input    = ref<string>('')
    const chatEl   = ref<HTMLElement | null>(null)

    function scrollBottom (): void {
      nextTick(() => {
        chatEl.value?.scrollTo({ top: chatEl.value.scrollHeight, behavior: 'smooth' })
      })
    }

    async function sendQuery (): Promise<void> {
      const query = input.value.trim()
      if (!query || loading.value) return

      input.value = ''

      const idx = messages.value.length
      messages.value.push({
        query,
        answer: '',
        detected_country: null,
        sources: [],
        streaming: true,
      })
      scrollBottom()

      await askStream(query, 5, {
        onMeta (data) {
          messages.value[idx]!.detected_country = data.detected_country
          messages.value[idx]!.sources          = data.sources
        },
        onToken (token) {
          messages.value[idx]!.answer += token
          scrollBottom()
        },
        onDone () {
          messages.value[idx]!.streaming = false
        },
      })
    }

    return {
      loading,
      messages,
      input,
      chatEl,
      sendQuery,
    }
  },
})
</script>

<style scoped>
.cursor-blink {
  animation: blink 1s step-end infinite;
}
@keyframes blink {
  50% { opacity: 0; }
}
</style>
