/** Short guest-facing chime when an order becomes ready. */
export function playReadyChime(audioContextCtor: typeof AudioContext | undefined = globalThis.AudioContext): void {
  if (!audioContextCtor) return
  const ctx = new audioContextCtor()
  const oscillator = ctx.createOscillator()
  const gain = ctx.createGain()
  oscillator.type = 'sine'
  oscillator.frequency.value = 880
  gain.gain.setValueAtTime(0.08, ctx.currentTime)
  gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.35)
  oscillator.connect(gain)
  gain.connect(ctx.destination)
  oscillator.onended = () => {
    void ctx.close()
  }
  oscillator.start()
  oscillator.stop(ctx.currentTime + 0.35)
}
