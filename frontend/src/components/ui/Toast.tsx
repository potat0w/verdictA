"use client";

import { useEffect, useState } from "react";

interface Toast {
  id: string;
  message: string;
  type: "success" | "error";
}

let toastId = 0;

export function showToast(message: string, type: "success" | "error" = "success") {
  const id = `toast-${toastId++}`;
  const event = new CustomEvent("showToast", { detail: { id, message, type } });
  window.dispatchEvent(event);
}

export default function ToastProvider() {
  const [toasts, setToasts] = useState<Toast[]>([]);

  useEffect(() => {
    const handleToast = (e: CustomEvent) => {
      const toast = e.detail as Toast;
      setToasts(prev => [...prev, toast]);
      setTimeout(() => {
        setToasts(prev => prev.filter(t => t.id !== toast.id));
      }, 3000);
    };

    window.addEventListener("showToast", handleToast as EventListener);
    return () => window.removeEventListener("showToast", handleToast as EventListener);
  }, []);

  return (
    <div className="fixed top-4 right-4 z-50 space-y-2">
      {toasts.map(toast => (
        <div
          key={toast.id}
          className={`px-6 py-4 rounded-xl shadow-2xl text-white font-medium transition-all transform animate-in slide-in-from-right-2 backdrop-blur-sm ${
            toast.type === "success" 
              ? "bg-gradient-to-r from-green-600 to-green-700 border border-green-500/30" 
              : "bg-gradient-to-r from-red-600 to-red-700 border border-red-500/30"
          }`}
        >
          <div className="flex items-center gap-3">
            <div className={`w-2 h-2 rounded-full ${
              toast.type === "success" ? "bg-green-300" : "bg-red-300"
            }`} />
            {toast.message}
          </div>
        </div>
      ))}
    </div>
  );
}
