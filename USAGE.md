# Using ScribeBox

You've flashed the USB and booted a computer from it. Here's how to use it.

---

## First Boot

When ScribeBox starts, you'll see:

- A **header bar** at the top with the ScribeBox title and control buttons
- A large **transcript area** in the middle (this is where your words appear)
- A **summary panel** at the bottom (shows a summary of recent speech)
- A **status bar** at the very bottom showing the current state

The first time you boot, ScribeBox automatically detects your hardware and
picks the best AI model. You don't need to configure anything.

---

## Recording

### Start Recording

**Press F5** or click the **"Start Recording"** button.

The status bar will change to show "Recording with [model name]..." and a
red recording indicator appears in the header.

Speak clearly into the computer's microphone (or an external mic if you
have one plugged in). Your words will appear in the transcript area as
you speak.

### Stop Recording

**Press F5 again**, press **Escape**, or click **"Stop Recording"**.

The transcript stays on screen and is automatically saved to the USB stick.

### Save Transcript

Click **"Save Transcript"** to save a copy right now (transcripts also
auto-save periodically — every 60 seconds by default).

Transcripts are saved as plain text files in the `/data/scribebox/transcripts/`
folder on the USB stick, named by date and time:
```
transcript_20250403_141530.txt
```

---

## The Summary Panel

The bottom section shows a **rolling summary** of approximately the last
2 minutes of speech. This uses an algorithm called TextRank that identifies
the most important sentences from what's been said.

The summary updates every 5 seconds while recording.

**Keywords** appear as small tags to the right of the "Summary" header,
showing the most-discussed topics.

### Hiding the Summary

If you want the full screen for the transcript:
1. Press **F2** to open Preferences
2. Change **Layout** to "Full Transcript"
3. Click Apply

---

## Speaker Detection (Diarization)

When enabled, ScribeBox tries to identify different speakers and labels
them "Speaker 1", "Speaker 2", etc. in different colors.

This works best with:
- 2-3 speakers (gets less reliable with more)
- Speakers taking turns (not talking over each other)
- Reasonably different voice characteristics

To turn it on or off: Preferences (F2) > Transcription > Speaker Detection.

**Note:** Diarization uses extra CPU. On very old/slow machines, you may
want to keep it off to ensure the transcription itself stays real-time.

---

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| **F5** | Start/stop recording |
| **F2** | Open Preferences |
| **F11** | Toggle fullscreen |
| **Escape** | Stop recording (while recording) |

---

## Preferences

Press **F2** or click **"Preferences"** to open the settings dialog.
Changes take effect immediately when you click Apply.

### Transcription Tab

| Setting | What It Does | Default |
|---------|-------------|---------|
| **Whisper Model** | Which AI model to use. "Auto-detect" lets ScribeBox pick based on your hardware. Larger models are more accurate but slower. | Auto-detect |
| **Language** | Language being spoken. "English" is most accurate for English. "Auto-detect" works for other languages but needs a multilingual model. | English |
| **Speaker Detection** | Try to identify who is speaking. | Off |
| **Summary Window** | How many seconds of recent speech to include in the summary. | 120 seconds |
| **Auto-save** | How often to save the transcript to disk. | 60 seconds |

### Appearance Tab

| Setting | What It Does | Default |
|---------|-------------|---------|
| **Theme** | Color scheme. Dark is easy on the eyes, High Contrast is best for visibility at a distance. | Dark |
| **Font Size** | How big the transcript text is. Range: 14pt to 48pt. Try 32-40 for reading from across a room. | 24pt |
| **Layout** | "Full Transcript" uses the whole screen for text. "Transcript + Summary" shows the summary below. | Transcript + Summary |
| **Show Timestamps** | Show [MM:SS] before each transcript segment. | On |
| **Font** | Monospace (typewriter-style), Sans-serif (clean), or Serif (traditional). | Monospace |

All preferences are saved on the USB stick and persist between reboots.

---

## The Benchmark Tool

Click **"Benchmark"** to test all available models on this specific hardware.

