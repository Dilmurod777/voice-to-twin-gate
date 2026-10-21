# One clip per command, synthesised locally so the demo ships with its own audio.
# Usage: powershell -NoProfile -File scripts\make_clips.ps1
# Files land in web\audio\<slug>.wav and are committed; nothing is fetched at runtime.

Add-Type -AssemblyName System.Speech

function Slug($text) { ($text.ToLower() -replace "[^a-z0-9]+", "-").Trim("-") }

$dir = Join-Path $PSScriptRoot "..\web\audio"
New-Item -ItemType Directory -Force $dir | Out-Null

$lines = @(
  "remove the access panel"
  "depressurise the fuel system"
  "open the fuel valve"
  "remove the fuel filter"
  "fit a new fuel filter"
  "show me the landing gear"
  "show the engine cowl"
  "close the access panel"
  "remove the hydraulic pump"
  "open the fuel valve it's fine I isolated it"
  "pull the filter out now"
  "open the wing"
  "close the cargo door"
  "remove that thing"
)

$format = [System.Speech.AudioFormat.SpeechAudioFormatInfo]::new(
  16000,
  [System.Speech.AudioFormat.AudioBitsPerSample]::Sixteen,
  [System.Speech.AudioFormat.AudioChannel]::Mono
)

$synth = New-Object System.Speech.Synthesis.SpeechSynthesizer
$synth.Rate = 1

foreach ($line in $lines) {
  $file = Join-Path $dir ((Slug $line) + ".wav")
  $synth.SetOutputToWaveFile($file, $format)
  $synth.Speak($line)
  $synth.SetOutputToNull()
  $kb = [int]((Get-Item $file).Length / 1KB)
  "{0,-46} {1,5} KB" -f (Split-Path $file -Leaf), $kb
}

$synth.Dispose()
