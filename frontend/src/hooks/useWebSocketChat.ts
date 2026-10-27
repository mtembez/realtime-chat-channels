import { useCallback, useEffect, useRef, useState } from "react";
import { Message, PresenceUser } from "../types";

interface UseWebSocketChatOptions {
  roomSlug: string;
  token: string | null;
  wsBaseUrl?: string;
  onUnauthorized?: () => void;
}

export function useWebSocketChat({
  roomSlug,
  token,
  wsBaseUrl = "ws://localhost:8000",
  onUnauthorized,
}: UseWebSocketChatOptions) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [activeUsers, setActiveUsers] = useState<PresenceUser[]>([]);
  const [typingUsers, setTypingUsers] = useState<string[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const [isReconnecting, setIsReconnecting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const socketRef = useRef<WebSocket | null>(null);
  const outboundQueueRef = useRef<string[]>([]);
  const reconnectAttemptsRef = useRef(0);
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const typingTimersRef = useRef<Map<string, ReturnType<typeof setTimeout>>>(new Map());
  const shouldReconnectRef = useRef(true);

  // Send raw JSON payload or enqueue if disconnected
  const sendPayload = useCallback((payload: object) => {
    const raw = JSON.stringify(payload);
    if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
      socketRef.current.send(raw);
    } else {
      // Outbound message queue
      outboundQueueRef.current.push(raw);
    }
  }, []);

  // Public action: send message
  const sendMessage = useCallback(
    (content: string, parentId?: string | null) => {
      if (!content.trim()) return;
      sendPayload({
        action: "send_message",
        content: content.trim(),
        parent_id: parentId || null,
      });
    },
    [sendPayload]
  );

  // Public action: soft delete message
  const deleteMessage = useCallback(
    (messageId: string) => {
      sendPayload({
        action: "delete_message",
        message_id: messageId,
      });
    },
    [sendPayload]
  );

  // Public action: broadcast typing indicator
  const setTyping = useCallback(
    (isTyping: boolean) => {
      sendPayload({
        action: "typing",
        is_typing: isTyping,
      });
    },
    [sendPayload]
  );

  // Public action: mark message read
  const markRead = useCallback(
    (messageId: string) => {
      sendPayload({
        action: "mark_read",
        message_id: messageId,
      });
    },
    [sendPayload]
  );

  useEffect(() => {
    if (!token || !roomSlug) return;
    shouldReconnectRef.current = true;

    const connect = () => {
      if (!token) return;

      const wsUrl = `${wsBaseUrl}/ws/chat/${roomSlug}/?token=${encodeURIComponent(token)}`;
      const ws = new WebSocket(wsUrl);
      socketRef.current = ws;

      ws.onopen = () => {
        setIsConnected(true);
        setIsReconnecting(false);
        setError(null);
        reconnectAttemptsRef.current = 0;

        // Drain outbound queue
        while (outboundQueueRef.current.length > 0) {
          const queued = outboundQueueRef.current.shift();
          if (queued) {
            ws.send(queued);
          }
        }
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);

          if (data.type === "chat_message") {
            setMessages((prev) => {
              if (prev.some((m) => m.id === data.id)) return prev;
              return [...prev, data];
            });
          } else if (data.type === "chat_message_deleted") {
            setMessages((prev) =>
              prev.map((m) =>
                m.id === data.id
                  ? { ...m, is_deleted: true, content: data.content }
                  : m
              )
            );
          } else if (data.type === "chat_typing") {
            const typingUsername = data.username;
            if (data.is_typing) {
              setTypingUsers((prev) =>
                prev.includes(typingUsername) ? prev : [...prev, typingUsername]
              );

              // Clear previous timer for this user if exists
              if (typingTimersRef.current.has(typingUsername)) {
                clearTimeout(typingTimersRef.current.get(typingUsername)!);
              }
              // Auto-remove typing after 3 seconds
              const timer = setTimeout(() => {
                setTypingUsers((prev) => prev.filter((u) => u !== typingUsername));
                typingTimersRef.current.delete(typingUsername);
              }, 3000);
              typingTimersRef.current.set(typingUsername, timer);
            } else {
              setTypingUsers((prev) => prev.filter((u) => u !== typingUsername));
              if (typingTimersRef.current.has(typingUsername)) {
                clearTimeout(typingTimersRef.current.get(typingUsername)!);
                typingTimersRef.current.delete(typingUsername);
              }
            }
          } else if (data.type === "chat_presence") {
            if (data.active_users) {
              setActiveUsers(data.active_users);
            }
          }
        } catch (err) {
          console.error("Failed to parse incoming WebSocket message:", err);
        }
      };

      ws.onerror = (evt) => {
        console.error("WebSocket error:", evt);
      };

      ws.onclose = (event) => {
        setIsConnected(false);

        // Close code 4001: Handshake Unauthorized rejection
        if (event.code === 4001) {
          setError("WebSocket handshake unauthorized (4001). Reconnecting halted.");
          shouldReconnectRef.current = false;
          if (onUnauthorized) onUnauthorized();
          return;
        }

        // Close code 4003: Forbidden (not room member)
        if (event.code === 4003) {
          setError("Room access forbidden (4003).");
          shouldReconnectRef.current = false;
          return;
        }

        if (shouldReconnectRef.current) {
          setIsReconnecting(true);
          // Exponential back-off: base 1000ms * 1.5 ^ attempts, max 15000ms + random jitter
          const delay = Math.min(
            15000,
            Math.pow(1.5, reconnectAttemptsRef.current) * 1000 + Math.random() * 500
          );
          reconnectAttemptsRef.current += 1;

          reconnectTimeoutRef.current = setTimeout(() => {
            connect();
          }, delay);
        }
      };
    };

    connect();

    return () => {
      shouldReconnectRef.current = false;
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (socketRef.current) {
        socketRef.current.close();
      }
      // Clear typing timers
      typingTimersRef.current.forEach((t) => clearTimeout(t));
      typingTimersRef.current.clear();
    };
  }, [roomSlug, token, wsBaseUrl, onUnauthorized]);

  return {
    messages,
    setMessages,
    activeUsers,
    typingUsers,
    isConnected,
    isReconnecting,
    error,
    sendMessage,
    deleteMessage,
    setTyping,
    markRead,
  };
}
