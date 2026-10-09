/** Ejemplos de uso de la API de inferencia (LLM, STT y TTS). Los mismos de docs/API_INFERENCIA.md. */

export const INFERENCE_PATH = '/api/v1/inference';

export function inferenceBaseUrl(origin: string) {
  return `${origin}${INFERENCE_PATH}`;
}

export type ExampleKind = 'llm' | 'stt' | 'tts' | 'stream' | 'python';

export const EXAMPLE_LABELS: Record<ExampleKind, string> = {
  llm: 'LLM (chat)',
  stt: 'Transcripción (STT)',
  tts: 'Síntesis (TTS)',
  stream: 'Streaming',
  python: 'Python (SDK de OpenAI)',
};

export function inferenceExample(kind: ExampleKind, origin: string, key = '<tu API key>'): string {
  const base = inferenceBaseUrl(origin);
  switch (kind) {
    case 'llm':
      return `curl ${base}/chat/completions \\
  -H "Authorization: Bearer ${key}" \\
  -H 'Content-Type: application/json' \\
  -d '{"messages":[{"role":"user","content":"Hola, ¿qué horarios tienen?"}],"max_tokens":200}'`;
    case 'stt':
      return `curl ${base}/audio/transcriptions \\
  -H "Authorization: Bearer ${key}" \\
  -F file=@audio.wav \\
  -F language=es`;
    case 'tts':
      return `curl ${base}/audio/speech \\
  -H "Authorization: Bearer ${key}" \\
  -H 'Content-Type: application/json' \\
  -d '{"voice":"sofia","input":"Hola, ¿en qué te puedo ayudar?"}' \\
  --output respuesta.wav`;
    case 'stream':
      return `# LLM: tokens a medida que se generan (SSE)
curl -N ${base}/chat/completions \\
  -H "Authorization: Bearer ${key}" \\
  -H 'Content-Type: application/json' \\
  -d '{"stream":true,"messages":[{"role":"user","content":"Contame algo breve"}]}'

# TTS: audio PCM (24 kHz, mono, 16 bits) mientras se sintetiza; acá se escucha con ffplay
curl -sN ${base}/audio/speech \\
  -H "Authorization: Bearer ${key}" \\
  -H 'Content-Type: application/json' \\
  -d '{"voice":"sofia","input":"Hola, ¿en qué te puedo ayudar?","response_format":"pcm"}' \\
  | ffplay -f s16le -ar 24000 -ac 1 -nodisp -autoexit -`;
    case 'python':
      return `from openai import OpenAI

client = OpenAI(base_url="${base}", api_key="${key}")

# LLM
chat = client.chat.completions.create(
    model="atentina",  # se ignora: el modelo lo fija la plataforma
    messages=[{"role": "user", "content": "Hola, ¿qué horarios tienen?"}],
)
print(chat.choices[0].message.content)

# STT
with open("audio.wav", "rb") as f:
    print(client.audio.transcriptions.create(model="atentina", file=f, language="es").text)

# TTS (archivo completo; para streaming: response_format="pcm" con with_streaming_response)
audio = client.audio.speech.create(model="atentina", voice="sofia", input="Hola", response_format="wav")
audio.write_to_file("respuesta.wav")`;
  }
}

export interface Endpoint {
  method: 'GET' | 'POST';
  path: string;
  scope: 'llm' | 'stt' | 'tts' | 'cualquiera';
  description: string;
}

export const ENDPOINTS: Endpoint[] = [
  {
    method: 'POST',
    path: '/chat/completions',
    scope: 'llm',
    description: 'Chat con el LLM (compatible con OpenAI, con stream).',
  },
  {
    method: 'POST',
    path: '/audio/transcriptions',
    scope: 'stt',
    description: 'Transcribe un archivo de audio.',
  },
  {
    method: 'POST',
    path: '/audio/speech',
    scope: 'tts',
    description: 'Sintetiza texto con una de las voces.',
  },
  { method: 'GET', path: '/voices', scope: 'tts', description: 'Voces disponibles.' },
  { method: 'GET', path: '/models', scope: 'cualquiera', description: 'Modelos que sirve la plataforma.' },
  {
    method: 'GET',
    path: '/usage',
    scope: 'cualquiera',
    description: 'Tu consumo del mes contra los límites del plan.',
  },
];
