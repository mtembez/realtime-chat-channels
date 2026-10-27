import { useState } from "react";
import { ChannelSidebar } from "./components/ChannelSidebar";
import { MessageView } from "./components/MessageView";
import { ThreadDrawer } from "./components/ThreadDrawer";
import { ChatInput } from "./components/ChatInput";
import { useWebSocketChat } from "./hooks/useWebSocketChat";
import { Message, Room, User } from "./types";
import { Hash, Sparkles } from "lucide-react";

// Default seed rooms
const INITIAL_ROOMS: Room[] = [
  {
    id: "r1",
    name: "General",
    slug: "general",
    is_direct: false,
    topic: "General team announcements & discussions",
    member_count: 5,
  },
  {
    id: "r2",
    name: "Engineering",
    slug: "engineering",
    is_direct: false,
    topic: "High throughput ASGI, Redis pub/sub, Daphne scaling",
    member_count: 4,
  },
  {
    id: "r3",
    name: "Random",
    slug: "random",
    is_direct: false,
    topic: "Watercooler banter and tech links",
    member_count: 3,
  },
];

// Demo logged-in user profile
const DEMO_USER: User = {
  id: "00000000-0000-0000-0000-000000000001",
  email: "simonmaeleq7@gmail.com",
  username: "simon",
  full_name: "Simon M. Munyambu",
};

// Mock demo JWT access token for preview UI (when running without live backend)
const DEMO_TOKEN = "demo-access-token-simon";

export default function App() {
  const [currentRoomSlug, setCurrentRoomSlug] = useState("general");
  const [selectedThreadParent, setSelectedThreadParent] = useState<Message | null>(null);

  const currentRoom =
    INITIAL_ROOMS.find((r) => r.slug === currentRoomSlug) || INITIAL_ROOMS[0];

  const {
    messages,
    activeUsers,
    typingUsers,
    isConnected,
    isReconnecting,
    sendMessage,
    deleteMessage,
    setTyping,
    markRead,
  } = useWebSocketChat({
    roomSlug: currentRoomSlug,
    token: DEMO_TOKEN,
  });

  // Filter replies for currently selected thread
  const threadReplies = selectedThreadParent
    ? messages.filter((m) => m.parent_id === selectedThreadParent.id)
    : [];

  const handleSelectRoom = (slug: string) => {
    setCurrentRoomSlug(slug);
    setSelectedThreadParent(null);
  };

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-slate-950 font-sans text-slate-100">
      {/* Left Sidebar */}
      <ChannelSidebar
        currentUser={DEMO_USER}
        rooms={INITIAL_ROOMS}
        currentRoomSlug={currentRoomSlug}
        onSelectRoom={handleSelectRoom}
        activeUsers={activeUsers}
        isConnected={isConnected}
        isReconnecting={isReconnecting}
      />

      {/* Main Chat Center Pane */}
      <main className="flex-1 flex flex-col h-full min-w-0 bg-slate-950">
        {/* Channel Header */}
        <header className="h-14 border-b border-slate-800 bg-slate-900/60 px-5 flex items-center justify-between flex-shrink-0">
          <div className="flex items-center gap-2">
            <Hash className="w-5 h-5 text-indigo-400" />
            <div>
              <h2 className="font-bold text-sm text-white tracking-wide">
                {currentRoom.name}
              </h2>
              {currentRoom.topic && (
                <p className="text-xs text-slate-400 hidden sm:block truncate max-w-md">
                  {currentRoom.topic}
                </p>
              )}
            </div>
          </div>

          <div className="flex items-center gap-3 text-xs text-slate-400">
            <span className="flex items-center gap-1.5 bg-slate-800/80 px-2.5 py-1 rounded-full border border-slate-700/60">
              <Sparkles className="w-3.5 h-3.5 text-indigo-400" />
              Redis Pub/Sub
            </span>
          </div>
        </header>

        {/* Message Stream */}
        <MessageView
          messages={messages}
          currentUser={DEMO_USER}
          onSelectThread={(msg) => setSelectedThreadParent(msg)}
          onDeleteMessage={deleteMessage}
          onMarkRead={markRead}
          typingUsers={typingUsers}
        />

        {/* Message Input Bar */}
        <ChatInput
          onSendMessage={(content) => sendMessage(content)}
          onTyping={setTyping}
          currentRoomName={currentRoom.name}
        />
      </main>

      {/* Thread Reply Drawer (Slide-out) */}
      {selectedThreadParent && (
        <ThreadDrawer
          parentMessage={selectedThreadParent}
          replies={threadReplies}
          currentUser={DEMO_USER}
          onClose={() => setSelectedThreadParent(null)}
          onSendReply={(content, parentId) => sendMessage(content, parentId)}
        />
      )}
    </div>
  );
}
