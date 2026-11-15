import { ChangeEvent, FormEvent, useEffect, useRef, useState } from 'react';
import { VisionCraftLogo } from './components/VisionCraftLogo';

type Page = 'login' | 'signin' | 'forgot' | 'adminLogin' | 'home' | 'history' | 'admin' | 'about' | 'contact' | 'feedback';

export type DescriptionMode = 'short' | 'detailed' | 'visually_impaired' | 'social_media' | 'seo';

export type DetectedObject = {
  name: string;
  emoji: string;
  count: number;
};

export type DominantColor = {
  hex: string;
  name: string;
  percentage: number;
  rgb?: number[];
};

export type DescriptionsMap = {
  short: string;
  detailed: string;
  visually_impaired: string;
  social_media: string;
  seo: string;
};

export type CaptionResponse = {
  id: string;
  filename: string;
  content_type: string;
  width: number;
  height: number;
  aspect_ratio?: string;
  orientation?: string;
  scene_category?: string;
  caption: string;
  descriptions?: DescriptionsMap;
  objects?: DetectedObject[];
  ocr_text?: string;
  dominant_colors?: DominantColor[];
  model_used: string;
  stored_path: string;
  timestamp?: string;
  file_size?: string;
  megapixels?: string;
  image_format?: string;
};

type CaptionHistoryItem = CaptionResponse & {
  created_at: string;
};

type AuthUser = { id: string; full_name: string; email: string; created_at: string };
type AuthResponse = { token: string; user: AuthUser };
type ActivityItem = { id: string; action: string; user_id: string | null; user_name: string; user_email: string; details: string; created_at: string };
type FeedbackItem = { id: string; user_id: string; user_name: string; user_email: string; subject: string; message: string; status: 'new' | 'reviewed' | 'resolved'; created_at: string };

type QAItem = {
  id: string;
  question: string;
  answer: string;
};

type ChatMessage = {
  id: string;
  sender: 'user' | 'assistant';
  text: string;
  time: string;
  suggestedPrompts?: string[];
};

const API_BASE_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000';

const APP_NAME = 'VisionCraft';

const SAMPLE_QUESTIONS = [
  'What is the person holding?',
  'How many people are in the image?',
  'What color is the car?',
  'What is the setting or environment?',
  'What objects are on the table?',
];

