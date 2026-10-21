const slug = (text) =>
  text.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");

async function pcm16(url) {
  const file = await fetch(url);
  if (!file.ok) throw new Error(`clip ${file.status}`);
  const buffer = await new AudioContext().decodeAudioData(await file.arrayBuffer());
  const rate = 16000;
  const off = new OfflineAudioContext(1, Math.ceil(buffer.duration * rate), rate);
  const source = off.createBufferSource();
  source.buffer = buffer;
  source.connect(off.destination);
  source.start();
  return (await off.startRendering()).getChannelData(0);
}

async function runClip(text) {
  const button = document.querySelector(`.play[data-text="${text}"]`);
  const audio = new Audio(`/audio/${slug(text)}.wav`);
  audio.play().catch(() => {});
  if (button) button.dataset.playing = "true";
  $("heard").textContent = `hearing ${text}`;
  try {
    const pcm = await pcm16(`/audio/${slug(text)}.wav`);
    const response = await fetch("/api/transcribe", {
      method: "POST",
      headers: { "Content-Type": "application/octet-stream" },
      body: pcm,
    });
    if (!response.ok) throw new Error(`server ${response.status}`);
    const { text: heard, ms: took } = await response.json();
    const said = heard.trim() || text;
    $("cmd").value = said;
    await send(said, took);
  } catch (error) {
    $("heard").textContent = `clip failed: ${error.message}`;
  } finally {
    if (button) button.dataset.playing = "false";
  }
}
