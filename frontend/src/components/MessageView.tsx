import React, { useEffect, useRef } from "react";
import { Trash2, MessageSquareReply, CornerDownRight, CheckCheck } from "lucide-react";
import { Message, User } from "../types";

interface MessageViewProps {
  messages: Message[];
  currentUser: User | null;
  onSelectThread: (message: Message) => void;
  onDeleteMessage: (messageId: string) => void;
  onMarkRead: (messageId: string) => void;
  typingUsers: string[];
}

export const MessageView: React.FC<MessageViewProps> = ({
  messages,
  currentUser,
  onSelectThread,
  onDeleteMessage,
  onMarkRead,
  typingUsers,
}) => {
  const bottomRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, typingUsers]);

  // Mark latest message read
  useEffect(() => {
    if (messages.length > 0) {
      const latest = messages[messages.length - 1];
      if (currentUser && latest.sender.id !== currentUser.id) {
        onMarkRead(latest.id);
      }
    }
  }, [messages, currentUser, onMarkRead]);

  // Filter root messages (messages with parent_id === null)
  const rootMessages = messages.filter((m) => !m.parent_id);

  return (
    <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-slate-950">
      {rootMessages.length === 0 ? (
        <div className="h-full flex flex-col items-center justify-center text-slate-500 space-y-2">
          <p className="text-sm font-medium">No messages yet in this channel.</p>
          <p className="text-xs">Be the first to start the conversation!</p>
        </div>
      ) : (
        rootMessages.map((msg) => {
          const isSender = currentUser && msg.sender.id === currentUser.id;

          return (
            <div
              key={msg.id}
              className={`group flex items-start gap-3 p-2 rounded-lg hover:bg-slate-900/60 transition-colors ${
                msg.is_deleted ? "opacity-75" : ""
              }`}
            >
              {/* Avatar */}
              <div className="w-9 h-9 rounded-full bg-slate-700 flex items-center justify-center text-white font-semibold text-xs uppercase flex-shrink-0">
                {msg.sender.username.slice(0, 2)}
              </div>

              {/* Message Content */}
              <div className="flex-1 min-w-0">
                <div className="flex items-baseline gap-2 mb-1">
                  <span className="font-semibold text-sm text-slate-200">
                    {msg.sender.full_name || msg.sender.username}
                  </span>
                  <span className="text-[11px] text-slate-500">
                    {new Date(msg.created_at).toLocaleTimeString([], {
                      hour: "2-digit",
                      minute: "2-digit",
                    })}
                  </span>
                  {isSender && (
                    <span className="text-slate-500 text-[10px] flex items-center">
                      <CheckCheck className="w-3.5 h-3.5 text-indigo-400" />
                    </span>
                  )}
                </div>

                {/* Message Body */}
                <div
                  className={`text-sm break-words ${
                    msg.is_deleted
                      ? "italic text-slate-500 line-through select-none"
                      : "text-slate-300"
                  }`}
                >
                  {msg.content}
                </div>

                {/* Thread Replies Button */}
                {msg.reply_count && msg.reply_count > 0 ? (
                  <button
                    onClick={() => onSelectThread(msg)}
                    className="mt-2 inline-flex items-center gap-1.5 text-xs font-medium text-indigo-400 hover:text-indigo-300 transition-colors bg-indigo-950/40 px-2 py-0.5 rounded border border-indigo-900/50"
                  >
                    <CornerDownRight className="w-3 h-3" />
                    {msg.reply_count} {msg.reply_count === 1 ? "reply" : "replies"}
                  </button>
                ) : null}
              </div>

              {/* Message Hover Actions */}
              {!msg.is_deleted && (
                <div className="opacity-0 group-hover:opacity-100 flex items-center gap-1 bg-slate-800 border border-slate-700 rounded px-1.5 py-0.5 shadow transition-opacity flex-shrink-0">
                  <button
                    onClick={() => onSelectThread(msg)}
                    title="Reply in thread"
                    className="p-1 hover:text-indigo-400 text-slate-400 transition-colors"
                  >
                    <MessageSquareReply className="w-3.5 h-3.5" />
                  </button>
                  {isSender && (
                    <button
                      onClick={() => onDeleteMessage(msg.id)}
                      title="Delete message"
                      className="p-1 hover:text-rose-400 text-slate-400 transition-colors"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  )}
                </div>
              )}
            </div>
          );
        })
      )}

      {/* Typing Indicator */}
      {typingUsers.length > 0 && (
        <div className="flex items-center gap-2 text-xs text-slate-400 italic px-2 animate-pulse">
          <div className="flex gap-1">
            <span className="w-1.5 h-1.5 rounded-full bg-indigo-400 animate-bounce"></span>
            <span className="w-1.5 h-1.5 rounded-full bg-indigo-400 animate-bounce delay-100"></span>
            <span className="w-1.5 h-1.5 rounded-full bg-indigo-400 animate-bounce delay-200"></span>
          </div>
          <span>
            {typingUsers.join(", ")} {typingUsers.length === 1 ? "is" : "are"} typing...
          </span>
        </div>
      )}

      <div ref={bottomRef} />
    </div>
  );
};
