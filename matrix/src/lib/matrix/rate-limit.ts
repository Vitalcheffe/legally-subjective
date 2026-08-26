/**
 * INFINITUM — public endpoint rate limiter (Phase 7, "durcir").
 *
 * The sandbox is the ONLY interactive surface of the public interface, and
 * each session consumes real LLM quota through the three-agent engine. An
 * unprotected public POST endpoint could exhaust the quota that the
 * scientific experiments themselves depend on — the 429 episodes archived
 * in Phase 4 are the documented proof that this risk is real, not
 * theoretical.
 *
 * Design rules (honesty contract):
 *   - In-memory sliding window per client key — no external dependency,
 *     no persistence, no silent queueing.
 *   - When the limit is hit the caller receives an explicit 429 with the
 *     exact wait time. Nothing is ever silently dropped or simulated.
 *   - Per-instance only (single-process deployment); the upstream engine
 *     keeps its own exponential backoff for provider-side throttling.
 *   - The map is pruned opportunistically so it cannot grow unboundedly.
 */

/** One limiter instance = one policy (limit requests per windowMs per key). */
export interface RateLimitPolicy {
  /** Max requests allowed inside the sliding window. */
  limit: number;
  /** Window size in milliseconds. */
  windowMs: number;
}

/** Result of a rate-limit check — always explicit, never silent. */
export interface RateLimitResult {
  allowed: boolean;
  /** Requests remaining inside the current window (0 when blocked). */
  remaining: number;
  /** Seconds until the oldest request leaves the window (0 when allowed). */
  retryAfterSeconds: number;
}

const buckets = new Map<string, number[]>();

function prune(now: number, windowMs: number) {
  // Opportunistic cleanup: drop expired buckets when the map grows.
  if (buckets.size < 4096) return;
  for (const [key, hits] of buckets) {
    const live = hits.filter((t) => now - t < windowMs);
    if (live.length === 0) buckets.delete(key);
    else buckets.set(key, live);
  }
}

/** Check (and register) one request against the sliding-window policy. */
export function rateLimit(key: string, policy: RateLimitPolicy): RateLimitResult {
  const now = Date.now();
  prune(now, policy.windowMs);

  const hits = (buckets.get(key) ?? []).filter((t) => now - t < policy.windowMs);

  if (hits.length >= policy.limit) {
    const oldest = Math.min(...hits);
    const retryAfterSeconds = Math.max(1, Math.ceil((oldest + policy.windowMs - now) / 1000));
    buckets.set(key, hits); // keep the window intact — blocked requests do not extend it
    return { allowed: false, remaining: 0, retryAfterSeconds };
  }

  hits.push(now);
  buckets.set(key, hits);
  return {
    allowed: true,
    remaining: policy.limit - hits.length,
    retryAfterSeconds: 0,
  };
}

/** Extract the best-effort client key from proxy/request headers. */
export function clientKeyOf(request: Request): string {
  const fwd = request.headers.get("x-forwarded-for");
  if (fwd) return fwd.split(",")[0]!.trim();
  return request.headers.get("x-real-ip")?.trim() || "local";
}
