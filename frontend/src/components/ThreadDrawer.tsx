import React, { useState } from "react";
import { X, Send, CornerDownRight } from "lucide-react";
import { Message, User } from "../types";

interface ThreadDrawerProps {
  parentMessage: Message | null;
  replies: Message[];
  currentUser?: User | null;
  onClose: () => void;
  onSendReply: (content: string, parentId: string) => void;
}

export const ThreadDrawer: React.FC<ThreadDrawerProps> = ({
  parentMessage,
  replies,
  onClose,
  onSendReply,
}) => {
  const [replyText, setReplyText] = useState("");

  if (!parentMessage) return null;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!replyText.trim()) return;
    onSendReply(replyText, parentMessage.id);
    setReplyText("");
  };

  return (
    <aside className="w-80 bg-slate-900 border-l border-slate-800 flex flex-col h-full z-10 shadow-xl">
      {/* Header */}
      <div className="p-4 border-b border-slate-800 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <CornerDownRight className="w-4 h-4 text-indigo-400" />
          <h2 className="font-semibold text-white text-sm">Thread Replies</h2>
        </div>
        <button
          onClick={onClose}
          className="text-slate-400 hover:text-white p-1 rounded hover:bg-slate-800 transition-colors"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      {/* Parent Root Message Preview */}
      <div className="p-4 border-b border-slate-800/80 bg-slate-950/40">
        <div className="flex items-center gap-2 mb-1.5">
          <div className="w-6 h-6 rounded-full bg-slate-700 flex items-center justify-center text-[10px] text-white font-bold uppercase">
            {parentMessage.sender.username.slice(0, 2)}
          </div>
          <span className="font-semibold text-xs text-slate-300">
            {parentMessage.sender.full_name || parentMessage.sender.username}
          </span>
          <span className="text-[10px] text-slate-500">
            {new Date(parentMessage.created_at).toLocaleTimeString([], {
              hour: "2-digit",
              minute: "2-digit",
            })}
          </span>
        </div>
        <p className="text-xs text-slate-300 pl-8 break-words">{parentMessage.content}</p>
      </div>

      {/* Reply Messages Stream */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {replies.length === 0 ? (
          <p className="text-xs text-slate-500 italic text-center py-6">
            No replies yet. Be the first to answer!
          </p>
        ) : (
          replies.map((reply) => {
            return (
              <div key={reply.id} className="flex items-start gap-2.5 p-2 rounded hover:bg-slate-800/50">
                <div className="w-6 h-6 rounded-full bg-indigo-600/60 flex items-center justify-center text-[10px] text-white font-bold uppercase flex-shrink-0">
                  {reply.sender.username.slice(0, 2)}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-baseline gap-1.5 mb-0.5">
                    <span className="font-medium text-xs text-slate-200">
                      {reply.sender.full_name || reply.sender.username}
                    </span>
                    <span className="text-[10px] text-slate-500">
                      {new Date(reply.created_at).toLocaleTimeString([], {
                        hour: "2-digit",
                        minute: "2-digit",
                      })}
                    </span>
                  </div>
                  <p className="text-xs text-slate-300 break-words">{reply.content}</p>
                </div>
              </div>
            );
          })
        )}
      </div>

      {/* Reply Input Form */}
      <form onSubmit={handleSubmit} className="p-3 border-t border-slate-800 bg-slate-950/70">
        <div className="flex items-center gap-2 bg-slate-800 border border-slate-700 rounded-lg px-2.5 py-1.5 focus-within:border-indigo-500">
          <input
            type="text"
            value={replyText}
            onChange={(e) => setReplyText(e.target.value)}
            placeholder="Reply to thread..."
            className="flex-1 bg-transparent text-xs text-white placeholder-slate-400 focus:outline-none"
          />
          <button
            type="submit"
            disabled={!replyText.trim()}
            className="text-indigo-400 hover:text-indigo-300 disabled:opacity-40 transition-opacity p-1"
          >
            <Send className="w-3.5 h-3.5" />
          </button>
        </div>
      </form>
    </aside>
  );
};
