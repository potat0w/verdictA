"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import Button from "@/components/ui/Button";
import { cn, tokens } from "@/lib/theme";
import { login, saveToken, verifyToken } from "@/lib/api";
import { showToast } from "@/components/ui/Toast";

export default function LoginPage() {
  const router = useRouter();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError(null);
    try {
      const auth = await login(username.trim(), password);
      saveToken(auth.access_token);
      // Optional: verify token; ignore failures for now
      try { await verifyToken(auth.access_token); } catch {}
      router.push("/profile");
    } catch (err) {
      let errorMessage = "Login failed";
      
      if (err instanceof Error) {
        try {
          const errorObj = JSON.parse(err.message);
          if (errorObj && errorObj.detail) {
            errorMessage = errorObj.detail;
          } else {
            errorMessage = err.message;
          }
        } catch {
          errorMessage = err.message;
        }
      }
      
      showToast(errorMessage, "error");
      setError(null);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className={cn(tokens.bg.gradient, "min-h-screen flex items-center justify-center p-4")}> 
      <div className="w-full max-w-md p-8 rounded-2xl bg-[rgba(15,28,36,0.9)] backdrop-blur-md border border-[#DCBC8C]/30 shadow-xl"> 
        <h1 className={cn(tokens.heading, "text-3xl mb-2 text-center")}>
          Welcome back
        </h1>
        <p className="text-white/70 text-center mb-8">Log in to your VerdictAI account</p>

        {error && (
          <div className="mb-4 text-sm text-red-400">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block mb-2 font-semibold">Username</label>
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="w-full px-4 py-3 rounded-lg bg-[#0e1a22]/80 text-white placeholder-white/50 focus:outline-none focus:ring-2 focus:ring-[var(--primary-gold)]"
              placeholder="your-username"
              required
            />
          </div>
          <div>
            <label className="block mb-2 font-semibold">Password</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full px-4 py-3 rounded-lg bg-[#0e1a22]/80 text-white placeholder-white/50 focus:outline-none focus:ring-2 focus:ring-[var(--primary-gold)]"
              placeholder="••••••••"
              required
            />
          </div>
          <Button 
            type="submit" 
            disabled={isLoading} 
            className="w-full bg-[var(--primary-gold)] text-[#0f1c24] hover:brightness-110 px-5 py-2.5 rounded-lg font-semibold transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-[var(--primary-gold)] border-none"
          >
            {isLoading ? "Signing in..." : "Sign in"}
          </Button>
        </form>

        <p className="text-center text-white/70 mt-6">
          Don&apos;t have an account? {" "}
          <Link href="/signup" className="text-[var(--primary-gold)] hover:underline">Sign up</Link>
        </p>
      </div>
    </div>
  );
} 