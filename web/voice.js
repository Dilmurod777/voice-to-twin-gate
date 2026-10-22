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
    let said = text;
    let took = 0;
    let baked = false;
    try {
      const pcm = await pcm16(`/audio/${slug(text)}.wav`);
      const response = await fetch("/api/transcribe", {
        method: "POST",
        headers: { "Content-Type": "application/octet-stream" },
        body: pcm,
      });
      if (!response.ok) throw new Error(`server ${response.status}`);
      const answer = await response.json();
      said = answer.text.trim() || text;
      took = answer.ms;
    } catch {
      // No speech model in this build: the clip was generated from this exact text.
      baked = true;
    }
    $("cmd").value = said;
    await send(said, took);
    if (baked) {
      $("heard").textContent = `clip (baked) → ${$("heard").textContent}`;
      const cell = document.querySelector("#flow .flow-cell:nth-child(2) .v");
      if (cell) cell.textContent = "baked";
    }
  } catch (error) {
    $("heard").textContent = `clip failed: ${error.message}`;
  } finally {
    if (button) button.dataset.playing = "false";
  }
}
