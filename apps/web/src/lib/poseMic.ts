const MAX_SECONDS = 8;

/** マイクを 16bit PCM の WAV で録る。最大8秒。 */
export async function startPoseMic(): Promise<{ stop: () => Promise<Blob> }> {
  if (!navigator.mediaDevices?.getUserMedia) {
    throw new Error("mic missing");
  }
  const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
  const context = new AudioContext();
  const rate = context.sampleRate || 16000;
  const source = context.createMediaStreamSource(stream);
  const processor = context.createScriptProcessor(4096, 1, 1);
  const silent = context.createGain();
  silent.gain.value = 0;
  const chunks: Float32Array[] = [];
  let samples = 0;
  const limit = Math.floor(rate * MAX_SECONDS);
  processor.onaudioprocess = (event) => {
    if (samples >= limit) {
      return;
    }
    const channel = event.inputBuffer.getChannelData(0);
    const room = limit - samples;
    const slice = channel.length > room ? channel.subarray(0, room) : channel;
    chunks.push(new Float32Array(slice));
    samples += slice.length;
  };
  source.connect(processor);
  processor.connect(silent);
  silent.connect(context.destination);
  return {
    stop: async () => {
      processor.onaudioprocess = null;
      processor.disconnect();
      source.disconnect();
      silent.disconnect();
      stream.getTracks().forEach((track) => track.stop());
      const blob = encodeWav(chunks, rate);
      await context.close();
      return blob;
    },
  };
}

function encodeWav(chunks: Float32Array[], rate: number): Blob {
  let length = 0;
  for (const chunk of chunks) {
    length += chunk.length;
  }
  const pcm = new Int16Array(length);
  let offset = 0;
  for (const chunk of chunks) {
    for (let index = 0; index < chunk.length; index += 1) {
      const sample = Math.max(-1, Math.min(1, chunk[index]));
      pcm[offset] = sample < 0 ? sample * 0x8000 : sample * 0x7fff;
      offset += 1;
    }
  }
  const buffer = new ArrayBuffer(44 + pcm.length * 2);
  const view = new DataView(buffer);
  write(view, 0, "RIFF");
  view.setUint32(4, 36 + pcm.length * 2, true);
  write(view, 8, "WAVE");
  write(view, 12, "fmt ");
  view.setUint32(16, 16, true);
  view.setUint16(20, 1, true);
  view.setUint16(22, 1, true);
  view.setUint32(24, rate, true);
  view.setUint32(28, rate * 2, true);
  view.setUint16(32, 2, true);
  view.setUint16(34, 16, true);
  write(view, 36, "data");
  view.setUint32(40, pcm.length * 2, true);
  new Int16Array(buffer, 44).set(pcm);
  return new Blob([buffer], { type: "audio/wav" });
}

function write(view: DataView, offset: number, text: string) {
  for (let index = 0; index < text.length; index += 1) {
    view.setUint8(offset + index, text.charCodeAt(index));
  }
}
