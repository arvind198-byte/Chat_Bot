const BASE = '/api'

async function request(path, options = {}) {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...options.headers },
    ...options,
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || 'Request failed')
  }
  if (res.status === 204) return null
  return res.json()
}

export const api = {
  status:       ()                    => request('/status'),
  getChats:     ()                    => request('/chats'),
  createChat:   (title = 'New Chat')  => request('/chats', { method: 'POST', body: JSON.stringify({ title }) }),
  deleteChat:   (id)                  => request(`/chats/${id}`, { method: 'DELETE' }),
  getMessages:  (id)                  => request(`/chats/${id}/messages`),
  sendMessage:  (id, content)         => request(`/chats/${id}/messages`, { method: 'POST', body: JSON.stringify({ content }) }),
  submitFeedback: (messageId, rating) => request('/feedback', { method: 'POST', body: JSON.stringify({ message_id: messageId, rating }) }),
}
