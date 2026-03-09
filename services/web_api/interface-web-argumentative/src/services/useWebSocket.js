import { useState, useEffect, useRef, useCallback } from 'react';

/**
 * React hook for WebSocket connections to the analysis/debate/deliberation streams.
 *
 * Usage:
 *   const { messages, connected, send } = useWebSocket('analysis', sessionId);
 *
 * @param {string} channel - 'analysis' | 'debate' | 'deliberation'
 * @param {string} sessionId - Session identifier
 * @param {object} options - { autoReconnect, maxMessages }
 */
export default function useWebSocket(channel, sessionId, options = {}) {
  const { autoReconnect = true, maxMessages = 200 } = options;
  const [messages, setMessages] = useState([]);
  const [connected, setConnected] = useState(false);
  const wsRef = useRef(null);
  const reconnectTimerRef = useRef(null);

  const connect = useCallback(() => {
    if (!sessionId || !channel) return;

    // Determine WebSocket URL
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = process.env.REACT_APP_BACKEND_URL
      ? new URL(process.env.REACT_APP_BACKEND_URL).host
      : window.location.host;
    const url = `${protocol}//${host}/ws/${channel}/${sessionId}`;

    try {
      const ws = new WebSocket(url);
      wsRef.current = ws;

      ws.onopen = () => {
        setConnected(true);
        // Start ping keepalive
        ws._pingInterval = setInterval(() => {
          if (ws.readyState === WebSocket.OPEN) {
            ws.send('ping');
          }
        }, 30000);
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.type === 'pong') return; // Ignore pong responses
          setMessages(prev => {
            const next = [...prev, data];
            return next.length > maxMessages ? next.slice(-maxMessages) : next;
          });
        } catch {
          // Non-JSON message — ignore
        }
      };

      ws.onclose = () => {
        setConnected(false);
        clearInterval(ws._pingInterval);
        if (autoReconnect) {
          reconnectTimerRef.current = setTimeout(connect, 3000);
        }
      };

      ws.onerror = () => {
        // onclose will fire after onerror
      };
    } catch {
      setConnected(false);
    }
  }, [channel, sessionId, autoReconnect, maxMessages]);

  const disconnect = useCallback(() => {
    clearTimeout(reconnectTimerRef.current);
    if (wsRef.current) {
      clearInterval(wsRef.current._pingInterval);
      wsRef.current.close();
      wsRef.current = null;
    }
    setConnected(false);
  }, []);

  const send = useCallback((data) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(typeof data === 'string' ? data : JSON.stringify(data));
    }
  }, []);

  const clearMessages = useCallback(() => {
    setMessages([]);
  }, []);

  useEffect(() => {
    connect();
    return disconnect;
  }, [connect, disconnect]);

  return { messages, connected, send, clearMessages, disconnect };
}
