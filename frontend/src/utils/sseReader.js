/**
 * W3C 标准 Server-Sent Events (SSE) 流式阅读器。
 * 支持跨网络数据包切片持久化、状态机累积与打字机解包。
 */
export async function readSseStream(response, { onDelta, onReasoning, onCitation, onCompleted, onError, onRefusal, onStage } = {}) {
  const reader = response.body.getReader()
  const decoder = new TextDecoder('utf-8')
  let buffer = ''
  let completed = false
  let currentEvent = null
  let currentDataLines = []

  function flushEvent() {
    if (currentEvent && currentDataLines.length > 0) {
      const rawData = currentDataLines.join('\n')
      let parsed = null
      try {
        parsed = JSON.parse(rawData)
      } catch {
        parsed = { text: rawData }
      }
      if (currentEvent === 'answer_completed' || currentEvent === 'refusal') {
        completed = true
      }
      dispatchSseEvent(currentEvent, parsed, {
        onDelta, onReasoning, onCitation, onCompleted, onError, onRefusal, onStage
      })
    }
    currentEvent = null
    currentDataLines = []
  }

  function processLine(rawLine) {
    const line = rawLine.replace(/\r$/, '')
    if (!line.trim()) {
      flushEvent()
    } else if (line.startsWith('event:')) {
      currentEvent = line.slice(6).trim()
    } else if (line.startsWith('data:')) {
      let dataContent = line.slice(5)
      if (dataContent.startsWith(' ')) {
        dataContent = dataContent.slice(1)
      }
      currentDataLines.push(dataContent)
    }
    // 以冒号开头的行（如 :ping）为 SSE 注释心跳帧，无需处理
  }

  try {
    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      // 保留未完成的尾段
      buffer = lines.pop() || ''

      for (const line of lines) {
        processLine(line)
      }
    }

    // 处理流结束时 buffer 中剩余的最后一行
    if (buffer.trim()) {
      processLine(buffer)
    }
    flushEvent()

    if (!completed && onError) {
      onError(new Error('SSE 流连接中断，未接收到完成标识'))
    }
  } catch (err) {
    if (onError) onError(err)
    else throw err
  } finally {
    reader.releaseLock()
  }
}

function dispatchSseEvent(eventType, payload, handlers) {
  // payload 结构: AI-007 标准包络 { eventId, sessionId, sequence, eventType, data } 或直接 data
  const data = payload && payload.data !== undefined ? payload.data : payload

  switch (eventType) {
    case 'answer_delta':
      if (handlers.onDelta && data && data.delta) handlers.onDelta(data.delta)
      break
    case 'reasoning_delta':
      if (handlers.onReasoning && data) {
        const text = data.delta !== undefined ? data.delta : (data.text || data)
        handlers.onReasoning(text)
      }
      break
    case 'citation':
      if (handlers.onCitation) handlers.onCitation(data?.citations || data)
      break
    case 'answer_completed':
      if (handlers.onCompleted) handlers.onCompleted(data)
      break
    case 'refusal':
      if (handlers.onRefusal) handlers.onRefusal(data)
      break
    case 'stage':
      if (handlers.onStage) handlers.onStage(data)
      break
    case 'error':
      if (handlers.onError) handlers.onError(new Error(data?.message || 'AI 服务异常'))
      break
    default:
      if (data?.delta && handlers.onDelta) handlers.onDelta(data.delta)
      break
  }
}
