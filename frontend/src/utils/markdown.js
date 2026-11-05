import { marked } from 'marked'

marked.setOptions({
  breaks: false,
  gfm: true
})

export function renderMarkdown(content) {
  if (!content) return ''
  try {
    return marked.parse(content)
  } catch (e) {
    console.warn('Failed to parse markdown:', e)
    return content
  }
}