The benchmark:
1. Generates a short test audio clip
2. Runs each model on it twice (once to warm up, once to measure)
3. Reports the **Real-Time Factor (RTF)** for each model
4. Recommends the best model for your hardware

**Understanding RTF:**
- **RTF below 1.0** = the model can keep up with live speech (real-time capable)
- **RTF of 0.5** = the model processes audio twice as fast as you speak it
- **RTF above 1.0** = the model is too slow for live transcription

After the benchmark, you can click "Use Recommended" to automatically switch
to the best model.

---

## Retrieving Your Transcripts

Transcripts are saved on the USB stick's data partition. To access them:

### On Linux
```bash
# Plug in the USB stick — it may auto-mount
# Look for a partition labeled "scribedata"
ls /media/$USER/scribedata/scribebox/transcripts/
```

### On Mac
The ext4 data partition won't mount natively on Mac. Options:
- Install [ext4fuse](https://github.com/gerard/ext4fuse): `brew install ext4fuse`
- Use [Paragon extFS](https://www.paragon-software.com/home/extfs-mac/) (paid)
- Boot into ScribeBox and copy transcripts to a FAT32 USB stick

### On Windows
The ext4 partition won't mount natively. Options:
- Use [Ext2Fsd](https://sourceforge.net/projects/ext2fsd/) (free)
- Use [Linux File Systems for Windows](https://www.paragon-software.com/home/linuxfs-windows/) by Paragon (paid)
- Boot into ScribeBox and copy files

### From Within ScribeBox
While booted into ScribeBox, transcripts are at:
```
/data/scribebox/transcripts/
```

---

## Tips for Best Results

### Audio Quality
- **Position matters.** Place the laptop close to the speaker(s), ideally 1-3 feet away.
- **External microphone.** A USB microphone dramatically improves accuracy. Even a cheap one helps.
- **Reduce background noise.** Close windows, turn off fans if possible.
- **One speaker at a time.** Whisper works best when speakers take turns.

### Performance
- **Close the lid (if using external display).** This reduces GPU load.
- **Keep the laptop plugged in.** Battery power-saving modes throttle the CPU.
- **Let it warm up.** The first few seconds after starting may be slower as caches fill.

### Model Selection
- **When in doubt, use Auto.** The benchmark test picks the best model.
- **If you see lag,** switch to a smaller model (Preferences > Whisper Model).
- **For noisy environments,** a larger model handles noise better but needs more CPU.
- **English-only models** (the `.en` variants) are noticeably better for English than multilingual models.

---

## FAQ

**Q: Can I use ScribeBox while the computer's normal OS is running?**
No. ScribeBox boots its own operating system from the USB stick. The
computer's hard drive is not used or modified. When you remove the USB
and reboot, the computer returns to its normal state.

**Q: Does ScribeBox modify the computer's hard drive?**
No. ScribeBox runs entirely from the USB stick. It doesn't touch the
internal drive at all.

**Q: Can I use it in languages other than English?**
Yes, but you need multilingual models (see [BUILD.md](BUILD.md) for how to
add them). Set the language to "Auto-detect" in Preferences. Accuracy is
lower than English for most languages.

**Q: How long can I record?**
As long as there's space on the USB stick. Transcripts are plain text and
very small — a 1-hour session is typically under 100 KB. The data partition
has about 2 GB of free space, enough for thousands of hours.

**Q: Can multiple computers share the same USB stick?**
Yes. The USB stick stores all preferences and transcripts. Plug it into
any compatible computer, boot, and your settings are there.

**Q: Can I record from a phone or Bluetooth speaker?**
Not directly. ScribeBox captures audio from the computer's microphone input.
However, you could play audio from a phone into the laptop's mic, or connect
a Bluetooth adapter and pair it (though Bluetooth support in the minimal
Linux system may be limited).

**Q: What happens if the computer crashes or loses power?**
Transcripts auto-save periodically (default: every 60 seconds). You'll lose
at most the last minute of transcription. Preferences are saved immediately
when you change them.
