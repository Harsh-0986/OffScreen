/**
 * Build a URL for an uploaded photograph.
 *
 * The backend returns a root-relative path like `/uploads/<uuid>.jpg`. Naive
 * concatenation with the API base produced `http://localhost:8000uploads/...`
 * (no separator) and every journal image 404'd, so normalise here rather than
 * trusting the shape.
 */
export function imageSrc(path: string | null | undefined): string {
  if (!path) return "";

  // Already absolute (or a data/blob URL): leave it alone.
  if (/^(https?:|blob:|data:)/.test(path)) return path;

  const relative = path.replace(/^\/+/, "");
  return `${API_BASE}/${relative}`;
}
