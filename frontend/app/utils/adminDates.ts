import type { AdminDateRange } from '~/types'

/** Presets include the current month through today; dates match the API's UTC days. */
export function adminDateRange(months = 12): AdminDateRange {
  const today = new Date()
  const start = new Date(Date.UTC(today.getUTCFullYear(), today.getUTCMonth() - months + 1, 1))
  return {
    start_date: start.toISOString().slice(0, 10),
    end_date: today.toISOString().slice(0, 10),
  }
}

/** Older SQLite/MySQL rows serialize without an offset, but store UTC. */
export function adminActivityDate(timestamp: string): string {
  const utc = /(?:Z|[+-]\d{2}:\d{2})$/i.test(timestamp) ? timestamp : `${timestamp}Z`
  return new Date(utc).toLocaleDateString('en-US', {
    month: 'short', day: 'numeric', year: 'numeric', timeZone: 'UTC',
  })
}