export default function App() {
  const [page, setPage] = useState<Page>('login');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [caption, setCaption] = useState<CaptionResponse | null>(null);
  const [history, setHistory] = useState<CaptionHistoryItem[]>([]);
  const [isDescribing, setIsDescribing] = useState(false);
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const [isAdminAuthenticated, setIsAdminAuthenticated] = useState(false);
  const [sessionToken, setSessionToken] = useState<string | null>(null);
  const [adminToken, setAdminToken] = useState<string | null>(null);
  const [currentUser, setCurrentUser] = useState<AuthUser | null>(null);
  const [users, setUsers] = useState<AuthUser[]>([]);
  const [activities, setActivities] = useState<ActivityItem[]>([]);
  const [feedback, setFeedback] = useState<FeedbackItem[]>([]);
  const [selectedAdminImage, setSelectedAdminImage] = useState<CaptionHistoryItem | null>(null);
  const [adminSection, setAdminSection] = useState<'overview' | 'users' | 'feedback'>('overview');
  const moreMenuRef = useRef<HTMLDivElement | null>(null);

  // Feature specific states
  const [descriptionMode, setDescriptionMode] = useState<DescriptionMode>('detailed');
  const [speechState, setSpeechState] = useState<{ isSpeaking: boolean; isPaused: boolean }>({
    isSpeaking: false,
    isPaused: false,
  });
  const [copyFeedback, setCopyFeedback] = useState<string | null>(null);
  const [qaQuestion, setQaQuestion] = useState('');
  const [isAsking, setIsAsking] = useState(false);
  const [qaItems, setQaItems] = useState<QAItem[]>([]);

  // Floating Chatbot States
  const [isChatOpen, setIsChatOpen] = useState(false);
  const [chatInput, setChatInput] = useState('');
  const [isChatLoading, setIsChatLoading] = useState(false);
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([
    {
      id: 'welcome',
      sender: 'assistant',
      text: "👋 Hi! I'm your VisionCraft Assistant. Ask me anything about using this app, our 5 description modes, or upload an image to analyze its details together!",
      time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    },
  ]);
  const [chatSuggestions, setChatSuggestions] = useState<string[]>([
    'What can this app do?',
    'What description modes exist?',
    'How does speech audio work?',
  ]);
  const chatScrollRef = useRef<HTMLDivElement | null>(null);

  // Sync chatbot when an image is analyzed
  useEffect(() => {
    if (caption) {
      setChatMessages((prev) => [
        ...prev,
        {
          id: Math.random().toString(36).substring(7),
          sender: 'assistant',
          text: `📷 I have analyzed **${caption.filename}** (${caption.scene_category ?? 'General Scene'})! You can ask me any questions about what is inside this image.`,
          time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
          suggestedPrompts: [
            'What is in this image?',
            'What are the dominant colors?',
            'What objects are detected?',
            'Is there any text visible?',
          ],
        },
      ]);
      setChatSuggestions([
        'What is in this image?',
        'What are the dominant colors?',
        'What objects are detected?',
        'Is there any text visible?',
      ]);
    }
  }, [caption?.id]);

  // Auto-scroll chat window on new message
  useEffect(() => {
    if (chatScrollRef.current) {
      chatScrollRef.current.scrollTop = chatScrollRef.current.scrollHeight;
    }
  }, [chatMessages, isChatLoading, isChatOpen]);

  const formatDate = (value: string) =>
    new Intl.DateTimeFormat('en', { month: 'short', day: 'numeric', year: 'numeric' }).format(new Date(value));

  // Speech synthesis cleanup
  useEffect(() => {
    return () => {
      if ('speechSynthesis' in window) {
        window.speechSynthesis.cancel();
      }
    };
  }, []);

  useEffect(() => {
    return () => {
      if (previewUrl) {
        URL.revokeObjectURL(previewUrl);
      }
    };
  }, [previewUrl]);

  useEffect(() => {
    if (page !== 'home' && page !== 'history') {
      return;
    }

    const loadHistory = async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/api/captions`);

        if (!response.ok) {
          throw new Error('Failed to load description history.');
        }

        const data = (await response.json()) as { items?: CaptionHistoryItem[] };
        setHistory(data.items ?? []);
      } catch {
        setHistory([]);
      }
    };

    void loadHistory();
  }, [page]);

  useEffect(() => {
    if (page === 'admin' && isAdminAuthenticated) void loadAdminData();
  }, [page, isAdminAuthenticated, adminToken]);

  useEffect(() => {
    if (!isMenuOpen) return;

    const closeMenuWhenClickedOutside = (event: MouseEvent) => {
      if (moreMenuRef.current && !moreMenuRef.current.contains(event.target as Node)) {
        setIsMenuOpen(false);
      }
    };

    document.addEventListener('mousedown', closeMenuWhenClickedOutside);
    return () => document.removeEventListener('mousedown', closeMenuWhenClickedOutside);
  }, [isMenuOpen]);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setIsSubmitting(true);
    setMessage(null);
    setError(null);

    const formData = new FormData(event.currentTarget);
    const email = String(formData.get('email') ?? '').trim();
    const password = String(formData.get('password') ?? '').trim();
    const fullName = String(formData.get('fullName') ?? '').trim();

    try {
      if (page === 'forgot') {
        if (!email) {
          throw new Error('Enter your email address to receive reset instructions.');
        }
        setMessage(`Password reset instructions were sent to ${email}.`);
        return;
      }

      if (page === 'login' && (!email || !password)) {
        throw new Error('Enter both email and password to continue.');
      }

      if (page === 'signin' && (!fullName || !email || !password)) {
        throw new Error('Fill in your name, email, and password to create the account.');
      }
      if (page === 'login' || page === 'signin' || page === 'adminLogin') {
        const endpoint = page === 'adminLogin' ? '/api/auth/admin/login' : page === 'login' ? '/api/auth/login' : '/api/auth/register';
        const payload = page === 'signin' ? { full_name: fullName, email, password } : { email, password };
        const response = await fetch(`${API_BASE_URL}${endpoint}`, {
          method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload),
        });
        const data = (await response.json().catch(() => null)) as (AuthResponse & { detail?: string }) | null;
        if (!response.ok || !data) throw new Error(data?.detail ?? 'Authentication failed.');
        setCurrentUser(data.user);
        if (page === 'adminLogin') {
          setAdminToken(data.token);
          setIsAdminAuthenticated(true);
          setPage('admin');
        } else {
          setSessionToken(data.token);
          setMessage(page === 'login' ? 'Login successful. Your session is ready.' : 'Account created successfully.');
          setPage('home');
          setIsMenuOpen(false);
        }
        return;
      }
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : 'Authentication failed.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleFileChange = (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0] ?? null;

    if ('speechSynthesis' in window) {
      window.speechSynthesis.cancel();
      setSpeechState({ isSpeaking: false, isPaused: false });
    }

    setSelectedFile(file);
    setCaption(null);
    setQaItems([]);
    setQaQuestion('');
    setError(null);
    setMessage(null);

    if (previewUrl) {
      URL.revokeObjectURL(previewUrl);
    }

    if (file) {
      setPreviewUrl(URL.createObjectURL(file));
    } else {
      setPreviewUrl(null);
    }
  };

  const handleDescribeImage = async () => {
    if (!selectedFile) {
      setError('Choose an image first, then click Describe Image.');
      return;
    }

    if ('speechSynthesis' in window) {
      window.speechSynthesis.cancel();
      setSpeechState({ isSpeaking: false, isPaused: false });
    }

    setIsDescribing(true);
    setError(null);
    setMessage(null);
    setQaItems([]);

    try {
      const formData = new FormData();
      formData.append('image', selectedFile);

      const response = await fetch(`${API_BASE_URL}/api/caption`, {
        method: 'POST',
        headers: sessionToken ? { 'X-Session-Token': sessionToken } : {},
        body: formData,
      });

      if (!response.ok) {
        const payload = (await response.json().catch(() => null)) as { detail?: string } | null;
        throw new Error(payload?.detail ?? 'Failed to describe the image.');
      }

      const data = (await response.json()) as CaptionResponse;
      setCaption(data);
      setMessage('Comprehensive image analysis generated successfully!');
      setHistory((currentHistory) => [
        { ...data, created_at: new Date().toISOString() },
        ...currentHistory.filter((item) => item.stored_path !== data.stored_path),
      ]);
    } catch (describeError) {
      setError(describeError instanceof Error ? describeError.message : 'Failed to describe the image.');
    } finally {
      setIsDescribing(false);
    }
  };

  const getActiveDescription = (item: CaptionResponse | null, mode: DescriptionMode): string => {
    if (!item) return '';
    if (item.descriptions && item.descriptions[mode]) {
      return item.descriptions[mode];
    }
    return item.caption || '';
  };

  const handleToggleSpeech = (text: string) => {
    if (!('speechSynthesis' in window)) {
      setError('Text-to-speech is not supported in this browser.');
      return;
    }

    if (speechState.isSpeaking) {
      if (speechState.isPaused) {
        window.speechSynthesis.resume();
        setSpeechState({ isSpeaking: true, isPaused: false });
      } else {
        window.speechSynthesis.pause();
        setSpeechState({ isSpeaking: true, isPaused: true });
      }
      return;
    }

    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.rate = 0.95;
    utterance.pitch = 1.0;
    utterance.onstart = () => {
      setSpeechState({ isSpeaking: true, isPaused: false });
    };
    utterance.onend = () => {
      setSpeechState({ isSpeaking: false, isPaused: false });
    };
    utterance.onerror = () => {
      setSpeechState({ isSpeaking: false, isPaused: false });
    };

    window.speechSynthesis.speak(utterance);
  };

  const handleStopSpeech = () => {
    if ('speechSynthesis' in window) {
      window.speechSynthesis.cancel();
    }
    setSpeechState({ isSpeaking: false, isPaused: false });
  };

  const handleCopy = async (text: string, label: string = 'Description') => {
    try {
      await navigator.clipboard.writeText(text);
      setCopyFeedback(`${label} copied!`);
      setTimeout(() => setCopyFeedback(null), 2500);
    } catch {
      setCopyFeedback('Failed to copy');
      setTimeout(() => setCopyFeedback(null), 2500);
    }
  };

  const handleDownloadTxt = (item: CaptionResponse, currentMode: DescriptionMode) => {
    const baseName = item.filename.replace(/\.[^/.]+$/, '').replace(/[^a-z0-9-_]+/gi, '-').replace(/^-+|-+$/g, '') || 'deep-caption';
    const activeDesc = getActiveDescription(item, currentMode);
    
    const lines = [
      `=============================================================`,
      `DEEP CAPTION - MULTI-MODAL IMAGE ANALYSIS REPORT`,
      `=============================================================`,
      `File: ${item.filename}`,
      `Format: ${item.image_format || 'N/A'} | Size: ${item.file_size || 'N/A'}`,
      `Dimensions: ${item.width} x ${item.height} (${item.aspect_ratio ?? 'N/A'}, ${item.orientation ?? 'N/A'}) ${item.megapixels ? `[${item.megapixels}]` : ''}`,
      `Timestamp / Captured: ${item.timestamp || 'N/A'}`,
      `Scene Category: ${item.scene_category ?? 'General Scene'}`,
      `Model: ${item.model_used}`,
      ``,
      `-------------------------------------------------------------`,
      `[ACTIVE DESCRIPTION - ${currentMode.toUpperCase().replace('_', ' ')}]`,
      `-------------------------------------------------------------`,
      activeDesc,
      ``,
      `-------------------------------------------------------------`,
      `[ALL DESCRIPTION MODES]`,
      `-------------------------------------------------------------`,
      `• SHORT:\n  ${item.descriptions?.short ?? item.caption}`,
      ``,
      `• DETAILED:\n  ${item.descriptions?.detailed ?? item.caption}`,
      ``,
      `• FOR VISUALLY IMPAIRED:\n  ${item.descriptions?.visually_impaired ?? 'N/A'}`,
      ``,
      `• SOCIAL MEDIA:\n  ${item.descriptions?.social_media ?? 'N/A'}`,
      ``,
      `• SEO DESCRIPTION:\n  ${item.descriptions?.seo ?? 'N/A'}`,
      ``,
      `-------------------------------------------------------------`,
      `[DETECTED OBJECTS]`,
      `-------------------------------------------------------------`,
      item.objects && item.objects.length
        ? item.objects.map(o => `• ${o.name} (${o.count})`).join('\n')
        : 'No isolated objects identified',
      ``,
      `-------------------------------------------------------------`,
      `[EXTRACTED TEXT (OCR)]`,
      `-------------------------------------------------------------`,
      item.ocr_text ? item.ocr_text : 'No text detected in image',
      ``,
      `-------------------------------------------------------------`,
      `[DOMINANT COLOR PALETTE]`,
      `-------------------------------------------------------------`,
      item.dominant_colors && item.dominant_colors.length
        ? item.dominant_colors.map(c => `• ${c.name} (${c.hex}) - ${c.percentage}% coverage`).join('\n')
        : 'N/A',
      ``,
      `Exported: ${new Date().toLocaleString()}`,
    ];

    const blob = new Blob([lines.join('\n')], { type: 'text/plain;charset=utf-8' });
    const downloadUrl = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = downloadUrl;
    link.download = `${baseName}-analysis.txt`;
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(downloadUrl);
  };

  const handleDownloadJson = (item: CaptionResponse) => {
    const baseName = item.filename.replace(/\.[^/.]+$/, '').replace(/[^a-z0-9-_]+/gi, '-').replace(/^-+|-+$/g, '') || 'deep-caption';
    const payload = {
      id: item.id,
      filename: item.filename,
      dimensions: {
        width: item.width,
        height: item.height,
        megapixels: item.megapixels ?? '',
        aspect_ratio: item.aspect_ratio ?? '1:1',
        orientation: item.orientation ?? 'Landscape',
      },
      technical_details: {
        image_format: item.image_format ?? '',
        file_size: item.file_size ?? '',
        timestamp: item.timestamp ?? '',
      },
      scene_category: item.scene_category ?? 'General Scene',
      descriptions: item.descriptions ?? {
        short: item.caption,
        detailed: item.caption,
        visually_impaired: item.caption,
        social_media: item.caption,
        seo: item.caption,
      },
      objects: item.objects ?? [],
      ocr_text: item.ocr_text ?? '',
      dominant_colors: item.dominant_colors ?? [],
      model_used: item.model_used,
      exported_at: new Date().toISOString(),
    };

    const blob = new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' });
    const downloadUrl = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = downloadUrl;
    link.download = `${baseName}-developer-spec.json`;
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(downloadUrl);
  };

  const handleAskQuestion = async (e?: FormEvent, customQuestion?: string) => {
    if (e) e.preventDefault();
    const query = (customQuestion ?? qaQuestion).trim();
    if (!query || !caption) return;

    setIsAsking(true);
    setError(null);

    try {
      const response = await fetch(`${API_BASE_URL}/api/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: query, caption_id: caption.id }),
      });

      let answerText = '';
      if (response.ok) {
        const data = (await response.json()) as { message: string; reply: string };
        answerText = data.reply;
      } else {
        const fbRes = await fetch(`${API_BASE_URL}/api/caption/${caption.id}/ask`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ question: query }),
        });
        if (!fbRes.ok) {
          const errData = await fbRes.json().catch(() => null);
          throw new Error(errData?.detail ?? 'Failed to get answer.');
        }
        const fbData = (await fbRes.json()) as { question: string; answer: string };
        answerText = fbData.answer;
      }

      setQaItems((prev) => [
        ...prev,
        { id: Math.random().toString(36).substring(7), question: query, answer: answerText },
      ]);
      setQaQuestion('');
    } catch (askError) {
      setError(askError instanceof Error ? askError.message : 'Could not answer question.');
    } finally {
      setIsAsking(false);
    }
  };

  const handleSendChatMessage = async (e?: FormEvent, directMessage?: string) => {
    if (e) e.preventDefault();
    const query = (directMessage ?? chatInput).trim();
    if (!query || isChatLoading) return;

    const userMsg: ChatMessage = {
      id: Math.random().toString(36).substring(7),
      sender: 'user',
      text: query,
      time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    };

    setChatMessages((prev) => [...prev, userMsg]);
    setChatInput('');
    setIsChatLoading(true);

    try {
      const response = await fetch(`${API_BASE_URL}/api/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: query,
          caption_id: caption ? caption.id : null,
        }),
      });

      if (!response.ok) {
        const errData = await response.json().catch(() => null);
        throw new Error(errData?.detail ?? 'Failed to get a response from AI.');
      }

      const data = (await response.json()) as {
        message: string;
        reply: string;
        suggested_prompts: string[];
      };

      const aiMsg: ChatMessage = {
        id: Math.random().toString(36).substring(7),
        sender: 'assistant',
        text: data.reply,
        time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        suggestedPrompts: data.suggested_prompts,
      };

      setChatMessages((prev) => [...prev, aiMsg]);
      if (data.suggested_prompts && data.suggested_prompts.length > 0) {
        setChatSuggestions(data.suggested_prompts);
      }
    } catch (chatError) {
      const errMsg: ChatMessage = {
        id: Math.random().toString(36).substring(7),
        sender: 'assistant',
        text: chatError instanceof Error ? `⚠️ ${chatError.message}` : '⚠️ Could not connect to AI service.',
        time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      };
      setChatMessages((prev) => [...prev, errMsg]);
    } finally {
      setIsChatLoading(false);
    }
  };

  const handleClearChat = () => {
    setChatMessages([
      {
        id: 'cleared',
        sender: 'assistant',
        text: "Chat cleared. What else can I help you analyze or explore?",
        time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        suggestedPrompts: caption ? [
          'What is in this image?',
          'What are the dominant colors?',
          'What objects are detected?',
        ] : [
          'What can this app do?',
          'What description modes exist?',
          'How do I upload an image?',
        ],
      },
    ]);
  };

  const loadHistory = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/captions`);

      if (!response.ok) {
        throw new Error('Failed to load description history.');
      }

      const data = (await response.json()) as { items?: CaptionHistoryItem[] };
      setHistory(data.items ?? []);
    } catch {
      setHistory([]);
    }
  };

  const loadAdminData = async () => {
    if (!adminToken) return;
    try {
      const headers = { 'X-Session-Token': adminToken };
      const [usersResponse, activityResponse, imagesResponse, feedbackResponse] = await Promise.all([
        fetch(`${API_BASE_URL}/api/admin/users`, { headers }),
        fetch(`${API_BASE_URL}/api/admin/activity`, { headers }),
        fetch(`${API_BASE_URL}/api/admin/images`, { headers }),
        fetch(`${API_BASE_URL}/api/admin/feedback`, { headers }),
      ]);
      if (!usersResponse.ok || !activityResponse.ok || !imagesResponse.ok || !feedbackResponse.ok) throw new Error('Unable to load administrator records.');
      setUsers((await usersResponse.json()) as AuthUser[]);
      const activityData = (await activityResponse.json()) as ActivityItem[];
      setActivities(activityData.filter((activity) => activity.action !== 'Generated a caption'));
      const imageData = (await imagesResponse.json()) as { items?: CaptionHistoryItem[] };
      setHistory(imageData.items ?? []);
      setFeedback((await feedbackResponse.json()) as FeedbackItem[]);
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : 'Unable to load administrator records.');
    }
  };

  const handleFeedbackSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!sessionToken) {
      setError('Please sign in before submitting feedback.');
      setPage('login');
      return;
    }

    const form = event.currentTarget;
    const formData = new FormData(form);
    setIsSubmitting(true);
    setMessage(null);
    setError(null);

    try {
      const response = await fetch(`${API_BASE_URL}/api/feedback`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-Session-Token': sessionToken },
        body: JSON.stringify({ subject: String(formData.get('subject') ?? '').trim(), message: String(formData.get('feedback') ?? '').trim() }),
      });
      const data = (await response.json().catch(() => null)) as { detail?: string } | null;
      if (!response.ok) throw new Error(data?.detail ?? 'Unable to submit feedback.');
      form.reset();
      setMessage('Thanks — your feedback has been sent to the administrator.');
    } catch (feedbackError) {
      setError(feedbackError instanceof Error ? feedbackError.message : 'Unable to submit feedback.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDeleteHistoryItem = async (captionId: string) => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/captions/${captionId}`, {
        method: 'DELETE',
      });

      if (!response.ok) {
        const payload = (await response.json().catch(() => null)) as { detail?: string } | null;
        throw new Error(payload?.detail ?? 'Failed to delete history item.');
      }

      setHistory((currentHistory) => currentHistory.filter((item) => item.id !== captionId));
      if (caption?.id === captionId) {
        setCaption(null);
      }
      setMessage('History item deleted successfully.');
    } catch (deleteError) {
      setError(deleteError instanceof Error ? deleteError.message : 'Failed to delete history item.');
    }
  };

  const renderHome = () => {
    const activeDescriptionText = getActiveDescription(caption, descriptionMode);

    return (
      <section className="home-layout">
        {/* Top Header Bar */}
        <header className="home-top-nav panel">
          <div
            className="home-brand"
            onClick={() => setPage('home')}
            role="button"
            tabIndex={0}
            title="VisionCraft AI - Multi-Modal Vision Intelligence"
          >
            <VisionCraftLogo size={44} showText={true} />
          </div>

          <div className="home-nav-right">
            {currentUser ? (
              <div className="user-pill">
                <span className="user-avatar-circle">
                  {currentUser.full_name ? currentUser.full_name[0].toUpperCase() : 'U'}
                </span>
                <span className="user-name-text">{currentUser.full_name}</span>
              </div>
            ) : null}

            <div className="dropdown-wrap" ref={moreMenuRef}>
              <button
                className={`menu-trigger-btn ${isMenuOpen ? 'active' : ''}`}
                type="button"
                onClick={() => setIsMenuOpen((current) => !current)}
                aria-expanded={isMenuOpen}
                aria-haspopup="menu"
                title={isMenuOpen ? "Close navigation menu" : "Open navigation menu"}
              >
                <span className={`menu-hamburger-icon ${isMenuOpen ? 'open' : ''}`} aria-hidden="true">
                  <span className="bar bar-1"></span>
                  <span className="bar bar-2"></span>
                  <span className="bar bar-3"></span>
                </span>
                <span className="menu-btn-text">Menu</span>
                <svg
                  className={`menu-chevron-icon ${isMenuOpen ? 'open' : ''}`}
                  width="13"
                  height="13"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2.8"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  aria-hidden="true"
                >
                  <polyline points="6 9 12 15 18 9"></polyline>
                </svg>
              </button>

              {isMenuOpen ? (
                <div className="dropdown-menu" role="menu">
                  <button
                    type="button"
                    role="menuitem"
                    onClick={() => {
                      setPage('history');
                      setIsMenuOpen(false);
                      void loadHistory();
                    }}
                  >
                    📂 History
                  </button>
                  <button
                    type="button"
                    role="menuitem"
                    onClick={() => {
                      setIsMenuOpen(false);
                      setPage('contact');
                    }}
                  >
                    📞 Contact Us
                  </button>
                  <button
                    type="button"
                    role="menuitem"
                    onClick={() => {
                      setIsMenuOpen(false);
                      setPage('about');
                    }}
                  >
                    ℹ️ About Us
                  </button>
                  <button
                    type="button"
                    role="menuitem"
                    onClick={() => {
                      setError(null);
                      setMessage(null);
                      setIsMenuOpen(false);
                      setPage('feedback');
                    }}
                  >
                    💬 Send Feedback
                  </button>
                  <button
                    type="button"
                    role="menuitem"
                    onClick={() => {
                      setPage('login');
                      setSessionToken(null);
                      setCurrentUser(null);
                      setMessage(null);
                      setCaption(null);
                      setSelectedFile(null);
                      setPreviewUrl(null);
                      setIsMenuOpen(false);
                      if ('speechSynthesis' in window) window.speechSynthesis.cancel();
                    }}
                  >
                    🚪 Logout
                  </button>
                </div>
              ) : null}
            </div>
          </div>
        </header>

        {/* Status Alerts */}
        {message ? <div className="alert-banner success-banner">{message}</div> : null}
        {error ? <div className="alert-banner error-banner">{error}</div> : null}
        {copyFeedback ? <div className="toast-notification">{copyFeedback}</div> : null}

        {/* Main 2-Column or Stacked Dashboard Grid */}
        <div className="dashboard-grid">
          {/* Left Column: Upload & Image Inspection */}
          <div className="dashboard-left-col">
            <div className="panel upload-inspector-card">
              <div className="panel-header-row">
                <h2>Upload Your Image</h2>
              </div>

              {/* Upload Dropzone */}
              <label className={`upload-dropzone-modern ${selectedFile ? 'has-file' : ''}`}>
                <input type="file" accept="image/*" onChange={handleFileChange} />
                <div className="dropzone-inner">
                  <span className="dropzone-icon">📷</span>
                  <strong>{selectedFile ? selectedFile.name : 'Choose or drop an image'}</strong>
                  <span className="dropzone-sub">Supports PNG, JPG, WEBP, GIF</span>
                </div>
              </label>

              {/* Describe Action Button */}
              <button
                className="primary-button describe-btn full-width"
                type="button"
                onClick={handleDescribeImage}
                disabled={!selectedFile || isDescribing}
              >
                {isDescribing ? (
                  <>
                    <span className="spinner-icon"></span>
                    <span>Analyzing Vision Intelligence...</span>
                  </>
                ) : (
                  <>
                    <span>⚡ Generate Full Analysis</span>
                  </>
                )}
              </button>

              {/* Image Preview Box */}
              <div className="image-preview-wrapper">
                <div className="preview-header-bar">
                  <span className="preview-label">IMAGE PREVIEW</span>
                  {caption ? (
                    <span className="category-pill">{caption.scene_category ?? 'General Scene'}</span>
                  ) : null}
                </div>

                <div className="preview-frame">
                  {isDescribing ? (
                    <div className="preview-placeholder preview-loading-state">
                      <div className="pulse-loader"></div>
                      <p>Processing neural vision tasks...</p>
                      <small>Generating modes • Detecting objects • Extracting text</small>
                    </div>
                  ) : previewUrl ? (
                    <img src={previewUrl} alt="Uploaded preview" className="main-preview-img" />
                  ) : (
                    <div className="preview-placeholder">
                      <span className="placeholder-icon">🖼️</span>
                      <p>Your uploaded image will appear here</p>
                    </div>
                  )}
                </div>

                {/* Quick Dimensions, Timestamp, and Technical Specs Bar */}
                {caption ? (
                  <div className="image-meta-grid">
                    <div className="meta-item">
                      <span className="meta-label">Dimensions</span>
                      <span className="meta-val">{caption.width} × {caption.height} px {caption.megapixels ? `(${caption.megapixels})` : ''}</span>
                    </div>
                    <div className="meta-item">
                      <span className="meta-label">Orientation</span>
                      <span className="meta-val">{caption.orientation ?? 'Landscape'}</span>
                    </div>
                    <div className="meta-item">
                      <span className="meta-label">Aspect Ratio</span>
                      <span className="meta-val">{caption.aspect_ratio ?? '1:1'}</span>
                    </div>
                    <div className="meta-item">
                      <span className="meta-label">Category</span>
                      <span className="meta-val">{caption.scene_category ?? 'General'}</span>
                    </div>
                    {caption.image_format || caption.file_size ? (
                      <div className="meta-item">
                        <span className="meta-label">Format & Size</span>
                        <span className="meta-val">{caption.image_format || 'IMG'} • {caption.file_size || 'N/A'}</span>
                      </div>
                    ) : null}
                    {caption.timestamp ? (
                      <div className="meta-item meta-span-full">
                        <span className="meta-label">Captured / Recorded</span>
                        <span className="meta-val">⏱️ {caption.timestamp}</span>
                      </div>
                    ) : null}
                  </div>
                ) : null}
              </div>
            </div>
          </div>

          {/* Right Column: Multi-Mode Descriptions + Analysis + Q&A */}
          <div className="dashboard-right-col">
            {caption ? (
              <div className="analysis-results-container">
                {/* 1. DESCRIPTION MODES & AUDIO BAR */}
                <div className="panel description-panel">
                  <div className="panel-header-row">
                    <div>
                      <p className="eyebrow">AI DESCRIPTION</p>
                      <h2>Multi-Mode Description</h2>
                    </div>
                    <span className="model-tag-pill">{caption.model_used}</span>
                  </div>

                  {/* Mode Selector Tabs */}
                  <div className="modes-tab-bar" role="tablist" aria-label="Description modes">
                    <button
                      type="button"
                      role="tab"
                      aria-selected={descriptionMode === 'short'}
                      className={`mode-tab-btn ${descriptionMode === 'short' ? 'active' : ''}`}
                      onClick={() => setDescriptionMode('short')}
                    >
                      ⚡ Short
                    </button>
                    <button
                      type="button"
                      role="tab"
                      aria-selected={descriptionMode === 'detailed'}
                      className={`mode-tab-btn ${descriptionMode === 'detailed' ? 'active' : ''}`}
                      onClick={() => setDescriptionMode('detailed')}
                    >
                      📖 Detailed
                    </button>
                    <button
                      type="button"
                      role="tab"
                      aria-selected={descriptionMode === 'visually_impaired'}
                      className={`mode-tab-btn ${descriptionMode === 'visually_impaired' ? 'active' : ''}`}
                      onClick={() => setDescriptionMode('visually_impaired')}
                    >
                      👁️ For Visually Impaired
                    </button>
                    <button
                      type="button"
                      role="tab"
                      aria-selected={descriptionMode === 'social_media'}
                      className={`mode-tab-btn ${descriptionMode === 'social_media' ? 'active' : ''}`}
                      onClick={() => setDescriptionMode('social_media')}
                    >
                      📱 Social Media
                    </button>
                    <button
                      type="button"
                      role="tab"
                      aria-selected={descriptionMode === 'seo'}
                      className={`mode-tab-btn ${descriptionMode === 'seo' ? 'active' : ''}`}
                      onClick={() => setDescriptionMode('seo')}
                    >
                      🔍 SEO Description
                    </button>
                  </div>

                  {/* Mode Helper Badge */}
                  <div className="mode-desc-helper">
                    {descriptionMode === 'short' && '💡 Crisp, high-level single-sentence summary of the image.'}
                    {descriptionMode === 'detailed' && '💡 Comprehensive narrative detailing subjects, environment, context, and activities.'}
                    {descriptionMode === 'visually_impaired' && '💡 High-accessibility description with spatial layout, focal subjects, lighting, and ambient balance.'}
                    {descriptionMode === 'social_media' && '💡 Engaging copy crafted for social feeds, complete with hashtags and emojis.'}
                    {descriptionMode === 'seo' && '💡 Keyword-optimized metadata and descriptive alt-text for search engines.'}
                  </div>

                  {/* Active Description Display */}
                  <div className="description-text-card">
                    <p className="active-caption-body">"{activeDescriptionText}"</p>
                  </div>

                  {/* Read Aloud & Action Bar */}
                  <div className="description-actions-bar">
                    {/* Audio Player Controls */}
                    <div className="audio-player-group">
                      <button
                        className={`action-btn audio-listen-btn ${speechState.isSpeaking && !speechState.isPaused ? 'playing' : ''}`}
                        type="button"
                        onClick={() => handleToggleSpeech(activeDescriptionText)}
                      >
                        {speechState.isSpeaking && !speechState.isPaused ? (
                          <>
                            <span className="btn-icon">⏸</span>
                            <span>Pause</span>
                          </>
                        ) : speechState.isPaused ? (
                          <>
                            <span className="btn-icon">▶</span>
                            <span>Resume</span>
                          </>
                        ) : (
                          <>
                            <span className="btn-icon">🔊</span>
                            <span>Listen Aloud</span>
                          </>
                        )}
                      </button>

                      {speechState.isSpeaking || speechState.isPaused ? (
                        <button
                          className="action-btn audio-stop-btn"
                          type="button"
                          onClick={handleStopSpeech}
                          title="Stop audio playback"
                        >
                          ⏹ Stop
                        </button>
                      ) : null}

                      {speechState.isSpeaking && !speechState.isPaused ? (
                        <div className="soundwave-anim">
                          <span className="bar bar1"></span>
                          <span className="bar bar2"></span>
                          <span className="bar bar3"></span>
                          <span className="bar bar4"></span>
                        </div>
                      ) : null}
                    </div>

                    {/* Copy & Export Controls */}
                    <div className="export-btn-group">
                      <button
                        className="action-btn copy-btn"
                        type="button"
                        onClick={() => handleCopy(activeDescriptionText, 'Description')}
                      >
                        📋 Copy Text
                      </button>

                      <button
                        className="action-btn download-txt-btn"
                        type="button"
                        onClick={() => handleDownloadTxt(caption, descriptionMode)}
                      >
                        ⬇ Download .txt
                      </button>

                      <button
                        className="action-btn download-json-btn"
                        type="button"
                        onClick={() => handleDownloadJson(caption)}
                        title="Generate structured JSON for developers"
                      >
                        {'{ }'} JSON for Devs
                      </button>
                    </div>
                  </div>
                </div>

                {/* 2. DETECTED OBJECTS & OCR TEXT IN 2-GRID */}
                <div className="features-subgrid">
                  {/* Detected Objects Card */}
                  <div className="panel feature-subcard">
                    <div className="subcard-header">
                      <div className="subcard-title">
                        <span className="subcard-icon">🏷️</span>
                        <div>
                          <p className="eyebrow">DETECTION</p>
                          <h3>Objects Detected</h3>
                        </div>
                      </div>
                      <span className="count-tag">{caption.objects?.length ?? 0}</span>
                    </div>

                    <div className="objects-pills-list">
                      {caption.objects && caption.objects.length > 0 ? (
                        caption.objects.map((obj, idx) => (
                          <span className="object-badge" key={`${obj.name}-${idx}`}>
                            <span className="obj-emoji">{obj.emoji}</span>
                            <span className="obj-name">{obj.name}</span>
                            <span className="obj-count">×{obj.count}</span>
                          </span>
                        ))
                      ) : (
                        <p className="empty-subtext">No isolated objects identified in this image.</p>
                      )}
                    </div>
                  </div>

                  {/* OCR / Text Extraction Card */}
                  <div className="panel feature-subcard">
                    <div className="subcard-header">
                      <div className="subcard-title">
                        <span className="subcard-icon">🔤</span>
                        <div>
                          <p className="eyebrow">OCR ENGINE</p>
                          <h3>Image Text (OCR)</h3>
                        </div>
                      </div>
                      {caption.ocr_text ? (
                        <button
                          className="ghost-button copy-mini-btn"
                          type="button"
                          onClick={() => handleCopy(caption.ocr_text ?? '', 'OCR Text')}
                        >
                          📋 Copy
                        </button>
                      ) : null}
                    </div>

                    <div className="ocr-text-box">
                      {caption.ocr_text ? (
                        <blockquote className="ocr-content-quote">"{caption.ocr_text}"</blockquote>
                      ) : (
                        <p className="empty-subtext">No written text or document characters detected in image.</p>
                      )}
                    </div>
                  </div>
                </div>

                {/* 3. DOMINANT COLORS PALETTE */}
                <div className="panel colors-panel">
                  <div className="subcard-header">
                    <div className="subcard-title">
                      <span className="subcard-icon">🎨</span>
                      <div>
                        <p className="eyebrow">COLOR ANALYSIS</p>
                        <h3>Dominant Colors</h3>
                      </div>
                    </div>
                    <small className="palette-helper">Click any swatch to copy Hex</small>
                  </div>

                  <div className="colors-swatches-grid">
                    {caption.dominant_colors && caption.dominant_colors.length > 0 ? (
                      caption.dominant_colors.map((col, idx) => (
                        <div
                          className="color-card"
                          key={`${col.hex}-${idx}`}
                          onClick={() => handleCopy(col.hex, `Hex ${col.hex}`)}
                          title={`Click to copy ${col.hex}`}
                        >
                          <div className="color-chip" style={{ backgroundColor: col.hex }}></div>
                          <div className="color-info">
                            <span className="color-name">{col.name}</span>
                            <span className="color-hex">{col.hex}</span>
                            <div className="color-bar-wrap">
                              <div className="color-bar-fill" style={{ width: `${col.percentage}%`, backgroundColor: col.hex }}></div>
                            </div>
                            <span className="color-pct">{col.percentage}%</span>
                          </div>
                        </div>
                      ))
                    ) : (
                      <p className="empty-subtext">Color palette unavailable.</p>
                    )}
                  </div>
                </div>

                {/* 4. IMAGE QUESTION & ANSWER (VQA) */}
                <div className="panel vqa-panel">
                  <div className="subcard-header">
                    <div className="subcard-title">
                      <span className="subcard-icon">💬</span>
                      <div>
                        <p className="eyebrow">INTERACTIVE INTELLIGENCE</p>
                        <h3>Ask About Image</h3>
                      </div>
                    </div>
                    <span className="panel-badge">VQA AI</span>
                  </div>

                  <p className="vqa-lead">
                    Ask any question about people, objects, actions, or scene details in the uploaded image.
                  </p>

                  {/* Preset Question Chips */}
                  <div className="preset-chips-wrap">
                    <span className="chips-label">Suggestions:</span>
                    {SAMPLE_QUESTIONS.map((q) => (
                      <button
                        key={q}
                        type="button"
                        className="preset-chip-btn"
                        onClick={() => void handleAskQuestion(undefined, q)}
                        disabled={isAsking}
                      >
                        {q}
                      </button>
                    ))}
                  </div>

                  {/* Custom Question Input Form */}
                  <form className="qa-input-form" onSubmit={(e) => void handleAskQuestion(e)}>
                    <input
                      type="text"
                      className="qa-text-input"
                      placeholder="e.g., What is the person holding? What color is the car?"
                      value={qaQuestion}
                      onChange={(e) => setQaQuestion(e.target.value)}
                      disabled={isAsking}
                    />
                    <button className="primary-button qa-submit-btn" type="submit" disabled={isAsking || !qaQuestion.trim()}>
                      {isAsking ? (
                        <>
                          <span className="spinner-icon mini"></span>
                          <span>Answering...</span>
                        </>
                      ) : (
                        'Ask AI'
                      )}
                    </button>
                  </form>

                  {/* Q&A Stream */}
                  {qaItems.length > 0 ? (
                    <div className="qa-stream">
                      {qaItems.map((qa) => (
                        <div className="qa-conversation-card" key={qa.id}>
                          <div className="qa-question-row">
                            <span className="qa-bubble-avatar user">Q</span>
                            <strong>{qa.question}</strong>
                          </div>
                          <div className="qa-answer-row">
                            <span className="qa-bubble-avatar ai">AI</span>
                            <div className="qa-answer-content">
                              <p>{qa.answer}</p>
                              <button
                                className="ghost-button qa-speak-btn"
                                type="button"
                                onClick={() => handleToggleSpeech(qa.answer)}
                              >
                                🔊 Read Answer
                              </button>
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : null}
                </div>
              </div>
            ) : (
              /* Empty Initial Welcome State */
              <div className="panel initial-empty-state">
                <div className="empty-state-logo-wrap">
                  <VisionCraftLogo size={64} />
                </div>
                <h2>Upload an image to start multi-modal analysis</h2>
                <p>
                  VisionCraft AI processes your image with deep learning vision models to provide:
                </p>
                <div className="features-showcase-grid">
                  <div className="showcase-card">
                    <span className="showcase-icon">⚡</span>
                    <strong>5 Description Modes</strong>
                    <span>Short, Detailed, Accessibility, Social Media, and SEO alt text.</span>
                  </div>
                  <div className="showcase-card">
                    <span className="showcase-icon">🔊</span>
                    <strong>Read Aloud (TTS)</strong>
                    <span>Instant speech synthesis audio with playback controls.</span>
                  </div>
                  <div className="showcase-card">
                    <span className="showcase-icon">🏷️</span>
                    <strong>Object Recognition</strong>
                    <span>Categorized badges with emoji identifiers and item counts.</span>
                  </div>
                  <div className="showcase-card">
                    <span className="showcase-icon">🔤</span>
                    <strong>OCR Text Extraction</strong>
                    <span>Extract written sentences from documents, signs, and screens.</span>
                  </div>
                  <div className="showcase-card">
                    <span className="showcase-icon">🎨</span>
                    <strong>Dominant Colors</strong>
                    <span>Palette breakdown with hex codes and color percentages.</span>
                  </div>
                  <div className="showcase-card">
                    <span className="showcase-icon">💬</span>
                    <strong>Image Question & Answer</strong>
                    <span>Ask natural language questions like "What is the person holding?".</span>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      </section>
    );
  };

  const renderAbout = () => (
    <section className="history-page">
      <div className="history-page-hero panel">
        <div className="home-copy">
          <span className="brand-mark inline-brand">{APP_NAME}</span>
          <p className="eyebrow">About Us</p>
          <h1>About Deep Caption</h1>
          <p className="lead">
            Deep Caption is an advanced multi-modal vision platform that turns images into comprehensive descriptions, detected objects, extracted text, color palettes, audio readouts, and interactive visual Q&A.
          </p>

          <div className="hero-actions">
            <button className="primary-button" type="button" onClick={() => setPage('home')}>
              Back to Workspace
            </button>
          </div>
        </div>

        <div className="home-panel panel-surface">
          <strong>What we do</strong>
          <p>We empower web creators, developers, social managers, and visually impaired users with state-of-the-art vision intelligence.</p>
          <p>Everything runs cleanly with multi-mode descriptions, instant speech synthesis, and visual question answering.</p>
        </div>
      </div>
    </section>
  );

  const renderContact = () => (
    <section className="history-page">
      <div className="history-page-hero panel">
        <div className="home-copy">
          <span className="brand-mark inline-brand">{APP_NAME}</span>
          <p className="eyebrow">Contact Us</p>
          <h1>Get in touch</h1>
          <p className="lead">
            Reach out for support, enterprise integration, or questions about the vision AI pipeline.
          </p>

          <div className="hero-actions">
            <button className="primary-button" type="button" onClick={() => setPage('home')}>
              Back to Workspace
            </button>
          </div>
        </div>

        <div className="home-panel panel-surface">
          <strong>Contact details</strong>
          <p>Email: support@deepcaption.local</p>
          <p>Phone: +91 96013 33006</p>
          <p>We usually respond within 24 hours.</p>
        </div>
      </div>
    </section>
  );

  const renderFeedback = () => (
    <section className="auth-layout single feedback-layout">
      <form className="auth-card panel feedback-card" onSubmit={handleFeedbackSubmit}>
        <div className="auth-header">
          <span className="brand-mark inline-brand">{APP_NAME}</span>
          <p className="eyebrow">Feedback</p>
          <h2>Help us improve</h2>
          <p>Tell us what worked well or what we can make better. The administrator will review your message.</p>
        </div>

        <label className="auth-field">
          <span>Subject</span>
          <input name="subject" type="text" placeholder="What is this about?" minLength={3} maxLength={120} required />
        </label>

        <label className="auth-field">
          <span>Your feedback</span>
          <textarea name="feedback" placeholder="Share your experience or suggestion..." minLength={10} maxLength={2000} required />
        </label>

        {error ? <p className="error-message">{error}</p> : null}
        {message ? <p className="success-message">{message}</p> : null}

        <button className="primary-button full-width" type="submit" disabled={isSubmitting}>
          {isSubmitting ? 'Sending feedback...' : 'Send feedback'}
        </button>
        <button className="ghost-button full-width" type="button" onClick={() => { setError(null); setMessage(null); setPage('home'); }}>
          Back to home
        </button>
      </form>
    </section>
  );

  const renderHistory = () => (
    <section className="history-page">
      <div className="history-page-hero panel">
        <div className="home-copy">
          <span className="brand-mark inline-brand">{APP_NAME}</span>
          <p className="eyebrow">History</p>
          <h1>Image description history</h1>
          <p className="lead">Review every saved analysis, read aloud, download text, or delete items you no longer want.</p>

          <div className="hero-actions">
            <button className="primary-button" type="button" onClick={() => setPage('home')}>
              Back to Workspace
            </button>
            <button className="ghost-button" type="button" onClick={() => void loadHistory()}>
              Refresh history
            </button>
          </div>
        </div>

        <div className="home-panel history-summary panel-surface">
          <p className="eyebrow">Library</p>
          <strong>Saved records</strong>
          <p className="history-summary-count">
            {history.length} image description{history.length === 1 ? '' : 's'} stored
          </p>
          <small>Use the actions below to download or inspect records.</small>
        </div>
      </div>

      <div className="history-section panel-surface">
        {history.length > 0 ? (
          <div className="history-list history-page-list">
            {history.map((item) => (
              <article className="history-item panel" key={item.id}>
                <div className="history-item-top">
                  <div className="history-title-row">
                    <strong>{item.filename}</strong>
                    <span className="category-pill">{item.scene_category ?? 'General Scene'}</span>
                  </div>
                  <p className="history-caption-snippet">"{item.caption}"</p>
                  <div className="history-meta-tags">
                    <span className="history-meta-pill">📐 {item.width} × {item.height}{item.megapixels ? ` (${item.megapixels})` : ''}</span>
                    {item.timestamp ? <span className="history-meta-pill">⏱️ {item.timestamp}</span> : null}
                    <span className="history-meta-pill">🏷️ {item.objects?.length ?? 0} objects</span>
                    {item.ocr_text ? <span className="history-meta-pill">🔤 Text detected</span> : null}
                  </div>
                </div>
                <div className="history-item-actions">
                  <button
                    className="ghost-button"
                    type="button"
                    onClick={() => handleToggleSpeech(item.caption)}
                  >
                    🔊 Listen
                  </button>
                  <button
                    className="ghost-button"
                    type="button"
                    onClick={() => handleDownloadTxt(item, 'detailed')}
                  >
                    ⬇ .TXT
                  </button>
                  <button
                    className="ghost-button"
                    type="button"
                    onClick={() => handleDownloadJson(item)}
                  >
                    {'{ }'} JSON
                  </button>
                  <button
                    className="ghost-button delete-history-button"
                    type="button"
                    onClick={() => handleDeleteHistoryItem(item.id)}
                  >
                    Delete
                  </button>
                </div>
              </article>
            ))}
          </div>
        ) : (
          <p className="history-empty">No image descriptions yet. Generate one to see it here.</p>
        )}
      </div>
    </section>
  );

  const renderAdmin = () => {
    return (
      <section className="admin-layout">
        <aside className="admin-sidebar panel">
          <div className="admin-user">
            <span className="admin-avatar">A</span>
            <div><strong>{currentUser?.full_name ?? 'Administrator'}</strong></div>
          </div>
          <nav className="admin-nav" aria-label="Admin navigation">
            <button className={adminSection === 'overview' ? 'active' : ''} type="button" onClick={() => setAdminSection('overview')}>Overview</button>
            <button className={adminSection === 'users' ? 'active' : ''} type="button" onClick={() => setAdminSection('users')}>
              Registered users <span className="admin-nav-count">{users.length}</span>
            </button>
            <button className={adminSection === 'feedback' ? 'active' : ''} type="button" onClick={() => setAdminSection('feedback')}>
              User feedback <span className="admin-nav-count">{feedback.length}</span>
            </button>
          </nav>
          <button className="ghost-button admin-signout" type="button" onClick={() => { setIsAdminAuthenticated(false); setAdminToken(null); setCurrentUser(null); setPage('adminLogin'); }}>Sign out</button>
        </aside>

        <div className="admin-content">
          <header className="admin-header">
            <div><p className="eyebrow">Administration</p><h1>Control center</h1></div>
            <button className="primary-button" type="button" onClick={() => void loadAdminData()}>Refresh data</button>
          </header>

          {error ? <p className="error-message">{error}</p> : null}
          {message ? <p className="success-message">{message}</p> : null}

          {adminSection === 'users' ? (
            <section className="admin-page-section admin-records panel-surface" aria-labelledby="registered-users-title">
                <div className="admin-section-title">
                  <div><p className="eyebrow">Accounts</p><h2 id="registered-users-title">Registered users</h2></div>
                </div>
                {users.length ? (
                  <div className="admin-table-wrap">
                    <table>
                      <thead><tr><th>Name</th><th>Email</th><th>Joined</th></tr></thead>
                      <tbody>{users.map((user) => <tr key={user.id}><td><strong>{user.full_name}</strong></td><td>{user.email}</td><td>{formatDate(user.created_at)}</td></tr>)}</tbody>
                    </table>
                  </div>
                ) : <div className="admin-empty"><p>No registered users yet.</p></div>}
            </section>
          ) : null}

          {adminSection === 'feedback' ? (
            <section className="admin-page-section admin-records admin-feedback-modal panel-surface" aria-labelledby="user-feedback-title">
                <div className="admin-section-title">
                  <div><p className="eyebrow">Messages</p><h2 id="user-feedback-title">User feedback</h2></div>
                </div>
                {feedback.length ? (
                  <div className="admin-table-wrap">
                    <table>
                      <thead><tr><th>User</th><th>Feedback</th><th>Status</th><th>Submitted</th><th aria-label="Actions" /></tr></thead>
                      <tbody>{feedback.map((item) => (
                        <tr key={item.id}>
                          <td><strong>{item.user_name}</strong><br />{item.user_email}</td>
                          <td className="feedback-message"><strong>{item.subject}</strong><br />{item.message}</td>
                          <td><select className="feedback-status" value={item.status} onChange={(event) => void handleFeedbackStatusChange(item.id, event.target.value as FeedbackItem['status'])}><option value="new">New</option><option value="reviewed">Reviewed</option><option value="resolved">Resolved</option></select></td>
                          <td>{formatDate(item.created_at)}</td>
                          <td><button className="admin-delete" type="button" onClick={() => void handleDeleteFeedback(item.id)}>Delete</button></td>
                        </tr>
                      ))}</tbody>
                    </table>
                  </div>
                ) : <div className="admin-empty"><p>No feedback submitted yet.</p></div>}
            </section>
          ) : null}

          {adminSection === 'overview' ? <>          <section className="admin-records panel-surface">
          <div className="admin-section-title"><div><h2>User activity</h2></div></div>
          <div className="admin-empty"><p>No activity recorded yet.</p></div>
          </section>

          <section className="admin-records panel-surface">
            <div className="admin-section-title"><div><h2>Uploaded images</h2></div></div>
            {history.length ? <div className="admin-table-wrap"><table><thead><tr><th>Image</th><th>File name</th><th>Category</th><th>Size</th><th>Uploaded</th><th aria-label="Actions" /></tr></thead><tbody>{history.map((image) => <tr key={image.id}><td><img className="admin-image-thumb" src={`${API_BASE_URL}${image.stored_path}`} alt="" /></td><td><strong>{image.filename}</strong><br />{image.content_type || 'Image'}</td><td>{image.scene_category ?? 'General'}</td><td>{image.width} × {image.height}</td><td>{formatDate(image.created_at)}</td><td><div className="admin-image-actions"><button className="admin-view" type="button" aria-label={`View description for ${image.filename}`} onClick={() => setSelectedAdminImage(image)}><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M2.5 12s3.5-6 9.5-6 9.5 6 9.5 6-3.5 6-9.5 6-9.5-6Z" /><circle cx="12" cy="12" r="2.5" /></svg></button><button className="admin-delete" type="button" onClick={() => void handleDeleteAdminImage(image.id)}>Delete</button></div></td></tr>)}</tbody></table></div> : <div className="admin-empty"><p>No uploaded images yet.</p></div>}
            {selectedAdminImage ? (
              <div className="admin-description-preview">
                <div className="admin-description-preview-header">
                  <div>
                    <p className="eyebrow">Image description</p>
                    <h3>{selectedAdminImage.filename}</h3>
                  </div>
                  <button className="ghost-button" type="button" onClick={() => setSelectedAdminImage(null)}>Close</button>
                </div>
                <p>{selectedAdminImage.caption}</p>
                <div className="admin-description-meta-row">
                  <button className="ghost-button" type="button" onClick={() => handleToggleSpeech(selectedAdminImage.caption)}>🔊 Listen</button>
                  <button className="ghost-button" type="button" onClick={() => handleDownloadTxt(selectedAdminImage, 'detailed')}>⬇ .TXT</button>
                </div>
              </div>
            ) : null}
          </section>
          </> : null}

        </div>
      </section>
    );
  };

  const handleDeleteAdminImage = async (imageId: string) => {
    if (!adminToken) return;
    try {
      const response = await fetch(`${API_BASE_URL}/api/admin/images/${imageId}`, {
        method: 'DELETE',
        headers: { 'X-Session-Token': adminToken },
      });

      if (!response.ok) {
        const payload = (await response.json().catch(() => null)) as { detail?: string } | null;
        throw new Error(payload?.detail ?? 'Failed to delete image.');
      }

      setHistory((currentHistory) => currentHistory.filter((item) => item.id !== imageId));
      setMessage('Image deleted successfully.');
    } catch (deleteError) {
      setError(deleteError instanceof Error ? deleteError.message : 'Failed to delete image.');
    }
  };

  const handleFeedbackStatusChange = async (feedbackId: string, status: FeedbackItem['status']) => {
    if (!adminToken) return;
    try {
      const response = await fetch(`${API_BASE_URL}/api/admin/feedback/${feedbackId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json', 'X-Session-Token': adminToken },
        body: JSON.stringify({ status }),
      });
      const data = (await response.json().catch(() => null)) as (FeedbackItem & { detail?: string }) | null;
      if (!response.ok || !data) throw new Error(data?.detail ?? 'Unable to update feedback.');
      setFeedback((items) => items.map((item) => item.id === feedbackId ? data : item));
      setMessage('Feedback status updated.');
    } catch (feedbackError) {
      setError(feedbackError instanceof Error ? feedbackError.message : 'Unable to update feedback.');
    }
  };

  const handleDeleteFeedback = async (feedbackId: string) => {
    if (!adminToken) return;
    try {
      const response = await fetch(`${API_BASE_URL}/api/admin/feedback/${feedbackId}`, {
        method: 'DELETE', headers: { 'X-Session-Token': adminToken },
      });
      const data = (await response.json().catch(() => null)) as { detail?: string } | null;
      if (!response.ok) throw new Error(data?.detail ?? 'Unable to delete feedback.');
      setFeedback((items) => items.filter((item) => item.id !== feedbackId));
      setMessage('Feedback deleted.');
    } catch (feedbackError) {
      setError(feedbackError instanceof Error ? feedbackError.message : 'Unable to delete feedback.');
    }
  };

  const renderLogin = () => (
    <section className="auth-layout login-layout">
      <aside className="auth-art login-art panel" aria-label="Image description generator illustration">
        <img src="/login.png" alt="Illustration of an image description generator powered by deep learning" />
      </aside>
      <form className="auth-card panel" onSubmit={handleSubmit}>
        <div className="auth-header">
          <div className="auth-brand-logo-wrap">
            <VisionCraftLogo size={40} showText={true} />
          </div>
          <h2>Login</h2>
        </div>

        <label className="auth-field">
          <span>Email</span>
          <input name="email" type="email" autoComplete="email" placeholder="you@example.com" required />
        </label>

        <label className="auth-field">
          <span>Password</span>
          <input name="password" type="password" autoComplete="current-password" placeholder="Enter your password" required />
        </label>

        <div className="auth-row">
          <label className="checkbox-field">
            <input type="checkbox" defaultChecked />
            <span>Remember me</span>
          </label>
          <button className="text-button" type="button" onClick={() => setPage('forgot')}>
            Forgot password?
          </button>
        </div>

        {error ? <p className="error-message">{error}</p> : null}
        {message ? <p className="success-message">{message}</p> : null}

        <button className="primary-button full-width" type="submit" disabled={isSubmitting}>
          {isSubmitting ? 'Logging in...' : 'Login'}
        </button>

        <button className="ghost-button full-width" type="button" onClick={() => setPage('signin')}>
          New here? Create an account
        </button>
        <button className="text-button admin-login-link" type="button" onClick={() => { setError(null); setMessage(null); setPage('adminLogin'); }}>
          Administrator login
        </button>
      </form>
    </section>
  );

  const renderSignIn = () => (
    <section className="auth-layout single">
      <form className="auth-card panel" onSubmit={handleSubmit}>
        <div className="auth-header">
          <h2>Create your access</h2>
        </div>

        <label className="auth-field">
          <span>Full name</span>
          <input name="fullName" type="text" placeholder="Your name" />
        </label>

        <label className="auth-field">
          <span>Email</span>
          <input name="email" type="email" placeholder="you@example.com" />
        </label>

        <label className="auth-field">
          <span>Password</span>
          <input name="password" type="password" placeholder="Create a password" />
        </label>

        {error ? <p className="error-message">{error}</p> : null}
        {message ? <p className="success-message">{message}</p> : null}

        <button className="primary-button full-width" type="submit" disabled={isSubmitting}>
          {isSubmitting ? 'Creating...' : 'Sign In'}
        </button>

        <button className="ghost-button full-width" type="button" onClick={() => setPage('login')}>
          Already have an account? Login
        </button>
      </form>
    </section>
  );

  const renderForgot = () => (
    <section className="auth-layout single">
      <form className="auth-card panel" onSubmit={handleSubmit}>
        <div className="auth-header">
          <h2>Forgot password</h2>
        </div>

        <label className="auth-field">
          <span>Email</span>
          <input name="email" type="email" placeholder="you@example.com" />
        </label>

        {error ? <p className="error-message">{error}</p> : null}
        {message ? <p className="success-message">{message}</p> : null}

        <button className="primary-button full-width" type="submit" disabled={isSubmitting}>
          {isSubmitting ? 'Sending...' : 'Send reset link'}
        </button>

        <button className="ghost-button full-width" type="button" onClick={() => setPage('login')}>
          Back to login
        </button>
      </form>
    </section>
  );

  const renderAdminLogin = () => (
    <section className="auth-layout single admin-login-layout">
      <form className="auth-card panel" onSubmit={handleSubmit}>
        <div className="auth-header">
          <span className="brand-mark inline-brand">{APP_NAME}</span>
          <p className="eyebrow admin-login-eyebrow">Administrator access</p>
          <h2>Admin panel login</h2>
          <p>Use your administrator credentials to manage saved caption records.</p>
        </div>

        <label className="auth-field">
          <span>Admin ID</span>
          <input name="email" type="text" autoComplete="username" placeholder="Enter admin ID" />
        </label>

        <label className="auth-field">
          <span>Password</span>
          <input name="password" type="password" autoComplete="current-password" placeholder="Enter password" />
        </label>

        {error ? <p className="error-message">{error}</p> : null}
        {message ? <p className="success-message">{message}</p> : null}

        <button className="primary-button full-width" type="submit" disabled={isSubmitting}>
          {isSubmitting ? 'Checking access...' : 'Sign in as administrator'}
        </button>
        <button className="ghost-button full-width" type="button" onClick={() => { setError(null); setMessage(null); setPage('login'); }}>
          Back to user login
        </button>
      </form>
    </section>
  );

  const renderFloatingChatbot = () => {
    // Do not render the Ask AI chatbot on login / authentication pages
    if (['login', 'signin', 'forgot', 'adminLogin'].includes(page) || (page === 'admin' && !isAdminAuthenticated)) {
      return null;
    }

    return (
      <div className="floating-chatbot-container">
      {/* Chat Window Dialog */}
      {isChatOpen ? (
        <div className="chatbot-window glass-panel" role="dialog" aria-label="AI Chatbot Assistant">
          {/* Header */}
          <div className="chatbot-header">
            <div className="chatbot-title-group">
              <VisionCraftLogo size={32} />
              <div>
                <div className="chatbot-heading-row">
                  <h4>VisionCraft AI</h4>
                  <span className="chatbot-status-dot" title="AI Service Online"></span>
                </div>
                <div className="chatbot-context-pill">
                  {caption ? (
                    <span className="context-badge active">
                      📷 Image: {caption.filename.length > 18 ? caption.filename.substring(0, 18) + '...' : caption.filename}
                    </span>
                  ) : (
                    <span className="context-badge idle">💡 App Guide & Vision Assistant</span>
                  )}
                </div>
              </div>
            </div>

            <div className="chatbot-header-actions">
              <button
                type="button"
                className="chatbot-icon-btn"
                onClick={handleClearChat}
                title="Clear conversation"
              >
                🗑️
              </button>
              <button
                type="button"
                className="chatbot-icon-btn close-btn"
                onClick={() => setIsChatOpen(false)}
                title="Close chat"
              >
                ✕
              </button>
            </div>
          </div>

          {/* Messages Stream */}
          <div className="chatbot-messages-body" ref={chatScrollRef}>
            {chatMessages.map((msg) => (
              <div key={msg.id} className={`chatbot-msg-row ${msg.sender}`}>
                <div className={`chatbot-msg-bubble ${msg.sender}`}>
                  <p className="msg-text">{msg.text}</p>
                  <div className="msg-meta-row">
                    <span className="msg-time">{msg.time}</span>
                    {msg.sender === 'assistant' ? (
                      <div className="msg-actions">
                        <button
                          type="button"
                          className="mini-action-link"
                          onClick={() => handleToggleSpeech(msg.text.replace(/[*•#]/g, ''))}
                          title="Read aloud"
                        >
                          🔊 Listen
                        </button>
                        <button
                          type="button"
                          className="mini-action-link"
                          onClick={() => handleCopy(msg.text, 'Answer')}
                          title="Copy text"
                        >
                          📋 Copy
                        </button>
                      </div>
                    ) : null}
                  </div>
                </div>
              </div>
            ))}

            {isChatLoading ? (
              <div className="chatbot-msg-row assistant">
                <div className="chatbot-msg-bubble assistant loading">
                  <div className="typing-indicator">
                    <span></span>
                    <span></span>
                    <span></span>
                  </div>
                  <span className="typing-label">VisionCraft AI is thinking...</span>
                </div>
              </div>
            ) : null}
          </div>

          {/* Input Bar Form */}
          <form className="chatbot-input-bar" onSubmit={(e) => void handleSendChatMessage(e)}>
            <input
              type="text"
              className="chatbot-input-field"
              placeholder={
                caption
                  ? "Ask anything about this image..."
                  : "Ask about VisionCraft or visual analysis..."
              }
              value={chatInput}
              onChange={(e) => setChatInput(e.target.value)}
              disabled={isChatLoading}
            />
            <button
              type="submit"
              className="chatbot-send-btn"
              disabled={isChatLoading || !chatInput.trim()}
              title="Send message"
            >
              ➤
            </button>
          </form>
        </div>
      ) : null}

      {/* Floating Action Button (Toggle) */}
      <button
        type="button"
        className={`floating-chatbot-toggle-btn ${isChatOpen ? 'active' : ''}`}
        onClick={() => setIsChatOpen((prev) => !prev)}
        aria-label="Toggle AI Chatbot Assistant"
        title="Chat with VisionCraft AI"
      >
        <span className="toggle-icon">{isChatOpen ? '✕' : '💬'}</span>
        {!isChatOpen ? (
          <>
            <span className="toggle-text">Ask AI</span>
            {caption ? <span className="toggle-pulse-badge"></span> : null}
          </>
        ) : null}
      </button>
    </div>
    );
  };

  return (
    <main className={`app-shell page-${page}`}>
      {page === 'home' ? renderHome() : null}
      {page === 'history' ? renderHistory() : null}
      {page === 'admin' ? (isAdminAuthenticated ? renderAdmin() : renderAdminLogin()) : null}
      {page === 'about' ? renderAbout() : null}
      {page === 'contact' ? renderContact() : null}
      {page === 'feedback' ? renderFeedback() : null}
      {page === 'login' ? renderLogin() : null}
      {page === 'signin' ? renderSignIn() : null}
      {page === 'forgot' ? renderForgot() : null}
      {page === 'adminLogin' ? renderAdminLogin() : null}

      {/* Global Floating AI Chatbot Assistant */}
      {renderFloatingChatbot()}
    </main>
  );
}

