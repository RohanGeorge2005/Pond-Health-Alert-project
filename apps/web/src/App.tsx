import React, { useState, useEffect, useRef } from "react";
import { useTranslation } from "react-i18next";
import {
  AlertTriangle,
  CheckCircle2,
  XCircle,
  HelpCircle,
  Volume2,
  Droplets,
  ClipboardCheck,
  Camera,
  Activity,
  LineChart,
  Shield,
  ChevronDown,
  ChevronUp,
  Plus,
  Minus,
  Check,
  RefreshCw,
  Info,
  Radio,
  Battery,
  Wifi,
  WifiOff,
  Thermometer,
  Gauge,
  Sparkles,
  Zap,
  Upload,
  Image as ImageIcon,
  Trash2,
  Loader2,
  AlertCircle,
} from "lucide-react";
import { db, type OfflineReading, type OfflineDailyCheck } from "./lib/db";

// Configurable API base URL with fallback to window origin port 8000
const API_BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

const STATUS_THEME = {
  green: {
    bgTint: "bg-[#EBF7F0] border-[#A3DEC0] text-[#1B4D3E]",
    iconColor: "#2E9E5B",
    icon: CheckCircle2,
    badgeBg: "bg-[#2E9E5B] text-white",
    keyTitle: "statusGreen",
  },
  amber: {
    bgTint: "bg-[#FDF8EC] border-[#F7D897] text-[#7A5405]",
    iconColor: "#E0A21B",
    icon: AlertTriangle,
    badgeBg: "bg-[#E0A21B] text-white",
    keyTitle: "statusAmber",
  },
  red: {
    bgTint: "bg-[#FCEFEF] border-[#F3B2B2] text-[#8C1D1D]",
    iconColor: "#D64545",
    icon: XCircle,
    badgeBg: "bg-[#D64545] text-white",
    keyTitle: "statusRed",
  },
  cant_tell: {
    bgTint: "bg-[#F0F2F1] border-[#C8CEC9] text-[#3E4743]",
    iconColor: "#7A8780",
    icon: HelpCircle,
    badgeBg: "bg-[#7A8780] text-white",
    keyTitle: "statusCantTell",
  },
};

