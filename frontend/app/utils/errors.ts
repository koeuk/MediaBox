/**
 * Turning a failed `$fetch` into something worth showing a person.
 *
 * FastAPI puts a plain string in `detail` for errors we raise ourselves, and an
 * array of per-field objects when request validation fails. The two helpers
 * below differ only in what they do with that array.
 */

/**
 * Use when the field-level detail would not mean anything to the user —
 * `whenInvalid` supplies a sentence for the validation case, usually more
 * specific than `fallback` (e.g. "each URL must start with http://").
 */
export function errorMessage(e: any, fallback: string, whenInvalid = fallback): string {
  const detail = e?.data?.detail
  if (Array.isArray(detail)) return whenInvalid
  return detail || fallback
}

/**
 * Use on forms where the first field error is worth surfacing verbatim —
 * "name must be at most 40 characters" beats a generic sentence.
 */
export function fieldErrorMessage(e: any, fallback: string): string {
  const detail = e?.data?.detail
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) return detail[0]?.msg || fallback
  return fallback
}
