# Live voice demo

Open the student screen on localhost in a browser with SpeechRecognition and speech synthesis support. Clear or send any existing draft, choose **Start voice call**, and allow microphone access. Speak one question, then pause for about two seconds. The app waits for recognition to finalize, sends once, and reads the reply aloud. It continues listening; speaking during playback cancels the bot audio immediately when the browser reports speech and starts the next student draft. End voice call stops the microphone and playback, keeping an unsent draft for review. Existing **Use voice** remains a one-question dictation mode.

Use headphones for interruption testing: browser speech recognition may hear the bot through the speakers, and ECHO cannot reliably distinguish that echo from a student. Speech service availability, event timing and simultaneous recognition/playback depend on the browser and operating system. Automatic microphone detection has not been verified on physical hardware by the automated tests. Voice may use a browser-provided remote speech service; ECHO does not persist recordings.

If the student interrupts while a model request is still running, the old answer is saved as text and its audio is suppressed. The new draft can be collected immediately; its request waits until the preceding request completes to keep one-prompt memory in order. Interrupting does not cancel a Groq request already sent or refund that request's usage. Permission/service errors stop the call rather than endlessly restarting. A request failure pauses the call for manual retry.

## Manual check

1. Start voice call and ask “What is the minimum attendance requirement?”. Pause; confirm one submission and audible response, including on the first turn of a new chat.
2. While the bot speaks, say “What if I miss it?”. Confirm its audio stops and your words appear in the draft. Pause and confirm the follow-up submits once.
3. Ask a longer question with a brief pause shorter than two seconds. Confirm it stays one turn.
4. End the call mid-draft. Confirm the draft remains and no new requests are sent. Reloading or leaving the page also stops microphone recognition.

## Two computers

Two independently started Docker stacks have separate databases and cannot exchange tickets. Both people must access one shared ECHO server: the student opens its root URL, and staff opens `/staff` on that same server and signs in with the server's staff credentials. This can remain a local-network demo on the same Wi-Fi; public cloud hosting is not inherently required.

The supplied Compose mapping binds port 8001 to `127.0.0.1`, so other computers cannot currently reach it. Sharing would require deliberately publishing the app on a LAN interface and allowing it through the host firewall; it does not require publishing PostgreSQL or Neo4j. For voice from another computer, use a trusted HTTPS origin because remote plain-HTTP microphone access is restricted by browsers. No LAN binding or deployment settings were changed by this feature update.
