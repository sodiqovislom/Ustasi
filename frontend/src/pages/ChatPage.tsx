import React, { useState, useEffect, useRef } from 'react';
import { useSearchParams, Link, useNavigate } from 'react-router-dom';
import {
  Send, Phone, ChevronLeft, User as UserIcon, MessageSquare,
  Clock, CheckCheck, Loader2, ShieldCheck, ArrowLeft
} from 'lucide-react';
import { api } from '../api/client';
import { ConversationItem, MessageItem } from '../types';
import { useAuth } from '../context/AuthContext';
import { TelegramAvatar } from '../components/TelegramAvatar';

export const ChatPage: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();
  const { user, isAuthenticated, openAuthModal } = useAuth();

  const partnerUserIdParam = searchParams.get('user_id');
  const [activePartnerId, setActivePartnerId] = useState<number | null>(
    partnerUserIdParam ? Number(partnerUserIdParam) : null
  );

  const [conversations, setConversations] = useState<ConversationItem[]>([]);
  const [messages, setMessages] = useState<MessageItem[]>([]);
  const [partnerInfo, setPartnerInfo] = useState<any>(null);

  const [textInput, setTextInput] = useState('');
  const [isSending, setIsSending] = useState(false);
  const [isLoadingMessages, setIsLoadingMessages] = useState(false);

  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Auth Guard
  useEffect(() => {
    if (!isAuthenticated) {
      openAuthModal("Xabarlarni ko‘rish uchun tizimga kiring");
    }
  }, [isAuthenticated]);

  // Load conversations list
  const loadConversations = async () => {
    if (!isAuthenticated) return;
    try {
      const list = await api.getConversations();
      setConversations(list);

      // If no active partner and conversations exist, select first conversation
      if (!activePartnerId && list.length > 0 && !partnerUserIdParam) {
        setActivePartnerId(list[0].partner.id);
      }
    } catch (err) {
      console.error(err);
    }
  };

  useEffect(() => {
    loadConversations();
  }, [isAuthenticated]);

  // Sync param with active partner
  useEffect(() => {
    if (partnerUserIdParam) {
      setActivePartnerId(Number(partnerUserIdParam));
    }
  }, [partnerUserIdParam]);

  // Load messages for active partner
  const loadActiveMessages = async (showLoading = false) => {
    if (!activePartnerId || !isAuthenticated) return;
    if (showLoading) setIsLoadingMessages(true);

    try {
      const res = await api.getMessages(activePartnerId);
      setMessages(res.messages || []);
      setPartnerInfo(res.partner);
    } catch (err) {
      console.error(err);
    } finally {
      if (showLoading) setIsLoadingMessages(false);
    }
  };

  useEffect(() => {
    if (activePartnerId) {
      loadActiveMessages(true);
      const interval = setInterval(() => loadActiveMessages(false), 3000);
      return () => clearInterval(interval);
    }
  }, [activePartnerId, isAuthenticated]);

  // Scroll to bottom on new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSelectConversation = (partnerId: number) => {
    setActivePartnerId(partnerId);
    setSearchParams({ user_id: String(partnerId) });
  };

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!textInput.trim() || !activePartnerId || isSending) return;

    const currentText = textInput.trim();
    setTextInput('');
    setIsSending(true);

    try {
      const sentMsg = await api.sendMessage(activePartnerId, currentText);
      setMessages(prev => [...prev, sentMsg]);
      loadConversations(); // refresh sidebar snippet
    } catch (err) {
      console.error("Xabar yuborishda xatolik:", err);
      setTextInput(currentText);
    } finally {
      setIsSending(false);
    }
  };

  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
      
      <div className="bg-white rounded-3xl border border-slate-200/90 shadow-xl overflow-hidden h-[78vh] flex">
        
        {/* LEFT PANE: CONVERSATION LIST (Hidden on mobile if chat is active) */}
        <div className={`w-full md:w-80 lg:w-96 border-r border-slate-200 flex flex-col ${
          activePartnerId ? 'hidden md:flex' : 'flex'
        }`}>
          {/* Header */}
          <div className="p-4 border-b border-slate-100 flex items-center justify-between">
            <h2 className="text-base font-black text-slate-900 flex items-center gap-2">
              <MessageSquare className="w-5 h-5 text-blue-600" />
              <span>Xabarlar</span>
            </h2>
            <span className="text-xs font-semibold text-slate-400">
              {conversations.length} ta suhbat
            </span>
          </div>

          {/* Conversations Scrollable List */}
          <div className="flex-1 overflow-y-auto divide-y divide-slate-100">
            {conversations.length > 0 ? (
              conversations.map((c) => {
                const isSelected = activePartnerId === c.partner.id;
                return (
                  <button
                    key={c.partner.id}
                    onClick={() => handleSelectConversation(c.partner.id)}
                    className={`w-full p-4 text-left flex items-start gap-3 transition ${
                      isSelected
                        ? 'bg-blue-50/70 border-l-4 border-blue-600'
                        : 'hover:bg-slate-50'
                    }`}
                  >
                    <TelegramAvatar
                      src={c.partner.avatar_url}
                      name={c.partner.full_name}
                      size="sm"
                      clickable={false}
                    />

                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between mb-1">
                        <h4 className="text-xs font-bold text-slate-900 truncate">
                          {c.partner.full_name}
                        </h4>
                        {c.last_message?.created_at && (
                          <span className="text-[10px] text-slate-400">
                            {new Date(c.last_message.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                          </span>
                        )}
                      </div>

                      <p className="text-xs text-slate-500 truncate">
                        {c.last_message?.is_me && <span className="font-semibold text-slate-600">Siz: </span>}
                        {c.last_message?.text || "Yangi suhbat..."}
                      </p>
                    </div>

                    {c.unread_count > 0 && (
                      <span className="w-5 h-5 bg-blue-600 text-white rounded-full text-[10px] font-bold flex items-center justify-center shrink-0">
                        {c.unread_count}
                      </span>
                    )}
                  </button>
                );
              })
            ) : (
              <div className="p-8 text-center text-xs text-slate-400">
                Hozircha xabarlar yo‘q. Usta profiliga kirib "Yozish" tugmasini bosing.
              </div>
            )}
          </div>
        </div>

        {/* RIGHT PANE: ACTIVE CHAT THREAD */}
        <div className={`flex-1 flex flex-col bg-slate-50/40 ${
          !activePartnerId ? 'hidden md:flex' : 'flex'
        }`}>
          {activePartnerId && partnerInfo ? (
            <>
              {/* Partner Top Bar */}
              <div className="p-3.5 px-5 bg-white border-b border-slate-200 flex items-center justify-between shadow-xs">
                <div className="flex items-center gap-3">
                  {/* Mobile Back Button */}
                  <button
                    onClick={() => {
                      setActivePartnerId(null);
                      setSearchParams({});
                    }}
                    className="md:hidden p-1.5 text-slate-400 hover:text-slate-600 rounded-lg hover:bg-slate-100 mr-1"
                  >
                    <ArrowLeft className="w-5 h-5" />
                  </button>

                  <TelegramAvatar
                    src={partnerInfo.avatar_url}
                    name={partnerInfo.full_name}
                    size="sm"
                    clickable={true}
                    subtitle={partnerInfo.master_category}
                  />

                  <div>
                    <h3 className="text-sm font-bold text-slate-900 leading-tight">
                      {partnerInfo.full_name}
                    </h3>
                    <p className="text-[11px] text-blue-600 font-semibold">
                      {partnerInfo.master_category || (partnerInfo.role === 'master' ? 'Usta' : 'Foydalanuvchi')}
                    </p>
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  {partnerInfo.master_id && (
                    <Link
                      to={`/masters/${partnerInfo.master_id}`}
                      className="px-3 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-bold rounded-xl transition"
                    >
                      Profil
                    </Link>
                  )}
                  {partnerInfo.phone && (
                    <a
                      href={`tel:${partnerInfo.phone.replace(/\s+/g, '')}`}
                      className="p-2 bg-emerald-50 text-emerald-700 hover:bg-emerald-100 rounded-xl transition"
                      title="Qo‘ng‘iroq qilish"
                    >
                      <Phone className="w-4 h-4" />
                    </a>
                  )}
                </div>
              </div>

              {/* Messages Container */}
              <div className="flex-1 p-4 sm:p-6 overflow-y-auto space-y-3">
                {isLoadingMessages ? (
                  <div className="text-center py-8 text-xs text-slate-400">
                    <Loader2 className="w-5 h-5 animate-spin mx-auto mb-1 text-blue-600" />
                    Yuklanmoqda...
                  </div>
                ) : messages.length > 0 ? (
                  messages.map((m) => {
                    const isMe = m.is_me || m.sender === user?.id;
                    return (
                      <div
                        key={m.id}
                        className={`flex flex-col ${isMe ? 'items-end' : 'items-start'}`}
                      >
                        <div
                          className={`max-w-xs sm:max-w-md px-4 py-2.5 rounded-2xl text-xs sm:text-sm leading-relaxed shadow-xs ${
                            isMe
                              ? 'bg-blue-600 text-white rounded-br-xs'
                              : 'bg-white text-slate-800 border border-slate-200/80 rounded-bl-xs'
                          }`}
                        >
                          {m.text}
                        </div>
                        <span className="text-[10px] text-slate-400 mt-1 px-1">
                          {new Date(m.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                        </span>
                      </div>
                    );
                  })
                ) : (
                  <div className="text-center py-16 text-slate-400 text-xs">
                    Suhbatni boshlash uchun quyida xabar yozing.
                  </div>
                )}
                <div ref={messagesEndRef} />
              </div>

              {/* Message Input Box */}
              <form
                onSubmit={handleSendMessage}
                className="p-3 bg-white border-t border-slate-200 flex items-center gap-2"
              >
                <input
                  type="text"
                  value={textInput}
                  onChange={(e) => setTextInput(e.target.value)}
                  placeholder="Xabaringizni yozing..."
                  className="flex-1 bg-slate-50 border border-slate-200 rounded-2xl px-4 py-2.5 text-xs text-slate-800 focus:outline-none focus:border-blue-600 focus:bg-white transition"
                />
                <button
                  type="submit"
                  disabled={!textInput.trim() || isSending}
                  className="p-2.5 bg-blue-600 hover:bg-blue-700 text-white rounded-2xl shadow-md shadow-blue-500/20 disabled:opacity-40 transition active:scale-95 shrink-0"
                >
                  {isSending ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <Send className="w-4 h-4" />
                  )}
                </button>
              </form>
            </>
          ) : (
            /* No conversation selected state */
            <div className="flex-1 flex flex-col items-center justify-center p-8 text-center text-slate-400">
              <MessageSquare className="w-12 h-12 text-slate-300 mb-2" />
              <h3 className="text-sm font-bold text-slate-700">Suhbatni tanlang</h3>
              <p className="text-xs text-slate-400 max-w-xs mt-1">
                Chap paneldan suhbatni tanlang yoki usta profilidan yozishni boshlang.
              </p>
            </div>
          )}
        </div>

      </div>

    </div>
  );
};
