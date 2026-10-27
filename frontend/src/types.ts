export interface User {
  id: string;
  email: string;
  username: string;
  full_name: string;
  avatar_url?: string | null;
}

export interface Room {
  id: string;
  name: string;
  slug: string;
  is_direct: boolean;
  topic?: string;
  created_by?: User | null;
  member_count: number;
  last_message?: Message | null;
}

export interface Message {
  id: string;
  room_slug: string;
  sender: User;
  content: string;
  parent_id?: string | null;
  is_deleted: boolean;
  created_at: string;
  updated_at?: string;
  reply_count?: number;
}

export interface PresenceUser {
  user_id: string;
  username: string;
}

export interface PresenceEvent {
  type: "chat_presence";
  user_id: string;
  username: string;
  status: "online" | "offline";
  active_users: PresenceUser[];
}

export interface TypingEvent {
  type: "chat_typing";
  sender_id: string;
  username: string;
  is_typing: boolean;
}

export interface ReadReceiptEvent {
  type: "chat_read_receipt";
  message_id: string;
  room_slug: string;
  reader: {
    id: string;
    username: string;
  };
  read_at: string;
}
