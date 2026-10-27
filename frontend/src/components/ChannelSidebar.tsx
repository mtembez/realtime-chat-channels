import React from "react";
import { Hash, MessageSquare, Users, Circle, Wifi, WifiOff } from "lucide-react";
import { PresenceUser, Room, User } from "../types";

interface ChannelSidebarProps {
  currentUser: User | null;
  rooms: Room[];
  currentRoomSlug: string;
  onSelectRoom: (slug: string) => void;
  activeUsers: PresenceUser[];
  isConnected: boolean;
  isReconnecting: boolean;
}

export const ChannelSidebar: React.FC<ChannelSidebarProps> = ({
  currentUser,
  rooms,
  currentRoomSlug,
  onSelectRoom,
  activeUsers,
  isConnected,
  isReconnecting,
}) => {
  return (
    <aside className="w-64 bg-slate-900 text-slate-200 flex flex-col h-full border-r border-slate-800 select-none">
      {/* Workspace Header */}
      <div className="p-4 border-b border-slate-800 flex items-center justify-between">
        <div>
          <h1 className="font-bold text-white text-base tracking-wide flex items-center gap-2">
            <MessageSquare className="w-5 h-5 text-indigo-400" />
            Realtime Chat
          </h1>
          <p className="text-xs text-slate-400">Simon M. Munyambu Workspace</p>
        </div>
        <div>
          {isConnected ? (
            <span title="WebSocket Connected" className="inline-flex items-center text-emerald-400 text-xs">
              <Wifi className="w-4 h-4 animate-pulse" />
            </span>
          ) : isReconnecting ? (
            <span title="Reconnecting (Exponential Backoff)..." className="inline-flex items-center text-amber-400 text-xs">
              <WifiOff className="w-4 h-4 animate-bounce" />
            </span>
          ) : (
            <span title="Disconnected" className="inline-flex items-center text-rose-400 text-xs">
              <WifiOff className="w-4 h-4" />
            </span>
          )}
        </div>
      </div>

      {/* Navigation Sections */}
      <div className="flex-1 overflow-y-auto p-3 space-y-6">
        {/* Channels Section */}
        <div>
          <div className="flex items-center justify-between text-xs font-semibold text-slate-400 uppercase tracking-wider px-2 mb-2">
            <span>Channels</span>
            <span className="text-[10px] bg-slate-800 px-1.5 py-0.5 rounded">{rooms.length}</span>
          </div>
          <div className="space-y-1">
            {rooms.map((room) => {
              const active = room.slug === currentRoomSlug;
              return (
                <button
                  key={room.id}
                  onClick={() => onSelectRoom(room.slug)}
                  className={`w-full flex items-center gap-2.5 px-2.5 py-1.5 rounded-md text-sm transition-colors text-left ${
                    active
                      ? "bg-indigo-600 text-white font-medium"
                      : "text-slate-300 hover:bg-slate-800 hover:text-white"
                  }`}
                >
                  <Hash className="w-4 h-4 text-slate-400 flex-shrink-0" />
                  <span className="truncate">{room.name}</span>
                </button>
              );
            })}
          </div>
        </div>

        {/* Presence: Online Users */}
        <div>
          <div className="flex items-center justify-between text-xs font-semibold text-slate-400 uppercase tracking-wider px-2 mb-2">
            <span className="flex items-center gap-1.5">
              <Users className="w-3.5 h-3.5" />
              Online Now ({activeUsers.length})
            </span>
          </div>
          <div className="space-y-1">
            {activeUsers.length === 0 ? (
              <p className="text-xs text-slate-500 italic px-2">No other users online</p>
            ) : (
              activeUsers.map((u) => (
                <div
                  key={u.user_id}
                  className="flex items-center gap-2 px-2.5 py-1 text-xs text-slate-300 rounded hover:bg-slate-800/60"
                >
                  <Circle className="w-2.5 h-2.5 fill-emerald-500 text-emerald-500" />
                  <span className="truncate">{u.username}</span>
                  {currentUser && u.user_id === currentUser.id && (
                    <span className="text-[10px] text-slate-400">(you)</span>
                  )}
                </div>
              ))
            )}
          </div>
        </div>
      </div>

      {/* User Footer Profile */}
      {currentUser && (
        <div className="p-3 bg-slate-950/70 border-t border-slate-800 flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-full bg-indigo-500 flex items-center justify-center text-white font-semibold text-xs uppercase flex-shrink-0">
            {currentUser.username.slice(0, 2)}
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-xs font-medium text-white truncate">{currentUser.full_name || currentUser.username}</p>
            <p className="text-[10px] text-slate-400 truncate">@{currentUser.username}</p>
          </div>
          <Circle className="w-2.5 h-2.5 fill-emerald-500 text-emerald-500" />
        </div>
      )}
    </aside>
  );
};