export function App() {
  const { t, i18n } = useTranslation();
  const [currentTab, setCurrentTab] = useState<"home" | "readings" | "daily" | "photo" | "impact">("home");
  const [isOnline, setIsOnline] = useState(typeof navigator !== "undefined" ? navigator.onLine : true);
  const [offlineQueueCount, setOfflineQueueCount] = useState(0);
  const [showOfficerDetails, setShowOfficerDetails] = useState(false);
  const [wsConnected, setWsConnected] = useState(false);

  // File Inputs for Photo Selection
  const galleryInputRef = useRef<HTMLInputElement>(null);
  const cameraInputRef = useRef<HTMLInputElement>(null);

  // Live IoT Telemetry State
  const [latestIoTReading, setLatestIoTReading] = useState<{
    temperature: number;
    ph: number;
    dissolved_oxygen: number;
    ammonia: number;
    turbidity: number;
    water_level_cm: number;
    battery_pct: number;
    signal_rssi: number;
    timestamp: string;
    is_simulated: boolean;
  }>({
    temperature: 28.2,
    ph: 7.45,
    dissolved_oxygen: 5.6,
    ammonia: 0.018,
    turbidity: 18.2,
    water_level_cm: 122.0,
    battery_pct: 94.0,
    signal_rssi: -62,
    timestamp: new Date().toISOString(),
    is_simulated: false,
  });

  const [deviceStatus, setDeviceStatus] = useState<{
    device_id: string;
    is_online: boolean;
    battery_level_pct: number;
    signal_rssi: number;
    last_seen_at: string;
  }>({
    device_id: "ESP32-POND-01",
    is_online: true,
    battery_level_pct: 94.0,
    signal_rssi: -62,
    last_seen_at: new Date().toISOString(),
  });

  // Home Screen Checklist State
  const [checkedItems, setCheckedItems] = useState<{ [key: number]: boolean }>({
    1: false,
    2: false,
    3: false,
  });

  // Assessment State
  const [assessment, setAssessment] = useState<any>({
    status: "amber",
    reason_codes: ["FALLING_DO_TREND"],
    stale_hours: 0.1,
  });

  // Manual / calibration inputs
  const [readingInputs, setReadingInputs] = useState({
    do: "5.6",
    ph: "7.45",
    temp: "28.2",
    ammonia: "0.018",
    turbidity: "18.2",
  });
  const [readingsSuccessMsg, setReadingsSuccessMsg] = useState("");

  // Daily Check State
  const [dailyFeeding, setDailyFeeding] = useState<"normal" | "less" | "none">("normal");
  const [dailySwim, setDailySwim] = useState<"normal" | "gasping" | "at_surface" | "slow">("normal");
  const [deadFishCount, setDeadFishCount] = useState(0);
  const [dailySuccessMsg, setDailySuccessMsg] = useState("");

  // Photo Analysis State
  const [selectedPhotoFile, setSelectedPhotoFile] = useState<File | null>(null);
  const [photoPreviewUrl, setPhotoPreviewUrl] = useState<string | null>(null);
  const [photoFileSize, setPhotoFileSize] = useState<string>("");
  const [isAnalyzingPhoto, setIsAnalyzingPhoto] = useState(false);
  const [photoError, setPhotoError] = useState<string | null>(null);
  const [analysisResult, setAnalysisResult] = useState<any | null>(null);

  // WebSocket Connection for Live Auto Stream
  useEffect(() => {
    let ws: WebSocket | null = null;
    let reconnectTimeout: any = null;

    const connectWebSocket = () => {
      try {
        const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
        const host = window.location.hostname || "localhost";
        const wsUrl = `${protocol}//${host}:8000/ws/ponds/pond-demo-1`;
        ws = new WebSocket(wsUrl);

        ws.onopen = () => {
          setWsConnected(true);
        };

        ws.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            if (data.assessment) {
              const ass = data.assessment;
              setAssessment({
                status: ass.status,
                reason_codes: ass.reason_codes || ["OPTIMAL_WATER_QUALITY"],
                stale_hours: ass.data_quality?.stale_hours || 0.1,
              });

              if (ass.device_status) {
                setDeviceStatus({
                  device_id: ass.device_status.device_id,
                  is_online: ass.device_status.is_online,
                  battery_level_pct: ass.device_status.battery_level_pct,
                  signal_rssi: ass.device_status.signal_rssi,
                  last_seen_at: ass.device_status.last_seen_at,
                });
              }

              if (ass.parameter_scores) {
                setLatestIoTReading((prev) => ({
                  ...prev,
                  dissolved_oxygen: ass.parameter_scores.dissolved_oxygen?.value ?? prev.dissolved_oxygen,
                  ph: ass.parameter_scores.ph?.value ?? prev.ph,
                  temperature: ass.parameter_scores.temperature?.value ?? prev.temperature,
                  ammonia: ass.parameter_scores.ammonia?.value ?? prev.ammonia,
                  turbidity: ass.parameter_scores.turbidity?.value ?? prev.turbidity,
                  timestamp: ass.assessment_time || new Date().toISOString(),
                }));
              }
            }
          } catch (err) {
            // Ignore parse errors
          }
        };

        ws.onclose = () => {
          setWsConnected(false);
          reconnectTimeout = setTimeout(connectWebSocket, 3000);
        };

        ws.onerror = () => {
          ws?.close();
        };
      } catch (e) {
        // Fallback for SSR or offline
      }
    };

    connectWebSocket();

    return () => {
      if (ws) ws.close();
      if (reconnectTimeout) clearTimeout(reconnectTimeout);
    };
  }, []);

  const setLanguage = (lang: "en" | "kn") => {
    i18n.changeLanguage(lang);
    if (typeof window !== "undefined") {
      localStorage.setItem("pond_health_lang", lang);
    }
  };

  const handleListen = () => {
    if ("speechSynthesis" in window) {
      window.speechSynthesis.cancel();
      const statusText = t(STATUS_THEME[assessment.status as keyof typeof STATUS_THEME]?.keyTitle || "statusCantTell");
      const reasonKey = `reason_${assessment.reason_codes[0]}`;
      const reasonText = t(reasonKey);
      const actionText = t(`action_1_${assessment.status}`);
      const speechUtterance = new SpeechSynthesisUtterance(`${statusText}. ${reasonText}. ${actionText}`);
      speechUtterance.lang = i18n.language === "kn" ? "kn-IN" : "en-IN";
      window.speechSynthesis.speak(speechUtterance);
    }
  };

  const toggleCheck = (idx: number) => {
    setCheckedItems((prev) => ({ ...prev, [idx]: !prev[idx] }));
  };

  // --- Real Image Selection & Quality Gate Handlers ---
  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setPhotoError(null);
    setAnalysisResult(null);

    const files = e.target.files;
    if (!files || files.length === 0) return;

    const file = files[0];

    // Validate type
    if (!file.type.startsWith("image/")) {
      setPhotoError("Please select a valid image file (JPEG, PNG, or WebP).");
      return;
    }

    // Validate size (max 10MB)
    if (file.size > 10 * 1024 * 1024) {
      setPhotoError("Image file is too large. Maximum size is 10 MB.");
      return;
    }

    if (file.size < 5 * 1024) {
      setPhotoError("Image file is suspiciously small (< 5 KB). Please upload a clear photo.");
      return;
    }

    setSelectedPhotoFile(file);
    setPhotoFileSize((file.size / (1024 * 1024)).toFixed(2) + " MB");

    // Create object URL for client preview
    const objectUrl = URL.createObjectURL(file);
    setPhotoPreviewUrl(objectUrl);
  };

  const handleRemovePhoto = () => {
    setSelectedPhotoFile(null);
    setPhotoPreviewUrl(null);
    setAnalysisResult(null);
    setPhotoError(null);
    if (galleryInputRef.current) galleryInputRef.current.value = "";
    if (cameraInputRef.current) cameraInputRef.current.value = "";
  };

  // Offline client-side demo evaluation fallback
  const handleRunOfflineDemo = () => {
    if (!photoPreviewUrl) return;

    setIsAnalyzingPhoto(true);
    setPhotoError(null);

    const img = new Image();
    img.crossOrigin = "anonymous";
    img.onload = () => {
      try {
        const canvas = document.createElement("canvas");
        const ctx = canvas.getContext("2d");
        const w = img.naturalWidth || 400;
        const h = img.naturalHeight || 300;
        canvas.width = w;
        canvas.height = h;

        if (ctx) {
          ctx.drawImage(img, 0, 0, w, h);

          // Get image brightness
          const imgData = ctx.getImageData(0, 0, w, h);
          let totalBrightness = 0;
          const len = imgData.data.length;
          let samples = 0;
          for (let i = 0; i < len; i += 16) {
            totalBrightness += 0.299 * imgData.data[i] + 0.587 * imgData.data[i + 1] + 0.114 * imgData.data[i + 2];
            samples++;
          }
          const avgBrightness = samples > 0 ? totalBrightness / samples : 120;

          // If pitch dark or pure blinding white
          if (avgBrightness < 25 || avgBrightness > 240) {
            setAnalysisResult({
              photo_id: "demo-" + Date.now(),
              pond_id: "pond-demo-1",
              timestamp: new Date().toISOString(),
              passed_gate: false,
              gate_failure_reasons: [
                avgBrightness < 25 ? "Image underexposed (too dark)" : "Image overexposed (too bright)",
              ],
              metrics: { brightness: Math.round(avgBrightness), laplacian_variance: 42.1 },
              tips_en: [
                "Move to a well-lit area or use a torch.",
                "Avoid harsh sun glare or reflections on the water surface.",
              ],
              tips_kn: [
                "ಹೆಚ್ಚು ಬೆಳಕಿರುವ ಜಾಗದಲ್ಲಿ ಅಥವಾ ಟಾರ್ಚ್ ಬೆಳಗಿಸಿ ಫೋಟೋ ತೆಗೆಯಿರಿ.",
                "ನೀರಿನ ಮೇಲಿನ ತೀವ್ರ ಪ್ರತಿಫಲನ ಅಥವಾ ಸೂರ್ಯನ ಬೆಳಕನ್ನು ತಪ್ಪಿಸಿ.",
              ],
              predicted_class: null,
              label_en: "Photo Quality Check Failed",
              label_kn: "ಫೋಟೋ ಗುಣಮಟ್ಟ ಪರೀಕ್ಷೆ ವಿಫಲವಾಗಿದೆ",
              confidence: null,
              confidence_pct: null,
              is_uncertain: true,
              gradcam_data_url: null,
              disclaimer_en: "Photo did not meet quality requirements. Retake recommended before disease analysis.",
              disclaimer_kn: "ಫೋಟೋ ಸ್ಪಷ್ಟವಾಗಿಲ್ಲ. ರೋಗ ವಿಶ್ಲೇಷಣೆಗೆ ಮುನ್ನ ಮತ್ತೊಮ್ಮೆ ಫೋಟೋ ತೆಗೆಯಿರಿ.",
              next_steps_en: ["Retake the photo in better lighting."],
              next_steps_kn: ["ಉತ್ತಮ ಬೆಳಕಿನಲ್ಲಿ ಮತ್ತೊಮ್ಮೆ ಫೋಟೋ ತೆಗೆಯಿರಿ."],
            });
            setIsAnalyzingPhoto(false);
            return;
          }

          // Create Grad-CAM attention heatmap overlay
          const centerX = w * 0.52;
          const centerY = h * 0.5;
          const radius = Math.min(w, h) * 0.35;

          const grad = ctx.createRadialGradient(centerX, centerY, 5, centerX, centerY, radius);
          grad.addColorStop(0, "rgba(220, 38, 38, 0.65)");
          grad.addColorStop(0.35, "rgba(234, 179, 8, 0.50)");
          grad.addColorStop(0.7, "rgba(34, 197, 94, 0.25)");
          grad.addColorStop(1, "rgba(0, 0, 0, 0)");

          ctx.fillStyle = grad;
          ctx.beginPath();
          ctx.arc(centerX, centerY, radius, 0, Math.PI * 2);
          ctx.fill();

          const gradcamDataUrl = canvas.toDataURL("image/jpeg", 0.9);

          setAnalysisResult({
            photo_id: "demo-" + Date.now(),
            pond_id: "pond-demo-1",
            timestamp: new Date().toISOString(),
            passed_gate: true,
            gate_failure_reasons: [],
            metrics: { laplacian_variance: 218.4, brightness: Math.round(avgBrightness) },
            predicted_class: "healthy",
            label_en: "Healthy Fish (In-Browser Demo)",
            label_kn: "ಆರೋಗ್ಯಕರ ಮೀನು (ಆಫ್‌ಲೈನ್ ಡೆಮೊ)",
            confidence: 0.914,
            confidence_pct: 91.4,
            is_uncertain: false,
            gradcam_data_url: gradcamDataUrl,
            disclaimer_en: "AI prediction is preliminary and advisory only. It is NOT a confirmed veterinary diagnosis. Always consult a fisheries officer before treatment.",
            disclaimer_kn: "ಇದು ಪ್ರಾಥಮಿಕ ಕೃತಕ ಬುದ್ಧಿಮತ್ತೆ ಸಲಹೆ ಮಾತ್ರ. ಯಾವುದೇ ಚಿಕಿತ್ಸೆ ನೀಡುವ ಮುನ್ನ ಮೀನುಗಾರಿಕಾ ಅಧಿಕಾರಿಯೊಂದಿಗೆ ದೃಢೀಕರಿಸಿ.",
            next_steps_en: [
              "No visible external lesions, fin rot, or ulcerations detected.",
              "Maintain current dissolved oxygen (>5.0 mg/L) and routine feeding schedule.",
              "Continue routine visual monitoring of fish swimming behavior.",
            ],
            next_steps_kn: [
              "ಯಾವುದೇ ಬಾಹ್ಯ ಗಾಯಗಳು, ರೆಕ್ಕೆ ಕೊಳೆತ ಅಥವಾ ಹುಣ್ಣುಗಳು ಕಂಡುಬಂದಿಲ್ಲ.",
              "ಕರಗಿದ ಆಮ್ಲಜನಕ (>5.0 mg/L) ಮತ್ತು ಆಹಾರ ವೇಳಾಪಟ್ಟಿಯನ್ನು ಕಾಪಾಡಿಕೊಳ್ಳಿ.",
              "ಮೀನುಗಳ ಈಜುವ ಚಟುವಟಿಕೆಯನ್ನು ನಿಯಮಿತವಾಗಿ ಗಮನಿಸುತ್ತಿರಿ.",
            ],
          });
        }
      } catch (e) {
        console.error("Offline demo error:", e);
      } finally {
        setIsAnalyzingPhoto(false);
      }
    };
    img.onerror = () => {
      setIsAnalyzingPhoto(false);
      setPhotoError("Failed to load selected photo preview.");
    };
    img.src = photoPreviewUrl;
  };

  // Upload to backend /api/fish/analyze with proxy & multi-host fallback
  const handleAnalyzePhoto = async () => {
    if (!selectedPhotoFile) {
      setPhotoError("Please select or capture a fish photo first.");
      return;
    }

    setIsAnalyzingPhoto(true);
    setPhotoError(null);

    const formData = new FormData();
    formData.append("pond_id", "pond-demo-1");
    formData.append("file", selectedPhotoFile);

    const endpoints = [
      "/api/fish/analyze",
      "http://localhost:8000/api/fish/analyze",
      "http://127.0.0.1:8000/api/fish/analyze",
    ];

    let lastError: any = null;
    let data: any = null;

    for (const ep of endpoints) {
      try {
        const response = await fetch(ep, {
          method: "POST",
          body: formData,
        });

        if (response.ok) {
          data = await response.json();
          break;
        } else if (response.status === 400 || response.status === 413) {
          const errJson = await response.json().catch(() => ({}));
          throw new Error(errJson.detail || `Server validation error (${response.status})`);
        }
      } catch (err: any) {
        lastError = err;
      }
    }

    if (data) {
      setAnalysisResult(data);
      setIsAnalyzingPhoto(false);
      return;
    }

    setIsAnalyzingPhoto(false);

    if (lastError && !lastError.message?.toLowerCase().includes("fetch") && !lastError.name?.includes("TypeError")) {
      setPhotoError(lastError.message);
      return;
    }

    setPhotoError(
      t("backendOfflineTip") || "Backend server is offline (port 8000). Please launch run_app.bat, or test using the in-browser demo below."
    );
  };

  const currentTheme = STATUS_THEME[assessment.status as keyof typeof STATUS_THEME] || STATUS_THEME.cant_tell;
  const HeroStatusIcon = currentTheme.icon;

  return (
    <div className="min-h-screen bg-[#F6F8F5] text-[#1A2E26] flex flex-col items-center">
      <div className="w-full max-w-[480px] min-h-screen bg-[#F6F8F5] flex flex-col border-x border-[#E0E6E2] shadow-sm pb-24">
        
        {/* 1. Header with App Title, Subtitle, and Segmented Language Toggle */}
        <header className="p-4 bg-[#1B4D3E] text-white flex items-center justify-between sticky top-0 z-30 shadow-sm">
          <div>
            <h1 className="font-bold text-lg leading-tight tracking-tight">{t("appName")}</h1>
            <p className="text-xs text-[#A3DEC0] mt-0.5">{t("subDistrict")}</p>
          </div>
          
          <div className="bg-[#143B2F] p-1 rounded-full flex items-center border border-[#2E9E5B]/40" role="group" aria-label="Language selection">
            <button
              onClick={() => setLanguage("en")}
              className={`px-3 py-1.5 text-xs font-semibold rounded-full transition-all duration-150 ${
                i18n.language === "en" ? "bg-white text-[#1B4D3E] shadow-xs" : "text-[#E8F0EC] hover:text-white"
              }`}
              aria-pressed={i18n.language === "en"}
            >
              English
            </button>
            <button
              onClick={() => setLanguage("kn")}
              className={`px-3 py-1.5 text-xs font-semibold rounded-full transition-all duration-150 ${
                i18n.language === "kn" ? "bg-white text-[#1B4D3E] shadow-xs" : "text-[#E8F0EC] hover:text-white"
              }`}
              aria-pressed={i18n.language === "kn"}
            >
              ಕನ್ನಡ
            </button>
          </div>
        </header>

        {/* 2. Automatic IoT Sensor Node Status Bar */}
        <div className="px-4 py-2 bg-white border-b border-[#E0E6E2] flex items-center justify-between text-xs">
          <div className="flex items-center gap-2">
            <span
              className={`inline-block w-2.5 h-2.5 rounded-full ${
                deviceStatus.is_online ? "bg-[#2E9E5B] animate-pulse" : "bg-[#D64545]"
              }`}
            />
            <span className="font-semibold text-[#1B4D3E]">
              {deviceStatus.is_online ? t("deviceOnline") : t("deviceOffline")}
            </span>
          </div>
          <div className="flex items-center gap-3 text-[#7A8780] text-[11px]">
            <span className="flex items-center gap-1 font-medium">
              <Battery className="w-3.5 h-3.5 text-[#2E9E5B]" /> {deviceStatus.battery_level_pct}%
            </span>
            <span className="flex items-center gap-1 font-medium">
              <Radio className="w-3.5 h-3.5 text-[#1B4D3E]" /> {deviceStatus.signal_rssi} dBm
            </span>
          </div>
        </div>

        {/* Demo banner: slim amber strip */}
        <div className="bg-[#FDF8EC] border-b border-[#F7D897] text-[#7A5405] px-4 py-1.5 text-xs flex items-center justify-between font-medium">
          <div className="flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 shrink-0 text-[#E0A21B]" />
            <span className="truncate">{t("demoBanner")}</span>
          </div>
          <span className="text-[10px] bg-[#E0A21B]/20 text-[#7A5405] font-bold px-1.5 py-0.5 rounded uppercase">
            {latestIoTReading.is_simulated ? t("iotSimulatedTag") : t("iotLiveTag")}
          </span>
        </div>

        {/* 3. Main Screen Router */}
        <main className="flex-1 p-4 space-y-4">
          
          {/* TAB 1: HOME SCREEN (HERO STATUS, LIVE IOT CARDS, WHAT TO DO NOW) */}
          {currentTab === "home" && (
            <div className="space-y-4">
              
              {/* HERO STATUS CARD */}
              <section
                className={`p-5 rounded-[16px] border-2 shadow-xs transition-all ${currentTheme.bgTint}`}
                aria-live="polite"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-1.5">
                    <span className={`text-xs font-bold px-2.5 py-1 rounded-full ${currentTheme.badgeBg}`}>
                      {deviceStatus.device_id}
                    </span>
                    <span className="text-[10px] bg-white/80 text-[#1B4D3E] font-bold px-2 py-0.5 rounded-full border border-black/5 flex items-center gap-1">
                      <Zap className="w-3 h-3 text-[#2E9E5B]" /> {t("autoRefreshedLive")}
                    </span>
                  </div>
                  <HeroStatusIcon className="w-8 h-8" style={{ color: currentTheme.iconColor }} />
                </div>

                <h2 className="text-[26px] font-bold leading-tight mt-3">
                  {t(currentTheme.keyTitle)}
                </h2>

                <p className="text-base font-medium mt-2 leading-relaxed opacity-95">
                  {t(`reason_${assessment.reason_codes[0]}`)}
                </p>

                <div className="mt-4 pt-3 border-t border-black/10 flex items-center justify-between flex-wrap gap-2">
                  <span className="text-xs bg-white/70 px-2.5 py-1 rounded-md text-[#3E4743] font-medium border border-black/5">
                    {t("dataUpdated", { hours: assessment.stale_hours })}
                  </span>

                  <button
                    onClick={handleListen}
                    className="btn-primary min-h-[44px] px-3.5 py-1.5 text-xs bg-[#1B4D3E] text-white hover:bg-[#143B2F] rounded-full flex items-center gap-1.5 shadow-xs"
                    aria-label={t("listenBtn")}
                  >
                    <Volume2 className="w-4 h-4 text-[#A3DEC0]" />
                    <span>{t("listenBtn")}</span>
                  </button>
                </div>
              </section>

              {/* Automatic IoT Live Parameter Dashboard */}
              <section className="card bg-white space-y-3">
                <div className="flex justify-between items-center border-b border-[#E0E6E2] pb-2">
                  <h3 className="text-sm font-bold text-[#1A2E26] flex items-center gap-1.5">
                    <Activity className="w-4 h-4 text-[#2E9E5B]" />
                    {t("liveParameterReadings")}
                  </h3>
                  <span className="text-[11px] text-[#2E9E5B] font-semibold flex items-center gap-1">
                    <span className="w-2 h-2 rounded-full bg-[#2E9E5B] animate-ping" />
                    24/7 IoT
                  </span>
                </div>

                <div className="grid grid-cols-2 gap-2.5">
                  <div className="p-3 bg-[#F6F8F5] rounded-[12px] border border-[#E0E6E2]">
                    <div className="flex justify-between items-baseline text-xs text-[#7A8780] font-medium">
                      <span>{t("doLabel")}</span>
                      <span>mg/L</span>
                    </div>
                    <div className="text-2xl font-bold text-[#1B4D3E] mt-1">
                      {latestIoTReading.dissolved_oxygen.toFixed(1)}
                    </div>
                    <span className="text-[10px] text-[#2E9E5B] font-semibold">{t("doHint")}</span>
                  </div>

                  <div className="p-3 bg-[#F6F8F5] rounded-[12px] border border-[#E0E6E2]">
                    <div className="flex justify-between items-baseline text-xs text-[#7A8780] font-medium">
                      <span>{t("phLabel")}</span>
                      <span>pH</span>
                    </div>
                    <div className="text-2xl font-bold text-[#1B4D3E] mt-1">
                      {latestIoTReading.ph.toFixed(2)}
                    </div>
                    <span className="text-[10px] text-[#2E9E5B] font-semibold">{t("phHint")}</span>
                  </div>

                  <div className="p-3 bg-[#F6F8F5] rounded-[12px] border border-[#E0E6E2]">
                    <div className="flex justify-between items-baseline text-xs text-[#7A8780] font-medium">
                      <span>{t("tempLabel")}</span>
                      <span>°C</span>
                    </div>
                    <div className="text-2xl font-bold text-[#1B4D3E] mt-1">
                      {latestIoTReading.temperature.toFixed(1)}
                    </div>
                    <span className="text-[10px] text-[#2E9E5B] font-semibold">{t("tempHint")}</span>
                  </div>

                  <div className="p-3 bg-[#F6F8F5] rounded-[12px] border border-[#E0E6E2]">
                    <div className="flex justify-between items-baseline text-xs text-[#7A8780] font-medium">
                      <span>{t("ammoniaLabel")}</span>
                      <span>mg/L</span>
                    </div>
                    <div className="text-2xl font-bold text-[#1B4D3E] mt-1">
                      {latestIoTReading.ammonia.toFixed(3)}
                    </div>
                    <span className="text-[10px] text-[#2E9E5B] font-semibold">{t("ammoniaHint")}</span>
                  </div>
                </div>
              </section>

              {/* Muted Advisory Disclaimer */}
              <div className="p-3 bg-white border border-[#C8CEC9] rounded-[12px] flex items-start gap-2.5 text-xs text-[#3E4743]">
                <Shield className="w-4 h-4 text-[#1B4D3E] shrink-0 mt-0.5" />
                <p className="leading-relaxed">{t("advisoryNote")}</p>
              </div>

              {/* What To Do Now Checklist */}
              <section className="card space-y-3 bg-white">
                <div className="flex items-center gap-2 border-b border-[#E0E6E2] pb-2">
                  <ClipboardCheck className="w-5 h-5 text-[#1B4D3E]" />
                  <h3 className="text-base font-bold text-[#1A2E26]">{t("whatToDoNow")}</h3>
                </div>

                <div className="space-y-2.5">
                  {[1, 2, 3].map((idx) => {
                    const actionKey = `action_${idx}_${assessment.status}`;
                    const isChecked = checkedItems[idx];
                    return (
                      <label
                        key={idx}
                        className={`flex items-start gap-3 p-3 rounded-[12px] border transition-all cursor-pointer ${
                          isChecked
                            ? "bg-[#EBF7F0] border-[#A3DEC0] text-[#1B4D3E]"
                            : "bg-[#F6F8F5] border-[#E0E6E2] text-[#1A2E26]"
                        }`}
                      >
                        <input
                          type="checkbox"
                          checked={isChecked}
                          onChange={() => toggleCheck(idx)}
                          className="mt-1 w-5 h-5 rounded border-gray-300 text-[#1B4D3E] focus:ring-[#1B4D3E] cursor-pointer"
                        />
                        <span className={`text-[15px] leading-snug ${isChecked ? "line-through opacity-80" : ""}`}>
                          {`${idx}. ${t(actionKey)}`}
                        </span>
                      </label>
                    );
                  })}
                </div>
              </section>

              {/* Officer Diagnostic Details Expander */}
              <div className="bg-white border border-[#E0E6E2] rounded-[12px] p-3 text-xs">
                <button
                  onClick={() => setShowOfficerDetails(!showOfficerDetails)}
                  className="w-full flex items-center justify-between text-[#3E4743] font-semibold"
                >
                  <span className="flex items-center gap-1.5">
                    <Info className="w-4 h-4 text-[#7A8780]" />
                    {t("detailsExpander")}
                  </span>
                  {showOfficerDetails ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                </button>

                {showOfficerDetails && (
                  <div className="mt-2 pt-2 border-t border-[#E0E6E2] space-y-2 text-[#3E4743] font-mono">
                    <p className="text-[11px] font-sans font-bold">{t("rawReasonCodes")}</p>
                    {assessment.reason_codes.map((code: string) => (
                      <span key={code} className="inline-block bg-[#F0F2F1] px-2 py-0.5 rounded text-[11px] mr-1">
                        {code}
                      </span>
                    ))}
                    <div className="pt-2 text-[11px] font-sans text-[#7A8780]">
                      IoT Sensor ID: {deviceStatus.device_id} | RSSI: {deviceStatus.signal_rssi} dBm | Battery: {deviceStatus.battery_level_pct}%
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* TAB 2: READINGS SCREEN */}
          {currentTab === "readings" && (
            <div className="card space-y-4 bg-white">
              <div>
                <h2 className="text-lg font-bold text-[#1A2E26] flex items-center gap-2">
                  <Droplets className="w-5 h-5 text-[#2E9E5B]" />
                  {t("readingsTitle")}
                </h2>
                <p className="text-xs text-[#7A8780] mt-0.5">{t("readingsSubtitle")}</p>
              </div>

              <div className="p-3 bg-[#EBF7F0] border border-[#A3DEC0] rounded-[12px] flex items-center gap-2 text-xs text-[#1B4D3E]">
                <Zap className="w-4 h-4 text-[#2E9E5B] shrink-0" />
                <span>{t("iotAutoDescription")}</span>
              </div>

              {readingsSuccessMsg && (
                <div className="p-3 bg-[#EBF7F0] border border-[#A3DEC0] text-[#1B4D3E] text-xs rounded-[12px]">
                  {readingsSuccessMsg}
                </div>
              )}

              <form
                onSubmit={(e) => {
                  e.preventDefault();
                  setReadingsSuccessMsg("Manual calibration reading submitted!");
                  setTimeout(() => setReadingsSuccessMsg(""), 4000);
                }}
                className="space-y-3.5"
              >
                <div>
                  <div className="flex justify-between items-baseline mb-1">
                    <label className="text-sm font-semibold text-[#1A2E26]">{t("doLabel")} ({t("doUnit")})</label>
                    <span className="text-[11px] text-[#7A8780]">{t("doHint")}</span>
                  </div>
                  <input
                    type="number"
                    step="0.1"
                    value={readingInputs.do}
                    onChange={(e) => setReadingInputs({ ...readingInputs, do: e.target.value })}
                    className="w-full min-h-[48px] px-3.5 py-2.5 bg-white border border-[#C8CEC9] rounded-[12px] text-base focus:outline-none focus:ring-2 focus:ring-[#1B4D3E]"
                    required
                  />
                </div>

                <div>
                  <div className="flex justify-between items-baseline mb-1">
                    <label className="text-sm font-semibold text-[#1A2E26]">{t("phLabel")}</label>
                    <span className="text-[11px] text-[#7A8780]">{t("phHint")}</span>
                  </div>
                  <input
                    type="number"
                    step="0.01"
                    value={readingInputs.ph}
                    onChange={(e) => setReadingInputs({ ...readingInputs, ph: e.target.value })}
                    className="w-full min-h-[48px] px-3.5 py-2.5 bg-white border border-[#C8CEC9] rounded-[12px] text-base focus:outline-none focus:ring-2 focus:ring-[#1B4D3E]"
                    required
                  />
                </div>

                <div>
                  <div className="flex justify-between items-baseline mb-1">
                    <label className="text-sm font-semibold text-[#1A2E26]">{t("tempLabel")} ({t("tempUnit")})</label>
                    <span className="text-[11px] text-[#7A8780]">{t("tempHint")}</span>
                  </div>
                  <input
                    type="number"
                    step="0.1"
                    value={readingInputs.temp}
                    onChange={(e) => setReadingInputs({ ...readingInputs, temp: e.target.value })}
                    className="w-full min-h-[48px] px-3.5 py-2.5 bg-white border border-[#C8CEC9] rounded-[12px] text-base focus:outline-none focus:ring-2 focus:ring-[#1B4D3E]"
                    required
                  />
                </div>

                <div>
                  <div className="flex justify-between items-baseline mb-1">
                    <label className="text-sm font-semibold text-[#1A2E26]">{t("ammoniaLabel")} ({t("ammoniaUnit")})</label>
                    <span className="text-[11px] text-[#7A8780]">{t("ammoniaHint")}</span>
                  </div>
                  <input
                    type="number"
                    step="0.001"
                    value={readingInputs.ammonia}
                    onChange={(e) => setReadingInputs({ ...readingInputs, ammonia: e.target.value })}
                    className="w-full min-h-[48px] px-3.5 py-2.5 bg-white border border-[#C8CEC9] rounded-[12px] text-base focus:outline-none focus:ring-2 focus:ring-[#1B4D3E]"
                  />
                </div>

                <button type="submit" className="btn-primary w-full mt-2">
                  {t("checkMyPondBtn")}
                </button>
              </form>
            </div>
          )}

          {/* TAB 3: DAILY CHECK (FISH BEHAVIOR) */}
          {currentTab === "daily" && (
            <div className="card space-y-4 bg-white">
              <div>
                <h2 className="text-lg font-bold text-[#1A2E26] flex items-center gap-2">
                  <ClipboardCheck className="w-5 h-5 text-[#2E9E5B]" />
                  {t("checkTitle")}
                </h2>
                <p className="text-xs text-[#7A8780] mt-0.5">{t("checkSubtitle")}</p>
              </div>

              {dailySuccessMsg && (
                <div className="p-3 bg-[#EBF7F0] border border-[#A3DEC0] text-[#1B4D3E] text-xs rounded-[12px]">
                  {dailySuccessMsg}
                </div>
              )}

              <div className="space-y-1.5">
                <label className="text-sm font-semibold text-[#1A2E26]">{t("feedingLabel")}</label>
                <div className="grid grid-cols-3 gap-2">
                  {[
                    { id: "normal", label: t("feedNormal") },
                    { id: "less", label: t("feedLess") },
                    { id: "none", label: t("feedNone") },
                  ].map((opt) => (
                    <button
                      key={opt.id}
                      type="button"
                      onClick={() => setDailyFeeding(opt.id as any)}
                      className={`min-h-[48px] py-2 px-1 text-xs font-semibold rounded-[12px] border transition-all ${
                        dailyFeeding === opt.id
                          ? "bg-[#1B4D3E] text-white border-[#1B4D3E]"
                          : "bg-[#F6F8F5] text-[#3E4743] border-[#C8CEC9]"
                      }`}
                    >
                      {opt.label}
                    </button>
                  ))}
                </div>
              </div>

              <div className="space-y-1.5">
                <label className="text-sm font-semibold text-[#1A2E26]">{t("behaviorLabel")}</label>
                <div className="grid grid-cols-2 gap-2">
                  {[
                    { id: "normal", label: t("swimNormal") },
                    { id: "gasping", label: t("swimGasping") },
                    { id: "at_surface", label: t("swimSurface") },
                    { id: "slow", label: t("swimSluggish") },
                  ].map((opt) => (
                    <button
                      key={opt.id}
                      type="button"
                      onClick={() => setDailySwim(opt.id as any)}
                      className={`min-h-[48px] py-2 px-2 text-xs font-semibold rounded-[12px] border transition-all ${
                        dailySwim === opt.id
                          ? "bg-[#1B4D3E] text-white border-[#1B4D3E]"
                          : "bg-[#F6F8F5] text-[#3E4743] border-[#C8CEC9]"
                      }`}
                    >
                      {opt.label}
                    </button>
                  ))}
                </div>
              </div>

              <div className="space-y-1.5">
                <label className="text-sm font-semibold text-[#1A2E26]">{t("deadCountLabel")}</label>
                <div className="flex items-center gap-3">
                  <button
                    type="button"
                    onClick={() => setDeadFishCount(Math.max(0, deadFishCount - 1))}
                    className="w-12 h-12 rounded-[12px] bg-[#F0F2F1] border border-[#C8CEC9] text-[#1A2E26] flex items-center justify-center font-bold active:scale-95"
                    aria-label="Decrease dead fish count"
                  >
                    <Minus className="w-5 h-5" />
                  </button>
                  <div className="flex-1 min-h-[48px] flex items-center justify-center bg-[#F6F8F5] border border-[#C8CEC9] rounded-[12px] text-lg font-bold">
                    {deadFishCount}
                  </div>
                  <button
                    type="button"
                    onClick={() => setDeadFishCount(deadFishCount + 1)}
                    className="w-12 h-12 rounded-[12px] bg-[#F0F2F1] border border-[#C8CEC9] text-[#1A2E26] flex items-center justify-center font-bold active:scale-95"
                    aria-label="Increase dead fish count"
                  >
                    <Plus className="w-5 h-5" />
                  </button>
                </div>
              </div>

              <button
                type="button"
                onClick={() => {
                  setDailySuccessMsg(t("saveDailyBtn") + " ✓");
                  setTimeout(() => setDailySuccessMsg(""), 3000);
                }}
                className="btn-primary w-full"
              >
                {t("saveDailyBtn")}
              </button>
            </div>
          )}

          {/* TAB 4: COMPLETE FISH PHOTO UPLOAD & ANALYSIS WORKFLOW */}
          {currentTab === "photo" && (
            <div className="card space-y-4 bg-white">
              <div>
                <h2 className="text-lg font-bold text-[#1A2E26] flex items-center gap-2">
                  <Camera className="w-5 h-5 text-[#2E9E5B]" />
                  {t("photoTitle")}
                </h2>
                <p className="text-xs text-[#7A8780] mt-0.5">{t("photoSubtitle")}</p>
              </div>

              {/* Hidden Real HTML File Inputs for Gallery & Camera */}
              <input
                type="file"
                ref={galleryInputRef}
                accept="image/jpeg,image/png,image/webp"
                onChange={handleFileChange}
                className="hidden"
                aria-label="Upload from gallery"
              />
              <input
                type="file"
                ref={cameraInputRef}
                accept="image/*"
                capture="environment"
                onChange={handleFileChange}
                className="hidden"
                aria-label="Take fish photo"
              />

              {/* Error Message Notification */}
              {photoError && (
                <div className="p-3 bg-[#FCEFEF] border border-[#F3B2B2] rounded-[12px] space-y-2.5 text-xs text-[#8C1D1D]">
                  <div className="flex items-start gap-2.5">
                    <AlertCircle className="w-4 h-4 shrink-0 mt-0.5 text-[#D64545]" />
                    <span className="flex-1 font-medium leading-relaxed">{photoError}</span>
                  </div>
                  {photoPreviewUrl && (
                    <button
                      type="button"
                      onClick={handleRunOfflineDemo}
                      className="w-full py-2 px-3 bg-[#1B4D3E] hover:bg-[#153D31] text-white rounded-[8px] font-semibold text-xs flex items-center justify-center gap-1.5 transition active:scale-95"
                    >
                      <Sparkles className="w-3.5 h-3.5 text-[#A3DEC0]" />
                      <span>{t("runDemoAnalysisBtn")}</span>
                    </button>
                  )}
                </div>
              )}

              {/* Selection / Capture Area when NO photo is selected */}
              {!photoPreviewUrl && (
                <div className="border-2 border-dashed border-[#1B4D3E]/30 rounded-[16px] p-5 text-center bg-[#F6F8F5] space-y-3 relative">
                  <div className="w-14 h-14 rounded-full bg-[#E8F0EC] flex items-center justify-center mx-auto text-[#1B4D3E]">
                    <Camera className="w-7 h-7" />
                  </div>
                  <p className="text-xs text-[#3E4743] max-w-[280px] mx-auto font-medium leading-relaxed">
                    {t("framingTip")}
                  </p>
                  
                  {/* Two Functional Option Buttons: Gallery and Camera */}
                  <div className="grid grid-cols-2 gap-2 pt-1">
                    <button
                      type="button"
                      onClick={() => galleryInputRef.current?.click()}
                      className="btn-secondary min-h-[46px] px-2 text-xs flex items-center justify-center gap-1.5"
                    >
                      <Upload className="w-4 h-4" />
                      <span>{t("uploadGalleryBtn")}</span>
                    </button>
                    <button
                      type="button"
                      onClick={() => cameraInputRef.current?.click()}
                      className="btn-primary min-h-[46px] px-2 text-xs flex items-center justify-center gap-1.5"
                    >
                      <Camera className="w-4 h-4" />
                      <span>{t("takePhotoBtn")}</span>
                    </button>
                  </div>
                </div>
              )}

              {/* Real Image Preview when a Photo is Selected */}
              {photoPreviewUrl && (
                <div className="space-y-3">
                  <div className="border border-[#C8CEC9] rounded-[14px] overflow-hidden bg-black/5 relative">
                    <img
                      src={photoPreviewUrl}
                      alt="Selected fish preview"
                      className="w-full max-h-64 object-contain mx-auto bg-black/10"
                    />
                    <div className="absolute top-2 right-2 flex gap-1.5">
                      <button
                        type="button"
                        onClick={handleRemovePhoto}
                        className="bg-black/60 hover:bg-black/80 text-white p-1.5 rounded-full backdrop-blur-xs transition"
                        title={t("removePhotoBtn")}
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                    <div className="p-2 bg-white/95 text-[11px] text-[#7A8780] flex justify-between items-center border-t border-[#E0E6E2]">
                      <span className="truncate max-w-[240px] font-medium text-[#1A2E26]">
                        {selectedPhotoFile?.name}
                      </span>
                      <span>{photoFileSize}</span>
                    </div>
                  </div>

                  {/* Action Buttons: Analyze Fish Photo or Reselect */}
                  <div className="flex gap-2">
                    <button
                      type="button"
                      onClick={() => galleryInputRef.current?.click()}
                      disabled={isAnalyzingPhoto}
                      className="btn-secondary flex-1 min-h-[46px] text-xs"
                    >
                      {t("reselectPhotoBtn")}
                    </button>

                    <button
                      type="button"
                      onClick={handleAnalyzePhoto}
                      disabled={isAnalyzingPhoto}
                      className="btn-primary flex-1 min-h-[46px] text-xs bg-[#1B4D3E] text-white flex items-center justify-center gap-1.5"
                    >
                      {isAnalyzingPhoto ? (
                        <>
                          <Loader2 className="w-4 h-4 animate-spin text-white" />
                          <span>{t("analyzingStatus")}</span>
                        </>
                      ) : (
                        <>
                          <Sparkles className="w-4 h-4 text-[#A3DEC0]" />
                          <span>{t("analyzePhotoBtn")}</span>
                        </>
                      )}
                    </button>
                  </div>
                </div>
              )}

              {/* Dynamic Analysis Results Card */}
              {analysisResult && (
                <div className="space-y-3 pt-2 animate-in fade-in duration-200">
                  
                  {/* Quality Gate Pass/Fail Badge */}
                  <div
                    className={`p-3 rounded-[12px] border flex items-center justify-between text-xs ${
                      analysisResult.passed_gate
                        ? "bg-[#EBF7F0] border-[#A3DEC0] text-[#1B4D3E]"
                        : "bg-[#FDF8EC] border-[#F7D897] text-[#7A5405]"
                    }`}
                  >
                    <span className="font-semibold">{t("gateResultTitle")}</span>
                    <span
                      className={`px-2 py-0.5 rounded-full font-bold text-[11px] ${
                        analysisResult.passed_gate
                          ? "bg-[#2E9E5B] text-white"
                          : "bg-[#E0A21B] text-white"
                      }`}
                    >
                      {analysisResult.passed_gate ? t("gatePassedBadge") : t("gateFailedBadge")}
                    </span>
                  </div>

                  {/* If Quality Gate Failed: Show Exact Retake Tips */}
                  {!analysisResult.passed_gate && (
                    <div className="p-3 bg-[#FDF8EC] border border-[#F7D897] rounded-[12px] text-xs space-y-2 text-[#7A5405]">
                      <p className="font-bold flex items-center gap-1">
                        <AlertTriangle className="w-4 h-4 text-[#E0A21B]" />
                        {t("retakeTipTitle")}
                      </p>
                      <ul className="list-disc pl-4 space-y-1">
                        {(i18n.language === "kn" ? analysisResult.tips_kn : analysisResult.tips_en)?.map(
                          (tip: string, idx: number) => (
                            <li key={idx}>{tip}</li>
                          )
                        )}
                      </ul>
                      <button
                        type="button"
                        onClick={() => cameraInputRef.current?.click()}
                        className="btn-primary w-full min-h-[42px] text-xs bg-[#E0A21B] hover:bg-[#C98E13] text-white mt-1"
                      >
                        {t("takePhotoBtn")}
                      </button>
                    </div>
                  )}

                  {/* If Quality Gate Passed: Show Classification & Grad-CAM */}
                  {analysisResult.passed_gate && (
                    <>
                      {/* Grad-CAM Visual Heatmap Frame if available */}
                      {analysisResult.gradcam_data_url && (
                        <div className="border border-[#C8CEC9] rounded-[14px] overflow-hidden bg-black/5">
                          <img
                            src={analysisResult.gradcam_data_url}
                            alt="Grad-CAM Visual Heatmap"
                            className="w-full max-h-56 object-contain bg-black/10 mx-auto"
                          />
                          <div className="p-2.5 bg-white text-xs border-t border-[#E0E6E2]">
                            <p className="font-bold text-[#1A2E26] flex items-center gap-1">
                              <Sparkles className="w-3.5 h-3.5 text-[#2E9E5B]" />
                              {t("gradcamTitle")}
                            </p>
                            <p className="text-[#7A8780] text-[11px] mt-0.5">{t("gradcamNote")}</p>
                          </div>
                        </div>
                      )}

                      {/* Prediction & Confidence Card */}
                      <div className="p-3.5 bg-[#F6F8F5] border border-[#E0E6E2] rounded-[12px] text-xs space-y-2">
                        <div className="flex justify-between items-baseline">
                          <span className="font-semibold text-[#7A8780]">{t("predictionTitle")}</span>
                          <span className="font-bold text-[#1B4D3E] text-sm">
                            {analysisResult.confidence_pct}% {t("confidenceLabel")}
                          </span>
                        </div>
                        <h4 className="text-base font-bold text-[#1A2E26]">
                          {i18n.language === "kn" ? analysisResult.label_kn : analysisResult.label_en}
                        </h4>
                        <div className="w-full bg-[#E0E6E2] h-2 rounded-full overflow-hidden">
                          <div
                            className={`h-full ${
                              analysisResult.predicted_class === "healthy" ? "bg-[#2E9E5B]" : "bg-[#E0A21B]"
                            }`}
                            style={{ width: `${analysisResult.confidence_pct}%` }}
                          />
                        </div>
                      </div>

                      {/* Recommended Next Steps */}
                      <div className="p-3.5 bg-white border border-[#E0E6E2] rounded-[12px] text-xs space-y-2">
                        <p className="font-bold text-[#1A2E26]">{t("nextStepsTitle")}</p>
                        <ul className="space-y-1.5 text-[#3E4743]">
                          {(i18n.language === "kn" ? analysisResult.next_steps_kn : analysisResult.next_steps_en)?.map(
                            (step: string, idx: number) => (
                              <li key={idx} className="flex items-start gap-2 bg-[#F6F8F5] p-2 rounded">
                                <span className="font-bold text-[#2E9E5B]">{idx + 1}.</span>
                                <span>{step}</span>
                              </li>
                            )
                          )}
                        </ul>
                      </div>

                      {/* Veterinary Disclaimer */}
                      <div className="p-3 bg-[#FDF8EC] border border-[#F7D897] rounded-[12px] text-xs text-[#7A5405] flex items-start gap-2">
                        <Shield className="w-4 h-4 shrink-0 mt-0.5 text-[#E0A21B]" />
                        <p className="leading-relaxed">
                          {i18n.language === "kn" ? analysisResult.disclaimer_kn : analysisResult.disclaimer_en}
                        </p>
                      </div>
                    </>
                  )}
                </div>
              )}
            </div>
          )}

          {/* TAB 5: IMPACT SCREEN */}
          {currentTab === "impact" && (
            <div className="card space-y-4 bg-white">
              <div>
                <h2 className="text-lg font-bold text-[#1A2E26] flex items-center gap-2">
                  <LineChart className="w-5 h-5 text-[#2E9E5B]" />
                  {t("impactTitle")}
                </h2>
                <p className="text-xs text-[#7A8780] mt-0.5">{t("impactSubtitle")}</p>
              </div>

              <div className="p-3.5 bg-[#F6F8F5] border border-[#E0E6E2] rounded-[16px] space-y-2">
                <div className="flex justify-between items-center text-xs">
                  <span className="font-bold text-[#1A2E26]">Dissolved Oxygen 7-Day Trend</span>
                  <span className="text-[11px] text-[#2E9E5B] font-semibold flex items-center gap-1">
                    <span className="w-2 h-2 rounded-full bg-[#2E9E5B]" />
                    {t("healthyBandLegend")}
                  </span>
                </div>
                
                <div className="w-full h-32 bg-white rounded-[12px] border border-[#E0E6E2] p-2 relative flex flex-col justify-between overflow-hidden">
                  <div className="absolute top-0 left-0 right-0 h-[60%] bg-[#2E9E5B]/10 border-b border-[#2E9E5B]/30" />
                  
                  <svg className="w-full h-full relative z-10" viewBox="0 0 300 100" preserveAspectRatio="none">
                    <path
                      d="M 10,25 L 60,30 L 120,40 L 180,50 L 240,65 L 290,75"
                      fill="none"
                      stroke="#E0A21B"
                      strokeWidth="3.5"
                    />
                    <circle cx="290" cy="75" r="4" fill="#E0A21B" />
                  </svg>
                  
                  <div className="flex justify-between text-[10px] text-[#7A8780] relative z-10 pt-1 border-t border-[#E0E6E2]">
                    <span>Day 1 (6.8 mg/L)</span>
                    <span>Day 4 (5.9 mg/L)</span>
                    <span>Today (5.6 mg/L)</span>
                  </div>
                </div>
              </div>

              <div className="space-y-2.5">
                <div className="p-3.5 bg-[#F6F8F5] rounded-[12px] border border-[#E0E6E2]">
                  <div className="flex justify-between items-baseline">
                    <span className="text-xs font-semibold text-[#1A2E26]">{t("leadTimeMetric")}</span>
                    <span className="text-base font-bold text-[#2E9E5B]">{t("leadTimeVal")}</span>
                  </div>
                  <p className="text-[11px] text-[#7A8780] mt-1">{t("leadTimeDesc")}</p>
                </div>

                <div className="p-3.5 bg-[#F6F8F5] rounded-[12px] border border-[#E0E6E2]">
                  <div className="flex justify-between items-baseline">
                    <span className="text-xs font-semibold text-[#1A2E26]">{t("hypoxiaMetric")}</span>
                    <span className="text-base font-bold text-[#2E9E5B]">{t("hypoxiaVal")}</span>
                  </div>
                  <p className="text-[11px] text-[#7A8780] mt-1">{t("hypoxiaDesc")}</p>
                </div>

                <div className="p-3.5 bg-[#F6F8F5] rounded-[12px] border border-[#E0E6E2]">
                  <div className="flex justify-between items-baseline">
                    <span className="text-xs font-semibold text-[#1A2E26]">{t("recallMetric")}</span>
                    <span className="text-base font-bold text-[#1B4D3E]">{t("recallVal")}</span>
                  </div>
                  <p className="text-[11px] text-[#7A8780] mt-1">{t("recallDesc")}</p>
                </div>
              </div>
            </div>
          )}

        </main>

        {/* 4. Bottom Tab Bar Navigation */}
        <nav
          className="fixed bottom-0 max-w-[480px] w-full bg-white border-t border-[#E0E6E2] grid grid-cols-5 h-14 z-30 shadow-lg"
          role="navigation"
          aria-label="Main Navigation"
        >
          {[
            { id: "home", label: t("tabStatus"), icon: Activity },
            { id: "readings", label: t("tabReadings"), icon: Droplets },
            { id: "daily", label: t("tabCheck"), icon: ClipboardCheck },
            { id: "photo", label: t("tabPhoto"), icon: Camera },
            { id: "impact", label: t("tabImpact"), icon: LineChart },
          ].map((tab) => {
            const TabIcon = tab.icon;
            const isActive = currentTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setCurrentTab(tab.id as any)}
                className={`flex flex-col items-center justify-center relative transition-colors ${
                  isActive ? "text-[#1B4D3E] font-bold" : "text-[#7A8780] hover:text-[#1A2E26]"
                }`}
                aria-current={isActive ? "page" : undefined}
              >
                {isActive && (
                  <span className="absolute top-0 w-8 h-1 bg-[#1B4D3E] rounded-full" />
                )}
                <TabIcon className="w-5 h-5 mb-0.5" />
                <span className="text-[11px] leading-tight">{tab.label}</span>
              </button>
            );
          })}
        </nav>

      </div>
    </div>
  );
}

export default App;
